#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_changeset.py — over changeset.json (rozparsovane pripomienky) proti changeset.schema.json.

Vstup:
  --changeset  changeset.json
  --schema     (volitelne) cesta k changeset.schema.json;
               default: <script_dir>/../references/changeset.schema.json
Vystup: report (pocty podla type/scope/priority, chybajuce klientske vstupy, needs_input polozky)
        + navratovy kod 0 = OK, 1 = STRUKTURALNE chyby (skill ma changeset opravit, nie sa pytat).

DOLEZITE: needs_input / unresolved NIE su chyby validacie — su to legitimne stavy, ktore len
reportujeme. Skill bezi dalej autonomne a zaradi ich do zaverecneho reportu (Faza 6).
"""
import sys, os, json, argparse

try:  # Windows konzola (cp1252) inak padne na emoji vo vypise
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "references", "changeset.schema.json")

# Fallback enumy (ak sa schema neda precitat). Musia sedet s changeset.schema.json.
FALLBACK = {
    "type": ["text", "link", "contact", "color", "image", "media_quality",
             "visibility", "structure", "global", "mixed"],
    "scope": ["page", "kit", "global", "instance"],
    "priority": ["priority", "normal", "low"],
    "status": ["pending", "applied", "verified", "unresolved", "needs_input", "skipped"],
    "page_type": ["hp", "about", "services", "contact", "pricing", "gallery",
                  "products", "unknown", None],
}


def load_enums(schema_path):
    """Vytiahne enum zoznamy zo schema ($defs.change.properties.<pole>.enum); fallback ak chyba."""
    enums = dict(FALLBACK)
    try:
        schema = json.load(open(schema_path, encoding="utf-8"))
        props = schema["$defs"]["change"]["properties"]
        for field in ("type", "scope", "priority", "status", "page_type"):
            if field in props and "enum" in props[field]:
                enums[field] = props[field]["enum"]
    except Exception as e:
        print(f"# (pouzivam fallback enumy — schema sa nedala precitat: {e})", file=sys.stderr)
    return enums


def validate(cs, enums):
    errors, warns = [], []
    if not isinstance(cs, dict):
        return ["changeset nie je objekt"], []
    changes = cs.get("changes")
    if not isinstance(changes, list) or not changes:
        return ["'changes' musi byt neprazdne pole"], []

    seen_ids = set()
    for i, ch in enumerate(changes):
        tag = f"changes[{i}]"
        if not isinstance(ch, dict):
            errors.append(f"{tag}: nie je objekt")
            continue
        cid = ch.get("id")
        tag = f"change {cid}" if cid else tag
        # povinne polia
        for req in ("id", "raw", "type", "scope"):
            if not ch.get(req):
                errors.append(f"{tag}: chyba povinne pole '{req}'")
        if cid in seen_ids:
            errors.append(f"{tag}: duplicitne id")
        if cid:
            seen_ids.add(cid)
        # enumy
        for field in ("type", "scope"):
            v = ch.get(field)
            if v is not None and v not in enums[field]:
                errors.append(f"{tag}: '{field}'='{v}' nie je platne {enums[field]}")
        for field in ("priority", "status"):
            v = ch.get(field)
            if v is not None and v not in enums[field]:
                warns.append(f"{tag}: '{field}'='{v}' mimo enumu (pouzijem default)")
        pt = ch.get("page_type")
        if pt is not None and pt not in enums["page_type"]:
            warns.append(f"{tag}: page_type='{pt}' nie je zname (spracuje sa ako 'unknown')")
        # mäkke: nic co by nas zastavilo, len upozornenia na kvalitu changesetu
        if not ch.get("intent"):
            warns.append(f"{tag}: chyba 'intent' (odporucane pre jasny report)")
        sel = ch.get("target_selector") or {}
        if not any(sel.get(k) for k in ("slot_id", "search_text")) and sel.get("section_index") is None:
            warns.append(f"{tag}: ziadna lokalizacna napoveda (slot_id/search_text/section_index) — Faza 4 ju musi odvodit zo struktury")
    return errors, warns


def summarize(cs):
    changes = cs.get("changes", [])
    def count(field, default=None):
        out = {}
        for ch in changes:
            k = ch.get(field, default)
            out[k] = out.get(k, 0) + 1
        return out
    needs = [ch.get("id") for ch in changes if ch.get("status") == "needs_input"]
    inputs = sorted({inp for ch in changes for inp in (ch.get("client_inputs_needed") or [])})
    return count("type"), count("scope"), count("priority", "normal"), needs, inputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changeset", required=True)
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    args = ap.parse_args()
    cs = json.load(open(args.changeset, encoding="utf-8"))
    enums = load_enums(args.schema)
    errors, warns = validate(cs, enums)
    by_type, by_scope, by_prio, needs, inputs = summarize(cs)

    print("=" * 60)
    print("VALIDATE CHANGESET")
    print(f"zmien: {len(cs.get('changes', []))} | chyb: {len(errors)} | varovani: {len(warns)}")
    print(f"podla typu:  {by_type}")
    print(f"podla scope: {by_scope}")
    print(f"priorita:    {by_prio}")
    if needs:
        print(f"needs_input (chyba klientsky vstup): {needs}")
    if inputs:
        print("chybajuce klientske vstupy (dozbierat):")
        for inp in inputs:
            print("   -", inp)
    print("-" * 60)
    for e in errors:
        print("  ❌", e)
    for w in warns:
        print("  ⚠", w)
    if not errors and not warns:
        print("  ✅ Changeset je v poriadku.")
    print("=" * 60)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
