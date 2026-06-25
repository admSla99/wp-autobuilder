#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_palette.py — z obrázka LOGA klienta vytiahne dominantné brand farby (primary/secondary/accent).

Použitie vo Fáze 0 (intake), KEĎ dotazník nemá farby webu: stiahni logo (02_Logo a branding) lokálne a spusti:
  python extract_palette.py --logo /cesta/logo.png
Výstup (JSON na stdout / -o): { "primary_color": "#RRGGBB", "secondary_color": "#RRGGBB", "accent_color": "#RRGGBB"? }
Tieto hodnoty vlož do brief.brand → ďalej ich spracuje build_palette (globálny kit). NEZapisuje nič na web.

Pozn.: Extrakciu z PÔVODNÉHO WEBU (nie logo) rieši agent za behu (prečíta brand farby zo štýlov stránky
dostupným nástrojom) — tento skript pracuje s obrázkom. Deterministický (median-cut kvantizácia).
"""
import sys, json, argparse, colorsys
from PIL import Image


def _clusters(path, ncolors=16, thumb=200):
    img = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))      # transparentnosť → na bielu
    img = Image.alpha_composite(bg, img).convert("RGB")
    img.thumbnail((thumb, thumb))
    q = img.quantize(colors=ncolors, method=Image.MEDIANCUT)
    pal = q.getpalette()
    out = []
    for count, idx in q.getcolors() or []:
        r, g, b = pal[idx * 3], pal[idx * 3 + 1], pal[idx * 3 + 2]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        out.append({"hex": "#%02X%02X%02X" % (r, g, b), "count": count, "h": h, "s": s, "v": v})
    return out


def extract(path):
    clusters = _clusters(path)
    if not clusters:
        return {}, []
    # chromatické = dosť sýte a nie skoro biele/čierne (vylúči pozadie loga a text)
    chromatic = sorted([c for c in clusters if c["s"] >= 0.20 and 0.12 <= c["v"] <= 0.97],
                       key=lambda c: -c["count"])
    res = {}
    if chromatic:
        primary = chromatic[0]
        res["primary_color"] = primary["hex"]
        secondary = None
        for c in chromatic[1:]:
            if abs(c["h"] - primary["h"]) > 0.08 or abs(c["s"] - primary["s"]) > 0.25:
                secondary = c
                break
        if not secondary and len(chromatic) > 1:
            secondary = chromatic[1]
        if secondary:
            res["secondary_color"] = secondary["hex"]
        for c in chromatic:
            if c["hex"] not in (res.get("primary_color"), res.get("secondary_color")):
                res["accent_color"] = c["hex"]
                break
    else:
        # achromatické logo (čiernobiele) — primary = najtmavší, secondary = najsvetlejší
        bydark = sorted(clusters, key=lambda c: c["v"])
        res["primary_color"] = bydark[0]["hex"]
        res["secondary_color"] = bydark[-1]["hex"]
    return res, clusters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logo", required=True, help="cesta k obrázku loga (png/jpg/webp)")
    ap.add_argument("-o", "--out")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    res, clusters = extract(args.logo)
    if args.out:
        json.dump(res, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if args.debug:
        for c in sorted(clusters, key=lambda c: -c["count"])[:8]:
            print(f"  {c['hex']} count={c['count']} s={c['s']:.2f} v={c['v']:.2f}", file=sys.stderr)
    sys.exit(0 if res.get("primary_color") else 1)


if __name__ == "__main__":
    main()
