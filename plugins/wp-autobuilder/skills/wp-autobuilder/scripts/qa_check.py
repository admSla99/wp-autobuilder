#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_check.py — predpublikačná QA kontrola naplnenej stránky.

Vstup:
  --structure  JSON z get-page-structure (po naplnení)
  --blueprint  (voliteľné) hp_slot_blueprint.json — pre per-slot kontroly
  --slotmap    (voliteľné) výstup resolve_slots.py — pre per-slot kontroly
Výstup: report + návratový kód (0 = OK, 1 = našli sa problémy).

Globálne kontroly (vždy): žiadny zostatkový placeholder (Lorem ipsum, 'Služba 1/2/3').
Per-slot (ak je blueprint+slotmap): štatistiky začínajú číslom, CTA <= 21 znakov, sloty nie sú prázdne.
"""
import sys, re, json, argparse

PLACEHOLDERS = [r"lorem ipsum", r"dolor sit amet",
                r"\bslužba\s*[123456]\b", r"\bsluzba\s*[123456]\b",
                r"popis služby", r"popis sluzby", r"cenník nadpis", r"cennik nadpis",
                r"\bitem\s+(one|two|three|four|five|six)\b",
                r"\bobrázok\s*[1-9]\b", r"\bobrazok\s*[1-9]\b",
                r"\[dopl"]  # [DOPLNIŤ: …] = nevyplnený fakt (produktové copy) → stránka ostane draft

# Mäkké varovania: zvyšky z master šablóny (agentúra/demo). Skill ich zámerne nemení,
# ale operátor ich má vyčistiť v globálnej téme/hlavičke/päte. Nezhadzujú QA (warn, nie error).
AGENCY_LEFTOVERS = [
    (r"netovapomoc", "agentúrny názov/e-mail/odkaz"),
    (r"nazovklientovejdomeny", "placeholder domény klienta"),
    (r"hor[úu]ce strely", "agentúrny newsletter text"),
    (r"default-logo", "default logo placeholder"),
]

# Kľúče v settings_summary, ktoré nie sú viditeľný text (preskoč pri skenovaní).
SKIP_KEY_SUBSTR = ("url", "link", "href", "src", "image", "icon", "css", "class", "color", "background")


def load_structure(obj):
    return obj["structure"] if isinstance(obj, dict) and "structure" in obj else obj


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get("elements", []))


def _skip_key(k):
    kl = str(k).lower()
    return kl in ("id", "_id") or any(t in kl for t in SKIP_KEY_SUBSTR)


def text_of(node):
    """Viditeľný text uzla = všetky skalárne reťazce zo settings_summary okrem url/
    technických kľúčov. Nezostupuje do zoznamov (repeater) ani vnorených objektov (link)."""
    s = node.get("settings_summary", {})
    if not isinstance(s, dict):
        return ""
    out = []
    for k, v in s.items():
        if not isinstance(v, str) or _skip_key(k):
            continue
        vs = v.strip()
        if not vs or vs.startswith("http") or vs.startswith("#") or "/wp-content" in vs:
            continue
        out.append(v)
    return " ".join(out)


def get_node(struct, path):
    nodes, node = struct, None
    for idx in path:
        if not isinstance(nodes, list) or idx >= len(nodes):
            return None
        node = nodes[idx]
        nodes = node.get("elements", [])
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--blueprint")
    ap.add_argument("--slotmap")
    args = ap.parse_args()
    struct = load_structure(json.load(open(args.structure, encoding="utf-8")))
    errors, warns, ok = [], [], []

    # global placeholder scan (chyba — nesmie ostať)
    for node in walk(struct):
        t = text_of(node).lower()
        for pat in PLACEHOLDERS:
            if re.search(pat, t):
                errors.append(f"placeholder '{pat}' v {node.get('id')}: {text_of(node)[:60]}")

    # globálne zvyšky šablóny (varovanie — vyčistiť v master téme), každý druh raz
    seen_leftover = set()
    for node in walk(struct):
        t = text_of(node).lower()
        for pat, why in AGENCY_LEFTOVERS:
            if pat not in seen_leftover and re.search(pat, t):
                seen_leftover.add(pat)
                warns.append(f"globálny zvyšok šablóny ({why}) — vyčisti v master téme/hlavičke/päte")

    # per-slot checks
    if args.blueprint:
        blueprint = json.load(open(args.blueprint, encoding="utf-8"))
        bp = {s["slot_id"]: s for s in blueprint["slots"]}
        for slot in blueprint["slots"]:
            node = get_node(struct, slot["path"])
            if node is None:
                warns.append(f"{slot['slot_id']}: cesta nenájdená")
                continue
            if slot.get("repeater") or slot["widget"] in ("section", "container", "column"):
                continue  # repeater/štruktúrne sloty nemajú textovú hodnotu v summary
            summary = node.get("settings_summary", {})
            if slot["setting"] in summary:
                val = str(summary[slot["setting"]]).strip()
            elif slot["setting"] in ("title", "editor", "text"):
                val = text_of(node).strip()
            else:
                continue  # setting nie je v summary (napr. ending_number live) — nevieme overiť
            if not val:
                if not slot.get("optional"):
                    warns.append(f"{slot['slot_id']}: prázdny slot")
                continue
            if slot.get("rule") == "must_be_number" and not re.match(r"^\s*[\d]", val):
                errors.append(f"{slot['slot_id']}: štatistika nezačína číslom: '{val[:30]}'")
            if slot.get("rule") == "cta_max_21":
                clean = re.sub(r"<[^>]+>", "", val)
                if len(clean) > 21:
                    errors.append(f"{slot['slot_id']}: CTA {len(clean)} znakov (>21): '{clean}'")
            ok.append(slot["slot_id"])

    print("=" * 56)
    print("QA CHECK")
    print(f"OK slotov: {len(ok)} | varovaní: {len(warns)} | chýb: {len(errors)}")
    print("-" * 56)
    for e in errors:
        print("  ❌", e)
    for w in warns:
        print("  ⚠", w)
    if not errors and not warns:
        print("  ✅ Žiadne problémy.")
    print("=" * 56)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
