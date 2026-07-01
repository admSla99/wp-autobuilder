#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_structure.py — bezpecnostna brana opravara: porovna stranku PRED a PO zmenach a overi,
ze sa zmenili LEN cielene prvky (ziadna kolateralna zmena).

Vstup:
  --before   snapshot_before_<page>.json  (z get-page-structure pred zapisom)
  --after    snapshot_after_<page>.json    (z get-page-structure po zapise)
  --allowed  (volitelne) ciarkou oddelene element_id, ktore SA SMU zmenit (cielene + kontajnery
             pri strukturalnych zmenach). Ak zadane, kazda zmena mimo tohto zoznamu = KOLATERAL.
  --allow-structural  (flag) povol pridane/odobrate prvky (pre visibility/structure zmeny)
Vystup: report zmenených / pridaných / odobraných element_id + navratovy kod
        0 = OK (ziadny kolateral), 1 = zisteny kolateral / neocakavana strukturalna zmena.

Princip: element_id su pri EDITE stabilne (na rozdiel od klonovania). Cielime konkretne id,
takze akakolvek zmena summary ineho id znamena, ze skill zasiahol mimo pripomienky -> STOP + rollback.
Pozn.: settings_summary z get-page-structure je podmnozina nastaveni; brana chyta hlavne textove/
viditelne a link zmeny (to su najcastejsie kolateraly). Obrazkove zmeny sa overuju osobitne re-readom.
"""
import sys, json, argparse

try:  # Windows konzola (cp1252) inak padne na emoji vo vypise
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_structure(obj):
    if isinstance(obj, dict) and "structure" in obj:
        return obj["structure"]
    if isinstance(obj, list):
        return obj
    raise ValueError("Neznamy format struktury (cakam list alebo {'structure': [...]}).")


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get("elements", []))


def summary_map(struct):
    """id -> normalizovany podpis settings_summary (json so zoradenymi klucmi)."""
    out = {}
    for n in walk(struct):
        nid = n.get("id")
        if nid is None:
            continue
        s = n.get("settings_summary", {})
        out[nid] = json.dumps(s, ensure_ascii=False, sort_keys=True) if isinstance(s, dict) else str(s)
    return out


def diff(before, after):
    b, a = summary_map(before), summary_map(after)
    ids_b, ids_a = set(b), set(a)
    added = sorted(ids_a - ids_b)
    removed = sorted(ids_b - ids_a)
    changed = sorted(nid for nid in (ids_b & ids_a) if b[nid] != a[nid])
    return added, removed, changed, b, a


def gate(changed, added, removed, allowed, allow_added, allow_removed,
         allow_structural=False, allow_empty=False):
    """Vrati (collateral, struct_problem). FAIL-CLOSED: prazdny allow-list + reálne zmeny = kolateral."""
    if allowed:
        collateral = [nid for nid in changed if nid not in allowed]
    elif changed and not allow_empty:
        collateral = list(changed)  # ziadne cielene ID zadane, no nieco sa zmenilo -> vsetko podozrive
    else:
        collateral = []
    if allow_structural:
        struct_problem = []       # blanket opt-out (menej bezpecne) — pouzi radsej --allow-added/--allow-removed
    else:
        struct_problem = ([("+", nid) for nid in added if nid not in allow_added]
                          + [("-", nid) for nid in removed if nid not in allow_removed])
    return collateral, struct_problem


def _idset(s):
    return {x.strip() for x in (s or "").split(",") if x.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--allowed", default="", help="cielene element_id, ktore SA SMU zmenit (in-place)")
    ap.add_argument("--allow-added", default="", help="ocakavane NOVE element_id (structure/visibility)")
    ap.add_argument("--allow-removed", default="", help="ocakavane ODOBRATE element_id")
    ap.add_argument("--allow-structural", action="store_true", help="blanket povolenie pridania/odobrania (menej bezpecne)")
    ap.add_argument("--allow-empty", action="store_true", help="dovol prazdny --allowed aj pri zmenach (vyslovny opt-out)")
    args = ap.parse_args()

    before = load_structure(json.load(open(args.before, encoding="utf-8")))
    after = load_structure(json.load(open(args.after, encoding="utf-8")))
    added, removed, changed, b, a = diff(before, after)
    allowed = _idset(args.allowed)
    collateral, struct_problem = gate(changed, added, removed, allowed,
                                      _idset(args.allow_added), _idset(args.allow_removed),
                                      args.allow_structural, args.allow_empty)

    print("=" * 60)
    print("DIFF STRUCTURE (bezpecnostna brana)")
    print(f"zmenene: {len(changed)} | pridane: {len(added)} | odobrate: {len(removed)}")
    if allowed:
        print(f"povolene (cielene) id: {sorted(allowed)}")
    if not allowed and changed and not args.allow_empty:
        print("  (⚠ prazdny --allowed — FAIL-CLOSED: kazda zmena sa berie ako kolateral)")
    print("-" * 60)
    coll_set = set(collateral)
    struct_set = {nid for _, nid in struct_problem}
    for nid in changed:
        flag = "❌ KOLATERAL" if nid in coll_set else "✓ cielena"
        old = b[nid][:50]
        new = a[nid][:50]
        print(f"  {flag}  {nid}\n      pred: {old}\n      po:   {new}")
    for nid in added:
        print(f"  {'❌ neocakavany' if nid in struct_set else '✓'} pridany prvok: {nid}")
    for nid in removed:
        print(f"  {'❌ neocakavany' if nid in struct_set else '✓'} odobrany prvok: {nid}")
    if not changed and not added and not removed:
        print("  (ziadna zmena struktury)")
    print("-" * 60)

    problems = len(collateral) + len(struct_problem)
    if problems:
        print(f"  ❌ {problems} problemov: {len(collateral)} kolateral, {len(struct_problem)} neocakavanych strukturalnych.")
        print("     -> ROLLBACK zo snapshotu (update-page-settings/element spat na 'before').")
    else:
        print("  ✅ Zmenili sa len cielene prvky.")
    print("=" * 60)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
