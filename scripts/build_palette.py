#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_palette.py - bezpecne prefarbenie Elementor kitu (read-merge-write).

ZISTENIE: zapisy do kitu su "partial-replace" = DESTRUKTIVNE. update-page-settings
(a add-custom-css) prepisu CELY kit a vsetko, co nie je v payloade, resetnu na
Elementor defaulty (typografia, paleta, custom CSS). Preto sa kit smie menit IBA tak:
  1) precitaj cely kit (get-global-settings),
  2) do KOPIE vloz nove brand farby (system + odvodene custom),
  3) zapis CELY objekt jednym update-page-settings.
Tento skript robi krok (2). NEPOUZIVAT update-global-colors (pise len custom, nie
system, a nuluje 8-miestny hex) ani add-custom-css na kit (resetne kit na defaulty).

Vstup:  --brief brief.json  --current <get-global-settings JSON>  --kit kit_colors.json
Vystup: -o kit_new.json  -> KOMPLETNY settings objekt pre update-page-settings(post_id=<kit>, settings=...)
"""
import sys, json, re, argparse, copy

NAME2HEX = {
    "modra": "#1565C0", "blue": "#1565C0", "tmavomodra": "#0D47A1", "svetlomodra": "#42A5F5",
    "zelena": "#2E7D32", "green": "#2E7D32", "tmavozelena": "#1B5E20", "svetlozelena": "#66BB6A",
    "cervena": "#C62828", "red": "#C62828", "oranzova": "#EF6C00", "orange": "#EF6C00",
    "zlta": "#F9A825", "yellow": "#F9A825", "cierna": "#111111", "black": "#111111",
    "biela": "#FFFFFF", "white": "#FFFFFF", "siva": "#607D8B", "gray": "#607D8B", "grey": "#607D8B",
    "hneda": "#6D4C41", "brown": "#6D4C41", "fialova": "#6A1B9A", "purple": "#6A1B9A",
    "ruzova": "#AD1457", "pink": "#AD1457", "tyrkysova": "#00838F", "cyan": "#00838F",
}

def strip_acc(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

def to_hex(val, fallback):
    if not val:
        return fallback
    v = str(val).strip()
    m = re.search(r"#([0-9a-fA-F]{6})", v)
    if m:
        return "#" + m.group(1).upper()
    for token in re.split(r"[\s,/]+", strip_acc(v)):
        if token in NAME2HEX:
            return NAME2HEX[token]
    return fallback

def rgb(h):
    h = h.lstrip("#")[:6]
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def hexs(r, g, b):
    return "#%02X%02X%02X" % (max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b))))

def lighten(h, a):
    r, g, b = rgb(h)
    return hexs(r + (255 - r) * a, g + (255 - g) * a, b + (255 - b) * a)

def darken(h, a):
    r, g, b = rgb(h)
    return hexs(r * (1 - a), g * (1 - a), b * (1 - a))

def alpha(h, a):
    return h.upper()[:7] + ("%02X" % max(0, min(255, round(a * 255))))

def derive(rule, base):
    if "keep" in rule:
        return rule["keep"]
    src = base[rule.get("from", "primary")]
    op = rule.get("op")
    if op == "lighten":
        return lighten(src, rule["amt"])
    if op == "darken":
        return darken(src, rule["amt"])
    if op == "alpha":
        return alpha(src, rule["amt"])
    return src

def settings_of(current):
    return current["settings"] if isinstance(current, dict) and "settings" in current else current

def build(brief, kit, current):
    b = brief.get("brand", {})
    base = {"primary": to_hex(b.get("primary_color"), "#96DB3E"),
            "secondary": to_hex(b.get("secondary_color"), "#102A25")}
    base["accent"] = to_hex(b.get("accent_color"), base["primary"])
    settings = copy.deepcopy(settings_of(current))
    cur_sys = {c["_id"]: c for c in settings.get("system_colors", [])}
    system = []
    for slot in kit["system"]:
        title = cur_sys.get(slot["_id"], {}).get("title", slot["title"])
        system.append({"_id": slot["_id"], "title": title, "color": derive(slot["derive"], base)})
    settings["system_colors"] = system
    derived = {s["_id"]: derive(s["derive"], base) for s in kit["custom"]}
    titles = {s["_id"]: s["title"] for s in kit["custom"]}
    seen = set()
    new_custom = []
    for c in settings.get("custom_colors", []):
        cid = c.get("_id")
        if cid in derived:
            c = {"_id": cid, "title": c.get("title", titles[cid]), "color": derived[cid]}
        new_custom.append(c)
        seen.add(cid)
    for s in kit["custom"]:
        if s["_id"] not in seen:
            new_custom.append({"_id": s["_id"], "title": s["title"], "color": derived[s["_id"]]})
    settings["custom_colors"] = new_custom
    return settings, base

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--kit", required=True)
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    brief = json.load(open(args.brief, encoding="utf-8"))
    kit = json.load(open(args.kit, encoding="utf-8"))
    current = json.load(open(args.current, encoding="utf-8"))
    settings, base = build(brief, kit, current)
    if args.out:
        json.dump(settings, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(settings, ensure_ascii=False))
    print("\n# COLOR PLAN: primary=%s secondary=%s accent=%s" % (base["primary"], base["secondary"], base["accent"]), file=sys.stderr)
    print("# zachovane: custom_typography=%d, custom_css=%s" % (len(settings.get("custom_typography", [])), "ano" if settings.get("custom_css") else "nie"), file=sys.stderr)
    print("# POSLI ako: update-page-settings(post_id=<kit_id>, settings=<tento objekt>) - JEDEN atomicky zapis", file=sys.stderr)

if __name__ == "__main__":
    main()
