# Dispatch podľa typu zmeny — ktorý nástroj + bezpečnostné pravidlá

Pre každý `change.type` je definované: akým MCP nástrojom/vzorom sa aplikuje, ktorý znovupoužitý skript
pomáha, a čo NIKDY nerobiť. Po každej zmene **over re-readom** a pridaj `element_id` medzi cielené pre
diff-bránu (Fáza 5). Lokalizáciu (nájdenie `element_id`) rieši `localization.md`.

---

## `text` — copy (nadpisy, popisy, CTA text, eyebrow)
- **Nástroj:** `elementor-mcp-batch-update(post_id, operations=[{element_id, settings}])` alebo
  `elementor-mcp-update-widget` pre jeden prvok. `heading`→`{title}`, `text-editor`→`{editor:"<p>…</p>"}`,
  `button`→`{text}`.
- **Dĺžka/SEO (z pripomienok):** popisné bloky **3–4 riadky (HP, O nás)**, **4–5 riadkov (Služby)**, viac
  SEO kľúčových slov segmentu, v rámci stránky rovnako dlhé. Detail: `AB_DIR/references/intake.md`
  („Dĺžka textov a SEO"). Tón 2. os. mn. č.
- **Countery O nás (`counter_number_plus_sentence`):** číslo+ na 1. riadku, krátka veta pod ním
  („100+ hostí mesačne, ktorí sa k nám pravidelne vracajú"). Číslo LEN od klienta; `cast:"int"`.
- **Invarianty:** CTA ≤ 21 znakov; štatistika začína číslom; NEVYMÝŠĽAJ fakty/čísla/ceny.
- **Nikdy:** neprepisuj `global` widgety a zdieľané CTA per stránka (rieši Fáza 4e).

## `link` — cieľ odkazu (CTA, Google recenzie)
- **Nástroj:** `update-widget(element_id, settings={link:{url:…, is_external:"", nofollow:""}})` (celý link objekt).
- **Google recenzie (`link_or_hide`):** ak klient dodal `content.reviews.google_url` → nalinkuj tlačidlo
  a nastav `button_text`/`rating`, a ak dodal aj `content.reviews.items[]` (author/text/rating), naplň karty
  (read-merge-write). Ak **nedodal `google_url` ani `items`** → **skry** sekciu (viď `visibility`).
  **Obsah recenzií sa NEŤAHÁ automaticky z Googlu** (Google Reviews API nie je zapojené) — „automaticky
  vložiť recenzie" znamená z **klientom dodaných** dát; ak ich klient nedodal, označ `needs_input` + report.
  Mená/text/rating **nikdy nevymýšľaj**.
- **CTA cieľ:** klientova konverzná stránka (`/kontakt/`, `tel:`); NIKDY agentúrny `/produktova-stranka/`.

## `contact` — kontaktné fakty (telefón, mail, adresa, fakturačné údaje)
- **icon-list / repeater (READ-MERGE-WRITE, nie batch):** `get-element-settings(post_id, element_id)` →
  v poli `icon_list` uprav IBA `text` (`<b>Telefón:</b> …`, `<b>E-mail:</b> …`) — **`_id` a `selected_icon`
  zachovaj** → `update-widget`.
- **Fakturačné údaje (pevné poradie, každý na riadku `<br>`):** meno spoločnosti / adresa / IČO / DIČ /
  IČ DPH. Chýbajúci údaj vynechaj (neprázdny riadok nenechávaj). Zdroj: `content.legal`/`billing_html`.
- **Mapa:** ak `map_query` chýba → mapu skry; nikdy nenechaj agentúrnu/cudziu adresu.
- **Nikdy:** nenechaj agentúrny kontakt (`…@netovapomoc.sk`, cudzie číslo).

## `color` — brand farby (globálny kit, RAZ)
- **Vzor read-merge-write (atomicky), presne ako autobuilder Fáza 1b** (`AB_DIR/references/colors.md`):
  1. `list-templates(template_type="kit")` → kit `post_id`.
  2. `get-global-settings` → `kit_before.json` (celý kit = záloha/rollback).
  3. `python AB_DIR/scripts/build_palette.py --brief brief.json --current kit_before.json --kit AB_DIR/references/kit_colors.json -o kit_new.json`
     (vloží brand system farby + dopočíta celú paletu — light/dark/transparent/oddeľovač/form; zachová typografiu/CSS).
  4. **JEDEN atomický zápis:** `update-page-settings(post_id=<kit_id>, settings=<kit_new.json>)`.
- **Farby zdroja:** z dotazníka (`brand.*`); ak chýbajú → z loga (`extract_palette.py`) alebo pôvodného webu.
- **Nikdy:** čiastočný zápis, `update-global-colors` ani `add-custom-css` na kit (resetnú celý kit).
  Brand paleta sa mení LEN globálne, nikdy po sekciách. Rollback = zapíš `kit_before.json` späť.
- **Výnimka — pozadie konkrétnej sekcie (`transparent_primary_bg`):** pripomienka „to zelené pozadie nech
  je stransparentnená primárna" NIE je zmena brand palety, ale **pozadia jedného kontajnera** →
  `update-element(container_id, settings={background_background:"classic", background_color:"rgba(<primárna>, 0.08–0.12)"})`.
  Primárnu vezmi z kitu (`get-global-settings`). Toto je **cielená per-element výnimka** z „farby len globálne"
  (rovnako to robí autobuilder pri zelenom pozadí ikonkovej sekcie produktu) — mení sa len background token
  daného kontajnera, nie brand paleta. Zapíš `element_before` (rollback) a pridaj id medzi `--allowed`.

## `image` — výmena / generovanie obrázka
- **Pipeline ako autobuilder Fáza 4b** (`AB_DIR/references/media.md`): dávka → n8n → sideload → priradenie.
  1. `python AB_DIR/scripts/plan_media.py …` (dedup + rozloženie + osoby ≥ 50 %) → plán.
  2. Dávka `{job_id, client, brand, defaults, reference_faces, items[]}`; prompty podľa
     `AB_DIR/references/image_prompt_guide.md`; **brand farby jemne zakomponuj** (primárna+sekundárna),
     zlaď color grading so stránkou.
  3. `execute_workflow(workflow_id="GtjjsjvLqPar2FwB", executionMode="manual", inputs={type:"webhook", webhookData:{method:"POST", body:<dávka>}})` → `get_execution` (poll).
  4. Pre `status:"ok"`: `sideload-image(image_url)` → media id → `update-element` na image slot.
- **Klientove fotky (`client_only`):** foto osoby (Kontakt), galéria — NIKDY negeneruj tvár; upload/enhance klientovej.
- **Foto osoby na Kontakte — fallback silueta:** ak klient nedodá foto, vygeneruj **neutrálnu siluetu muža/ženy
  (beztvárová, bez identity)** — to NIE je generovanie skutočnej tváre (dovolené), alebo slot skry. Nikdy agentúrnu fotku.
- **Hero pozadie (`generate_abstract_bg`):** vygeneruj abstraktné pozadie, vlož ako obrázok (nižšia priorita).

## `media_quality` — kvalita, dedup, rozmer, farebnosť (z pripomienok)
- **Dedup (`dedupe`):** žiadna fotka viac než **1× na stránke** (klientove fotky 2× len v galérii).
  `plan_media.py` to vynucuje; pri revízii over aktuálne priradenie a duplicitné nahraď/preskladaj.
- **Osoby ≥ 50 % (`person_ratio_50`):** medzi naplnenými slotmi aspoň polovica `shot_type:"person"`.
- **Rozmazané malé fotky (`sharp_small`):** malé cik-cak sloty generuj/uprav vo **vyššom rozlíšení**
  (aspoň natívny rozmer slotu), nech nie sú rozmazané ako veľké.
- **Vylepšenie / odstránenie neporiadku (`enhance` / `remove_clutter`):** `mode:"edit"`/`"enhance"` na
  klientovej fotke (napr. odstrániť stavebné vedrá z fotky domu, zvýšiť kvalitu).
- **Šírka/pomer (`match_other_sections`):** ak je fotka v jednej sekcii užšia, zjednoť `aspect_ratio`/
  rozmer s ostatnými sekciami stránky (uprav nastavenie image widgetu / vygeneruj v správnom pomere).
- **Farebnosť (`brand_grading`):** generované fotky ladia s primárnou/sekundárnou farbou stránky.
- **Video-animácie (rozanimované fotky) — ZATIAĽ NEPODPOROVANÉ:** sesterský Runway workflow (`mode:"video"`)
  **ešte neexistuje** (viď `AB_DIR/references/media.md` → „Video ešte nie je"). Takúto pripomienku **neaplikuj
  naslepo** — nastav `status:"needs_input"` (chýba Runway workflow ID/kontrakt) a zapíš do reportu. Vlož zatiaľ
  len statický obrázok, ak to dáva zmysel.

## `visibility` — skry / zmaž sekciu
- **Skry sekciu:** `update-element(element_id, settings={hide_desktop:"hidden", hide_tablet:"hidden", hide_mobile:"hidden"})`
  na **kontajner** sekcie. Preferuj **skryť** pred trvalým zmazaním (bezpečnejšie, vratné).
- **Prázdne sekcie (`hide_if_empty`):** sekcie, ktoré AI nevie naplniť (klient nedodal obsah), skry.
  Ak blueprint má pre ne hide-slot (`hide_if_missing`, napr. `hp.reviews.tabs`, referencie/logá), použi ho.
- **Referencie/logá:** ak klient nedodal logá → skry sekciu; ak dodal → vlož logá (image).
- **Galéria (duplicitné varianty):** master má viac variantov galérie — nechaj **jeden** (zvyčajne prvý),
  ostatné skry; rozloženie nemeň (4 fotky v riadku). Viď autobuilder Fáza 4 (gallery).
- **Overenie skrytia (NIE cez diff):** kontajnery často **nemajú `settings_summary`**, takže `hide_*` sa
  v štruktúre nemusí prejaviť a `diff_structure.py` skrytie nezachytí. Aplikovanie preto over **explicitným
  re-readom** `get-element-settings(container_id)` (že `hide_*` je nastavené). Diff-bránu použi na kolaterál;
  ak reálne **mažeš** prvok, `diff_structure.py --allow-removed <id kontajnera>` (nie blanket `--allow-structural`).

## `structure` — duplikuj / preusporiadaj sekciu (najrizikovejšie)
- **Duplikovanie sekcie (napr. kontakt na kontakt):** ak je kontaktov viac, **každý kontakt = vlastná
  sekcia** (nie dva kontakty pod jednou fotkou). Duplikuj kontajner kontaktnej karty a naplň druhým kontaktom.
- **Postup opatrne:** over pred aj po (`get-page-structure`); zisti **id nového podstromu** a spusti
  `diff_structure.py --allow-added <id nových kontajnerov>` (radšej než blanket `--allow-structural`), aby
  brána stále zachytila **neočakávané** pridania/odobrania inde. Pri pochybnosti → `unresolved` + report.
- **Rollback štruktúry:** pridaný podstrom sa nevráti zápisom starých nastavení — treba ho **zmazať**
  (`delete-element`/ekvivalent); odobraný prvok **znova vytvoriť**. Ak MCP nevie prvok zmazať/vytvoriť,
  štruktúrnu zmenu **nerob** autonómne — označ `unresolved` + report (bezpečnejšie než nevratný zásah).
- **Nemeň** menu štruktúru, layout ani poradie fotiek (invariant).

## `global` — footer, CTA bublina, popup, GDPR, cookies (RAZ na inštanciu)
- **Vzor ako autobuilder Fáza 6** (`AB_DIR/references/globals_blueprint.json`, `global_tokens.json`):
  1. `find-element(search_text="netovapomoc"` / `"fajne-weby")` na footer/popup/CTA bublinu a stránky GDPR/cookies.
  2. `get-element-settings` → `python AB_DIR/scripts/fill_globals.py --brief brief.json --tokens AB_DIR/references/global_tokens.json --in value.html -o value_new.html` → `update-element`/`update-widget`.
  3. Footer: logo klienta + kontakt; **menu štruktúru nemeň**. CTA bublina + globálne CTA: text + cieľ klienta.
- **Právny TEXT GDPR/cookies sa NEMENÍ** — menia sa len identifikačné údaje firmy (`content.legal`).
- **Kontrola:** po behu over, že nikde neostal `netovapomoc`/`fajne-weby` (qa_fix_check to hlási ako varovanie).

## `mixed` — viac vecí v jednej pripomienke
Rozlož na čiastkové úkony podľa typov vyššie a aplikuj postupne; každý čiastkový cieľ lokalizuj a over
zvlášť. Ak obsahuje obrázkový pod-úkol, zaraď ho aj do media dávky (Fáza 4d). V reporte uveď všetky čiastky.

## Produktové stránky (`page_type:"products"`)
- **Cielená úprava** existujúcej produktovej stránky (text/obrázok/ikonka/pozadie) → rieš ako bežnú page zmenu
  cez `AB_DIR/references/products_slot_blueprint.json` + `resolve_slots.py` (rovnaký hybrid ako iné stránky).
- **Ikonková sekcia (3× `xpro-icon-box`):** popisy ≥ 3 riadky, približne rovnako dlhé; **zelené pozadie** sekcie
  → transparentná primárna (viď `color` → `transparent_primary_bg`). Ikony smú dediť globálnu primárnu.
- **Ikonky podľa kontextu:** ak to widget dovolí, zmeň `selected_icon` na kontextovo vhodnú (best-effort);
  ak nie, nechaj a zapíš do reportu. Nie je to blocker.
- **„Vyplniť aspoň základnú šablónu" (prázdna/podvyplnená produktová stránka):** ak pripomienka žiada
  **naplniť celú stránku od šablóny** (nie cielenú opravu), to je robota **`wp-autobuilder`** (Fáza 7 produkty) —
  presmeruj tam (zdroj = produktové dáta klienta), fixer sa naň nehodí. Kritérium: chýba > polovica slotov / je to celoplošné vyplnenie.

## Mimo rozsahu (zapíš do reportu, needituj naslepo)
- **Import albumov z existujúceho webu klienta** (NIE SU PRIORITY v pripomienkach) — zatiaľ nepodporované;
  označ `needs_input`/mimo rozsahu a zapíš do reportu.
- **Sťahovanie obsahu recenzií z Google** (Google Reviews API) — nezapojené (viď `link`).
- **Video-animácie (Runway)** — workflow ešte neexistuje (viď `media_quality`).
