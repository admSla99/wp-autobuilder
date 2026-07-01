---
name: wp-fixer
description: >
  Autonómny OPRAVÁR už postaveného WordPress webu cez Elementor MCP. Používateľ zadá iba ZDROJ
  pripomienok (čo treba na stránke zmeniť) — dokument v priečinku klienta na Google Drive (napr.
  „pripomienky"/„revízia") ALEBO text vložený priamo do chatu; skill si ich prečíta, znormalizuje na
  changeset.json a autonómne aplikuje cielené úpravy na ŽIVÝCH stránkach: prepis textov (dĺžka/SEO),
  výmena/generovanie/vylepšenie obrázkov (n8n Image 2.0), brand farby v globálnom kite, opravy odkazov
  a kontaktných/fakturačných údajov, skrytie prázdnych sekcií, duplikovanie sekcií, aj globálne prvky
  (footer, CTA bublina, popup, GDPR, cookies). Mení LEN to, čo je v pripomienke (snapshot + diff),
  po QA ukladá naživo a pri chybe robí rollback — celé bez prerušovania a bez doplňujúcich otázok.
  Použi tento skill VŽDY, keď používateľ chce OPRAVIŤ / UPRAVIŤ / ZMENIŤ / doladiť / zrevidovať existujúci
  web podľa pripomienok, poznámok alebo feedbacku (nie postaviť nový — to je wp-autobuilder). Spúšťa sa
  ako jeden vstupný bod a vnútri prejde celý proces (intake → echo inštancie → plán → snapshot → lokalizuj
  a aplikuj → QA + diff → uloženie naživo → report).
---

# WP Fixer (opravár)

Sesterský skill k **`wp-autobuilder`**. Kým autobuilder **stavia celý web z briefu**, fixer **aplikuje
cielené pripomienky na už postavený živý web** — je to „opravár / revízia". Vstup = **voľné pripomienky**
(čo treba zmeniť), ktoré Claude znormalizuje na `changeset.json` a autonómne vykoná. Architektúra,
rozdiely a znovupoužitie autobuildera: `references/architecture.md`.

## Autonómia — DÔLEŽITÉ
Skill beží **od zdroja pripomienok po uložené zmeny naživo, bez prerušovania**.
- **NEPÝTAJ sa** a **nepoužívaj AskUserQuestion** (jediná výnimka je pred-behová: ak úplne chýba zdroj
  pripomienok — viď „Vstup"). Keď sa cieľ nedá jednoznačne lokalizovať alebo chýba klientsky vstup, zmenu
  **neaplikuj naslepo** — označ `unresolved`/`needs_input` a zaraď do reportu.
- **Uloženie naživo (default):** po Fáze 5 sa zmena **uloží naživo**, ak QA aj diff-brána prešli bez CHÝB.
  **Poistka — QA/diff gate:** ak `qa_fix_check` nájde chybu alebo `diff_structure` nájde **kolaterál**
  (zmenu mimo cielených prvkov), zmeny **NEUKLADAJ** a sprav **rollback zo snapshotu** (Fáza 3) + zapíš dôvod.
  Flag `publish_after_fix` (default `true`) vie ukladanie vypnúť (zmeny ostanú na ručnú kontrolu + preview).
- **Meň LEN to, čo je v pripomienke** — nič „pri tom". Snapshot + diff to vynucujú.
- Cieľ: používateľ v novej session iba spomenie skill a zadá zdroj pripomienok — zvyšok dobehne sám.

## Vstup od používateľa
Používateľ zadá **iba zdroj pripomienok** (dva podporované, skill sám rozozná):
1. **Google Drive** — priečinok/súbor klienta s pripomienkami (názov „pripomienky"/„revízia"/„úpravy"/„feedback").
2. **Text v chate** — pripomienky vložené priamo do konverzácie.
Postup intake: `references/intake_notes.md`. Ak zdroj nie je jasný, použi posledný spomenutý priečinok
klienta z konverzácie; iba ak naozaj žiadny nie je, vypýtaj si jednu vec — kde sú pripomienky. Toto je
**jediná pred-behová výnimka** (kým beh vôbec nezačal); **počas behu sa už nikdy nepýtaj** (viď Autonómia).

Cieľom sú **živé stránky inštancie klienta** (jeden web = jeden klient). Skill pracuje priamo na nich.

Flag `publish_after_fix` (default `true`) — uložiť po úspešnej QA+diff naživo. `false` = nechať na ručnú kontrolu.

## Potrebné konektory
- **Elementor MCP** — inštancia klienta (čítanie štruktúry, úpravy prvkov, kit, publikovanie).
- **Google Drive MCP** — pripomienky + prípadný dotazník/podklady (logo, fotky, `content.legal`).
- **n8n — built-in connector** (`execute_workflow` + `get_execution`) — generovanie/úprava obrázkov
  (Image 2.0, `GtjjsjvLqPar2FwB`; Runway pre video). Potrebné len pri `image`/`media_quality` zmenách.
Over dostupnosť: `elementor-mcp-list-pages` a GDrive `search_files`.

> **Prepnutie inštancie:** skill `elementor-mcp` connector NEprepína. Ak ukazuje na iný web než cieľového
> klienta, najprv prepni inštanciu — manuálny postup (`Prepni-Elementor.bat`, reštart Claude) je v projektovom
> **`CLAUDE.md`**. Bez správnej inštancie nepokračuj (viď Fáza 1).

## Pracovný priečinok a cesty
- **SKILL_DIR** = priečinok tohto súboru (`wp-fixer`). Skripty: `SKILL_DIR/scripts/`, dáta: `SKILL_DIR/references/`.
- **AB_DIR** = priečinok skillu **`wp-autobuilder`** (znovupoužité blueprinty a skripty — viď architecture.md).
  Nájdi ho skúšaním v tomto poradí (prvá existujúca cesta vyhráva):
  1. nainštalovaný plugin: `SKILL_DIR/../../../../wp-autobuilder/*/skills/wp-autobuilder` (glob — verzia v ceste),
  2. marketplace repo: `SKILL_DIR/../../../wp-autobuilder/skills/wp-autobuilder`,
  3. plochý layout (skilly vedľa seba): `SKILL_DIR/../wp-autobuilder`.
  Ak nič neexistuje, plugin `wp-autobuilder` nie je nainštalovaný — nainštaluj ho (fixer ho vyžaduje).
- Medzisúbory (`changeset.json`, `plan.json`, `brief.json`, `snapshot_before_<page>.json`,
  `snapshot_after_<page>.json`, `kit_before.json`, `slotmap_<page>.json`) ukladaj do **aktuálneho pracovného
  priečinka**. Vždy používaj **absolútne cesty**.

## Pipeline (jeden beh)
Pracuj po krokoch, po každom zápise over výsledok. **Mimo cielených prvkov (z pripomienky) nič nemeň.**

### Fáza 0 — Intake pripomienok → `changeset.json`
Postupuj podľa `references/intake_notes.md`:
1. Získaj pripomienky zo **zdroja** (GDrive dokument `search_files`+`read_file_content`, alebo text v chate).
2. Znormalizuj voľný text na `changeset.json` (`changes[]`: `id`, `raw`, `priority`, `page_hint`,
   `page_type`, `location_hint`, `type`, `scope`, `target_selector`, `intent`, `desired`,
   `client_inputs_needed`, `status`) podľa `changeset.schema.json`. **Bez pýtania sa.**
3. Ak niektoré zmeny potrebujú klientske dáta (texty, `brand.*`, `content.legal`, `google_url`, ceny) a je
   dostupný **dotazník** v priečinku klienta, načítaj brief podľa `AB_DIR/references/intake.md` → `brief.json`.
   Čo chýba, označ `status:"needs_input"` + `client_inputs_needed`.
4. `python SKILL_DIR/scripts/validate_changeset.py --changeset changeset.json` — over štruktúru; chyby oprav
   sám. Vypíše počty podľa typu/scope/priority a **chýbajúce klientske vstupy** → zaraď do hlavičky behu.

### Fáza 1 — Overenie inštancie (echo identity) — PRED PRVÝM ZÁPISOM
**Účel:** najdrahšia chyba je oprava na **zlej inštancii** (connector mieril na iný web). Skill nevie, na
ktorý web je pripojený — všetky klientske weby majú rovnaké tituly stránok. Preto **ako úplne prvú vec pred
akýmkoľvek zápisom** prečítaj živú doménu a spáruj ju s klientom z pripomienok.
1. **Prečítaj živú doménu (read-only):** `elementor-mcp-list-pages` → z URL ktorejkoľvek stránky
   (`preview_url`/`link`/permalink) vytiahni doménu (napr. `new1.eshopion.sk`). (Zároveň test dostupnosti connectora.)
2. **Vypíš echo ako prvý riadok behu** (vždy), napr.:
   `🔌 Pripojený web (live): news6.eshopion.sk · klient z pripomienok: Enova · zdroj: gdrive:05_Pripomienky.
   Ak doména NEpatrí tomuto klientovi → ZASTAV a prepni inštanciu (CLAUDE.md).`
3. **Platné ciele:** pracovné/dev inštancie `newsX.eshopion.sk` (news1, news6…) a `newX.eshopion.sk`
   (new1, new6…) sú **bežné, platné** — nikdy sa neblokujú.
4. **Auto-blok = PRESNÝ menný denylist agentúrnych HOSTOV** (celý host 1:1, nie prefix): build **nepokračuj**
   iba ak sa živá doména presne zhoduje so zakázaným agentúrnym hostom `newo.eshopion.sk` (master/predloha).
   `netovapomoc.sk`/`fajne-weby.cz` v OBSAHU sú TEXT (rieši Fáza 4e), nie inštancia — nezamieňaj.
5. **Zámenu dvoch dev/klientskych inštancií** (napr. `new1` vs `new6`) skill sám nerozozná (oba sú platné) —
   zachytí ju iba človek z echo riadku. Zapamätaj `instance_domain` a uveď v hlavičke aj v reporte (Fáza 6).
- **Voliteľná tvrdá brána:** ak existuje register `instances.json` (GDrive klient → pracovná doména),
  porovnaj `instance_domain` s očakávanou (`meta.instance_expected`) a pri nezhode **STOP**.

### Fáza 2 — Plán behu → `plan.json`
`python SKILL_DIR/scripts/plan_changes.py --changeset changeset.json -o plan.json`.
- Zoskupí zmeny podľa cieľa: **`pages`** (per stránka), **`kit`** (farby, RAZ), **`global`** (footer/popup…, RAZ),
  **`media`** (dávka obrázkov naprieč stránkami), **`instance_rules`** (pravidlá pre všetky stránky, napr. dedup).
- Určí **poradie** (najprv per stránka po prioritách; kit a global na konci — RAZ) a **konflikty** (dve zmeny
  na ten istý prvok). Konflikt → vyrieš spojením/poradím alebo zapíš do reportu; nehádž obidve naslepo.

### Fáza 3 — Snapshot (rollback base) — PRED zápismi
- **Per stránka** (z `plan.pages`): `get-page-structure(post_id)` → `snapshot_before_<page>.json` (na diff).
- **Per cielený prvok** (z lokalizácie, Krok C): `get-element-settings(element_id)` → `element_before_<id>.json`
  (**plné** nastavenia = verný rollback; `settings_summary` je len podmnožina).
- **Farby** (`plan.kit` neprázdny): `get-global-settings` → `kit_before.json`.
- **Globálne prvky** (`plan.global` neprázdny, Fáza 4e): pre každý dotknutý theme widget/právnu stránku
  `get-element-settings`/`get-page-structure` → `global_before_<id>.json`. **Bez tejto zálohy globál needituj.**
Viď `references/qa_fix.md`.

### Fáza 4 — Lokalizuj + aplikuj (hybrid, per zmena)
Prejdi **všetky** zmeny v poradí z `plan.order` (obsahuje aj `plan.instance_rules` — napr. dedup fotiek —
takže žiadny scope sa nevynechá). **Lokalizuj** cieľ podľa `references/localization.md` (A: stránka →
B: element_id cez blueprint / find-element / štruktúra → C: over súčasnú hodnotu + ulož `element_before` +
pridaj `element_id` medzi **cielené** pre diff-bránu). Cieľ sa nedá jednoznačne určiť → `unresolved` + report.
Potom **aplikuj podľa typu** (`references/change_types.md`) a **over re-readom**:

- **4a — Texty / linky / kontakt** (`text`,`link`,`contact`): `batch-update`/`update-widget`;
  repeatery (FAQ, icon-list kontaktov) **read-merge-write** (zachovaj `_id`). Dĺžka/SEO a invarianty
  (CTA ≤ 21, štatistika číslo, žiadne vymyslené fakty) podľa `AB_DIR/references/intake.md`.
- **4b — Viditeľnosť / štruktúra** (`visibility`,`structure`): skry sekciu (`hide_*:"hidden"` na kontajner)
  radšej než mazať; skrytie over **re-readom** (nie diffom). Duplikovanie sekcie (kontakt na kontakt) opatrne —
  `diff_structure --allow-added <id nového podstromu>` (nie blanket `--allow-structural`). Ak sa štruktúra nedá
  bezpečne vrátiť (delete/create), radšej `unresolved` + report.
- **4c — Farby (kit), RAZ** (`color`): read-merge-write cez `AB_DIR/scripts/build_palette.py` → jeden
  atomický `update-page-settings` na kit (`kit_before.json` je záloha). Nikdy čiastočne, nikdy per sekcia.
  **Výnimka `transparent_primary_bg`** (pozadie jednej sekcie na transparentnú primárnu) = cielený per-element
  `background_color` (rgba primárnej), NIE zmena kitu — viď `change_types.md`.
- **4d — Médiá, dávka** (`image`,`media_quality`, aj `mixed` s fotkou — zoznam v `plan.media`): plán
  `AB_DIR/scripts/plan_media.py` (dedup, osoby ≥ 50 %, malé sloty ostré, brand grading) → dávka →
  `execute_workflow("GtjjsjvLqPar2FwB")` → `get_execution` → `sideload-image` → `update-element`. Klientove
  fotky (`client_only`) negeneruj (foto osoby = fallback silueta). **Video-animácie (Runway) zatiaľ nepodporované**
  → `needs_input` + report. Viď `AB_DIR/references/media.md`.
- **4e — Globálne prvky, RAZ** (`global`): `find-element("netovapomoc"/"fajne-weby")` na footer/popup/CTA
  bublinu + GDPR/cookies → `AB_DIR/scripts/fill_globals.py` (tokeny `AB_DIR/references/global_tokens.json`) →
  `update-element`. Právny TEXT sa nemení, len identifikačné údaje firmy (`content.legal`). Menu nemeň.
  Zmenu over **re-readom** proti `global_before_<id>.json` (nie sú v page štruktúre → diff-brána ich nevidí).
- **Produktová stránka:** cielená úprava = ako page (blueprint `products`); **celoplošné vyplnenie** prázdnej
  produktovej stránky patrí `wp-autobuilder` (Fáza 7) — presmeruj. Viď `change_types.md`.

### Fáza 5 — QA + diff + uloženie naživo (per dotknutá stránka)
Podľa `references/qa_fix.md`:
1. `get-page-structure(post_id)` → `snapshot_after_<page>.json`.
2. **Diff brána:** `python SKILL_DIR/scripts/diff_structure.py --before snapshot_before_<page>.json --after
   snapshot_after_<page>.json --allowed <cielené element_id>` (pri štruktúre `--allow-added`/`--allow-removed`).
   **FAIL-CLOSED** pri prázdnom `--allowed`. Kolaterál/neočakávaná štruktúra → **exit 1 → ROLLBACK** a nepublikuj.
3. **QA zmien:** `python SKILL_DIR/scripts/qa_fix_check.py --structure snapshot_after_<page>.json --changeset
   changeset.json --page <page_type/hint>` — žiadny nový placeholder, cieľové hodnoty prítomné, CTA ≤ 21, žiadny agentúrny odkaz.
4. **Uloženie (gate):** ak diff **aj** QA prešli bez CHÝB (+ re-ready obrázkov/skrytí/globálov sedia) a
   `publish_after_fix=true` → zmena je naživo (draft → status `publish`). Inak **rollback**: in-place prvky
   z `element_before_<id>.json` (globály z `global_before_<id>.json`, kit z `kit_before.json`); štruktúru zmaž/obnov.
   `publish_after_fix=false` → nechaj + preview URL na ručnú kontrolu.

### Fáza 6 — Report
Vypíš súhrn: **`instance_domain`** (na ktorý web sa opravovalo — z Fázy 1) a **per zmena**: `id`, stránka,
čo sa zmenilo (**before → after**), stav (`applied`/`verified`/`unresolved`/`needs_input`/`skipped`),
QA+diff výsledok, uloženie (naživo / rollback + dôvod). Osobitne:
- **Nevyriešené pripomienky** (`unresolved` — cieľ sa nenašiel/nejednoznačný, konflikt) — čo overiť ručne.
- **Chýbajúce klientske vstupy** (`needs_input`) — čo dodať (logá referencií, `google_url`, ceny, IČO/DIČ,
  foto osoby, konkrétne štatistiky), aby sa dokončili odložené zmeny.
- Priorita vs neprioritné pripomienky.

## Nemenné invarianty
Rovnaké honesty pravidlá ako autobuilder + fixer-špecifické:
- **Meň LEN cielené prvky** z pripomienky — žiadny kolaterál (diff-brána to vynucuje).
- Nevymýšľať ceny, recenzie, mená, hodnotenia, fakty, čísla, technické parametre — vždy dodá klient.
- Nemeniť brand fonty, layout, štruktúru menu, poradie fotiek (farby len globálne v kite).
- CTA ≤ 21 znakov; CTA cieľ = klientova stránka/kontakt, nikdy agentúrny `/produktova-stranka/`.
- Nikdy nenechať agentúrne zvyšky (`netovapomoc`/`fajne-weby`, cudzí kontakt/adresu) — rieši Fáza 4e.
- Ak sa cieľ nedá jednoznačne lokalizovať → NEaplikuj naslepo (`unresolved` + report).

## Overenie skriptov
- `python SKILL_DIR/scripts/selftest.py` — synteticky overí reťazec validate → plan → diff → qa (vrátane
  detekcie kolaterálu a placeholderu) bez živého webu.
- `python SKILL_DIR/scripts/validate_changeset.py --changeset <changeset.json>` — kontrola štruktúry pripomienok.
- Vzor changesetu: `references/changeset.example.json` (odvodený z reálnych pripomienok).

## Vzťah k wp-autobuilder
- **Autobuilder** = postaviť nový web z briefu (všetky sloty). **Fixer** = opraviť existujúci web podľa pripomienok.
- Fixer **znovupoužíva** autobuilderove blueprinty a skripty (`AB_DIR`) — neduplikuje ich (viď architecture.md).
- Ak pripomienka de-facto žiada „postav odznova celú stránku", presmeruj na `wp-autobuilder`.
