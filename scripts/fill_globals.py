#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fill_globals.py — nahradí AGENTÚRNE tokeny údajmi KLIENTA v hodnotách globálnych prvkov
(footer, CTA bublina, popup) a na právnych stránkach (GDPR, cookies).

Princíp: master/šablóna obsahuje agentúrne údaje (Netova pomoc s.r.o., jan@netovapomoc.sk, ...).
Pre každého klienta sa tieto KONŠTANTNÉ tokeny (references/global_tokens.json) nahradia hodnotami
z brief.content.legal. Substituuje sa zostupne podľa dĺžky agentúrneho tokenu (najdlhší prvý),
aby sa nezamenili čiastočné výskyty.

Použitie (vo Fáze „Globálne sekcie"):
  1. get-element-settings na cieľový widget (napr. GDPR text-editor, footer copyright, popup email).
  2. uložiť hodnotu (editor/HTML) do súboru a spustiť:
     python fill_globals.py --brief brief.json --tokens SKILL_DIR/references/global_tokens.json --in value.html -o value_new.html
  3. update-element / update-widget s novou hodnotou.
Skript NIČ nezapisuje na web — len transformuje text. Hlási NEnahradené agentúrne zvyšky.
"""
import sys, json, re, argparse


def get_brief_value(brief, expr):
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


def resolve_pairs(brief, tokens):
    """Vráti (pairs, missing): pairs = [(agency, client_value)] zoradené od najdlhšieho agency tokenu."""
    pairs, missing = [], []
    for t in tokens.get("tokens", []):
        val = get_brief_value(brief, t["brief"])
        if val in (None, ""):
            missing.append(t["brief"])
            continue
        pairs.append((t["agency"], str(val)))
    pairs.sort(key=lambda p: -len(p[0]))  # najdlhší agentúrny token prvý
    return pairs, missing


def substitute(text, pairs):
    n = 0
    for agency, client in pairs:
        if agency and agency in text:
            n += text.count(agency)
            text = text.replace(agency, client)
    return text, n


def find_leftovers(text, markers):
    low = text.lower()
    return [m for m in markers if m.lower() in low]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--in", dest="infile", required=True, help="súbor s hodnotou (HTML/text) alebo '-' pre stdin")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    brief = json.load(open(args.brief, encoding="utf-8"))
    tokens = json.load(open(args.tokens, encoding="utf-8"))
    text = sys.stdin.read() if args.infile == "-" else open(args.infile, encoding="utf-8").read()
    pairs, missing = resolve_pairs(brief, tokens)
    new, n = substitute(text, pairs)
    leftovers = find_leftovers(new, tokens.get("leftover_markers", []))
    if args.out:
        open(args.out, "w", encoding="utf-8").write(new)
    sys.stdout.write(new)
    print(f"\n# nahradených výskytov: {n}; chýbajúce brief polia: {missing or '—'}", file=sys.stderr)
    if leftovers:
        print(f"  ⚠ NEnahradené agentúrne zvyšky: {leftovers} — doplň chýbajúce brief polia alebo over token mapu", file=sys.stderr)
    sys.exit(1 if leftovers else 0)


if __name__ == "__main__":
    main()
