# Médiá — generovanie a úprava obrázkov (skill-side kontrakt)

Fáza Médiá volá **n8n workflow** (OpenAI `gpt-image-2-2026-04-21`, interný názov „Image 2.0") cez **n8n MCP**.
Plný build-spec workflowu: `n8n_obrazky_workflow_SPEC.md`. Tu je len to, čo robí skill.

## Predpoklady
- **Oficiálne n8n MCP** pripojené (má `execute_workflow` + `get_execution`). Pozn.: read-only `n8n-mcp`
  (czlonkowski) tento beh nevie spustiť — tam by bol potrebný webhook trigger.
- Workflow existuje: **„Image 2.0 — Generovanie a úprava obrázkov (wp-autobuilder)"**, na inštancii
  `netovapomoc.app.n8n.cloud`, **workflow_id `GtjjsjvLqPar2FwB`** (trigger = *Webhook Trigger*,
  path `wp-autobuilder-image`; dávka sa odovzdáva v `body`, Validate ju číta z `body` aj priamo).
  Plný build-spec: `n8n_obrazky_workflow_SPEC.md`.
- Credentials v n8n **musia byť priložené** (workflow ich nedrží):
  OpenAI (`openAiApi`) na 2 OpenAI uzloch + **WP Application Password** (HTTP Basic Auth) na 2 WordPress
  uzloch. WP credential je **per-inštancia klienta** (base_url chodí v dávke, ale auth je v n8n credentiali).
- Na produkcii WordPress Application Password (aby workflow nahral do media). Ak `wordpress.upload=false`,
  workflow vráti `data:`-URI namiesto verejnej URL — to `sideload-image` neprijme, preto **na produkcii vždy
  `upload=true`** (alebo dorobiť GDrive/S3 vetvu vo workflowe).

## base_url — ktorá doména (DÔLEŽITÉ)
`wordpress.base_url` v dávke = doména **WP inštancie, ktorú reálne edituješ cez Elementor MCP** (kam sa
nahrávajú médiá). **NIE** je to doména z URL obrázkov v obsahu stránky.
- Kópie/šablónové stránky majú v sebe **absolútne URL z master/zdrojového webu** (napr. `newo.eshopion.sk`)
  a z **agentúrneho** webu (`netovapomoc.sk` — logo, Google recenzie, zdieľané bloky). Sú to len **zvyšky**
  z predlohy; postupne ich prepíšu naplnené sloty. **NEPOUŽÍVAJ ich ako base_url.**
- **Ako zistiť doménu inštancie:** nahraj cez `elementor-mcp-sideload-image(<ľubovoľná URL>)` a z vrátenej
  `url` prečítaj doménu → to je `base_url`. (Alebo ju maj nakonfigurovanú per klient.)
- Nesúlad `base_url` ↔ inštancia = WP vráti **401 `rest_cannot_create`** (App Password platí pre iný web).
- Príklad (aktuálna testovacia inštancia): `https://news10.eshopion.sk` — pozor, `newo…` vs `news10…`
  sa ľahko zamenia.

## Tok (fáza Médiá)
1. Pre každý **image slot** (z blueprintu) zostav `item`: `slot_id`, `mode` (generate|edit|enhance),
   `prompt` (z briefu + kontextu sekcie + brand farby), `aspect_ratio`, `shot_type`, `seo_filename`, `alt`.
2. Zlož dávku `{ job_id, client, brand, defaults, wordpress, reference_faces, items[] }` (viď SPEC 1.1).
   `wordpress.base_url` = doména editovanej inštancie (viď sekciu „base_url"), `wordpress.upload=true`.
3. `n8n: execute_workflow(workflow_id, executionMode="manual", inputs={ type:"webhook", webhookData:{ method:"POST", body:<dávka> } })` → `get_execution` (poll do dokončenia).
4. Pre každý výsledok so `status:"ok"`:
   - ak `wp_media_id` → použi priamo,
   - inak `elementor-mcp-sideload-image(image_url)` → media id,
   - `elementor-mcp-update-element` priradí obrázok do image slotu (cez index-cestu z blueprintu).
5. Pri `status:"error"`/`partial` zopakuj danú položku alebo nechaj placeholder + zapíš do reportu.

## Priradenie médií (dedup + rozloženie) — `plan_media.py`
Pred zostavením dávky spusti `scripts/plan_media.py` (blueprint image_slots + `media.source` + počet
klientových fotiek) → `plan_<page>.json`. Plán je deterministický a vynucuje:
- **Dedup:** žiadna fotka (klientova ani generovaná) nie je vo viac než jednom slote na stránke.
  Klientove fotky sa môžu opakovať len v galérii (rieši gallery flow, nie tu).
- **Rozloženie:** klientove fotky idú prednostne do veľkých (primary) sekcií, generované sa rozložia do
  veľkých aj malých slotov (nielen malé), typy záberov sa striedajú.
- **Osoby ≥ 50 %:** medzi naplnenými slotmi je aspoň polovica `shot_type:"person"` (plánovač v prípade
  potreby promuje generované sekundárne sloty na person).
- **`client_only`** (fotka osoby na Kontakte, galéria) sa NIKDY negeneruje — len klientova fotka, inak skip.
Dávku stavaj presne podľa plánu (`mode`, `shot_type`, `client_index`); `mode:"skip"` slot vynechaj.

## 3 vetvy podľa `media.source` (z briefu/dotazníka)
- `client` — len upload (príp. `enhance`) klientových fotiek; negeneruj nové.
- `generated` — všetko `generate`.
- `mix` — väčšie sekcie = fotky klienta, menšie = generované (timeline).

## Pravidlá (z 01_SABLONA + timeline)
- Brand farby (primárna + sekundárna) jemne zakomponuj do fotiek a zlaď color grading so stránkou (nesmú dominovať);
  pestrosť záberov (person/detail/symbol/wide); 2–3 opakujúce sa tváre
  (cez `reference_faces`); pri remeslách konkrétna činnosť; min. 1 video / stránka (sesterský Runway workflow,
  rovnaký kontrakt, `mode:"video"`).
- SEO: každý obrázok má `seo_filename` + `alt`.

## Stav (skill-side)
- ✅ **Image sloty** definované v `hp_slot_blueprint.json` → pole `image_slots` (aspect_ratio, shot_type,
  prompt_context, seo_hint). `path` (index-cesta na image widget) je **vyplnená pre všetky pokryté stránky**
  (hp 9, about 13, services 8, contact 1, pricing 1, gallery 4 — spolu **36 image slotov**) a **overená
  resolverom proti živým draft stránkam** (2026-06-18: 36/36 OK, exit 0). Pri **zmene mastera** ju over/
  aktualizuj jedným `get-page-structure` + `resolve_slots.py`. Resolver mapuje `path` → element_id ako pri
  textových slotoch.
- ✅ **Fáza Médiá** je v `SKILL.md` (Fáza 4b, medzi textami a QA).

## Známe obmedzenia (zatiaľ neimplementované vo workflowe)
- **Konzistentné tváre** — `use_reference_face` / `reference_faces` workflow zatiaľ **ignoruje** (generate robí
  čistú generáciu; edits posiela len 1 vstupný obrázok). 2–3 opakujúce sa tváre naprieč webom teda zatiaľ
  nedrží. Spec to označuje ako voliteľné; doplní sa neskôr (edits endpoint s viacerými vstupnými obrázkami).
- **Video** (min. 1/stránka) rieši **sesterský Runway workflow** (`mode:"video"`, rovnaký kontrakt) — ešte nie je.
- **`upload=false`** vetva vracia `data:`-URI (nepoužiteľné pre `sideload-image`) — na produkcii drž `upload=true`.

## Hotfixy / poznámky k workflowu (z testu 18.6.2026)
- **Convert to File zahadzuje JSON** → uzly *Upload to WordPress* a *Set Alt & Title* musia `wp_base_url`/
  `_filename` brať z `$('Decode to Binary').item.json.…`, nie z `$json.…` (inak „Invalid URL: /wp-json/wp/v2/media").
  [Vo workflowe už opravené.]
- **High-quality timeout:** OpenAI uzly majú timeout 120 s; `gpt-image-2` pri `quality:"high"` to prekračuje
  (chyba „connection was aborted") → zvýš timeout na ~300000 ms na *OpenAI Generate* aj *OpenAI Edit*.
- **WP 401 `rest_cannot_create`:** skoro vždy nesúlad `base_url` ↔ inštancia, alebo credential nepriradený
  na uzle (vytvoriť credential ≠ priradiť ho na uzol). Heslo App Password sa zadáva ako Basic Auth (user + heslo),
  bez ručného base64; medzery v hesle WP ignoruje.

## Prompty pre obrázky (zákazníkov štandard)
Prompty (`items[].prompt`) + `seo_filename` zostavuj **podľa `references/image_prompt_guide.md`** (verne prebratý zákazníkov prompt z `Prompt-obrázky.docx`). Vstup beriem z briefu + kontextu sekcie (Režim E), nepýtam sa, generujem presne toľko promptov koľko je image slotov. Per-stránka prompty (Prompt _HP_, _o nás_…) môžu doplniť.
