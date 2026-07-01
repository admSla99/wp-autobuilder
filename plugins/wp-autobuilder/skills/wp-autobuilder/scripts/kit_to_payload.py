#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kit_to_payload.py — z výstupu get-global-settings vyrobí payload pre update-global-colors.
Použitie: záloha/obnova farieb kitu (bezpečný roundtrip test) alebo seed kit_colors.

  python kit_to_payload.py global_settings.json -o restore.json
"""
import sys, json, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("settings")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    s = json.load(open(args.settings, encoding="utf-8"))
    system = s.get("colors", [])
    custom = s.get("settings", {}).get("custom_colors", [])
    payload = [{"_id": c["_id"], "title": c.get("title", c["_id"]), "color": c.get("color", "#000000")}
               for c in system + custom if c.get("_id")]
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(out)
    print(out)
    print(f"\n# {len(payload)} farieb (system {len(system)} + custom {len(custom)})", file=sys.stderr)


if __name__ == "__main__":
    main()
