#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bezpecny test farebnej logiky (bez dotyku webu): read-merge-write build_palette."""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_palette as bp

kit = json.load(open(os.path.join(ROOT, "references/kit_colors.json"), encoding="utf-8"))
HEXRE = re.compile(r"^#[0-9A-F]{6}([0-9A-F]{2})?$")

def fake_current():
    return {"settings": {
        "system_colors": [
            {"_id": "primary", "title": "Primarni", "color": "#96DB3E"},
            {"_id": "secondary", "title": "Sekundarni", "color": "#102A25"},
            {"_id": "text", "title": "HTML", "color": "#000000"},
            {"_id": "accent", "title": "Akcent", "color": "#96DB3E"}],
        "custom_colors": [
            {"_id": "5840c11", "title": "Oddelovac", "color": "#96DB3E"},
            {"_id": "d260eac", "title": "Primary-transparent", "color": "#96DB3E96"},
            {"_id": "zzz9999", "title": "Extra", "color": "#ABCDEF"}],
        "custom_typography": [{"_id": "a885d87", "title": "Heading - hero",
                               "typography_font_family": "Lexend", "typography_font_weight": "700"}],
        "custom_css": "/*KEEP*/ .primary-color{color:var(--e-global-color-primary);}",
        "default_page_template": "elementor_header_footer",
        "site_logo": {"url": "https://x/logo.png", "id": 22}}}

def main():
    brief = {"brand": {"primary_color": "#2E7D32", "secondary_color": "#1565C0", "accent_color": "#F39200"}}
    out, base = bp.build(brief, kit, fake_current())
    assert base == {"primary": "#2E7D32", "secondary": "#1565C0", "accent": "#F39200"}
    sb = {c["_id"]: c["color"] for c in out["system_colors"]}
    assert sb["primary"] == "#2E7D32" and sb["secondary"] == "#1565C0" and sb["accent"] == "#F39200"
    assert sb["text"] == "#000000"
    print("OK system: brand farby nastavene")
    assert out["custom_typography"] == fake_current()["settings"]["custom_typography"], "typografia sa stratila"
    assert out["custom_css"].startswith("/*KEEP*/"), "custom CSS sa stratil"
    assert out["default_page_template"] == "elementor_header_footer"
    assert out["site_logo"]["id"] == 22
    print("OK preserve: typografia, custom CSS aj ostatne polia zachovane")
    cust = {c["_id"]: c for c in out["custom_colors"]}
    assert cust["5840c11"]["color"] == "#2E7D32"
    assert cust["zzz9999"]["color"] == "#ABCDEF"
    assert len(cust["d260eac"]["color"].lstrip("#")) == 8
    assert all(s["_id"] in cust for s in kit["custom"])
    bad = [(c["_id"], c["color"]) for c in out["custom_colors"] if not HEXRE.match(c["color"])]
    assert not bad, "nevalidne hex: %s" % bad
    print("OK custom: %d farieb, validne, alfa zachovana" % len(out["custom_colors"]))
    out2, base2 = bp.build({"brand": {"primary_color": "zelena", "secondary_color": "modra", "accent_color": "oranzova"}}, kit, fake_current())
    assert base2["primary"] == "#2E7D32" and base2["secondary"] == "#1565C0" and base2["accent"] == "#EF6C00"
    print("OK nazvy: %s %s %s" % (base2["primary"], base2["secondary"], base2["accent"]))
    print("PALETTE SELF-TEST PRESIEL")

if __name__ == "__main__":
    main()
