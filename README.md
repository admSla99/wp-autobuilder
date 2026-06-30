# wp-autobuilder — dokumentácia aktuálneho stavu

Skill pre Claude Cowork, ktorý z podkladov klienta **autonómne poskladá stránky WordPress webu**
(HP, O nás, Služby, Kontakt, Cenník, Galéria) v Elementore. Jeden vstupný bod, beží bez prerušenia,
a po úspešnej QA stránky **automaticky publikuje** (draft ostáva len ak QA hlási chybu, alebo ak je
vypnutý flag `publish_after_build`).

---

## 1. Veľký obraz — dátový tok

Sú dva nezávislé vstupy, ktoré sa stretnú v skille:

```
PRAVIDLÁ (raz za projekt/šablónu)              PODKLADY (na každého klienta)
01_SABLONA_v2.xlsx                              Dotazník + súbory na Google Drive
   │  (človek edituje)                             │  (klient dodá)
   ▼  python compile_rules.py                      ▼  intake (Claude číta a normalizuje)
references/rules.json  ──────────┐         ┌──────  brief.json
                                 ▼         ▼
                         wp-autobuilder (orchestrátor, SKILL.md)
                                 │  + <page>_slot_blueprint.json (hp/about/services/contact/pricing/gallery) + kit_colors.json
                                 ▼  Elementor MCP (+ Google Drive + n8n médiá)
                         hotové stránky webu (publikované) + QA report
```

Kľúčové: **skill nikdy nečíta surový Excel.** Excel sa najprv skompiluje do `rules.json`
a skill pracuje s tým. To je zámer — oddelenie „autorskej vrstvy" (Excel, edituje netechnik)
od „runtime vrstvy" (rules.json, číta stroj).

---

## 1b. Kto spúšťa skripty (mentálny model)

Skill nie je program, čo beží sám. Runtime je **Claude v Cowork session** — žiadny cron/server.

- **Claude (agent) = vykonávateľ.** Číta SKILL.md, spúšťa skripty cez shell, volá MCP nástroje a rozhoduje (intake, generovanie copy).
- **Python skripty = kalkulačky.** Deterministický výpočet (Excel→rules, sloty, operácie, paleta, plán médií, globály, QA). Bez siete a bez MCP.
- **MCP (Elementor, Google Drive, n8n) = jediné reálne čítanie/zápis** na web, Drive a generovanie médií; volá ich Claude.

Príkazy sú napísané priamo v SKILL.md (napr. `python SKILL_DIR/scripts/build_ops.py …`); Claude ich v danej fáze spustí. Výstup skriptu (napr. `ops.json`) potom Claude pošle do MCP nástroja.

---

## 2. Odkiaľ sa berie rules.json a ako sa berie Excel do úvahy

Trojvrstvový model pravidiel:

1. **Autorská vrstva — `01_SABLONA_v2.xlsx`** (na Google Drive / lokálne). 11 hárkov, jeden na typ
   stránky (HP, O nás, Služby, Kontakt, cenník, produkty, Produktová stránka, galéria, blog,
   referencie, okolie). Obsahuje: názvy sekcií, počty položiek (min–max), typ vizuálu, **AI môže
   meniť / AI NESMIE meniť** (guardrails), zdroj dát, `slot_id`, STAV (POVINNÁ/VOLITEĽNÁ/ALTERNATÍVA)
   a stĺpec Podmienky (napr. „CTA max 21 znakov", „cenu nesmie vymyslieť"). Toto edituje človek.

2. **Kompilát — `references/rules.json`.** Vzniká spustením `scripts/compile_rules.py <cesta_k_v2.xlsx>`,
   ktorý Excel prečíta, znormalizuje a **zvaliduje** (chýbajúce stĺpce, protirečivé počty, sekcia bez
   slot_id…) a vypíše report. Aktuálne: **11 stránok, 133 sekcií, 0 chýb.** Štruktúru rules.json
   popisuje `references/rules.schema.json`. Skill číta toto.

3. **Skill — procedúra + nemenné invarianty.** Skill rešpektuje pravidlá z rules.json:
   `build_ops.py` vynucuje „CTA ≤ 21 znakov" a „štatistika musí začínať číslom"; `qa_check.py` ich
   kontroluje; tvrdé invarianty (nevymýšľať ceny/recenzie/fakty, nemeniť brand/layout) sú v rules.json
   v poli `global_invariants` aj priamo v SKILL.md a **nedajú sa prepísať z briefu**.

**Kedy prekompilovať:** po každej zmene Excelu spusti `compile_rules.py` — prepíše rules.json.
Ak report hlási chyby, tvorba stránky sa nemá spustiť.

---

## 3. Súbory v skille

| Súbor | Účel |
|---|---|
| `SKILL.md` | Orchestrátor — popis, fázy pipeline, invarianty, vstupný kontrakt |
| `README.md` | Tento prehľad |
| `CHANGELOG.md` | História zmien skillu |
| `references/rules.json` | Skompilované pravidlá obsahu (z Excelu) — skill číta toto |
| `references/rules.schema.json` | JSON schéma rules.json (validácia) |
| `references/hp_slot_blueprint.json` | Mapovanie sekcií HP na index-cesty v strome + na polia briefu |
| `references/about_slot_blueprint.json` | Blueprint stránky O nás (countery, FAQ repeater) |
| `references/services_slot_blueprint.json` | Blueprint stránky Služby (CTA bloky = global) |
| `references/contact_slot_blueprint.json` | Blueprint stránky Kontakt (fakty 1:1, link.url) |
| `references/pricing_slot_blueprint.json` | Blueprint stránky Cenník (hide/clear_if_missing riadkov) |
| `references/gallery_slot_blueprint.json` | Blueprint stránky Galéria (gallery widgety, fotky len od klienta) |
| `references/products_slot_blueprint.json` | Blueprint produktovej stránky (Fáza 7, klon na produkt) |
| `references/globals_blueprint.json` | Globálne prvky (footer, CTA bublina, popup, GDPR/cookies) — Fáza 6 |
| `references/global_tokens.json` | Agentúrne tokeny → mapovanie na `content.legal` (pre fill_globals) |
| `references/brief.schema.json` | Štruktúra briefu (vstup do buildu) |
| `references/brief.example.json` | Príklad briefu (Podlahy Novák) |
| `references/brief.example.enova.json` | Reálny príklad z intake (Enova House) |
| `references/intake.md` | Postup Google Drive → brief.json (mapovanie dotazníka) + dĺžky textov/SEO |
| `references/hp_copy_guide.md` | Zákazníkov štandard pre copy hlavnej stránky (AKO písať HP texty) |
| `references/about_copy_guide.md` | Zákazníkov štandard pre copy stránky O nás |
| `references/GAP3_navrh_cta_portfolio.md` | Návrh riešenia CTA odkazov + HP portfolio (do_not_touch widgety) |
| `references/colors.md` | Postup pre farby (read-merge-write) + zistenia |
| `references/kit_colors.json` | Sloty Elementor kitu + pravidlá odvodenia odtieňov |
| `references/media.md` | Kontrakt médií (n8n dávka, SPEC) pre Fázu 4b |
| `references/image_prompt_guide.md` | Návod na stavbu promptov + SEO názvov pre generované obrázky |
| `references/product_copy_guide.md` | Návod na copy produktovej stránky (Fáza 7) |
| `references/product_master_cleanup.md` | Poznámky k vyčisteniu demo sekcií master produktovej stránky |
| `references/architecture.md` | Fázy a ich stav vs návrhový dokument |
| `scripts/compile_rules.py` | Excel `01_SABLONA_v2.xlsx` → `rules.json` + validačný report |
| `scripts/resolve_slots.py` | Štruktúra stránky → mapa `slot_id` → aktuálne `element_id` |
| `scripts/build_ops.py` | brief + slotmap + blueprint → operácie pre `batch-update` |
| `scripts/qa_check.py` | Predpublikačná QA (placeholdery, CTA dĺžky, číselné štatistiky, agentúrne zvyšky) |
| `scripts/check_intake.py` | Pred-letová kontrola úplnosti briefu (chýbajúce klientske vstupy: BLOCKER/WARN/INFO); nezastavuje build |
| `scripts/build_palette.py` | brief + aktuálny kit → nový kit (farby, read-merge-write) |
| `scripts/build_page_color_css.py` | Z nového kitu vyrobí per-stránka custom_css (farby len pre danú stránku, nedotkne sa kitu) |
| `scripts/extract_palette.py` | Z loga klienta vytiahne brand farby (intake, ak dotazník farby nemá) |
| `scripts/kit_to_payload.py` | Pomôcka: get-global-settings → payload (záloha/obnova) |
| `scripts/plan_media.py` | Plán priradenia fotiek do image slotov (dedup, rozloženie, osoby ≥ 50 %) |
| `scripts/fill_globals.py` | Nahradí agentúrne tokeny údajmi klienta v globáloch/právnych stránkach (Fáza 6) |
| `scripts/selftest.py` | Test reťazca resolve → build_ops → QA pre všetkých 6 pokrytých stránok |
| `scripts/palette_selftest.py` | Test farebnej logiky (merge zachová kit, mení len farby) |

---

## 4. Pipeline — ako to beží krok po kroku

- **Fáza 0 — Intake (`intake.md`).** Používateľ zadá iba zdroj (GDrive priečinok klienta, napr. „test1").
  Claude nájde priečinok, prečíta `01_Formulár a info/dotazník_.xlsx` (+ info.docx), namapuje stĺpce na
  brief, vygeneruje copy podľa pravidiel a uloží `brief.json` (validuje voči `brief.schema.json`). Ak
  dotazník nemá farby, `extract_palette.py` ich vytiahne z loga. Nakoniec `check_intake.py` spraví
  **pred-letovú kontrolu úplnosti** — vypíše chýbajúce klientske vstupy (logo, IČO/DIČ, ceny, fotky,
  príjemca formulára…) ako BLOCKER / WARN / INFO. **Build sa nezastavuje**, zoznam ide do hlavičky behu
  a do záverečného reportu.
- **Fáza 1 — Pravidlá.** Skontroluje `rules.json` (stránka `hp`); ak treba, prekompiluje z Excelu.
- **Fáza 1a — Overenie inštancie (echo identity, PRED prvým zápisom).** Skill nevie, na ktorý web je
  connector pripojený (všetky klientske weby majú rovnaké tituly stránok). Preto ešte pred akýmkoľvek
  zápisom prečíta **živú doménu** pripojenej inštancie (`list-pages` → doména z `preview_url`) a vypíše ju
  spárovanú s klientom z briefu. Dev/pracovné inštancie (`newX`/`newsX.eshopion.sk`) sú platné ciele a
  neblokujú sa; build **nepokračuje len** pri presnej zhode s agentúrnym hostom z denylistu
  (`newo.eshopion.sk`). `instance_domain` sa zapamätá a uvedie v reporte (Fáza 5). Zámenu dvoch platných
  inštancií zachytí iba človek z echo riadku (skill je autonómny, nepýta sa).
- **Fáza 1b — Brand / Farby (`colors.md`).** Read-merge-write celého kitu (viď kap. 7). Flag `color_mode`
  (default `"kit"`) rozhoduje o zápise: `kit` = atomický zápis do globálneho kitu; `page_css` = `--e-global-color-*`
  len na cieľové stránky (`build_page_color_css.py`, nedotkne sa kitu); `plan` = len „color plan" bez zápisu.
- **Fáza 2 — Cieľové stránky.** Predpoklad je **jedna vlastná inštancia klienta** (jeden web = jeden klient);
  stránky sú už hotové z template inštalácie a skill pracuje priamo na **živých stránkach** — **NEklonuje**
  (výnimka = produkty, Fáza 7). `list-pages` → pre každú stránku z `brief.pages` nájdi `post_id` podľa
  `page_title_candidates` v jej blueprinte. Žiadne zdieľané dev weby, draft kópie ani „test mód".
- **Fáza 3 — Mapovanie slotov.** `get-page-structure` → `resolve_slots.py` → `slotmap_<page>.json`.
- **Fáza 4 — Texty.** `build_ops.py` (brief + slotmap + blueprint) → `ops_<page>.json` → `batch-update`.
  Repeatery (FAQ na O nás, galéria) sa plnia ručne read-merge-write (zachovaj `_id`).
- **Fáza 4b — Médiá (`media.md`).** Len ak `brief.media.source != "placeholder"`. `plan_media.py` naplánuje
  priradenie (dedup, osoby ≥ 50 %) → dávka promptov → n8n `execute_workflow` (Image 2.0) → priradenie do
  image slotov cez `sideload-image` + `update-element`. Video = sesterský Runway workflow (TODO).
- **Fáza 5 — QA + publikovanie.** `qa_check.py`; ak QA prejde bez CHÝB a `publish_after_build=true` (default),
  stránka sa **publikuje**. Pri čo i len jednej CHYBE ostáva **draft** + dôvod v reporte (QA gate).
  Varovania (globálne zvyšky šablóny) publikovaniu nebránia. Súhrnný report uvádza aj **`instance_domain`**
  (na ktorý web sa stavalo — z Fázy 1a) a zopakuje **BLOCKER/WARN** z completeness checku (Fáza 0).
- **Fáza 6 — Globálne prvky a právne stránky (raz na inštanciu).** Footer, CTA bublina, popup, GDPR/cookies
  obsahujú agentúrne údaje → `fill_globals.py` ich nahradí údajmi z `content.legal`. Právny TEXT sa obsahovo
  nemení, menia sa len identifikačné údaje firmy. Blueprint: `globals_blueprint.json`.
- **Fáza 7 — Produktové stránky + Google recenzie.** Len ak `brief.content.products` nie je prázdne. Pre KAŽDÝ
  produkt sa klonuje vlastná stránka (jediné miesto, kde skill klonuje) a naplní podľa `products_slot_blueprint.json`
  + `product_copy_guide.md`. Recenzie sa plnia **výhradne z klientových dát** (`content.reviews`), inak sekcia skryje.

---

## 5. Ako funguje mapovanie slotov (blueprint + resolver)

Pri klonovaní Elementor pridelí nové `element_id`, ale **poradie a štruktúra ostávajú**. Preto
`<page>_slot_blueprint.json` adresuje každý slot **index-cestou** v strome (napr. hero H1 = `[0,0,0]`),
nie natvrdo cez ID. `resolve_slots.py` podľa cesty nájde aktuálne ID a overí typ widgetu. `build_ops.py`
potom k slotom priradí hodnoty z briefu (pole `brief` v blueprinte) a vyrobí operácie. Vďaka tomu skill
funguje na ľubovoľnej kópii/inštancii bez zásahu do master šablóny.

---

## 6. Ako funguje intake (Google Drive → brief)

`intake.md` popisuje: nájdi priečinok klienta → podpriečinok „01_Formulár a info" → dotazník (`.xlsx`)
→ `read_file_content` → mapovanie stĺpcov dotazníka na polia briefu → vygenerovanie copy (claim,
štatistiky, služby, hodnotové bloky, CTA, about, contact…) podľa pravidiel → validácia voči schéme.
Dĺžky textov a SEO sú záväzné (HP a O nás 3–4 riadky, Služby 4–5 riadkov). Honesty pravidlo:
nevymýšľať ceny/recenzie/fakty; marketingové formulácie sú OK, tvrdé fakty musia byť z dotazníka.

---

## 7. Ako funguje farby (read-merge-write) — a prečo tak

Zistenie z testu: **zápisy do Elementor kitu sú deštruktívne** — `update-page-settings` aj
`add-custom-css` prepíšu celý kit a nezahrnuté polia resetnú na defaulty; `update-global-colors` píše
len custom paletu (nie system) a nuluje alfa hex. Preto jediný bezpečný vzor:
1. `get-global-settings` → ulož `kit_current.json` (celý kit + záloha),
2. `build_palette.py --current kit_current.json` → vloží brand farby a **zachová** typografiu/CSS/ostatné,
3. **jeden atomický** `update-page-settings(post_id=<kit>, settings=<kit_new.json>)`,
4. rollback = zapísať `kit_current.json` naspäť (pri `page_css` rollback = `{custom_css:""}`).
Flag `color_mode` riadi zápis: `kit` (default, atomický zápis do kitu), `page_css` (farby len na cieľové
stránky cez `build_page_color_css.py`, kit ostáva nedotknutý) alebo `plan` (len „color plan" do reportu). Detaily: `colors.md`.

---

## 8. Stav — čo je hotové a čo nie

**Hotové:**
- Autonómny intake z Google Drive → brief.json (mapovanie dotazníka, copy podľa pravidiel, farby z loga ak chýbajú).
- Rules engine: Excel → compile_rules.py → rules.json (11 stránok, 133 sekcií, 0 chýb).
- **6 pokrytých stránok** (blueprint + resolver + selftest): HP, O nás, Služby, Kontakt, Cenník, Galéria.
- Fáza Farby bezpečným read-merge-write (system + odvodená paleta, zachová typografiu/CSS).
- **Médiá zapojené** — n8n Image 2.0 (`gpt-image-2-2026-04-21`, workflow `GtjjsjvLqPar2FwB`): plán (dedup,
  osoby ≥ 50 %), generovanie/enhance, upload do WP, priradenie do image slotov. 3 vetvy: client / generated / mix.
- **Globálne prvky a právne stránky (Fáza 6)** — footer, CTA bublina, popup, GDPR/cookies: agentúrne údaje
  nahradené údajmi klienta cez `fill_globals.py` (právny text sa obsahovo nemení).
- **Produktové stránky (Fáza 7)** — klon na produkt + naplnenie podľa blueprintu/copy guide.
- **Recenzie** — plnené z klientových dát (`content.reviews`); nikdy sa nevymýšľajú.
- QA (placeholdery, CTA dĺžky, číselné štatistiky, agentúrne zvyšky) + **automatické publikovanie** za QA gate.
- **Pred-letová kontrola úplnosti** (`check_intake.py`) — chýbajúce klientske vstupy hneď po intaku (nezastaví build).
- **Overenie inštancie pred prvým zápisom** (Fáza 1a, echo identity + denylist agentúrnych hostov).
- Direktíva autonómie (bez doplňujúcich otázok), self-testy (resolve→build→QA pre 6 stránok, farby).

**Zatiaľ nie / vedome vynechané:**
- **Video médiá** — sesterský Runway workflow (rovnaký kontrakt, `mode:"video"`) je TODO.
- **Globálne sekcie štruktúrne** mimo textu (Theme Builder header/footer layout, zdieľané `xpro-template`) sa riešia raz na inštanciu, nie automaticky per stránka.
- **Ďalšie stránky bez blueprintu:** blog, area (okolie). **team_refs (Referencie)** sa nepokrýva zámerne — živý master je prezentácia Google recenzií (samostatný zdroj, nie text-fill).
- **Obsah Google recenzií** sa negeneruje — len odkaz na profil + dáta dodané klientom (Google Reviews API ako zdroj nie je integrovaný).

---

## 9. Ako spustiť a testovať

**Použitie (po inštalácii skillu), nová session:**
> „Použi wp-autobuilder. Podklady klienta sú v GDrive priečinku test1. Spusti celý proces."

**Self-testy (bez živého webu):**
- `python scripts/selftest.py` — reťazec resolve → build_ops → QA pre všetkých 6 pokrytých stránok.
- `python scripts/palette_selftest.py` — farebná logika (merge zachová kit).

**Kontrola úplnosti briefu:** `python scripts/check_intake.py --brief <brief.json>` (`--json` pre strojový výstup) — vypíše BLOCKER/WARN/INFO chýbajúcich klientskych vstupov; vždy exit 0 (nezastavuje build).

**Po zmene Excelu:** `python scripts/compile_rules.py <cesta_k_01_SABLONA_v2.xlsx>` → nové rules.json.

---

## 10. Známe obmedzenia / poznámky

- **Kit je site-wide:** zápis do kitu (`color_mode="kit"`) prefarbí celý web. Ak nechceš zasiahnuť globálny kit, použi `color_mode="page_css"` (farby len na cieľové stránky) alebo `"plan"` (len návrh). Predpoklad behu = vlastná inštancia klienta.
- **Multi-inštancia:** každý klient = nová WP inštancia; Elementor MCP sa nasmeruje na ňu (skill connector sám neprepína — viď `CLAUDE.md` / `Prepni-Elementor.bat`).
- **Publikovanie:** default je auto-publish po úspešnej QA (`publish_after_build=true`). Nastav `false`, ak má vždy ostať draft na ručné schválenie.
- **Povolenia nástrojov:** prvý beh v Coworku môže vyžadovať schválenie zápisov (vytvorenie/úprava stránky, čítanie GDrive, n8n).

---

## 11. Pokrytie stránok (jún 2026)

| page | blueprint | master | text sloty | image sloty | špeciality |
|---|---|---|---|---|---|
| hp | hp_slot_blueprint.json | 11154 | 34 | 9 | — |
| about | about_slot_blueprint.json | 13109 | 30 | 13 | countery (cast int), FAQ repeater (read-merge-write) |
| services | services_slot_blueprint.json | 12842 | 13 | 8 | CTA blokov = global (needitovať), videá = Runway |
| contact | contact_slot_blueprint.json | 13359 | 12 | 1 | fakty 1:1, link.url (tel/mailto/maps), fotka osoby client_only |
| pricing | pricing_slot_blueprint.json | 15389 | 54 | 1 | ceny len od klienta; hide_if_missing + clear_if_missing riadkov |
| gallery | gallery_slot_blueprint.json | — | 15 | 4 | jeden variant galérie, fotky 1:1 od klienta, item_per_row biasovaný |
| products | products_slot_blueprint.json | 17045 | 26 | 1 | Fáza 7: klon na produkt, foto client_only, recenzie len od klienta |

Blueprinty boli odčítané zo živých template masterov (stĺpec „master") a overené `resolve_slots.py` proti
snapshotom (`snapshots/` v projekte; nie sú súčasťou balíčka). `selftest.py` pokrýva 6 stránok
(hp, about, services, contact, pricing, gallery); products beží vlastnou klon-slučkou (Fáza 7).
Image sloty pokrytých stránok = **36** (overené resolverom proti živým draftom). Nepokryté: blog,
area (okolie), team_refs (zámerne — Google recenzie).

---

## 12. Architektonický diagram — flow od spustenia skillu

```
POUŽÍVATEĽ: „postav web pre klienta test1"          (jediný vstup = zdroj podkladov na GDrive)
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 0 — INTAKE (Claude + Google Drive MCP)                                  intake.md   │
│   search_files("test1") → priečinok klienta                                              │
│   └─ 01_Formulár a info/ → dotazník_.xlsx + informácie.docx → read_file_content          │
│   └─ 02_Logo a branding/, 03_Fotky/ → referencie do brief.brand / brief.media            │
│      (ak dotazník nemá farby: extract_palette.py z loga → brief.brand)                    │
│   Claude normalizuje odpovede + generuje copy (claim, KPI, služby, about, contact…)      │
│   honesty: tvrdé fakty 1:1, ceny/recenzie/kontakty sa NIKDY nevymýšľajú                  │
│   flags → brief.pages (napr. pricing „individuálny" ⇒ stránka sa nestavia)               │
│   ──► brief.json   (validácia: brief.schema.json; vzory: brief.example*.json)            │
│   check_intake.py --brief brief.json → BLOCKER/WARN/INFO chýbajúcich vstupov (nezastaví) │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 1 — PRAVIDLÁ (offline, len ak sa menil Excel)                                       │
│   01_SABLONA_v2.xlsx ──compile_rules.py──► references/rules.json (11 stránok, invarianty)│
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 1a — OVERENIE INŠTANCIE (echo identity, read-only, PRED PRVÝM ZÁPISOM)              │
│   list-pages → živá doména inštancie (z preview_url, napr. new1.eshopion.sk)             │
│   🔌 echo: „pripojený web = <doména> · klient z briefu = <meno>" (prvý riadok behu)      │
│   newX/newsX.eshopion.sk = platné ciele (neblokovať) · denylist host = newo.eshopion.sk  │
│   presná zhoda s denylistom ⇒ STOP (prepni inštanciu) · inak zapamätaj instance_domain   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 1b — BRAND / FARBY (Claude + Elementor MCP + build_palette.py)         colors.md    │
│   list-templates(kit) → get-global-settings → kit_current.json (= záloha)                │
│   build_palette.py (brief farby + kit_colors.json odvodzovacie pravidlá) → kit_new.json  │
│   color_mode? ── "kit" (default) ─► update-page-settings(kit) [1 atomický zápis]         │
│               ├─ "page_css" ──────► build_page_color_css.py → custom_css len na stránky  │
│               └─ "plan" ──────────► len „color plan" do reportu                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 2 — CIEĽOVÉ STRÁNKY (Claude + Elementor MCP)                                        │
│   list-pages → pre každú stránku z brief.pages nájdi post_id                             │
│   podľa page_title_candidates v <page>_slot_blueprint.json                               │
│   pokryté: hp · about · services · contact · pricing · gallery                           │
│   jedna vlastná inštancia klienta → cieľ = priamo živé stránky (skill NEklonuje)         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼  ┌──────────────────── SLUČKA PRE KAŽDÚ STRÁNKU z brief.pages ─────────────────────┐
   │  │                                                                                  │
   │  │ FÁZA 3 — MAPOVANIE SLOTOV                                                        │
   │  │   get-page-structure(post_id) → structure_<page>.json                            │
   │  │   resolve_slots.py + <page>_slot_blueprint.json                                  │
   │  │      (index-cesty → aktuálne element_id, kontrola typu widgetu)                  │
   │  │   ──► slotmap_<page>.json      [nesúlad typu ⇒ STOP, zmenil sa master]           │
   │  │                                                                                  │
   │  │ FÁZA 4 — TEXTY                                                                   │
   │  │   build_ops.py (brief + slotmap + blueprint) ──► ops_<page>.json                 │
   │  │      • CTA ≤ 21 znakov · štatistika začína číslom (warn)                         │
   │  │      • cast:"int" (countery) · "link.url" + link_extra (tel/mailto/maps)         │
   │  │      • hide_if_missing → skry riadok/tabuľku · clear_if_missing → vyčisti        │
   │  │      • repeater sloty preskočí (vypíše dôvod)                                    │
   │  │   batch-update(post_id, ops)                                                     │
   │  │   repeater ručne (read-merge-write, zachovaj _id):                               │
   │  │      • FAQ (about): get-element-settings → items[].item_title → update-widget    │
   │  │      • galéria: upload fotiek → gallery=[{filter,_id,images[]}] +                │
   │  │        item_per_row podľa počtu (≤4→2, 5–8→3, 9+→4) → update-widget              │
   │  │   NEDOTÝKAŤ SA: global CTA · xpro šablóny · hlavičky (riešia Fázy 6/7)            │
   │  │                                                                                  │
   │  │ FÁZA 4b — MÉDIÁ (len ak brief.media.source ≠ "placeholder")          media.md    │
   │  │   plan_media.py → plan_<page>.json (dedup, osoby ≥ 50 %, client_only=skip)        │
   │  │   image_slots blueprintu → prompty (image_prompt_guide.md) → dávka               │
   │  │   n8n execute_workflow(Webhook, id GtjjsjvLqPar2FwB, body=dávka) → get_execution  │
   │  │   results[] → wp_media_id alebo sideload-image → update-element(image slot)      │
   │  │   • 3 vetvy: client (len upload/enhance) · generated · mix                       │
   │  │   • source_policy:"client_only" (fotka osoby, galéria) sa NIKDY negeneruje       │
   │  │   • video: sesterský Runway workflow (TODO)                                      │
   │  │                                                                                  │
   │  │ FÁZA 5 — QA + PUBLIKOVANIE                                                       │
   │  │   get-page-structure → structure_after_<page>.json                               │
   │  │   qa_check.py + blueprint: žiadne placeholdery („Lorem/Služba 1–6/popis…"),      │
   │  │   štatistiky číselné, CTA ≤ 21, optional sloty smú byť prázdne                   │
   │  │   QA bez CHÝB + publish_after_build ⇒ PUBLIKUJ; inak DRAFT + dôvod do reportu    │
   │  └──────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 6 — GLOBÁLNE PRVKY A PRÁVNE STRÁNKY (raz na inštanciu)        globals_blueprint.json│
│   find-element("netovapomoc"/"fajne-weby") → footer · CTA bublina · popup · GDPR · cookies│
│   get-element-settings → fill_globals.py (global_tokens.json ↔ content.legal) → update    │
│   právny TEXT sa NEMENÍ, menia sa len identifikačné údaje firmy; menu štruktúru nemeň     │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 7 — PRODUKTOVÉ STRÁNKY + GOOGLE RECENZIE (len ak brief.content.products)            │
│   pre KAŽDÝ produkt: klon mastera (jediný klon v skille) → resolve → build_ops → batch    │
│   foto produktu = client_only (upload, negeneruj); recenzie LEN z content.reviews         │
│   product_copy_guide.md · products_slot_blueprint.json                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ ODOVZDANIE: stránky PUBLIKOVANÉ (alebo DRAFT, ak QA hlási chybu) + súhrnný report        │
│   (instance_domain = na ktorý web sa stavalo · preview_url per stránka ·                 │
│    stav publikovaná/draft+dôvod · čo je naplnené / placeholder / skryté · QA výsledky ·   │
│    color plan · BLOCKER/WARN chýbajúcich vstupov · agentúrne zvyšky na ručné dočistenie)  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Vrstvy a zodpovednosti:
  Claude (agent)      = orchestrácia, intake, copy, rozhodnutia, MCP volania
  Python skripty      = deterministické kalkulačky (resolve/build/QA/paleta/plán médií/globály) — bez siete
  Elementor MCP       = jediný zápis na web   ·   GDrive MCP = čítanie podkladov
  n8n MCP             = generovanie/úprava médií (Image 2.0, neskôr Runway)
  Dáta (references/)  = rules.json (kompilát Excelu) · blueprinty · kit_colors · global_tokens · schéma
```
