# Intake z Google Drive → brief.json

Cieľ: z **priečinka klienta** (zdroj zadá používateľ) vytvoriť `brief.json` **plne autonómne**,
bez doplňujúcich otázok. Brief je vstup pre zvyšok pipeline.

## 1) Nájdi podklady (Google Drive MCP)
1. Zo zdroja od používateľa (názov ako „test1", cesta, alebo GDrive ID) nájdi priečinok klienta:
   `search_files` s `title contains '<názov>'` (mimeType folder). Ak zadal ID/odkaz, použi priamo.
2. Vylistuj jeho obsah: `search_files` s `parentId = '<id>'`. Očakávaná štruktúra:
   `01_Formulár a info`, `02_Logo a branding`, `03_Fotky`, `04_Výstup AI`.
   Ak názvy sedia inak, vyber priečinok, ktorý obsahuje „Formulár"/„dotazník"; logo a fotky podľa významu.
3. V `01_Formulár a info` nájdi **dotazník** (`*.xlsx`, názov obsahuje „dotazník") a `informácie.docx`.
4. Prečítaj ich obsah: `read_file_content(fileId=...)` (vráti text aj z xlsx/docx).
5. Pozn.: logo (`02_*`) a fotky (`03_*`) si len zaznač do `brief.media`/`brief.brand` — v MVP sa
   nesťahujú (placeholder), ale cesta sa hodí pre neskorší n8n krok.

## 2) Mapovanie stĺpcov dotazníka → brief
Dotazník je riadkový formulár (hlavička = otázky, druhý riadok = odpovede). Mapuj podľa významu
otázky (znenie sa môže mierne líšiť):

| Otázka v dotazníku (kľúčové slová) | Brief pole |
|---|---|
| E-mailová adresa | `client.email` |
| Cieľová skupina / typický klient | `client.target_audience` |
| Pôvodná web stránka (doména) | `client.domain` |
| Firemná/preferovaná farba webu | `brand.primary/secondary/accent_color` |
| Logo – ako dodáme | `brand.logo_url` (+ súbor z `02_Logo`) |
| Úvodné video / link na video | `media.video` |
| Telefón v hornej časti webu | `contact.header_phone` |
| Obrázky – zdroj fotiek | `media.source` |
| Recenzie / referencie | `contact.reviews_note` |
| Menu – kategórie | zoznam služieb (kandidáti na `content.services`) |
| Výhody oproti konkurencii (2–4) | podklad pre `content.value_props` |
| Rýchle čísla (voliteľné) | podklad pre `content.kpis` |
| Produkty / služby – názvy | `content.services[].title` |
| Predstavenie biznisu (1–2 vety) | podklad pre `content.claim` |
| Hlavná činnosť – popis | podklad pre `claim` + `services` texty |
| O nás – príbeh firmy | `content.about` (HP nepoužije, drž pre ďalšie stránky) |
| Adresa na mapu (prevádzka) | `contact.addresses` |
| Kontaktné osoby (1–2) | `contact.contacts[]` |
| Galéria (áno/nie) | `flags.gallery` |
| Blog (áno/nie) | `flags.blog` |
| Cenník | `flags.pricing` |
| GDPR | `flags.gdpr` |

> **`wordpress.base_url` nie je z dotazníka** — je to doména WP inštancie, ktorú edituješ cez Elementor MCP
> (kam sa nahrávajú médiá). Zisti ju cez `elementor-mcp-sideload-image` (doména vo vrátenej `url`), príp.
> nakonfiguruj per klient. NIE je to doména obrázkov v skopírovanom obsahu (tie ukazujú na master/agentúru).
> Default `wordpress.upload = true`. Detaily: `references/media.md` → sekcia „base_url".

## 2b) Brand farby — fallback z loga / pôvodného webu
Ak dotazník **neobsahuje** firemné farby (alebo sú prázdne), nepoužívaj default — odvoď ich:
1. **Z loga:** stiahni logo z `02_Logo a branding` lokálne (`read_file_content`/download) a spusti
   `python SKILL_DIR/scripts/extract_palette.py --logo <cesta_k_logu>` → vráti `primary_color`/`secondary_color`/
   (`accent_color`). Hodnoty vlož do `brief.brand`.
2. **Z pôvodného webu:** ak klient uviedol doménu a logo farby nie sú jednoznačné, prečítaj brand farby
   zo štýlov pôvodnej stránky (dostupným nástrojom) a doplň do `brief.brand`.
3. Výsledok ide ďalej do Fázy 1b (`build_palette` → globálny kit) — žiadna zmena farebnej write-logiky.
Tvrdé pravidlo: farby z dotazníka majú prednosť; logo/web je fallback, keď v dotazníku chýbajú.

## 3) Vygeneruj HP copy (Claude) — podľa pravidiel rules.json
Surové odpovede nestačia; HP sloty vyžadujú marketingovú copy. Generuj takto:

> **Štýl/štruktúra textov HP = `references/hp_copy_guide.md`** (zákazníkov copywriting štandard pre hlavnú
> stránku — tón v 2. os. mn. č., osnova HERO → špecializácia → sekundárna → benefity → CTA sekcia →
> CTA bublina → newsletter, SEO nadpisy, CTA ≤21 znakov, odporúčanie fontov). Slot-mapping nižšie určuje,
> KAM text patrí; `hp_copy_guide.md` určuje, AKO ho napísať. Honesty pravidlá (nižšie) platia bez výnimky.

### Dĺžka textov a SEO (ZÁVÄZNÉ — platí pre HP, O nás aj Služby)
- **Nedrž sa pôvodného krátkeho/„botovitého" nastavenia.** Texty píš ako plnohodnotný web copywriting,
  nie ako jednovetové odrážky. Cieľová dĺžka popisných blokov (cik-cak / value bloky / popisy služieb):
  **3–4 riadky pre HP a O nás, 4–5 riadkov pre Služby** (≈ 2–4 súvislé vety, žiadne útržky).
  Nadpisy (H1/H2/H3), CTA, štatistiky a fakty ostávajú krátke podľa svojich pravidiel nižšie.
- **SEO:** do každého popisného textu prirodzene zapracuj **hlavné kľúčové slovo segmentu + 1–2 vedľajšie**
  (typ služby, lokalita ak ju klient dodal, úžitok pre klienta). Kľúčové slová neopakuj nasilu — text musí
  znieť prirodzene a čitateľsky. Žiadny keyword stuffing.
- **Konzistentná dĺžka:** v rámci jednej stránky drž popisné bloky **približne rovnako dlhé** (na Službách
  zjednoť rozsah všetkých blokov), aby layout pôsobil vyvážene.
- Honesty pravidlá (nižšie) platia bez výnimky aj pri dlhšom texte — viac textu ≠ vymýšľanie faktov.

- **claim (H1)**: ≤ ~7 slov, obsahuje hlavné kľúčové slovo segmentu + konkrétny prínos.
  Vychádzaj z „predstavenie biznisu" / „hlavná činnosť". Príklad (fotovoltika): „Fotovoltika, ktorá sa vám vráti."
- **kpis (3×)**: každá `number` **musí začínať číslom**. Použi „rýchle čísla" a tvrdé fakty
  (roky na trhu, počet služieb). Ak chýbajú, doplň max. 1 marketingovú (napr. „100% riešenie na kľúč").
  Nikdy nevymýšľaj konkrétne počty (klientov, realizácií), ktoré klient neuviedol.
- **services (3×)**: vyber 3 najdôležitejšie z „produkty/služby – názvy". Text = **2–4 vety (3–4 riadky)**,
  čo to je, pre koho a aký konkrétny prínos; zapracuj kľúčové slovo segmentu. Nevymýšľaj technické parametre.
- **value_props (3×)**: z „výhod oproti konkurencii" + „o nás". Nadpis = úžitok; text = **2–4 vety (3–4 riadky)**,
  konkrétne a so SEO kľúčovými slovami segmentu.
- **cta_primary / cta_secondary**: default „Chcem cenovú ponuku" / „Chcem konzultáciu" (≤21 znakov).
  Nepoužívaj „Kliknite sem / Viac / Tu / Kúpte hneď".
- **cta_target (+ _secondary)**: cieľ (link) CTA buttonov — klientova konverzná stránka, default `/kontakt/`
  (príp. `tel:<phone>`). NIKDY agentúrny `/produktova-stranka/`. Sekundárny default = `cta_target`.
- **sections.use_portfolio**: nechaj prázdne (default) → HP použije kartovú sekciu služieb a portfóliový variant skryje.
  Vyplň iba, ak klient chce portfólio namiesto kariet (potom doplň fotky portfólia).
- **video_section**: default nadpis „Pozrite si naše realizácie" + 1 veta k segmentu.
- **contact**: prenes kontaktné osoby, adresy, telefóny 1:1 (needituj fakty).

### Honesty (nemenné)
Nevymýšľaj ceny, recenzie, mená, čísla, technické údaje ani fakty, ktoré klient nedodal.
Marketingové formulácie (claim, mäkké úžitky) sú v poriadku; tvrdé fakty musia pochádzať z dotazníka.
Do `brief.json` pridaj pole `"_pozn_odhad"` s tým, čo je marketing vs. fakt (pre neskoršiu kontrolu).

## 4) Validuj a ulož
- Over `brief.json` oproti `references/brief.schema.json` (3 kpis, 1–3 services/value_props,
  CTA ≤21, kpi.number číselné). Ak validácia padne, oprav copy — **nepýtaj sa používateľa**.
- Ulož `brief.json` do pracovného priečinka a pokračuj Fázou 1.

Hotový príklad výstupu intake: `references/brief.example.enova.json`.

## Sekcne nadpisy (HP 100%)
- Okrem hlavnej copy vygeneruj aj `content.sections`: eyebrow + heading pre sekcie sluzby/portfolio, karty, galeriu a blog (+ blog button text). Su to kratke nadpisy/labely; ak chyba podklad, pouzi rozumny default (napr. eyebrow „NASE SLUZBY"/„NAS BLOG", blog button „Vsetky clanky").
- Recenzie a header/footer/CTA banner NEGENERUJ tu: recenzie idu z Google Reviews API; header/footer su globalne theme templates; CTA banner je zdielana sablona.

## 5) Copy pre ďalšie stránky (about / services / contact / pricing)
Generuj IBA pre stránky v `brief.pages` (z dotazníka: Galéria/Blog/Cenník áno-nie + štandard
HP, O nás, Služby, Kontakt). Rovnaké honesty pravidlá ako pri HP.

### content.about (O nás)
> **Štýl/štruktúra textov O nás = `references/about_copy_guide.md`** (zákazníkov copywriting štandard pre
> stránku O nás — tón v 2. os. mn. č., súvislý text BEZ odrážok s bodkami, osnova hero → 4 štatistiky →
> 2–3 bloky → FAQ, SEO nadpisy, CTA ≤21 znakov). Slot-mapping nižšie určuje, KAM text patrí;
> `about_copy_guide.md` určuje, AKO ho napísať. Honesty pravidlá platia bez výnimky.

- **hero.title/text**: z „O nás – príbeh firmy" + „predstavenie biznisu". Nadpis ≤ ~8 slov.
- **stats (presne 4)**: counter widgety — `number` = ČISTÉ číslo (bez medzier, napr. "1200"),
  `suffix` = **prednostne "+"** (príp. "%"/"★"/"r.") alebo null, `label` = **krátka konkrétna veta**
  (nie jedno slovo). Cieľový tvar zobrazenia: `číslo+` na prvom riadku, krátka veta pod ním —
  napr. **„100+ hostí mesačne, ktorí sa k nám pravidelne vracajú"** (number="100", suffix="+",
  label="hostí mesačne, ktorí sa k nám pravidelne vracajú").
  Vhodné typy štatistík podľa segmentu: počet hostí/klientov za mesiac či rok, počet vyrobených/predaných
  kusov, počet realizácií, najazdené kilometre, roky praxe, % spokojnosti. Tvrdé čísla LEN z dotazníka.
  Ak klient dodá menej než 4 čísla, doplň NEčíselné fakty premenené na číslo, ktoré klient uviedol
  (počet služieb, rokov od založenia) — nikdy nevymýšľaj počty.
  Pozn.: centrovanie a layout countera určuje master šablóna — AI ich nemení, generuje len číslo/suffix/vetu.
- **blocks (presne 3)**: z „výhod oproti konkurencii" + príbehu. Poradie na masteri:
  1. špecializácia (komu pomáhame), 2. spoľahlivosť, 3. rýchlosť/kvalita. Nadpis = úžitok;
  text = **2–4 vety (3–4 riadky)**, konkrétne a so SEO kľúčovými slovami segmentu (viď „Dĺžka textov a SEO").
- **faq (presne 4 q/a)**: z najčastejších otázok segmentu + faktov dotazníka (cena → „cenovú
  ponuku pošleme", trvanie, záruka, rozsah služieb). Odpovede 1–3 vety, žiadne vymyslené čísla.
  POZOR: otázky sú repeater slot (rieši sa read-merge-write, viď SKILL.md Fáza 4).

### content.services_page (Služby)
- **hero**: title = hlavná činnosť + prínos; text 2–3 vety; cta ≤ 21 znakov (default „Chcem cenovú ponuku").
- **blocks (presne 5)**: z „produkty/služby – názvy". Ak je služieb menej než 5, doplň PROCESNÉ
  bloky (poradenstvo/obhliadka, servis/opravy, materiály) — nevymýšľaj nové služby. Ak viac, vyber 5
  najdôležitejších (zvyšok pokryje HP/karty). Text každého bloku = **3–4 vety (4–5 riadkov)**,
  **zjednotený rozsah pre všetkých 5 blokov** (približne rovnako dlhé), so SEO kľúčovými slovami segmentu.

### content.contact (Kontakt) — fakty 1:1, NIČ negenerovať
Pozn.: top-level `contact` v briefe = SUROVÉ fakty z dotazníka (kontakty, adresy, poznámky);
`content.contact` = z nich odvodené hodnoty pre sloty stránky Kontakt (1:1, žiadna tvorivosť).
- `person_html`: `<strong>Meno - rola</strong>` + mailto/tel odkazy z „kontaktné osoby".
- `phone`/`email` + `phone_link` (tel:) / `email_link` (mailto:) z dotazníka.
- `map_query` = „adresa na mapu"; `map_directions_url` = Google dir link s adresou.
- `billing_html` = fakturačné údaje 1:1 v PEVNOM poradí, každý údaj na samostatnom riadku (`<br>`):
  **meno spoločnosti / adresa / IČO / DIČ / IČ DPH**. IČ DPH zahrň, ak ho klient uviedol; chýbajúci
  údaj vynechaj (neuvádzaj prázdny riadok, nevymýšľaj). Príklad:
  `<strong>Firma s.r.o.</strong><br>Ulica 1, 010 01 Mesto<br>IČO: 12345678<br>DIČ: 2020202020<br>IČ DPH: SK2020202020`.
  `office_html` = adresa pobočky 1:1.
- `phone`/`email` + `phone_link` (tel:) / `email_link` (mailto:), `map_query` (adresa na mapu) — prenes z dotazníka 1:1
  (telefón a mail sa menia automaticky z údajov klienta). Fotka vedľa mapky = image slot (rieši Fáza 4b Médiá).
- Fotka osoby: LEN z `03_Fotky` klienta (source_policy client_only) — nikdy negenerovať tvár.

### content.legal (Globálne prvky + právne stránky) — fakty 1:1
Identifikačné údaje firmy klienta pre footer, popup, CTA bublinu a stránky GDPR/cookies. Z dotazníka
(fakturačné údaje, kontakt, doména) vyplň: `company_name` (plný názov s právnou formou), `company_short`,
`brand_label` (pre copyright), `address`, `ico`, `dic`, `ic_dph`, `register` (zápis v OR), `domain`,
`email`, `phone`. Prekrýva sa s `content.contact`/`billing_html` — drž rovnaké hodnoty. Tieto nahrádzajú
agentúrne tokeny (Netova pomoc s.r.o. …) cez `fill_globals.py` (viď SKILL.md Globálna fáza). NIČ nevymýšľaj;
chýbajúce pole nechaj prázdne (token sa nenahradí a zapíše do reportu).

### content.products (Produktové stránky) — copy podľa product_copy_guide.md
Generuj len ak klient dodá produkty (z dotazníka/GDrive). Pre KAŽDÝ produkt vyplň položku
`content.products[]`: `name`, `category`, `h1` (kľúčové slovo + prínos), `description` (3–5 odsekov),
`price_no_vat`/`price_vat`/`price_note` (**LEN od klienta** — inak `[DOPLNIŤ: cena]`), `photos` (LEN klientove,
negenerovať), `benefits` (3–6: názov + 2–3 vety, ≥3 riadky, rovnako dlhé), `cta_primary`/`cta_secondary` (≤21 znakov).
Texty píš podľa **`product_copy_guide.md`** (2. osoba mn. č., konkrétne fakty alebo `[DOPLNIŤ: …]`, SEO nadpisy).
Do `brief.pages` pridaj `products`, ak klient produkty má. Recenzie produktovej stránky = `content.reviews` (zdieľané).

### content.reviews (Google recenzie) — VÝHRADNE od klienta
Z dotazníka vyplň `google_url` (odkaz na Google profil/recenzie), príp. `rating` a `items[]` (reálne recenzie,
ktoré klient dodal: author/text/rating). **Nikdy nevymýšľaj recenzie ani rating.** Ak klient nedodá `google_url`
ani `items`, sekcia recenzií sa skryje (hide_if_missing). Ak dodá len odkaz, naplní sa link tlačidlo (a rating, ak je).

### content.pricing (Cenník) — INVARIANT: ceny len od klienta
- Generuj len ak `flags.pricing` / klient dodal cenník. `title` = „Cenník <segment>".
- `packages` (tabuľka 1, max 6) = balíčky; `items` (tabuľka 2, max 6) = jednotlivé služby.
  `price` prenes DOSLOVA (vrátane „od", mien, jednotiek). Položku bez ceny vynechaj.
- Chýbajúce riadky sa automaticky skryjú (hide_if_missing) — netreba ich dopĺňať.
- `benefits` = 3 krátke labely (default: „Transparentné ceny", „Férový prístup", „Individuálne riešenia").

### brief.pages
Vždy zapíš zoznam stránok na postavenie, napr. `["hp","about","services","contact","pricing"]`.
Cenník zaraď len ak klient cenník dodal.

### content.gallery (Galéria) — fotky LEN od klienta
- Generuj len ak `flags.gallery`. `title` = H1 (napr. „Naše realizácie") + voliteľné `section_labels`/`cards` texty.
- `categories[].photos` = zoznam fotiek z `03_Fotky` v PORADÍ od klienta — AI fotky negeneruje,
  nemení ani nepreusporadúva. Filter záložky len ak kategórií > 1 (AI smie záložky pomenovať).
- Rozloženie: 4–8 fotiek → 2 stĺpce, 9–16 → 3, 17+ → 4 (item_per_row).
