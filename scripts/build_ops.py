#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_ops.py — z briefu + slotmapy + blueprintu vyrobí operácie pre elementor batch-update.

Vstup:
  --brief      brief.json (štruktúra podľa brief.schema.json)
  --slotmap    výstup z resolve_slots.py (slot_id -> {element_id, widget, setting, ...})
  --blueprint  <page>_slot_blueprint.json (mapuje slot -> brief cesta)
Podporuje: nested setting "link.url", cast:"int" (counter), hide_if_missing (skry sekciu/riadok),
clear_if_missing (vyčisti placeholder), repeater (preskočí — rieši sa read-merge-write).
Výstup: JSON pole operácií [{element_id, settings}] na stdout / do -o.
Toto pole sa pošle do mcp tool: elementor-mcp-batch-update(post_id, operations).
"""
import sys, json, re, argparse


def get_brief_value(brief, expr):
    """Vyhodnotí cestu typu 'content.kpis[0].number'."""
    cur = brief
    for part in expr.split("."):
        m = re.match(r"^(\w+)(\[(\d+)\])?$", part)
        if not m:
            return None
        key, idx = m.group(1), m.group(3)
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
        if idx is not None:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur):
                return None
            cur = cur[i]
    return cur


HIDE_SETTINGS = {"hide_desktop": "hidden", "hide_tablet": "hidden", "hide_mobile": "hidden"}


def is_missing(val):
    """Jednotná detekcia 'chýba obsah': None, prázdny/medzerový reťazec, prázdny list/dict.
    Vďaka tomu auto-skrytie sekcie funguje aj pri list-based prítomnosti (napr. referenčné logá,
    kategórie galérie) — prázdny zoznam = sekcia sa skryje."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


def build(brief, slotmap, blueprint):
    ops, skipped, warns = [], [], []
    bp = {s["slot_id"]: s for s in blueprint["slots"]}
    for slot_id, info in slotmap.items():
        spec = bp.get(slot_id)
        if not spec:
            continue  # image sloty rieši Fáza Médiá
        if not info.get("element_id") or not info.get("ok", True):
            skipped.append((slot_id, "slot nerozriešený / chýba blueprint"))
            continue
        if spec.get("repeater"):
            skipped.append((slot_id, "repeater slot — read-merge-write cez get-element-settings + update-widget (zachovaj _id), NIE batch"))
            continue
        val = get_brief_value(brief, spec.get("brief", ""))
        if isinstance(val, dict):
            val = val.get("name") or val.get("title")  # hide-sloty mieria na objekt
        if is_missing(val):
            if spec.get("hide_if_missing") or spec.get("hide_element_if_missing"):
                ops.append({"element_id": info["element_id"], "settings": dict(HIDE_SETTINGS)})
                continue
            if spec.get("clear_if_missing"):
                ops.append({"element_id": info["element_id"], "settings": {spec["setting"]: ""}})
                continue
            skipped.append((slot_id, f"brief nemá {spec.get('brief')}"))
            continue
        if spec.get("hide_if_missing"):
            continue  # kontajner: hodnota existuje -> sekcia ostáva viditeľná, texty plnia child sloty
        # hide_element_if_missing: hodnota existuje -> leaf slot sa zapíše normálne (napr. mapa)
        val = str(val)
        rule = spec.get("rule")
        if rule == "cta_max_21" and len(val) > 21:
            warns.append(f"{slot_id}: CTA '{val}' má {len(val)} znakov (>21)")
        if rule == "must_be_number" and not re.match(r"^\s*[\d]", val):
            warns.append(f"{slot_id}: štatistika '{val}' nezačína číslom")
        if spec.get("cast") == "int":
            digits = re.sub(r"\D", "", val)
            if digits:
                val = int(digits)
        setting = spec["setting"]
        if setting == "editor":
            sval = str(val)
            settings = {"editor": sval if sval.lstrip().startswith("<") else f"<p>{sval}</p>"}
        elif "." in setting:
            parts = setting.split(".")
            inner = val
            for key in reversed(parts[1:]):
                inner = {key: inner}
            if parts[0] == "link" and isinstance(inner, dict):
                # zapis nahradza cely link objekt -> dopln defaulty + link_extra z blueprintu
                full = {"url": inner.get("url", val), "is_external": "", "nofollow": "", "custom_attributes": ""}
                full.update(spec.get("link_extra", {}))
                inner = full
            settings = {parts[0]: inner}
        else:
            settings = {setting: val}
        ops.append({"element_id": info["element_id"], "settings": settings})
    return ops, skipped, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--slotmap", required=True)
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    brief = json.load(open(args.brief, encoding="utf-8"))
    slotmap = json.load(open(args.slotmap, encoding="utf-8"))
    blueprint = json.load(open(args.blueprint, encoding="utf-8"))
    ops, skipped, warns = build(brief, slotmap, blueprint)
    if args.out:
        json.dump(ops, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(ops, ensure_ascii=False, indent=2))
    print(f"\n# {len(ops)} operácií, {len(skipped)} preskočených", file=sys.stderr)
    for s, why in skipped:
        print(f"   skip {s}: {why}", file=sys.stderr)
    for w in warns:
        print("   ⚠", w, file=sys.stderr)


if __name__ == "__main__":
    main()
