#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_fix_check.py — QA orientovana na ZMENY (nie na cely build).

Rozdiel oproti autobuilderovej qa_check.py: nekontroluje, ci je cela stranka naplnena
(edituje sa iba to, co je v pripomienke), ale ci:
  (1) sa NEZAVIEDOL novy placeholder/zvysok sablony (Lorem, 'Sluzba N', [DOPLNIT], Item One...),
  (2) kazda zmena s KONKRETNOU cielovou hodnotou je v strukture pritomna (verifikacia aplikovania),
  (3) drzia sa invarianty (CTA <= 21 znakov na tlacidlach, statistika zacina cislom ak to vieme).

Vstup:
  --structure  snapshot_after_<page>.json (po zmenach)
  --changeset  (volitelne) changeset.json — overi 'desired' hodnoty pre zmeny tejto stranky
  --page       (volitelne) page_type alebo page_hint — filtruje zmeny changesetu na tuto stranku
Vystup: report + navratovy kod 0 = OK, 1 = chyba (nepublikuj / rollback).
"""
import sys, re, json, argparse

try:  # Windows konzola (cp1252) inak padne na emoji vo vypise
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PLACEHOLDERS = [r"lorem ipsum", r"dolor sit amet",
                r"\bslužba\s*[123456]\b", r"\bsluzba\s*[123456]\b",
                r"popis služby", r"popis sluzby", r"cenník nadpis", r"cennik nadpis",
                r"\bitem\s+(one|two|three|four|five|six)\b",
                r"\bobrázok\s*[1-9]\b", r"\bobrazok\s*[1-9]\b",
                r"\[dopl"]

AGENCY_LEFTOVERS = [
    (r"netovapomoc", "agenturny nazov/e-mail/odkaz"),
    (r"fajne-weby", "agenturny web"),
    (r"nazovklientovejdomeny", "placeholder domeny klienta"),
    (r"hor[úu]ce strely", "agenturny newsletter text"),
    (r"default-logo", "default logo placeholder"),
]

SKIP_KEY_SUBSTR = ("url", "link", "href", "src", "image", "icon", "css", "class", "color", "background")

# Odkazove kluce sa skenuju OSOBITNE (text_of ich preskakuje) — agenturne zvysky v URL/mailto.
LINK_KEY_SUBSTR = ("url", "link", "href")
FORBIDDEN_LINKS = [
    (r"/produktova-stranka", "agenturny CTA ciel /produktova-stranka/"),
    (r"netovapomoc", "agenturny odkaz/mail"),
    (r"fajne-weby", "agenturny odkaz"),
]
# Genericke tokeny domen/URL — nie su rozlisujuce pri parovani stranky.
GENERIC_TOK = {"https", "http", "www", "sk", "cz", "com", "net", "eu", "eshopion", "page", "stranka"}


def load_structure(obj):
    return obj["structure"] if isinstance(obj, dict) and "structure" in obj else obj


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get("elements", []))


def _skip_key(k):
    kl = str(k).lower()
    return kl in ("id", "_id") or any(t in kl for t in SKIP_KEY_SUBSTR)


def text_of(node):
    s = node.get("settings_summary", {})
    if not isinstance(s, dict):
        return ""
    out = []
    for k, v in s.items():
        if not isinstance(v, str) or _skip_key(k):
            continue
        vs = v.strip()
        if not vs or vs.startswith("http") or vs.startswith("#") or "/wp-content" in vs:
            continue
        out.append(v)
    return " ".join(out)


def button_texts(struct):
    for n in walk(struct):
        if n.get("widgetType") == "button":
            s = n.get("settings_summary", {})
            if isinstance(s, dict) and isinstance(s.get("text"), str):
                yield n.get("id"), s["text"]


def link_values(struct):
    for n in walk(struct):
        s = n.get("settings_summary", {})
        if not isinstance(s, dict):
            continue
        for k, v in s.items():
            if isinstance(v, str) and any(t in str(k).lower() for t in LINK_KEY_SUBSTR):
                yield n.get("id"), k, v


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _distinctive(toks):
    """Rozlisujuce tokeny = bez genericke domen a bez dev-instancii (newX/newsX)."""
    return {t for t in toks if t not in GENERIC_TOK and not re.fullmatch(r"news?\d+", t)}


def changes_for_page(cs, page):
    """Paruj zmeny na stranku token-based (nie substring): page_type presne alebo ako cely token;
    hint len cez ROZLISUJUCE tokeny (slug), aby sa nezhodovali dve rozne stranky tej istej domeny."""
    if not cs or not page:
        return []
    pnorm = _norm(page)
    ptoks = set(pnorm.split())
    pdist = _distinctive(ptoks)
    out = []
    for ch in cs.get("changes", []):
        pt = _norm(ch.get("page_type"))
        hint_dist = _distinctive(set(_norm(ch.get("page_hint")).split()))
        if pt and (pt == pnorm or pt in ptoks):
            out.append(ch)
        elif pdist and (pdist & hint_dist):
            out.append(ch)
    return out


def run_checks(struct, cs=None, page=None):
    """Vrati (errors, warns, verified). Zdielane main() aj selftestom."""
    errors, warns, verified = [], [], []

    corpus_nodes = list(walk(struct))
    full_lower = " ".join(text_of(n) for n in corpus_nodes).lower()

    # (1) novy placeholder = chyba
    for node in corpus_nodes:
        t = text_of(node).lower()
        for pat in PLACEHOLDERS:
            if re.search(pat, t):
                errors.append(f"placeholder '{pat}' v {node.get('id')}: {text_of(node)[:60]}")

    # zvysky sablony = varovanie (riesi Faza Global, nie tu)
    seen = set()
    for node in corpus_nodes:
        t = text_of(node).lower()
        for pat, why in AGENCY_LEFTOVERS:
            if pat not in seen and re.search(pat, t):
                seen.add(pat)
                warns.append(f"zvysok sablony ({why}) — over/vycisti v globalnych prvkoch (Faza Global)")

    # (3a) invariant: CTA <= 21 znakov na tlacidlach
    for nid, txt in button_texts(struct):
        clean = re.sub(r"<[^>]+>", "", txt).strip()
        # globalne zdielane CTA ('Chcem viac informacii') su vynimka — riesi Faza Global
        if clean and len(clean) > 21 and "viac informáci" not in clean.lower():
            warns.append(f"CTA '{clean}' ma {len(clean)} znakov (>21) v {nid}")

    # (3b) invariant: zakazane/agenturne odkazy (osobitny sken url/link klucov — text_of ich preskakuje)
    for nid, k, v in link_values(struct):
        for pat, why in FORBIDDEN_LINKS:
            if re.search(pat, v, re.I):
                warns.append(f"zakazany odkaz ({why}) v {nid}.{k}: {v[:60]}")

    # (2) verifikacia aplikovania: desired hodnoty pre zmeny tejto stranky.
    # POZN.: toto je len PAGE-LEVEL pritomnost textu (moze byt aj v inom prvku) — smerodajne
    # potvrdenie aplikovania je re-read cieleneho prvku (localization Krok C), nie tento sken.
    for ch in changes_for_page(cs, page):
        desired = ch.get("desired") or {}
        needles = []
        if isinstance(desired.get("value"), str) and desired["value"].strip():
            needles.append(desired["value"].strip())
        ts = desired.get("text_spec") or {}
        for c in (ts.get("contains") or []):
            if isinstance(c, str) and c.strip():
                needles.append(c.strip())
        if not needles:
            continue  # zmena je pravidlova (bez literalu) — verifikuje sa re-readom prvku, nie tu
        for needle in needles:
            if needle.lower() in full_lower:
                verified.append(f"{ch.get('id')}: text na stranke pritomny '{needle[:40]}' (page-level; potvrd re-readom prvku)")
            else:
                warns.append(f"{ch.get('id')}: cielovy text '{needle[:40]}' NENAJDENY na stranke — over aplikovanie")

    return errors, warns, verified


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structure", required=True)
    ap.add_argument("--changeset")
    ap.add_argument("--page")
    args = ap.parse_args()
    struct = load_structure(json.load(open(args.structure, encoding="utf-8")))
    cs = json.load(open(args.changeset, encoding="utf-8")) if args.changeset else None
    errors, warns, verified = run_checks(struct, cs, args.page)

    print("=" * 60)
    print("QA FIX CHECK")
    print(f"overene zmeny: {len(verified)} | varovani: {len(warns)} | chyb: {len(errors)}")
    print("-" * 60)
    for e in errors:
        print("  ❌", e)
    for w in warns:
        print("  ⚠", w)
    for v in verified:
        print("  ✓", v)
    if not errors and not warns:
        print("  ✅ Ziadne problemy; zmeny overene.")
    print("=" * 60)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
