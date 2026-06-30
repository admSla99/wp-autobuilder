# Changelog — wp-autobuilder

## v1.4.0 — 2026-06-29
Médiá: n8n workflow **Image 2.0** prerobený z uploadu do WordPressu na **agentúrny Google Drive** — škálovateľné
naprieč inštanciami klientov (žiadne per-klient WP credentials v n8n).

**n8n workflow (`GtjjsjvLqPar2FwB`)**
- Vyhodené uzly *Upload to WordPress* + *Set Alt & Title* (per-inštancia WP Application Password). Nový chvost:
  *Has Image? → Convert to File → Upload to Drive → Make Public → Build Public URL → Map Result*.
- Obrázok sa uloží na **Google Drive** (priečinok `wp-autobuilder-media`, jeden agentúrny GDrive credential),
  sprístupní „anyone with link" a workflow vráti **verejnú URL** (`lh3.googleusercontent.com/d/<id>`);
  `wp_media_id` je vždy `null`. Upload do inštancie klienta robí `elementor-mcp-sideload-image` (auth z prepínača).
- **Výsledok:** pridanie nového klienta = iba prepnutie Elementor MCP; **do n8n sa už nič nepridáva.**
- **Kvalita obrázkov:** default `quality` znížený na **`medium`** (`defaults.quality || 'medium'`). Timeout na
  *OpenAI Generate*/*OpenAI Edit* je **dynamický** — `high → 300000 ms`, inak `120000 ms` (vyhne sa „connection aborted" pri high).

**Skill (`SKILL.md`, `references/media.md`)**
- Fáza 4b: dávka **už neposiela `wordpress`**; vždy sa ide `sideload-image(image_url)` → `update-element`
  (alt/title na slote z `result`). Odstránené poznámky o `upload=true` / `base_url` / WP 401 `rest_cannot_create`.
- Spresnené, ktorý n8n nástroj použiť: **built-in n8n connector** (cowork) — `execute_workflow` + `get_execution`;
  NIE `n8n_*` z druhého servera `n8n-mcp` (czlonkowski). `execute_workflow` existuje len na connectore.
- Známe tradeoffy zdokumentované: SEO filename sa pri sideloade môže nahradiť Drive ID; priečinok
  `wp-autobuilder-media` občas vyčistiť. (Build-spec `n8n_obrazky_workflow_SPEC.md` v projekte zosúladený.)

## v1.3.1 — 2026-06-29
Aktualizácia copywriting štandardu pre HP a O nás (zákazníkove nové inštrukcie).
- Nové referencie **`references/hp_copy_guide.md`** a **`references/about_copy_guide.md`** (zákazníkov
  systémový copywriting prompt pre hlavnú stránku a O nás — tón v 2. os. mn. č., osnovy, SEO nadpisy,
  zákaz vágnych klišé, CTA ≤21, O nás bez odrážok s bodkami, odporúčanie fontov pre HP).
- `references/intake.md`: sekcie „3) Vygeneruj HP copy" a „content.about (O nás)" teraz odkazujú na tieto
  guide-y (rovnaký vzor ako `product_copy_guide.md`). Slot-mapping zostáva; guide určuje štýl/štruktúru.

## v1.3.0 — 2026-06-25
Konsolidácia po end-to-end teste (utesni.sk): odstránenie dev/„shared instance" logiky + deterministické
dorobenie nepoužitých sekcií, kontaktu a CTA (z auditu proti fázam).

**Inštancia / beh**
- Skill predpokladá **jednu vlastnú inštanciu klienta**. Odstránené: zdieľané dev weby, draft kópie, „test mód", podsúvanie `post_id`. Cieľ = živé stránky (`list-pages`).
- Farby: `apply_global_colors` (true/false) → **`color_mode`** = `kit` (default, zápis do kitu) | `page_css` | `plan`. Nový skript **`scripts/build_page_color_css.py`** (per-stránka `--e-global-color-*` cez `custom_css`, bez dotyku kitu).
- Médiá: Fáza 4b **beží vždy**; `placeholder` už nie je default (`client`/`generated`/`mix`); doplnená cesta sideload z verejných URL pôvodného webu klienta (bez WP app-password).
- Publikovanie po QA bez chýb; doplnený revert (`post_status:"draft"`).

**Deterministické auto-skrytie nepoužitých sekcií (oprava gapov z auditu)**
- HP **recenzie + blog**: kontajnerové hide-sloty v blueprinte (`hp.reviews.cards`, `hp.reviews.tabs`, `hp.blog.section`) — `build_ops` ich skryje, keď chýba `content.reviews.*` / `content.blog.posts`. Už nie ad-hoc rozhodnutie agenta.
- `rules.json` + `01_SABLONA_v2.xlsx` (HP): Referencie / Google recenzie / Blog prepnuté na **VOLITEĽNÁ** (zhoda 3-vrstvového modelu Excel → rules → blueprint).

**Globálne prvky (Fáza 6)**
- **Zapojená do behu**: spúšťa sa vždy raz po per-stránka slučke (trigger), nie je voliteľná; chýbajúce `content.legal` pole → token nechá + report.

**Kontakt**
- icon-list (kontaktné ikony, repeater): napĺňa sa **read-merge-write** klientovým tel/mailom (`_id` + ikona zachované); zrušené „neditovať" → odstránenie agentúrneho kontaktu.

**CTA odkazy + portfólio (gap 3)**
- **`content.cta_target`** (+`_secondary`): link-sloty (`setting:"link.url"`) na HP hero (×2), HP block1 a Služby hero → cieľ buttonov na klientovu stránku. Globálne „Chcem viac informácii" rieši Fáza 6 (`cta_global` v `globals_blueprint.json`). Invariant: nikdy agentúrny `/produktova-stranka/`.
- HP portfóliový variant služieb sa default **skryje** (`hp.services.portfolio_section` ← `content.sections.use_portfolio`; kartová sekcia pokrýva služby).

**Dokumentácia**
- Frontmatter proces: `intake → farby → sloty → texty → médiá → QA → publish` (odstránené zavádzajúce „klon").
- `references/GAP3_navrh_cta_portfolio.md` (design rationale pre CTA/portfólio).

**Validácia:** `selftest.py` prešiel (HP 50 slotov, všetky stránky + section-hide + plan-media + fill-globals); briefy validujú voči schéme.

## v1.2.0 — 2026-06-24
Veľká aktualizácia z pripomienok klienta (Tier 1 + Tier 2 + Tier 3 produkty/recenzie).

**Texty / copy**
- Dĺžka popisných blokov: HP a O nás 3–4 riadky, Služby 4–5 riadkov + SEO kľúčové slová; odpojené od „botovitého" krátkeho štýlu (`intake.md`, `SKILL.md`).
- O nás countery: číslo + „+" + krátka konkrétna veta, variabilné štatistiky.
- Kontakt: fakturačné údaje vo formáte meno/adresa/IČO/DIČ/IČ DPH.

**Médiá**
- `plan_media.py` (NOVÉ): deduplikácia fotiek (žiadna 2× na stránke), rovnomerné rozloženie klient/AI + veľké/malé sloty, osoby ≥ 50 %; `client_only` sa negeneruje.
- Fotky ladia s brand farbami (primárna + sekundárna) — opravený protichodný `avoid corporate color` (`image_prompt_guide.md`).
- Kontakt: fallback na neutrálny avatar (negeneruje sa fotorealistická osoba).

**Štruktúra / sekcie**
- Auto-skrytie prázdnych sekcií zovšeobecnené (`build_ops.is_missing` — funguje aj pre prázdny zoznam, napr. referenčné logá).
- Galéria: použiť iba jeden variant, ostatné skryť; `item_per_row` biasované na 4.
- Farby z loga / pôvodného webu (`extract_palette.py` NOVÉ) ako fallback v intake.

**Globálne prvky a právne stránky (Fáza 6, NOVÉ)**
- `fill_globals.py` + `global_tokens.json` + `globals_blueprint.json`: footer, CTA bublina, popup, GDPR, cookies — nahradenie agentúrnych údajov údajmi klienta z `content.legal`.

**Produktové stránky + Google recenzie (Fáza 7, NOVÉ)**
- `products_slot_blueprint.json` (vyčistený master) + `product_copy_guide.md` (zákazníkov copy-bot) + `content.products[]`/`content.reviews` v schéme.
- Google recenzie výhradne od klienta (link + rating + karty), inak sa sekcia skryje. `[DOPLNIŤ:…]` markery zachytáva QA → nekompletná stránka ostane draft.
- Klonovanie 1 produktovej stránky na produkt z vyčisteného mastera.

**Publikovanie**
- Po úspešnej QA sa stránka publikuje (flag `publish_after_build`, default true); pri QA chybe ostáva draft.

**Pozn.:** auto-odsúhlasenie nástrojov a prepínanie inštancie sú zdokumentované v projektovom `CLAUDE.md` (mimo skillu, operátorské).

## v1.1.0 — 2026-06-22
- SKILL.md: doplnená poznámka **„Prepnutie inštancie"** v sekcii *Potrebné konektory* —
  skill sám `elementor-mcp` connector neprepína; postup prepnutia inštancie je v projektovom `CLAUDE.md`.
- Bez zmeny logiky pipeline ani Python skriptov.

## v1.0.0
- Pôvodná verzia: intake → farby → sloty → texty → médiá → QA
  (HP, O nás, Služby, Kontakt, Cenník, Galéria).
