# wp-autobuilder — dokumentácia aktuálneho stavu

Skill pre Claude Cowork, ktorý z podkladov klienta **autonómne poskladá stránky WordPress webu**
(HP, O nás, Služby, Kontakt, Cenník) v Elementore. Jeden vstupný bod, beží bez prerušenia,
končí stránkami v stave **draft**.

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
                                 │  + <page>_slot_blueprint.json (hp/about/services/contact/pricing) + kit_colors.json
                                 ▼  Elementor MCP (+ Google Drive)
                         hotové stránky webu (draft) + QA report
```

Kľúčové: **skill nikdy nečíta surový Excel.** Excel sa najprv skompiluje do `rules.json`
a skill pracuje s tým. To je zámer — oddelenie „autorskej vrstvy" (Excel, edituje netechnik)
od „runtime vrstvy" (rules.json, číta stroj).

---

## 1b. Kto spúšťa skripty (mentálny model)

Skill nie je program, čo beží sám. Runtime je **Claude v Cowork session** — žiadny cron/server.

- **Claude (agent) = vykonávateľ.** Číta SKILL.md, spúšťa skripty cez shell, volá MCP nástroje a rozhoduje (intake, generovanie copy).
- **Python skripty = kalkulačky.** Deterministický výpočet (Excel→rules, sloty, operácie, paleta, QA). Bez siete a bez MCP.
- **MCP (Elementor, Google Drive) = jediné reálne čítanie/zápis** na web a Drive; volá ich Claude.

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
| `references/rules.json` | Skompilované pravidlá obsahu (z Excelu) — skill číta toto |
| `references/rules.schema.json` | JSON schéma rules.json (validácia) |
| `references/hp_slot_blueprint.json` | Mapovanie sekcií HP na index-cesty v strome + na polia briefu |
| `references/brief.schema.json` | Štruktúra briefu (vstup do buildu) |
| `references/brief.example.json` | Príklad briefu (Podlahy Novák) |
| `references/brief.example.enova.json` | Reálny príklad z intake (Enova House) |
| `references/intake.md` | Postup Google Drive → brief.json (mapovanie dotazníka) |
| `references/colors.md` | Postup pre farby (read-merge-write) + zistenia |
| `references/kit_colors.json` | Sloty Elementor kitu + pravidlá odvodenia odtieňov |
| `references/architecture.md` | Fázy a ich stav vs návrhový dokument |
| `scripts/compile_rules.py` | Excel `01_SABLONA_v2.xlsx` → `rules.json` + validačný report |
| `scripts/resolve_slots.py` | Štruktúra stránky → mapa `slot_id` → aktuálne `element_id` |
| `scripts/build_ops.py` | brief + slotmap + blueprint → operácie pre `batch-update` |
| `scripts/qa_check.py` | Predpublikačná QA (placeholdery, CTA dĺžky, číselné štatistiky) |
| `scripts/build_palette.py` | brief + aktuálny kit → nový kit (farby, read-merge-write) |
| `scripts/kit_to_payload.py` | Pomôcka: get-global-settings → payload (záloha/obnova) |
| `scripts/selftest.py` | Test reťazca resolve → build_ops → QA (bez živého webu) |
| `scripts/palette_selftest.py` | Test farebnej logiky (merge zachová kit, mení len farby) |

---

## 4. Pipeline — ako to beží krok po kroku

- **Fáza 0 — Intake (`intake.md`).** Používateľ zadá iba zdroj (GDrive priečinok klienta, napr. „test1").
  Claude nájde priečinok, prečíta `01_Formulár a info/dotazník_.xlsx` (+ info.docx), namapuje stĺpce na
  brief, vygeneruje HP copy podľa pravidiel a uloží `brief.json` (validuje voči `brief.schema.json`).
- **Fáza 1 — Pravidlá.** Skontroluje `rules.json` (stránka `hp`); ak treba, prekompiluje z Excelu.
- **Fáza 1b — Brand / Farby (`colors.md`).** Read-merge-write celého kitu (viď kap. 7). Na dev webe len „color plan".
- **Fáza 2 — Cieľová HP stránka.** Na vlastnej inštancii klienta sa pracuje priamo na HP (`list-pages`).
  Na zdieľanom dev webe sa cieli draft **kópia** HP (klon sa v skille NErobí).
- **Fáza 3 — Mapovanie slotov.** `get-page-structure` → `resolve_slots.py` → `slotmap.json`.
- **Fáza 4 — Texty.** `build_ops.py` (brief + slotmap + blueprint) → `ops.json` → `batch-update`.
- **Fáza 5 — QA + odovzdanie.** `qa_check.py`; stránka ostáva **draft**; report + odkaz na náhľad.

---

## 5. Ako funguje mapovanie slotov (blueprint + resolver)

Pri klonovaní Elementor pridelí nové `element_id`, ale **poradie a štruktúra ostávajú**. Preto
`hp_slot_blueprint.json` adresuje každý slot **index-cestou** v strome (napr. hero H1 = `[0,0,0]`),
nie natvrdo cez ID. `resolve_slots.py` podľa cesty nájde aktuálne ID a overí typ widgetu. `build_ops.py`
potom k slotom priradí hodnoty z briefu (pole `brief` v blueprinte) a vyrobí operácie. Vďaka tomu skill
funguje na ľubovoľnej kópii/inštancii bez zásahu do master šablóny.

---

## 6. Ako funguje intake (Google Drive → brief)

`intake.md` popisuje: nájdi priečinok klienta → podpriečinok „01_Formulár a info" → dotazník (`.xlsx`)
→ `read_file_content` → mapovanie stĺpcov dotazníka na polia briefu → vygenerovanie HP copy (claim,
štatistiky, 3 služby, 3 hodnotové bloky, CTA) podľa pravidiel → validácia voči schéme. Honesty pravidlo:
nevymýšľať ceny/recenzie/fakty; marketingové formulácie sú OK, tvrdé fakty musia byť z dotazníka.

---

## 7. Ako funguje farby (read-merge-write) — a prečo tak

Zistenie z testu: **zápisy do Elementor kitu sú deštruktívne** — `update-page-settings` aj
`add-custom-css` prepíšu celý kit a nezahrnuté polia resetnú na defaulty; `update-global-colors` píše
len custom paletu (nie system) a nuluje alfa hex. Preto jediný bezpečný vzor:
1. `get-global-settings` → ulož `kit_current.json` (celý kit + záloha),
2. `build_palette.py --current kit_current.json` → vloží brand farby a **zachová** typografiu/CSS/ostatné,
3. **jeden atomický** `update-page-settings(post_id=<kit>, settings=<kit_new.json>)`,
4. rollback = zapísať `kit_current.json` naspäť.
Na dev webe sa kit nemení (flag `apply_global_colors=false`), len sa vypíše „color plan". Detaily: `colors.md`.

---

## 8. Stav — čo je hotové a čo nie

**Hotové:**
- Autonómny intake z Google Drive → brief.json (mapovanie dotazníka).
- Rules engine: Excel → compile_rules.py → rules.json (11 stránok, 133 sekcií, 0 chýb).
- Naplnenie **všetkých inline editovateľných textových slotov HP** (HP 100% bez recenzií): hero (H1, štatistiky, 2 CTA), 3 karty služieb, 3 hodnotové bloky, video, + eyebrows a H3 nadpisy sekcií (služby/portfólio, karty, galéria, blog) a blog button. 34 slotov cez blueprint+resolver.
- Fáza Farby bezpečným read-merge-write (system + odvodená paleta, zachová typografiu/CSS).
- QA (placeholdery, CTA dĺžky, číselné štatistiky) + draft ako kontrolný bod.
- Direktíva autonómie (bez doplňujúcich otázok), self-testy (resolve→build→QA, farby).

**Zatiaľ nie:**
- Médiá (fotky/videá) — placeholder, kým sa nezapojí n8n (Image 2.0 / Runway).
- **Globálne sekcie** (samostatná fáza, nie HP): header a footer sú **theme templates** (Theme Builder, site-wide); CTA banner a divider sú zdieľané `xpro-template`. Riešia sa raz na inštanciu.
- Recenzie (Google Reviews API) — zámerne vynechané.
- Ďalšie stránky (O nás, Služby, Kontakt, cenník, galéria, blog…).
- Galéria/portfólio, recenzie z Google Reviews API.
- Automatické publikovanie (zámerne — človek schvaľuje draft).

---

## 9. Ako spustiť a testovať

**Použitie (po inštalácii skillu), nová session:**
> „Použi wp-autobuilder. Podklady klienta sú v GDrive priečinku test1. Spusti celý proces."

**Self-testy (bez živého webu):**
- `python scripts/selftest.py` — reťazec resolve → build_ops → QA.
- `python scripts/palette_selftest.py` — farebná logika (merge zachová kit).

**Po zmene Excelu:** `python scripts/compile_rules.py <cesta_k_01_SABLONA_v2.xlsx>` → nové rules.json.

---

## 10. Známe obmedzenia / poznámky

- **Kit je site-wide:** na zdieľanom dev webe farby nezapisovať (prefarbili by master). Produkcia = vlastná inštancia klienta.
- **Multi-inštancia:** každý klient = nová WP inštancia; Elementor MCP sa nasmeruje na ňu.
- **Povolenia nástrojov:** prvý beh v Coworku môže vyžadovať schválenie zápisov (vytvorenie/úprava stránky, čítanie GDrive).


---

## 10. Pokrytie stránok (jún 2026)

| page | blueprint | master (dev) | text sloty | image sloty | špeciality |
|---|---|---|---|---|---|
| hp | hp_slot_blueprint.json | 11154 | 34 | 9 | — |
| about | about_slot_blueprint.json | 13109 | 30 | 13 | countery (cast int), FAQ repeater (read-merge-write) |
| services | services_page blueprint | 12842 | 13 | 8 | CTA blokov = global (needitovať), videá = Runway |
| contact | contact_slot_blueprint.json | 13359 | 12 | 1 | fakty 1:1, link.url (tel/mailto/maps), fotka osoby client_only |
| pricing | pricing_slot_blueprint.json | 15389 | 54 | 1 | ceny len od klienta; hide_if_missing + clear_if_missing riadkov |

Blueprinty boli odčítané zo živých masterov na dev webe a overené `resolve_slots.py` proti
snapshotom (`snapshots/` v projekte; nie sú súčasťou balíčka). `selftest.py` pokrýva všetkých
5 stránok. Nepokryté: blog, gallery, team_refs, products/product_page, area.


---

## 11. Architektonický diagram — flow od spustenia skillu

```
POUŽÍVATEĽ: „postav web pre klienta test1"          (jediný vstup = zdroj podkladov na GDrive)
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 0 — INTAKE (Claude + Google Drive MCP)                                  intake.md   │
│   search_files("test1") → priečinok klienta                                              │
│   └─ 01_Formulár a info/ → dotazník_.xlsx + informácie.docx → read_file_content          │
│   └─ 02_Logo a branding/, 03_Fotky/ → len referencie do brief.brand / brief.media        │
│   Claude normalizuje odpovede + generuje copy (claim, KPI, služby, about, contact…)      │
│   honesty: tvrdé fakty 1:1, ceny/recenzie/kontakty sa NIKDY nevymýšľajú                  │
│   flags → brief.pages (napr. pricing „individuálny" ⇒ stránka sa nestavia)               │
│   ──► brief.json   (validácia: brief.schema.json; vzory: brief.example*.json)            │
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
│ FÁZA 1b — BRAND / FARBY (Claude + Elementor MCP + build_palette.py)         colors.md    │
│   list-templates(kit) → get-global-settings → kit_current.json (= záloha)                │
│   build_palette.py (brief farby + kit_colors.json odvodzovacie pravidlá) → kit_new.json  │
│   apply_global_colors?  ── true (produkcia) ──► update-page-settings(kit) [1 atomický    │
│                         └─ false (dev) ──────► len „color plan" do reportu     zápis]    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ FÁZA 2 — CIEĽOVÉ STRÁNKY (Claude + Elementor MCP)                                        │
│   list-pages → pre každú stránku z brief.pages nájdi post_id                             │
│   podľa page_title_candidates v <page>_slot_blueprint.json                               │
│   pokryté: hp · about · services · contact · pricing · gallery                           │
│   (dev web: cieľ = draft KÓPIE; produkcia: priamo stránky inštalácie)                    │
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
   │  │        item_per_row podľa počtu (4–8→2, 9–16→3, 17+→4) → update-widget           │
   │  │   NEDOTÝKAŤ SA: global CTA · recenzie (Google API) · xpro šablóny · hlavičky     │
   │  │                                                                                  │
   │  │ FÁZA 4b — MÉDIÁ (len ak brief.media.source ≠ "placeholder")          media.md    │
   │  │   image_slots blueprintu → prompty (image_prompt_guide.md) → dávka               │
   │  │   n8n execute_workflow(Webhook, id GtjjsjvLqPar2FwB, body=dávka) → get_execution  │
   │  │   results[] → wp_media_id alebo sideload-image → update-element(image slot)      │
   │  │   • 3 vetvy: client (len upload/enhance) · generated · mix                       │
   │  │   • source_policy:"client_only" (fotka osoby, galéria) sa NIKDY negeneruje       │
   │  │   • video: sesterský Runway workflow (TODO)                                      │
   │  │                                                                                  │
   │  │ FÁZA 5 — QA                                                                      │
   │  │   get-page-structure → structure_after_<page>.json                               │
   │  │   qa_check.py + blueprint: žiadne placeholdery („Lorem/Služba 1–6/popis…"),      │
   │  │   štatistiky číselné, CTA ≤ 21, optional sloty smú byť prázdne                   │
   │  └──────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ ODOVZDANIE: všetky stránky ostávajú DRAFT + súhrnný report                               │
│   (preview_url per stránka · čo je naplnené / placeholder / skryté · QA výsledky        │
│    · color plan)  →  PUBLIKUJE ČLOVEK (jediný kontrolný bod)                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Vrstvy a zodpovednosti:
  Claude (agent)      = orchestrácia, intake, copy, rozhodnutia, MCP volania
  Python skripty      = deterministické kalkulačky (resolve/build/QA/paleta) — bez siete
  Elementor MCP       = jediný zápis na web   ·   GDrive MCP = čítanie podkladov
  n8n MCP             = generovanie/úprava médií (Image 2.0, neskôr Runway)
  Dáta (references/)  = rules.json (kompilát Excelu) · blueprinty · kit_colors · schéma
```
