#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_page_color_css.py — z kit_new.json (build_palette výstup) vyrobí per-stránka
custom_css blok, ktorý nastaví --e-global-color-* IBA pre danú stránku (body.elementor-page-<id>).
Nedotkne sa zdieľaného kitu. Reverzibilné (custom_css="").
Použitie: python build_page_color_css.py --kit kit_new.json --post-id 17992 [--kit-id 6]
"""
import json, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True)
    ap.add_argument("--post-id", required=True)
    ap.add_argument("--kit-id", default="6")
    args = ap.parse_args()
    s = json.load(open(args.kit, encoding="utf-8"))
    lines = []
    for c in s.get("system_colors", []):
        lines.append(f"--e-global-color-{c['_id']}:{c['color']};")
    for c in s.get("custom_colors", []):
        lines.append(f"--e-global-color-{c['_id']}:{c['color']};")
    sel = f".elementor-kit-{args.kit_id}.elementor-page-{args.post_id}"
    css = sel + "{" + "".join(lines) + "}"
    print(css)

if __name__ == "__main__":
    main()
