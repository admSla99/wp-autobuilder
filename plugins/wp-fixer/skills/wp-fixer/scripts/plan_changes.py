#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan_changes.py — z changeset.json vyrobi deterministicky plan behu (plan.json).

Vstup:
  --changeset changeset.json
Vystup: plan.json na stdout / do -o.

Plan zabezpecuje:
  - Zoskupenie zmien podla ciela (per-stranka / kit / global / instance-media).
  - PORADIE: najprv per-stranka (zoskupene po strankach), potom kit (farby) RAZ,
    potom global (footer/popup...) RAZ, media davka sa zbiera cez vsetky stranky (dedup).
  - Detekcia konfliktov: dve zmeny cielia na ten isty prvok (rovnaky slot_id/search_text na tej istej stranke).
  - Vytiahnutie 'needs_input' a chybajucich klientskych vstupov do hlavicky (pre report).

Poradie je dolezite: kit aj global sa robia RAZ na instanciu (nie per stranka), presne ako v autobuilderi.
"""
import sys, json, argparse
from collections import OrderedDict

try:  # Windows konzola (cp1252) inak padne na emoji vo vypise
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE_ORDER = ["hp", "about", "services", "contact", "pricing", "gallery", "products", "unknown"]


def page_key(ch):
    """Kluc stranky pre zoskupenie: primarne page_type, sekundarne page_hint (URL/titul)."""
    pt = ch.get("page_type") or "unknown"
    hint = (ch.get("page_hint") or "").strip()
    return f"{pt}::{hint}" if hint else pt


def selector_key(ch):
    sel = ch.get("target_selector") or {}
    for k in ("slot_id", "search_text"):
        if sel.get(k):
            return f"{k}:{sel[k]}"
    if sel.get("section_index") is not None:
        return f"section_index:{sel['section_index']}"
    return None


def _has_image_subtask(ch):
    """'mixed' zmena, ktora obsahuje aj obrazkovy pod-ukol (napr. zjednotenie sirky fotky)."""
    sel = ch.get("target_selector") or {}
    if sel.get("widget") == "image":
        return True
    blob = f"{ch.get('intent', '')} {(ch.get('desired') or {}).get('rule', '')} {ch.get('location_hint', '')}".lower()
    return any(w in blob for w in ("fotk", "foto", "obraz", "image", "pozadie", "galer"))


def build_plan(cs):
    changes = cs.get("changes", [])
    by_id = {ch["id"]: ch for ch in changes if ch.get("id")}

    pages = OrderedDict()   # page_key -> [ids]  (len scope=page/mixed a page-viazane)
    kit, glob, media, instance_rules, malformed = [], [], [], [], []

    for ch in changes:
        cid = ch.get("id")
        if not cid:
            malformed.append(ch.get("raw", "")[:40])  # bez id — validate to hlasi ako chybu; sem nevstupuje
            continue
        scope = ch.get("scope")
        ctype = ch.get("type")
        if scope == "kit" or ctype == "color":
            kit.append(cid)
        elif scope == "global" or ctype == "global":
            glob.append(cid)
        elif scope == "instance":
            # instance-wide pravidlo (napr. dedup fotiek) — plati pre kazdu stranku
            instance_rules.append(cid)
        else:
            pk = page_key(ch)
            pages.setdefault(pk, []).append(cid)
        # media davka: vsetko co je obrazok/kvalita media (aj ked je scope=page),
        # vratane 'mixed' zmien s obrazkovym pod-ukolom
        if ctype in ("image", "media_quality") or (ctype == "mixed" and _has_image_subtask(ch)):
            media.append(cid)

    # konflikty: rovnaky selektor na tej istej stranke
    conflicts = []
    for pk, ids in pages.items():
        seen = {}
        for cid in ids:
            sk = selector_key(by_id[cid])
            if sk and sk in seen:
                conflicts.append({"page": pk, "selector": sk, "ids": [seen[sk], cid]})
            elif sk:
                seen[sk] = cid

    # deterministicke poradie stranok
    def page_sort(pk):
        pt = pk.split("::", 1)[0]
        return (PAGE_ORDER.index(pt) if pt in PAGE_ORDER else len(PAGE_ORDER), pk)
    ordered_pages = OrderedDict(sorted(pages.items(), key=lambda kv: page_sort(kv[0])))

    # v ramci stranky: priority zmeny prv, potom normal, low; a strukturalne zmeny nakoniec
    prio_rank = {"priority": 0, "normal": 1, "low": 2}
    type_rank = {"structure": 9, "visibility": 8}  # rizikove zmeny stromu az po textoch
    for pk in ordered_pages:
        ordered_pages[pk].sort(key=lambda cid: (
            prio_rank.get(by_id[cid].get("priority", "normal"), 1),
            type_rank.get(by_id[cid].get("type"), 0),
        ))

    order = []
    for pk, ids in ordered_pages.items():
        order.extend(ids)
    # instance pravidla (napr. dedup fotiek) sa aplikuju napriec strankami (Faza 4d) — ale MUSIA byt
    # v poradi, aby ich Faza 4 nevynechala; media-only instance polozky su uz medzi nimi/mediom.
    order += [cid for cid in instance_rules if cid not in order]
    order += kit + glob   # kit a global RAZ, na konci behu

    needs_input = [cid for cid, ch in by_id.items() if ch.get("status") == "needs_input"]
    client_inputs = sorted({inp for ch in changes for inp in (ch.get("client_inputs_needed") or [])})

    return {
        "pages": ordered_pages,
        "kit": kit,
        "global": glob,
        "media": media,
        "instance_rules": instance_rules,
        "order": order,
        "conflicts": conflicts,
        "malformed": malformed,
        "needs_input": needs_input,
        "client_inputs_needed": client_inputs,
        "counts": {
            "total": len(changes),
            "pages": len(ordered_pages),
            "kit": len(kit),
            "global": len(glob),
            "media": len(media),
            "instance_rules": len(instance_rules),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changeset", required=True)
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    cs = json.load(open(args.changeset, encoding="utf-8"))
    plan = build_plan(cs)
    text = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.out:
        json.dump(plan, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(text)
    if plan["conflicts"]:
        print("\n# ⚠ KONFLIKTY (dve zmeny na ten isty prvok — vyries poradim/spojenim):", file=sys.stderr)
        for c in plan["conflicts"]:
            print(f"   {c['page']} · {c['selector']} · {c['ids']}", file=sys.stderr)


if __name__ == "__main__":
    main()
