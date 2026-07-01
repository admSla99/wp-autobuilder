# Hybridná lokalizácia cieľa (jadro opravára)

Najťažší a najrizikovejší krok fixera: z pripomienky (`change`) nájsť **presný element_id** na živej
stránke, ktorý treba zmeniť — a **nič iné nezasiahnuť**. Používa sa **hybridná** stratégia s poradím
istoty: najprv najspoľahlivejšie signály, potom fallbacky. Ak sa cieľ **nedá jednoznačne** určiť,
zmena sa **NEaplikuje** (`status:"unresolved"`) a ide do reportu — nikdy sa nehádže naslepo.

## Krok A — Urči stránku (post_id)
1. `elementor-mcp-list-pages` (raz na začiatku, drž v pamäti).
2. Ak `change.page_hint` je **URL/slug** → nájdi stránku, ktorej `link`/`permalink` obsahuje ten slug.
3. Ak `page_hint` je **titul** („O nás", „Kontakt") → zhoduj s `title` stránky.
4. Ak `page_hint` je prázdne, ale `page_type` je známy → použi `page_title_candidates` z blueprintu
   `AB_DIR/references/<page_type>_slot_blueprint.json` (ako autobuilder Fáza 2).
5. Ak `scope` = `kit`/`global`/`instance` → stránka sa nerieši (kit = kit id; global = theme templaty;
   instance = pravidlo naprieč, aplikuje sa v každej relevantnej stránke).
6. Ak sa stránka nedá určiť → `unresolved` + report. (Nehádaj medzi dvoma dev inštanciami — viď Fáza 1 echo.)

## Krok B — Nájdi element_id (poradie istoty)

### B1. Blueprint slot (najpresnejšie) — ak `page_type` je známy a cieľ je pomenovaný slot
- `elementor-mcp-get-page-structure(post_id)` → `structure_<page>.json`.
- `python AB_DIR/scripts/resolve_slots.py --structure structure_<page>.json --blueprint AB_DIR/references/<page_type>_slot_blueprint.json -o slotmap_<page>.json`.
- Z `slotmap` vezmi `element_id` pre `target_selector.slot_id` (alebo pre slot, ktorý významovo zodpovedá
  `location_hint`). **Over `ok:true`** (typ widgetu sedí). Toto je preferovaná cesta pre 6 známych typov
  stránok — presné index-cesty, žiadne hádanie.
- Ak resolver hlási `ok:false` (nesúlad typu) → master sa mohol zmeniť; neaplikuj, zapíš do reportu
  (možno treba aktualizovať blueprint v autobuilderi).

### B2. find-element podľa textu — ak pripomienka cituje súčasný text
- `elementor-mcp-find-element(post_id, search_text=<target_selector.search_text alebo citovaný text>)`.
- Vhodné na: agentúrne zvyšky (`"netovapomoc"`, `"fajne-weby"`), konkrétny nadpis, e-mail, „Chcem viac informácii".
- Ak vráti **práve 1** zhodu → to je cieľ. Ak **viac** → zúž podľa `page_type`/`widget`/`location_hint`
  (napr. len `button`, len v poslednej sekcii). Ak stále nejednoznačné → `unresolved`.

### B3. Štruktúra + sémantické priradenie — pre neznáme stránky / popis miesta
- `get-page-structure(post_id)` a preveď na strom (`id`, `elType`, `widgetType`, `elements[]`, `settings_summary`).
- Podľa `location_hint` a `section_index` vyber uzol:
  - `section_index` = index **obsahovej** sekcie na najvyššej úrovni (`structure[i]`). **POZOR na koniec
    stránky:** posledné top-level kontajnery často NIE sú obsah, ale **zdieľané template/footer**
    (`xpro-template`, `global`, prvky z `do_not_touch` — napr. services `structure[6]` je len footer template
    bez obrázka). Preto **„posledná sekcia" (`-1`) = posledný kontajner, ktorý reálne drží hľadaný `widget`** —
    pri hľadaní od konca **preskoč** kontajnery obsahujúce iba `xpro-template`/`global`/`do_not_touch`. Footer template needituj.
  - `widget` = typ hľadaného widgetu (`heading`, `image`, `text-editor`, `button`, `counter`, `icon-list`…).
  - Sémantika: „hero" = prvá sekcia; „fotka vedľa mapky" = `image` v sekcii, kde je aj mapa/adresa;
    „cik-cak malá fotka" = menší `image` vo dvojici veľký+malý; „sekcia so 4 countermi" = kontajner
    so 4 opakujúcimi sa deťmi s číslom+popisom.
- Vyber **najbližší jednoznačný** uzol. Ak sa významovo zhoduje viac a nevieš rozhodnúť → `unresolved`.

### B4. Kombinuj signály
Ak je k dispozícii viac napovied (`slot_id` + `search_text` + `section_index`), použi ich na **potvrdenie**
tej istej zhody (prienik). Zhoda potvrdená dvoma nezávislými signálmi je bezpečná; jediný slabý signál
(len `section_index` bez typu) over ešte `widgetType`.

## Krok C — Over pred zápisom + ulož rollback base
- Pred úpravou si zapamätaj `element_id` a **prečítaj jeho súčasnú hodnotu `get-element-settings`** —
  to je (a) potvrdenie, že cieľ je správny (súčasný text/hodnota dáva zmysel voči pripomienke),
  (b) podklad pre before→after v reporte, a (c) **rollback base**.
- **Ulož PLNÉ nastavenia prvku** do `element_before_<element_id>.json` (nie iba `settings_summary` zo
  štruktúry — to je len podmnožina a na verný rollback nestačí). Pri chybe QA/diff (Fáza 5) zapíšeš
  presne tieto plné nastavenia späť cez `update-element`/`update-widget`.
- Do plánu diff-brány (Fáza 5) pridaj tento `element_id` medzi **povolené (`--allowed`)**. `diff_structure.py`
  potom overí, že sa zmenilo len toto ID; pri **štruktúrnych** zmenách pridaj očakávané pridané/odobrané
  kontajnery cez `--allow-added`/`--allow-removed` (nie blanket `--allow-structural`).
- **Skrytie sekcie (visibility) sa nemusí prejaviť v `settings_summary`** (kontajnery ho často nemajú) —
  jeho aplikovanie over **explicitným re-readom** `get-element-settings` (že `hide_*` je nastavené), nie diffom.

## Nemenné pravidlá lokalizácie
- **Nikdy nehádž naslepo.** 0 zhôd alebo nejednoznačných >1 bez rozlíšenia → NEaplikuj, `unresolved` + report.
- **Repeater a globálne widgety** (FAQ akordeón, icon-list kontaktov, `global` „Chcem viac informácii")
  sa **NEeditujú batchom** — read-merge-write cez `get-element-settings` → `update-widget` (zachovaj `_id`).
  Viď `change_types.md`.
- **Global/theme prvky** (footer, CTA bublina, popup, GDPR, cookies) NIE sú na stránke — hľadajú sa cez
  `find-element` na theme templatoch / popupoch (Fáza 4e, `fill_globals.py`).
- **`do_not_touch`** v blueprintoch (global CTA, CTA banner, header/footer templaty, karty recenzií) rešpektuj —
  ak pripomienka mieri práve na ne, rieš ich určeným kanálom (Fáza 4e / Google Reviews), nie ako page slot.
