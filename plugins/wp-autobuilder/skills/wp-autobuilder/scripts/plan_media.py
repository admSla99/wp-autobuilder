#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan_media.py — deterministický plánovač priradenia fotiek do image slotov stránky.

Rieši pripomienky klienta k médiám:
  • DEDUP: žiadna fotka (klientova ani generovaná) sa nepriradí do viac než 1 slotu na stránke.
    (Klientove fotky sa môžu opakovať len v galérii — tú rieši samostatný gallery flow, nie tento skript.)
  • ROZLOŽENIE: klientove vs generované rovnomerne; generované idú do veľkých AJ malých slotov,
    nielen do malých; typy záberov sa striedajú.
  • OSOBY ≥ 50 %: medzi NAPLNENÝMI slotmi je aspoň polovica so záberom osoby (shot_type == "person").
  • source_policy "client_only" (galéria, fotka osoby na Kontakte) sa NIKDY negeneruje.

Vstup:
  --blueprint   <page>_slot_blueprint.json (číta pole image_slots)
  --source      placeholder | client | generated | mix   (= brief.media.source)
  --client-photos  počet dostupných klientových fotiek (int), alebo --client-photos-json '["url1",...]'
Výstup (stdout / -o): zoznam položiek plánu + report pomerov; návratový kód 0 = OK.

Položka plánu:
  { slot_id, mode (generate|client|skip), client_index (int|None), shot_type, size (primary|secondary),
    aspect_ratio, optional, source_policy }

Tento plán potom Claude vo Fáze 4b premení na n8n dávku (generate) resp. upload/enhance (client)
a priradí do slotov — pričom dedup a pomery sú už vyriešené tu.
"""
import sys, json, argparse


def slot_size(slot):
    """Veľkosť slotu: primárny (veľký) ak nie je optional, inak sekundárny (malý)."""
    return "secondary" if slot.get("optional") else "primary"


def build_plan(image_slots, source, client_count):
    """Vráti (plan, report). Deterministické, bez náhodnosti."""
    plan = []
    used_client = 0  # koľko klientových fotiek sme už priradili (dedup = každú raz)

    # poradie: najprv primárne (veľké), potom sekundárne (malé) — aby klientove fotky
    # padli aj do veľkých sekcií a generované sa rozložili do oboch veľkostí.
    order = sorted(range(len(image_slots)),
                   key=lambda i: (0 if slot_size(image_slots[i]) == "primary" else 1, i))

    for i in order:
        s = image_slots[i]
        sid = s["slot_id"]
        size = slot_size(s)
        shot = s.get("shot_type", "detail")
        policy = s.get("source_policy")
        item = {"slot_id": sid, "shot_type": shot, "size": size,
                "aspect_ratio": s.get("aspect_ratio"), "optional": bool(s.get("optional")),
                "source_policy": policy}

        if policy == "client_only":
            # nikdy negenerovať; len klientova fotka, inak skip (placeholder/avatar rieši inde)
            if used_client < client_count:
                item.update(mode="client", client_index=used_client)
                used_client += 1
            else:
                item.update(mode="skip", client_index=None)
            plan.append(item)
            continue

        if source == "placeholder":
            item.update(mode="skip", client_index=None)
        elif source == "generated":
            item.update(mode="generate", client_index=None)
        elif source == "client":
            if used_client < client_count:
                item.update(mode="client", client_index=used_client)
                used_client += 1
            else:
                item.update(mode="skip", client_index=None)  # nemáme viac fotiek, negenerujeme
        elif source == "mix":
            # väčšie (primary) sekcie = klientove fotky; menšie = generované.
            if size == "primary" and used_client < client_count:
                item.update(mode="client", client_index=used_client)
                used_client += 1
            else:
                item.update(mode="generate", client_index=None)
        else:
            item.update(mode="skip", client_index=None)
        plan.append(item)

    # --- vynútenie osoby ≥ 50 % medzi naplnenými slotmi ---
    filled = [p for p in plan if p["mode"] in ("generate", "client")]
    persons = [p for p in filled if p["shot_type"] == "person"]
    need = (len(filled) + 1) // 2  # ceil(50 %)
    promoted = 0
    if filled and len(persons) < need:
        # promuj generované ne-person sloty na person (najprv sekundárne, nech veľké držia kompozíciu)
        for p in sorted(filled, key=lambda p: 0 if p["size"] == "secondary" else 1):
            if len(persons) >= need:
                break
            if p["mode"] == "generate" and p["shot_type"] != "person":
                p["shot_type"] = "person"
                p["_promoted_to_person"] = True
                persons.append(p)
                promoted += 1

    # plán vráť v pôvodnom poradí slotov (nie v poradí spracovania)
    by_id = {p["slot_id"]: p for p in plan}
    plan_ordered = [by_id[s["slot_id"]] for s in image_slots]

    n_filled = len(filled)
    n_person = len([p for p in filled if p["shot_type"] == "person"])
    report = {
        "slots_total": len(image_slots),
        "filled": n_filled,
        "client": len([p for p in filled if p["mode"] == "client"]),
        "generated": len([p for p in filled if p["mode"] == "generate"]),
        "skipped": len([p for p in plan if p["mode"] == "skip"]),
        "person_filled": n_person,
        "person_ratio": round(n_person / n_filled, 2) if n_filled else 0.0,
        "person_promoted": promoted,
        "client_used": used_client,
    }
    return plan_ordered, report


def validate(plan, report, client_count):
    """Tvrdé kontroly: dedup klientových fotiek + pomer osôb. Vráti zoznam chýb."""
    errs = []
    idxs = [p["client_index"] for p in plan if p["mode"] == "client"]
    if len(idxs) != len(set(idxs)):
        errs.append("DEDUP: klientova fotka priradená do viac slotov")
    if any(ix is None or ix >= client_count for ix in idxs):
        errs.append("client_index mimo rozsahu dostupných fotiek")
    if report["filled"] and report["person_ratio"] < 0.5:
        # môže nastať len ak je príliš veľa client_only ne-person slotov a málo generovaných
        errs.append(f"OSOBY < 50 % ({report['person_ratio']}) a nedá sa dovynútiť generovaním")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("--source", default="mix", choices=["placeholder", "client", "generated", "mix"])
    ap.add_argument("--client-photos", type=int, default=0)
    ap.add_argument("--client-photos-json")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    bp = json.load(open(args.blueprint, encoding="utf-8"))
    image_slots = bp.get("image_slots", [])
    client_count = args.client_photos
    if args.client_photos_json:
        client_count = len(json.load(open(args.client_photos_json, encoding="utf-8")))
    plan, report = build_plan(image_slots, args.source, client_count)
    errs = validate(plan, report, client_count)
    out = {"plan": plan, "report": report, "errors": errs}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.out:
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(text)
    print(f"\n# report: {report}", file=sys.stderr)
    for e in errs:
        print("  ❌", e, file=sys.stderr)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
