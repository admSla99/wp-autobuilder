---
name: wp-autobuilder
description: >
  Autonómne poskladá WordPress stránku z briefu klienta cez Elementor MCP. Používateľ zadá iba
  ZDROJ podkladov (priečinok klienta na Google Drive, napr. „test1"); skill sám nájde dotazník,
  prečíta ho, vytvorí brief.json, naplní textové sloty stránok webu (HP, O nás, Služby, Kontakt,
  Cenník) podľa pravidiel (rules.json), spraví QA a stránky po úspešnej QA publikuje (draft ostáva len ak
  QA hlási chybu) — celé bez prerušovania a bez doplňujúcich otázok.
  Použi tento skill VŽDY, keď používateľ chce vygenerovať/poskladať/naplniť/vytvoriť web alebo HP
  stránku z briefu, dotazníka alebo podkladov na GDrive, „spustiť autobuilder", „spraviť kópiu HP a
  naplniť ju", alebo automatizovať tvorbu webu klienta v Elementore — aj keď nepovie presne „skill".
  Spúšťa sa ako jeden vstupný bod a vnútri prejde celý proces (intake → klon → sloty → texty → QA).
---

# WP Autobuilder

Orchestrátor, ktorý z **podkladov klienta na Google Drive** poskladá stránku v Elementore podľa
**pravidiel**. Architektúra a fázy: `references/architecture.md`. Pokryté stránky (blueprinty):
**HP, O nás (about), Služby (services), Kontakt (contact), Cenník (pricing), Galéria (gallery)** — fázy 2–5 bežia
v slučke pre každú stránku z `brief.pages`.

## Autonómia — DÔLEŽITÉ
Tento skill beží **od zdroja po hotovú PUBLIKOVANÚ stránku bez prerušovania**.
- **NEPÝTAJ sa** na doplňujúce informácie a **nepoužívaj AskUserQuestion.** Keď niečo v dotazníku
  chýba, použi zdokumentovaný default alebo pravidlo „skry sekciu" z `rules.json` — a pokračuj.
- **Publikovanie (default):** po Fáze 5 sa stránka **automaticky publikuje**, ak QA prešla bez CHÝB.
  **Bezpečnostná poistka — QA gate:** ak `qa_check` nájde čo i len jednu CHYBU, stránku **nechaj ako DRAFT**
  a zapíš dôvod do reportu (nikdy nepublikuj rozbitú stránku). VAROVANIA QA (globálne zvyšky šablóny)
  publikovaniu nebránia. Flag `publish_after_build` (default `true`) vie publikovanie vypnúť (→ ostane draft).
- Cieľ: používateľ v novej session iba spomenie skill a zadá zdroj — zvyšok dobehne sám.

## Vstup od používateľa
Používateľ zadá **iba zdroj podkladov** — názov/cestu/ID **priečinka klienta na Google Drive**
(napr. „test1", „klient Enova", alebo GDrive odkaz). Všetko ostatné (nájdenie dotazníka, čítanie,
vytvorenie `brief.json`) **robí skill sám**. Ak používateľ zdroj nezadá, použi posledný spomenutý
priečinok klienta z konverzácie; iba ak naozaj žiadny nie je, vypýtaj si jednu vec — cestu k podkladom.

Na **vlastnej inštancii klienta** je cieľová stránka priamo HP (nájde sa cez `list-pages`).
Pri **testovaní na zdieľanom dev webe** používateľ navyše zadá `post_id` draft **kópie HP**
(aby sa neprepísal master) — viď Fáza 2.

Flag `apply_global_colors` (default `true` — globálne farby sa reálne zapíšu do kitu) rozhoduje,
či sa farby zapíšu, alebo sa len vygeneruje „color plan". Nastav `false` IBA ak cieľový web zdieľa
jeden kit s inými klientmi/masterom (vtedy by zápis prepísal aj ich) — viď Fáza 1b.

Flag `publish_after_build` (default `true`) rozhoduje, či sa stránka po úspešnej QA publikuje. Pri
`true` sa publikuje len ak QA prejde bez CHÝB (inak ostáva draft + zápis do reportu); `false` = vždy ostane
draft (publikuje človek) — viď Fáza 5.

## Potrebné konektory
- **Elementor MCP** — cieľový web (klon a úpravy stránky).
- **Google Drive MCP** — podklady klienta (dotazník, logo, fotky).
- **n8n (oficiálne MCP s `execute_workflow`)** — generovanie/úprava médií (Image 2.0; Runway neskôr).
  Potrebné len vo **Fáze 4b Médiá**, a to iba ak `brief.media.source != "placeholder"`. Inak vizuály = placeholder.
Over dostupnosť: `elementor-mcp-list-pages` a GDrive `search_files`.

> **Prepnutie inštancie:** skill sám `elementor-mcp` connector NEprepína. Ak ukazuje na iný web než
> cieľového klienta, najprv prepni inštanciu — manuálny postup (`Prepni-Elementor.bat`, reštart Claude)
> je v projektovom **`CLAUDE.md`**. Bez správnej inštancie nepokračuj.

## Pracovný priečinok a cesty
- **SKILL_DIR** = priečinok tohto súboru. Skripty: `SKILL_DIR/scripts/`, dáta: `SKILL_DIR/references/`.
- Medzisúbory (`brief.json`, `structure.json`, `slotmap.json`, `ops.json`) ukladaj do **aktuálneho
  pracovného / outputs priečinka**. Vždy používaj **absolútne cesty**.

## Pipeline (jeden beh)

Pracuj po krokoch, po každom zápise over výsledok. **NEROB zmeny na master stránke ani v globálnom kite.**

### Fáza 0 — Intake z GDrive  → `brief.json`
Postupuj presne podľa `references/intake.md`:
1. Z používateľom zadaného zdroja nájdi priečinok klienta na GDrive (`search_files`).
2. Nájdi v ňom podpriečinok s formulárom („01_Formulár a info" / „Formulár") a v ňom **dotazník**
   (`*.xlsx`) + prípadné `informácie.docx`. Prečítaj cez `read_file_content`.
3. Znormalizuj odpovede na `brief.json` podľa mapovania v `intake.md` a vygeneruj HP copy podľa
   pravidiel (claim, štatistiky, 3 služby, 3 hodnotové bloky, CTA). **Bez pýtania sa.**
4. Over `brief.json` oproti `references/brief.schema.json`. Ulož do pracovného priečinka.

### Fáza 1 — Pravidlá
Skontroluj `references/rules.json` (stránka `hp`). Ak sa Excel zmenil:
`python SKILL_DIR/scripts/compile_rules.py <cesta_k_01_SABLONA_v2.xlsx>`.

### Fáza 1b — Brand / Farby (read-merge-write, atomicky)
Farby sa nastavujú IBA globálne v kite, nikdy po sekciách (01_SABLONA: „AI NESMIE meniť farby").
POZOR — zápisy do kitu sú **deštruktívne (partial-replace)**: každý prepíše celý kit a nezahrnuté
polia resetne na defaulty. Preto vždy **celý kit naraz**. Detaily a varovania: `references/colors.md`.
1. Nájdi kit: `elementor-mcp-list-templates(template_type="kit")` → `post_id` (napr. 6).
2. `elementor-mcp-get-global-settings` → ulož `kit_current.json` (celý kit = zároveň záloha).
3. `python SKILL_DIR/scripts/build_palette.py --brief brief.json --current kit_current.json --kit SKILL_DIR/references/kit_colors.json -o kit_new.json` (vloží brand farby, zachová typografiu/CSS/ostatné).
4. **Zápis farieb (default `apply_global_colors=true`):** `elementor-mcp-update-page-settings(post_id=<kit_id>, settings=<kit_new.json>)` — JEDEN atomický zápis (predtým MUSÍ existovať `kit_current.json` ako záloha z kroku 2). NIKDY čiastočne, NIKDY `update-global-colors` ani `add-custom-css` na kit.
5. **Iba ak `apply_global_colors=false` (zdieľaný kit):** kit NEMENIŤ; vygeneruj `kit_new.json` + „color plan" do reportu.
- Rollback: `update-page-settings(post_id=<kit_id>, settings=<kit_current.json>)`. Typografiu needitovať (iba ak brief žiada font).

### Fáza 2 — Urči cieľové stránky
Na novej WP inštancii klienta sú stránky už hotové (z template inštalácie). Skill **NEklonuje** —
pracuje priamo na cieľových stránkach:
- `elementor-mcp-list-pages` → pre každú stránku z `brief.pages` nájdi `post_id` podľa
  `page_title_candidates` v jej blueprinte (nepredpokladaj ID natvrdo):
  | page | blueprint | typický titul |
  |---|---|---|
  | hp | `hp_slot_blueprint.json` | „Hp" |
  | about | `about_slot_blueprint.json` | „O nás" |
  | services | `services_slot_blueprint.json` | „Služby" |
  | contact | `contact_slot_blueprint.json` | „Kontakt" |
  | pricing | `pricing_slot_blueprint.json` | „cenník" |
  | gallery | `gallery_slot_blueprint.json` | „Jednoúrovňová galéria" / „Galéria" |
- Stránku z `brief.pages` bez blueprintu preskoč a zapíš do reportu. Zaznač `preview_url`/`edit_url`.
- **Pozn. k doménam:** obsah skopírovaných stránok môže referencovať cudzie domény (master `newo…`,
  agentúrny `netovapomoc.sk`) v URL obrázkov — sú to zvyšky z predlohy, NIE iná inštancia. Reálne
  editovaná inštancia je tá, kam zapisuje Elementor MCP (= `wordpress.base_url` pre médiá vo Fáze 4b).

> **Teraz (testovanie na zdieľanom dev webe):** nepracuj na živých masteroch — prepísal by si master
> pre ostatných. Použi **draft KÓPIE** stránok a ich `post_id` zadaj ako vstup (alebo pokračuj na
> posledných vytvorených kópiách). Kópie sa v skille nevytvárajú; na vlastnej inštancii klienta sú
> cieľom priamo živé stránky.

**Fázy 3 → 4 → 4b → 5 odtiaľto bež v slučke pre KAŽDÚ cieľovú stránku** (medzisúbory per stránka:
`structure_<page>.json`, `slotmap_<page>.json`, `ops_<page>.json`).

### Fáza 3 — Mapovanie slotov (per stránka)
- `elementor-mcp-get-page-structure(post_id=<cieľová stránka>)` → ulož `structure_<page>.json`.
- `python SKILL_DIR/scripts/resolve_slots.py --structure structure_<page>.json --blueprint SKILL_DIR/references/<page>_slot_blueprint.json -o slotmap_<page>.json`
- Ak resolver hlási nesúlad typu widgetu, **nepokračuj naslepo** — pravdepodobne sa zmenil master a treba aktualizovať blueprint.

### Fáza 4 — Texty (per stránka)
- `python SKILL_DIR/scripts/build_ops.py --brief brief.json --slotmap slotmap_<page>.json --blueprint SKILL_DIR/references/<page>_slot_blueprint.json -o ops_<page>.json`
  (rešpektuje CTA ≤ 21 znakov a „štatistika musí začínať číslom"; varovania vypíše). build_ops navyše:
  - **hide_if_missing** (všeobecné): kontajner sekcie bez obsahu v briefe dostane hide-op (skrytie sekcie).
    „Chýba" = `None`/prázdny reťazec/**prázdny zoznam**/prázdny objekt (`is_missing`), takže funguje aj pre
    list-based prítomnosť (napr. referenčné logá `[]` → sekcia sa skryje). Platí pre všetky stránky, nielen cenník.
  - **clear_if_missing**: placeholder texty skrytých riadkov/sekcií sa vyčistia (kvôli QA),
  - **cast:"int"** (countery O nás): číslo sa zapíše ako int do `ending_number`,
  - `link.url` setting: zapíše sa vnorený link objekt (tel:/mailto:/maps),
  - **repeater sloty preskočí** — viď nižšie.
- Pošli `ops_<page>.json` ako `operations` do `elementor-mcp-batch-update(post_id=<cieľová stránka>, operations=...)`.
- **Auto-skrytie voliteľných sekcií bez obsahu (všetky stránky):** sekciu, pre ktorú klient nedodal obsah,
  **skry** (hide-op na kontajner) + vyčisti jej placeholder texty — nikdy nenechaj viditeľný demo obsah.
  Týka sa najmä: **referencie/logá** (ak klient nedodal logá), **blog** (ak niet článkov), prázdne value/cik-cak
  bloky. Pri **Google recenziách** skry sekciu len ak klient recenzie nemá; ak má, vlož odkaz na Google profil —
  OBSAH recenzií negeneruj (Google Reviews API). Ak sekcia ešte nie je v blueprinte (napr. referencie/recenzie/blog
  na HP), zisti cestu jej kontajnera z `get-page-structure` a pridaj hide-slot (`widget:"section"`, `hide_if_missing`,
  `brief` = pole prítomnosti) — NEHÁDŽ cesty naslepo, over typ cez resolver.
- **Gallery widgety (Galéria):** master má **viac variantov galérie** (hlavná, sekundárna, kartové mini-galérie).
  Pri bežných fotkách použi **IBA jeden variant — `gallery.widget.main`** a všetky fotky daj tam; **ostatné varianty
  skry** (hide-op na `gallery.widget.secondary` a na kartovú sekciu + jej nadpisy/labely), aby sa nezobrazovali prázdne
  alebo duplicitné galérie. Plnenie read-merge-write: nahraj klientove fotky do WP médií (n8n upload / sideload), potom
  `update-widget` s celým poľom `gallery=[{filter,_id,images:[{id,url}…]}]` z `content.gallery.categories` — **poradie
  fotiek 1:1 od klienta, NIČ negeneruj**. **Rozloženie nemeň**; `item_per_row` (biasované na 4): **≤4→2, 5–8→3, 9+→4**.
  `show_filter` len ak kategórií >1. Ak klient fotky nedodal, celú galériovú sekciu skry a zapíš do reportu.
- **Repeater sloty (FAQ na O nás):** otázky akordeónu NIKDY neprepisuj batchom. Postup:
  1. `elementor-mcp-get-element-settings(post_id, element_id=<nested-accordion z slotmap>)`,
  2. v poli `items` uprav IBA `item_title` podľa `content.about.faq.items[k].q` — **`_id` zachovaj!**,
  3. `elementor-mcp-update-widget(post_id, element_id, settings={"items": <celé upravené pole>})`.
- **Recenzie:** napĺňaj z `content.reviews` (od klienta), inak sekciu skry — viď Fáza 7 (nikdy nevymýšľaj).
- **NEEDITUJ** `global` widgety (zdieľané CTA), hlavičkové riadky
  cenníka, icon-list na Kontakte, ani obrázky (image sloty rieši Fáza 4b).

### Fáza 4b — Médiá (obrázky cez n8n Image 2.0)
Spusti **iba ak** `brief.media.source != "placeholder"`. Inak fázu preskoč (vizuály ostanú placeholder).
Kontrakt: `references/media.md`; image sloty: pole `image_slots` v `references/<page>_slot_blueprint.json`
(každá pokrytá stránka má vlastné). Dávku môžeš poslať jednu pre všetky stránky naraz (slot_id má
prefix stránky). Sloty so `source_policy:"client_only"` (fotka osoby na Kontakte, galéria) NIKDY negeneruj —
len upload/enhance klientovej fotky; ak nie je: na Kontakte vlož **neutrálny avatar/placeholder** (`fallback:"neutral_avatar"`,
ikona/silueta bez identity), v galérii slot preskoč. Nikdy nenechaj agentúrnu fotku z masteru.
1. **Index-cesty image slotov sú už vyplnené a overené** pre všetky pokryté stránky (36 slotov, resolver OK
   proti živým draftom 2026-06-18). Pri **zmene mastera** ich znova over: `structure.json` (Fáza 3) +
   `resolve_slots.py`. Slot bez `path` alebo s `ok=false` preskoč a zapíš do reportu (negeneruj naslepo).
1b. **Naplánuj priradenie médií (dedup + rozloženie + osoby):**
   `python SKILL_DIR/scripts/plan_media.py --blueprint SKILL_DIR/references/<page>_slot_blueprint.json --source <brief.media.source> --client-photos <počet fotiek klienta> -o plan_<page>.json`.
   Plán zabezpečí: **žiadna fotka vo dvoch slotoch** (dedup), klientove vs generované rovnomerne,
   generované do veľkých aj malých slotov, **osoby ≥ 50 %** naplnených slotov, a `client_only` sa NEgeneruje.
   Dávku v kroku 2 stavaj PODĽA `plan_<page>.json` (mode/shot_type/client_index per slot); `mode:"skip"` slot vynechaj.
2. **Zostav dávku** `{ job_id, client, brand, defaults, wordpress, reference_faces, items[] }` (media.md / SPEC 1.1):
   - pre každý image slot jeden `item` (`slot_id`, `mode`, `prompt`, `aspect_ratio`, `shot_type`, `seo_filename`, `alt`);
     `prompt` + `seo_filename` stavaj podľa `references/image_prompt_guide.md` z `image_slots[].prompt_context`
     + briefu + brand HEX. **Nepýtaj sa**; generuj presne toľko promptov, koľko je slotov.
   - `wordpress.upload = true` na produkcii (na dev bez WP app password nechaj placeholder).
   - **`wordpress.base_url` = doména WP inštancie, ktorú edituješ cez Elementor MCP** (kam sa nahrávajú médiá),
     NIE URL obrázkov v obsahu (tie môžu ukazovať na master `newo…`/agentúrny `netovapomoc.sk` — zvyšky z predlohy).
     Zisti ju cez `sideload-image` (doména vo vrátenej `url`). Nesúlad → WP 401 `rest_cannot_create`.
   - **3 vetvy podľa `brief.media.source`:** `client` = len upload/`enhance` klientových fotiek (`input_image_url`
     z GDrive), negeneruj nové · `generated` = všetko `mode:"generate"` · `mix` = väčšie sekcie fotky klienta
     (enhance), menšie generované.
3. **Spusti workflow (Webhook Trigger):** `execute_workflow(workflow_id="GtjjsjvLqPar2FwB", executionMode="manual", inputs={ type:"webhook", webhookData:{ method:"POST", body:<dávka> } })` → `get_execution`
   (poll do dokončenia). Výstup `{ job_id, status, results[] }` (SPEC 1.2).
4. **Priraď do slotov** — pre každý `result` so `status:"ok"`: ak `wp_media_id` → použi priamo, inak
   `elementor-mcp-sideload-image(image_url)` → media id; potom `elementor-mcp-update-element` na image slot
   (element_id z resolvera podľa `image_slots[].path` + `setting`).
5. **Chyby:** `status:"error"` alebo `partial` → daný slot zopakuj, alebo nechaj placeholder a zapíš do reportu (negeneruj naslepo). Aspoň 1 video / stránka rieši sesterský Runway workflow (rovnaký kontrakt).

### Fáza 5 — QA + odovzdanie (per stránka)
- `elementor-mcp-get-page-structure(post_id=<cieľová stránka>)` → `structure_after_<page>.json`.
- `python SKILL_DIR/scripts/qa_check.py --structure structure_after_<page>.json --blueprint SKILL_DIR/references/<page>_slot_blueprint.json`
  (musí prejsť bez CHÝB: žiadny „Lorem ipsum"/„dolor sit amet"/„Služba 1–6"/„Item One…"/„Obrázok 1–9"/
  „popis služby"/„cenník nadpis", štatistiky číselné, CTA ≤ 21 znakov; `optional` sloty smú ostať prázdne).
- QA hlási aj **VAROVANIA „globálny zvyšok šablóny"** (napr. „netovapomoc", „Nazovklientovejdomeny", „Horúce strely",
  „default-logo"). To NIE sú chyby skillu — sú to agentúrne/demo placeholdery v **globálnej téme** (hlavička, päta,
  popup, newsletter, Google recenzie, referenčné logá), ktoré skill zámerne nemení. Zapíš ich do reportu na **ručné
  vyčistenie v master téme**, neprepisuj ich per stránka.
- **Publikovanie (QA gate):** ak QA prešla **bez CHÝB** (varovania nevadia) a `publish_after_build=true`
  (default), stránku **publikuj** — nastav status na `publish` (napr. `elementor-mcp-update-page-settings`
  s post statusom `publish`; ak konkrétne pole nie je isté, over cez `get-page-structure`/page settings).
  Ak QA hlási čo i len jednu **CHYBU**, stránku **nechaj ako draft** a chybu zapíš do reportu.
- Vypíš súhrnný report za všetky stránky: `preview_url`, stav (publikovaná / draft + dôvod), čo je naplnené
  (texty / farby / médiá), čo ostalo placeholder/skryté, a QA výsledok per stránka.

### Fáza 6 — Globálne prvky a právne stránky (RAZ na inštanciu, nie per stránka)
Blueprint: `references/globals_blueprint.json`; tokeny: `references/global_tokens.json`. Footer, CTA bublina,
popup a stránky GDPR/cookies obsahujú **agentúrne údaje** (Netova pomoc s.r.o., `jan@netovapomoc.sk`,
`info@fajne-weby.cz`, „Copyright … Netovapomoc.sk", IČO/DIČ…). Tie nahraď údajmi klienta z `content.legal`:
1. **Nájdi cieľové widgety** cez `find-element(post_id/template, search_text="netovapomoc"` resp. `"fajne-weby")`
   na: GDPR (14065), cookies (10840), footer (template 10998), popupy (15139, 15926), CTA bublina (header/footer).
   Nehádž element_id natvrdo — dohľadaj (theme template mohol byť aktualizovaný).
2. Pre každý nájdený widget: `get-element-settings` → ulož hodnotu (`editor`/`description_text`/`email_to`) →
   `python SKILL_DIR/scripts/fill_globals.py --brief brief.json --tokens SKILL_DIR/references/global_tokens.json --in value.html -o value_new.html`
   → `update-element`/`update-widget` s novou hodnotou. fill_globals hlási NEnahradené agentúrne zvyšky.
3. **Footer štruktúrne:** nastav logo klienta (image), kontakt (tel/mail/adresa); **menu štruktúru nemeň** (invariant).
4. **CTA bublina:** nastav CTA text + cieľový odkaz (tel:/kontakt) klienta; farby/kit needituj.
5. **Právny TEXT GDPR/cookies sa obsahovo NEMENÍ** — menia sa len identifikačné údaje firmy.
6. **Kontrola:** po behu spusti QA / over, že nikde neostal `netovapomoc`/`fajne-weby` (qa_check AGENCY_LEFTOVERS
   už tieto hlási ako varovanie — po Fáze 6 majú zmiznúť).

### Fáza 7 — Produktové stránky (1 stránka na produkt) + Google recenzie
Blueprint: `references/products_slot_blueprint.json`; copy podľa `references/product_copy_guide.md`.
Spusti len ak `brief.content.products` nie je prázdne (a `products` je v `brief.pages`).
- **Klonovanie (nový krok — inde skill neklonuje):** pre KAŽDÝ produkt vytvor vlastnú stránku z mastera
  („Produktová stránka" template / duplikát 17045) cez Elementor MCP, potom v slučke:
  1. do `brief.content.product` (singular) vlož aktuálny produkt z `content.products[i]`,
  2. `get-page-structure` → `resolve_slots` → `build_ops` → `batch-update` (rovnako ako iné stránky),
  3. **foto produktu** = upload klientovho (`client_only`, image slot `products.hero.photo`) — negeneruj,
  4. **ikonková sekcia** (3× `xpro-icon-box`): naplň `title`+`description` (≥3 riadky, rovnako dlhé); ikony aj
     nadpisy už dedia globálnu primárnu (Fáza 1b). **Zelené pozadie sekcie** (kontajner `[5]`) zmeň na
     **transparentnú primárnu** (rgba primárnej ~8–12 % alfa) — jednorazová výnimka z „AI nemení farby per sekcia".
  5. **DEMO sekcie** mastera (Featured stories, Services, Visual identity, image-carousel…) sú anglické zvyšky —
     skry/vyčisti alebo počkaj na vyčistený master (viď `do_not_touch.demo_sections` v blueprinte).
- **Google recenzie (produkt aj HP) — VÝHRADNE od klienta (`content.reviews`):** naplň link tlačidlo
  (`google_url` → `link.url`, `button_text`), `rating` a karty (`items[].author/text`). Ak klient nedodal
  `google_url` → skry intro/link sekciu; ak nedodal `items` → skry sekciu kariet (hide_if_missing).
  **Nikdy nevymýšľaj recenzie, mená ani rating** (invariant). Tým sa mení doterajší „needituj recenzie" stav —
  recenzie sa teraz plnia z klientových dát, ale len z nich.

## Nemenné invarianty (z rules.json → global_invariants)
Nikdy sa neprepíšu z briefu ani z Excelu:
- Nevymýšľať ceny — vždy dodá klient.
- Nevymýšľať recenzie, mená ani hodnotenia.
- Nemeniť fakty, čísla, legislatívu, technické parametre, poradie fotiek.
- Nemeniť brand farby, fonty, layout, štruktúru menu.
- CTA default max 21 znakov; nepoužívať „Kliknite sem / Viac / Tu / Kúpte hneď".

## Mapovanie brief → sloty
- Textové sloty: pole `slots` v `references/<page>_slot_blueprint.json` (pole `brief` pri každom slote).
- Image sloty: pole `image_slots` tamtiež (`prompt_context` = brief pole, `shot_type`, `aspect_ratio`, `path`, `setting`).
- **hp**: hero H1 ← `content.claim`; štatistiky ← `content.kpis[]`; CTA ← `content.cta_*`; karty ← `content.services[]`;
  hodnotové bloky ← `content.value_props[]`; video ← `content.video_section`; eyebrows/H3 ← `content.sections`.
- **about**: hero (2 varianty na masteri, rovnaký text) ← `content.about.hero`; 4 countery ←
  `content.about.stats[]` (ending_number/suffix/title); 3 bloky ← `content.about.blocks[]`;
  FAQ ← `content.about.faq` (odpovede = text sloty, otázky = repeater).
- **services**: hero ← `content.services_page.hero` (CTA = button, editovateľný); 5 blokov ←
  `content.services_page.blocks[]` (CTA blokov sú global — needitovať).
- **contact**: všetko ← `content.contact.*` (fakty 1:1; phone/email aj ako `link.url`; mapa ← `map_query`).
- **pricing**: nadpis ← `content.pricing.title`; tabuľka 1 ← `packages[]`; tabuľka 2 ← `items[]`
  (max 6 riadkov, chýbajúce sa skryjú); benefity ← `benefits[]`. Ceny LEN od klienta.
- **gallery**: H1 ← `content.gallery.title`; podsekcie/karty ← `section_labels[]`/`cards[]`;
  fotky ← `categories[].photos` cez gallery widgety (read-merge-write, fotky LEN od klienta).

## Kvalita textu a fallbacky (povinné)
- **Dĺžka a SEO (záväzné, detail v `intake.md` → „Dĺžka textov a SEO"):** popisné bloky píš ako plnohodnotný
  web copywriting (nie „botovité" jednovetové útržky): **HP a O nás 3–4 riadky, Služby 4–5 riadkov** (≈2–4 vety),
  s prirodzene zapracovanými kľúčovými slovami segmentu. V rámci stránky drž bloky približne rovnako dlhé.
- **Cikcak / value bloky (HP, O nás, Služby):** každý blok napíš ako súvislý, konkrétny text v uvedenej dĺžke.
  Ak blok obsahuje viac textových widgetov, naplň **všetky** — NIKDY nenechaj druhý odsek ako „Lorem ipsum".
- **Karty služieb (HP):** naplň názov aj popis každej karty z `content.services[]`. Ak je kariet na masteri viac než
  služieb v briefe, prebytočné karty skry — needituj ich pôvodný (marketingový) text, ale ani ho nenechaj viditeľný.
- **Galéria:** titulky/popisy ber od klienta; ak chýbajú, nechaj prázdne alebo sekciu skry — NIKDY nenechaj
  „Item One"/„Obrázok 1" + „Lorem ipsum". Ak klient galériu nemá, celú galériovú sekciu skry a zapíš do reportu.
- **Kontakt — úvodný text:** píš prirodzene a konkrétne k oboru klienta; žiadne generické/„botovité" frázy.
- **Kontakt — mapa:** ak `content.contact.map_query` chýba, mapa sa automaticky skryje (`hide_element_if_missing`),
  nech neostane default adresa šablóny. Nikdy nenechaj cudziu/agentúrnu adresu.
- **Kontakt — foto osoby:** `client_only` (negeneruj). Ak klient foto nedodá, použi neutrálny avatar/placeholder
  alebo slot skry — NIKDY nenechaj agentúrnu fotku z masteru.

## Overenie skriptov
- `python SKILL_DIR/scripts/selftest.py` — synteticky overí reťazec resolve → build_ops → QA
  (text + image sloty) **pre všetky pokryté stránky** (hp, about, services, contact, pricing, gallery) bez živého webu.
- `python SKILL_DIR/scripts/palette_selftest.py` — overí farebnú logiku (merge zachová kit) bez dotyku webu.
- Príklady briefov: `references/brief.example.json` (Podlahy Novák), `references/brief.example.enova.json` (reálny intake).

## Rozšírenie
- Ďalšia stránka = pridať `references/<page>_slot_blueprint.json` (rovnaký formát; index-cesty over na
  živom masteri cez `get-page-structure`); stránka už je v `rules.json`. Zatiaľ nepokryté: blog,
  products/product_page, area. **team_refs (Referencie) sa nepokrýva zámerne** — živý master je
  prezentácia Google recenzií (dáta z Google Reviews API, samostatný zdroj, nie text-fill).
- Médiá = zapojené (n8n `gpt-image-2-2026-04-21`, Fáza 4b); video (Runway) = sesterský workflow s rovnakým kontraktom (`mode:"video"`).
