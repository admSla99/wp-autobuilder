#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_intake.py — pred-letová kontrola úplnosti briefu (intake completeness check).

Cieľ: HNEĎ po Fáze 0 (brief.json) vypísať, ktoré KLIENTSKE vstupy chýbajú, takže sa
dozbierajú vopred — namiesto toho, aby sa to zistilo až v polovici buildu (chýbajúce
logo / IČO-DIČ / ceny / fotky / príjemca formulára …). Kontroluje len to, čo musí dodať
KLIENT a čo by inak skončilo ako placeholder, agentúrny zvyšok alebo skrytá sekcia.

DÔLEŽITÉ: tento skript build NEZASTAVUJE. Skill beží autonómne ďalej (placeholder + zápis
do reportu). Zmysel je VIDITEĽNOSŤ vopred + položky do záverečného reportu.

Vstup:
  --brief   cesta k brief.json (povinné)
  --json    (voliteľné) namiesto textu vypíš strojový JSON

Návratový kód: VŽDY 0 — tento check NIKDY nezastavuje autonómny beh skillu. Závažnosť
(BLOCKER/WARN/INFO) je výhradne v texte/JSON výstupe, NIE v exit kóde, aby sa nedal omylom
interpretovať ako brána (ako napr. qa_check, kde exit 1 = draft).

Závažnosti:
  BLOCKER (❌) — bez tohto bude na STAVANEJ stránke viditeľná diera (placeholder / agentúrny
                 údaj / prázdna povinná sekcia). Klient to musí dodať.
  WARN    (⚠)  — doplní sa default / sekcia sa skryje; build je OK, ale dobré vedieť.
  INFO    (ℹ)  — externá vec mimo briefu (súbor loga, príjemca formulára, kredit OpenAI,
                 video workflow) — over/zariaď ručne; z briefu sa overiť nedá.
"""
import sys, json, argparse

try:  # aby ❌/⚠/✅ nepadlo na Windows konzole (cp1252); v sandboxe je UTF-8 aj tak
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BLOCKER, WARN, INFO = "BLOCKER", "WARN", "INFO"
ICON = {BLOCKER: "❌", WARN: "⚠", INFO: "ℹ"}


def get(obj, path, default=None):
    """Bezpečné čítanie vnorenej cesty 'a.b.c' z dict/list briefu."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def is_missing(v):
    """Chýba = None / prázdny reťazec (aj samé medzery) / prázdny zoznam / prázdny dict."""
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def has_any_photos(categories):
    """V galérii: aspoň jedna kategória má aspoň jednu fotku."""
    if not isinstance(categories, list):
        return False
    return any(not is_missing(get(c, "photos")) for c in categories)


def check(brief):
    """Vráti zoznam (severity, oblasť, správa) podľa toho, čo sa reálne stavia."""
    out = []
    pages = brief.get("pages", []) or []
    content = brief.get("content", {}) or {}
    media_source = get(brief, "media.source", "placeholder")

    def add(sev, area, msg):
        out.append((sev, area, msg))

    # --- Branding (vždy: logo ide do hlavičky/päty cez globálnu fázu) ---
    if is_missing(get(brief, "brand.logo_url")):
        add(INFO, "Branding",
            "Logo (brand.logo_url) nie je v briefe — over, že súbor je v '02_Logo a branding'. "
            "Bez loga ostane v hlavičke/päte 'default-logo'.")
    if is_missing(get(brief, "brand.primary_color")) and is_missing(get(brief, "brand.secondary_color")):
        add(WARN, "Branding",
            "Brand farby chýbajú — odvodia sa z loga / pôvodného webu (extract_palette). "
            "Ak ani to nevyjde, kit ostane na master farbách.")

    # --- Právne/identifikačné údaje (Fáza 6 beží VŽDY: footer, popup, GDPR, cookies) ---
    legal = content.get("legal", {}) or {}
    legal_required = {
        "company_name": "názov firmy",
        "address": "sídlo/adresa",
        "ico": "IČO",
        "dic": "DIČ",
        "email": "e-mail",
        "phone": "telefón",
    }
    missing_legal = [lbl for key, lbl in legal_required.items() if is_missing(legal.get(key))]
    if missing_legal:
        add(BLOCKER, "Právne údaje (footer/GDPR/cookies)",
            "Chýba: " + ", ".join(missing_legal) +
            ". Bez nich sa agentúrne tokeny (Netova pomoc s.r.o., IČO/DIČ…) v päte a na "
            "GDPR/cookies NEnahradia a ostanú tam.")

    # --- Kontakt ---
    if "contact" in pages:
        c = content.get("contact", {}) or {}
        if is_missing(c.get("phone")) or is_missing(c.get("email")):
            add(BLOCKER, "Kontakt",
                "Chýba telefón a/alebo e-mail klienta — inak na stránke ostane agentúrny "
                "kontakt (…@netovapomoc.sk / cudzie číslo).")
        if is_missing(c.get("map_query")):
            add(WARN, "Kontakt", "Adresa na mapu (map_query) chýba — mapa sa skryje.")
        if is_missing(c.get("billing_html")) and is_missing(legal.get("ico")):
            add(WARN, "Kontakt", "Fakturačné údaje chýbajú — fakturačný blok ostane prázdny/skrytý.")
        add(INFO, "Kontakt",
            "Príjemca kontaktného formulára sa nastavuje v WP forme (nie v briefe) — over, "
            "že je nastavený klientov e-mail, nie agentúrny.")

    # --- Cenník (INVARIANT: ceny len od klienta) ---
    if "pricing" in pages:
        packages = get(brief, "content.pricing.packages")
        items = get(brief, "content.pricing.items")
        if is_missing(packages) and is_missing(items):
            add(BLOCKER, "Cenník",
                "Cenník je v stránkach, ale klient nedodal žiadne ceny (packages/items prázdne). "
                "Ceny sa NIKDY nevymýšľajú — cenníková stránka ostane prázdna.")

    # --- Galéria (fotky len od klienta) ---
    if "gallery" in pages:
        if not has_any_photos(get(brief, "content.gallery.categories")):
            add(BLOCKER, "Galéria",
                "Galéria je v stránkach, ale nie sú dodané žiadne fotky (03_Fotky) — "
                "galériová sekcia sa skryje.")

    # --- Produkty (ceny aj foto VÝHRADNE od klienta) ---
    products = content.get("products") or []
    if products:
        no_price = [p.get("name", "?") for p in products
                    if is_missing(p.get("price_no_vat")) and is_missing(p.get("price_vat"))]
        no_photo = [p.get("name", "?") for p in products if is_missing(p.get("photos"))]
        if no_price:
            add(BLOCKER, "Produkty",
                "Bez ceny (ostane [DOPLNIŤ: cena] → draft): " + ", ".join(no_price))
        if no_photo:
            add(BLOCKER, "Produkty",
                "Bez fotky produktu (client_only, negeneruje sa): " + ", ".join(no_photo))

    # --- Médiá ---
    if media_source in ("client", "mix"):
        if is_missing(get(brief, "media.client_folder_url")) and not has_any_photos(get(brief, "content.gallery.categories")):
            add(BLOCKER, "Médiá",
                f"media.source='{media_source}' vyžaduje klientove fotky, ale nie sú dodané "
                "(client_folder_url ani fotky). Doplň fotky alebo prepni zdroj na 'generated'.")
    elif media_source == "generated":
        add(INFO, "Médiá",
            "media.source='generated' — over kredit/limit na OpenAI účte (gpt-image), inak "
            "generovanie padne na 'Bad request'.")
    elif media_source == "placeholder":
        add(WARN, "Médiá",
            "media.source='placeholder' — vizuál sa nerieši (obrázky ostanú placeholder). "
            "Ak má web mať fotky, nastav 'client' / 'generated' / 'mix'.")

    if get(brief, "media.video_required") is True:
        add(INFO, "Médiá",
            "video_required=true — Runway video workflow zatiaľ nie je nasadený; video ostane "
            "placeholder (zapíše sa do reportu).")

    # --- Recenzie (výhradne od klienta; ak chýbajú, sekcia sa skryje) ---
    if is_missing(get(brief, "content.reviews.google_url")) and is_missing(get(brief, "content.reviews.items")):
        add(INFO, "Recenzie",
            "Google recenzie (google_url ani items) nedodané — sekcia recenzií sa skryje "
            "(nikdy sa nevymýšľajú).")

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    brief = json.load(open(args.brief, encoding="utf-8"))
    findings = check(brief)
    blockers = [f for f in findings if f[0] == BLOCKER]
    warns = [f for f in findings if f[0] == WARN]
    infos = [f for f in findings if f[0] == INFO]

    if args.json:
        print(json.dumps(
            {"blocker": [{"area": a, "msg": m} for s, a, m in blockers],
             "warn":    [{"area": a, "msg": m} for s, a, m in warns],
             "info":    [{"area": a, "msg": m} for s, a, m in infos]},
            ensure_ascii=False, indent=2))
        sys.exit(0)  # nikdy nezastavuje beh — závažnosť je vo výstupe, nie v exit kóde

    client = get(brief, "client.name", "?")
    print("=" * 60)
    print(f"INTAKE COMPLETENESS CHECK — {client}")
    print(f"BLOCKER: {len(blockers)} | WARN: {len(warns)} | INFO: {len(infos)}")
    print("-" * 60)
    if not findings:
        print("  ✅ Všetky klientske vstupy sú dodané.")
    for sev in (BLOCKER, WARN, INFO):
        for s, area, msg in findings:
            if s == sev:
                print(f"  {ICON[sev]} [{area}] {msg}")
    print("-" * 60)
    print("Pozn.: build NEZASTAVUJE — chýbajúce položky skončia ako placeholder/skrytá sekcia")
    print("a zapíšu sa do záverečného reportu. BLOCKER = dozbieraj od klienta čo najskôr.")
    print("=" * 60)
    sys.exit(0)  # nikdy nezastavuje beh — závažnosť je vo výstupe, nie v exit kóde


if __name__ == "__main__":
    main()
