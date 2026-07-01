# Intake pripomienok → changeset.json

Cieľ: z **voľných pripomienok** (čo treba na webe zmeniť) vyrobiť štruktúrovaný `changeset.json`
**plne autonómne, bez doplňujúcich otázok**. Formát a enumy: `references/changeset.schema.json`;
hotový vzor: `references/changeset.example.json`.

## 1) Získaj pripomienky (dva zdroje — skill sám rozozná)
Používateľ zadá **zdroj** pripomienok. Podporované sú DVA a skill sám zistí, ktorý dostal:

**A) Google Drive dokument** (default, konzistentné s autobuilderom):
1. Zo zdroja (názov klienta „test1", cesta, GDrive ID/odkaz) nájdi priečinok klienta: `search_files`.
2. V ňom nájdi dokument s pripomienkami — hľadaj názvy obsahujúce **„pripomienky" / „revízia" /
   „úpravy" / „feedback" / „poznámky"** (napr. priečinok `05_Pripomienky` alebo súbor `pripomienky.docx`).
   Ak štruktúra sedí inak, vyber súbor, ktorý významovo obsahuje zoznam úprav webu.
3. Prečítaj `read_file_content(fileId=...)` (vráti text aj z docx/xlsx/gdoc).

**B) Text priamo v chate:** ak používateľ vloží pripomienky ako text do konverzácie, použi ten text
priamo (žiadny GDrive krok). Ak vloží aj odkaz na GDrive aj text, prednosť má **explicitný text v chate**.

Ak zdroj nie je jasný, použi **posledný spomenutý priečinok klienta** z konverzácie; iba ak naozaj
žiadny nie je, vypýtaj si jednu vec — kde sú pripomienky. (Toto je jediná povolená otázka; ďalej beží autonómne.)

## 2) Znormalizuj na changeset.json (Claude, bez pýtania sa)
Pripomienky sú voľný text (často v štýle `pripomienky.md`): odrážky, odseky, občas **odkaz na konkrétnu
URL** (napr. „na .../sluzby-2/ je v poslednej sekcii fotka užšia"). Rozbi ich na **jednotlivé zmeny**
(`changes[]`), každú s jednou logickou úpravou. Pravidlá mapovania:

### Priorita
Ak dokument delí pripomienky na sekcie **„PRIORITY"** / **„NIE SU PRIORITY"** (ako `pripomienky.md`),
nastav `priority`: `priority` pre prioritné, `low` pre neprioritné, inak `normal`.

### Stránka (`page_hint`, `page_type`)
- **`page_hint`** = URL/titul/slug spomenutý v pripomienke doslova (napr. `https://news6.eshopion.sk/sluzby-2/`,
  „HOMEPAGE", „O nás", „kontakt"). Ak nič, `null`.
- **`page_type`** = ktorý blueprint použiť (rozpoznanie typu podľa nadpisov pripomienky):
  `hp` (HOMEPAGE/HP), `about` (O nás), `services` (Služby), `contact` (Kontakt), `pricing` (Cenník),
  `gallery` (Galéria), `products` (Produktové stránky). Ak sa nedá určiť → `unknown`/`null` (hybrid fallback).

### Typ zmeny (`type`) — rozhoduje, ktorým vzorom sa aplikuje (viď `change_types.md`)
| Signál v pripomienke | `type` | `scope` |
|---|---|---|
| „texty na 3–4 riadky", „viac SEO", prepíš nadpis/popis | `text` | `page` |
| „nalinkuj Google recenzie", zmeň cieľ tlačidla | `link` | `page` |
| telefón/mail/fakturačné údaje/adresa | `contact` | `page` |
| „farby do globálnych", prefarbi web, brand paleta | `color` | `kit` |
| vymeň/vygeneruj/vlož obrázok, pozadie hero | `image` | `page` |
| dedup fotiek, vylepši kvalitu, odstráň neporiadok, rozmazané malé fotky, pomer/šírka fotky | `media_quality` | `page`/`instance` |
| „sekcie bez obsahu zmaž", skry duplicitnú galériu | `visibility` | `page` |
| „duplikuj kontaktnú sekciu", preusporiadaj | `structure` | `page` |
| footer, CTA bublina, popup, GDPR, cookies | `global` | `global` |
| pripomienka mieša viac vecí naraz | `mixed` | podľa hlavnej |

- **`scope`**: `page` (jedna stránka), `kit` (globálny kit farieb — RAZ), `global` (theme templaty — RAZ),
  `instance` (pravidlo pre VŠETKY stránky, napr. „nikde neduplikuj fotky").

### Lokalizačné napovede (`target_selector`) — vyplň, čo je zrejmé (zvyšok nechá lokalizácia)
- `slot_id` — ak miesto zodpovedá **existujúcemu pomenovanému slotu** v blueprinte daného typu stránky
  (napr. `hp.hero.h1`, `about.stat1.number`, `services.block2.text`). **Over, že slot naozaj existuje** v
  `AB_DIR/references/<page>_slot_blueprint.json` a že `widget` sedí (countery O nás sú `widget:"counter"`,
  nie `heading`; `hp.reviews.tabs` je **kontajner hide-slot** — nepoužívaj ho ako cieľ tlačidla/textu).
  Ak zmena zasahuje viac slotov naraz (napr. všetky 4 countery) alebo si slotom nie si istý, nechaj
  `slot_id:null` a spoľahni sa na `search_text`/`section_index`/`widget`.
- `search_text` — **presný/blízky súčasný text** z pripomienky (na `find-element`), napr. `"netovapomoc"`,
  citovaný nadpis, agentúrny e-mail.
- `section_index` — ak pripomienka hovorí „posledná sekcia" → `-1`, „prvá/hero" → `0`, „sekcia 4" → `3`.
  Pozn.: „posledná sekcia" = posledná **obsahová** sekcia, ktorá drží hľadaný widget — lokalizácia
  **preskočí** koncové zdieľané template/footer kontajnery (xpro-template, `do_not_touch`). Viď `localization.md`.
- `widget` — očakávaný typ: `heading|text-editor|button|image|counter|icon-list|nested-accordion|container`.
- **Zmiešaná zmena s obrázkom** (`type:"mixed"` + obrázkový pod-úkol, napr. „zjednoť šírku fotky"):
  daj `target_selector.widget:"image"` alebo do `intent`/`rule` zaraď slovo fotka/obrázok/pozadie — plánovač
  ju potom zaradí aj do media dávky (Fáza 4d). Ešte lepšie: rozdeľ na samostatnú `image`/`media_quality` zmenu.

### Zámer a cieľ (`intent`, `desired`)
- `intent` — 1 veta: čo sa má stať (normalizované).
- `desired`:
  - `value` — konkrétny literál (nový text, URL, HEX, `aspect_ratio`), ak ho pripomienka dáva.
  - `rule` — pravidlo bez literálu: `len_3_4_riadky`, `len_4_5_riadkov`, `more_seo`,
    `match_other_sections`, `enhance`, `remove_clutter`, `dedupe`, `person_ratio_50`,
    `transparent_primary_bg`, `counter_number_plus_sentence`, `link_or_hide`, `hide_if_empty`,
    `one_section_per_contact`, `fill_globals_from_legal`, `brand_palette_from_brief`, `generate_abstract_bg`.
  - `text_spec` — pre textové zmeny: `{contains:[kľúčové slová], max_chars, tone}`.

### Chýbajúce klientske vstupy (`client_inputs_needed`, `status`)
Ak zmena vyžaduje **niečo, čo klient musí dodať** (logá referencií, `google_url`, ceny, foto osoby,
IČO/DIČ, konkrétne štatistiky) a nie je to v podkladoch → vypíš do `client_inputs_needed` a nastav
`status:"needs_input"`. Zmena sa **nezahodí** — v behu sa buď aplikuje čiastočne (napr. „skry, ak chýba"),
alebo sa preskočí a zaradí do reportu ako „treba dodať".

## 3) Doplnenie briefu (voliteľné)
Niektoré pripomienky (napr. „prepíš texty s viac SEO", „vyplň fakturačné údaje", „nastav brand farby")
potrebujú **klientske dáta**. Ak v priečinku klienta existuje **dotazník** (ako pre autobuilder), načítaj
z neho potrebné polia podľa `AB_DIR/references/intake.md` (mapovanie dotazník → brief) a ulož ako
`brief.json` do pracovného priečinka. Fixer ho použije ako zdroj hodnôt (texty, `brand.*`, `content.legal`,
`content.reviews.google_url`…). Ak dotazník nie je, pracuj len s tým, čo je v pripomienkach, a chýbajúce
označ `needs_input`.

## 4) Validuj a ulož
`python SKILL_DIR/scripts/validate_changeset.py --changeset changeset.json` — over štruktúru
(unikátne id, platné `type`/`scope`, povinné polia). **Chyby oprav sám** (neopýtaj sa). Vypíše aj počty
podľa typu/scope/priority a **zoznam chýbajúcich klientskych vstupov** — ten zaraď do hlavičky behu.
Ulož `changeset.json` do pracovného priečinka a pokračuj Fázou 1.
