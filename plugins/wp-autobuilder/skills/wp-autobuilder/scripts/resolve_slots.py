#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_slots.py — priradí slot_id -> aktuálne element_id na čerstvej kópii stránky.

Vstup:
  --structure  JSON z get-page-structure ({"structure":[...]} alebo priamo zoznam)
  --blueprint  references/hp_slot_blueprint.json
Výstup: slotmap JSON (slot_id -> {element_id, widget, ok}) na stdout alebo do -o.

Princíp: blueprint definuje index-cestu (poradie detí) ku každému slotu.
Pri klonovaní sa menia ID, ale poradie/štruktúra ostáva, takže cesta sedí.
Overuje sa aj zhoda typu widgetu — ak nesedí, slot sa označí ok=false (varovanie).
"""
import sys, json, argparse


def load_structure(obj):
    if isinstance(obj, dict) and "structure" in obj:
        return obj["structure"]
    if isinstance(obj, list):
        return obj
    raise ValueError("Neznámy formát štruktúry (čakám list alebo {'structure': [...]}).")


def get_node(struct, path):
    nodes = struct
    node = None
    for idx in path:
        if not isinstance(nodes, list) or idx >= len(nodes):
            return None
        node = nodes[idx]
        nodes = node.get("elements", [])
    return node


def resolve(structure, blueprint):
    out = {}
    warnings = []
    for slot in (blueprint.get("slots", []) + blueprint.get("image_slots", [])):
        node = get_node(structure, slot["path"])
        if node is None:
            out[slot["slot_id"]] = {"element_id": None, "widget": slot["widget"], "ok": False}
            warnings.append(f"{slot['slot_id']}: cesta {slot['path']} nenájdená")
            continue
        actual = node.get("widgetType") or node.get("elType")
        ok = (actual == slot["widget"])
        out[slot["slot_id"]] = {"element_id": node.get("id"), "widget": slot["widget"],
                                "widget_actual": actual, "ok": ok,
                                "setting": slot["setting"], "brief": slot.get("brief"),
                                "rule": slot.get("rule")}
        if not ok:
            warnings.append(f"{slot['slot_id']}: čakaný {slot['widget']}, našiel {actual} (id {node.get('id')})")
    return out, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    raw = json.load(open(args.structure, encoding="utf-8"))
    structure = load_structure(raw)
    blueprint = json.load(open(args.blueprint, encoding="utf-8"))
    slotmap, warnings = resolve(structure, blueprint)
    text = json.dumps(slotmap, ensure_ascii=False, indent=2)
    if args.out:
        json.dump(slotmap, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(text)
    if warnings:
        print("\n# VAROVANIA:", file=sys.stderr)
        for w in warnings:
            print(" -", w, file=sys.stderr)
    sys.exit(1 if any(not v["ok"] for v in slotmap.values()) else 0)


if __name__ == "__main__":
    main()
