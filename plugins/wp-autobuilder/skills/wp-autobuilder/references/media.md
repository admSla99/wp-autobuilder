# Médiá — generovanie a úprava obrázkov (skill-side kontrakt)

Fáza Médiá volá **n8n workflow** (OpenAI `gpt-image-2-2026-04-21`, interný názov „Image 2.0") cez **n8n MCP**.
Plný build-spec workflowu: `n8n_obrazky_workflow_SPEC.md`. Tu je len to, čo robí skill.

## Predpoklady
- **Built-in n8n connector** (ten, čo používa Claude cowork) pripojený — poskytuje **`execute_workflow` + `get_execution`**.
  Na spustenie workflowu použi **`execute_workflow`** (tento názov má LEN connector). **NEpoužívaj** nástroje
  `n8n_*` z druhého servera `n8n-mcp` (czlonkowski) — slúžia na správu/diagnostiku workflowov, nie na tento beh.
- Workflow existuje: **„Image 2.0 — Generovanie a úprava obrázkov (wp-autobuilder)"**, na inštancii
  `netovapomoc.app.n8n.cloud`, **workflow_id `GtjjsjvLqPar2FwB`** (trigger = *Webhook Trigger*,
  path `wp-autobuilder-image`; dávka sa odovzdáva v `body`, Validate ju číta z `body` aj priamo).
  Plný build-spec: `n8n_obrazky_workflow_SPEC.md`.
- Credentials v n8n **musia byť priložené** (workflow ich nedrží):
  OpenAI (`openAiApi`) na 2 OpenAI uzloch + **jeden agentúrny Google Drive** (`googleDriveOAuth2Api`,
  „Google Drive account") na uzloch *Upload to Drive* + *Make Public*. **Žiadne WP credentials** —
  workflow do WordPressu nenahráva.
- Výstup obrázka: workflow ho uloží na Drive do priečinka **`wp-autobuilder-media`**
  (`folderId 17up1uU8zxK0g4fo3UpYbKOG1BiRFGeVz`), sprístupní „anyone with link" a vráti **verejnú URL**
  `https://lh3.googleusercontent.com/d/<fileId>` v poli `image_url`; `wp_media_id` je vždy `null`.
  Upload do inštancie klienta robí `elementor-mcp-sideload-image` (auth má per-inštancia z prepínača).

## Inštancia a domény (DÔLEŽITÉ)
Dávka **už neobsahuje `wordpress`** — workflow nepotrebuje vedieť, na ktorú inštanciu sa píše. Cieľová
inštancia je výlučne tá, na ktorú je práve nasmerovaný **Elementor MCP** (prepínač v `CLAUDE.md`); tam
`sideload-image` nahrá obrázok z verejnej Drive URL.
- Kópie/šablónové stránky majú v sebe **absolútne URL z master/zdrojového webu** (napr. `newo.eshopion.sk`)
  a z **agentúrneho** webu (`netovapomoc.sk` — logo, Google recenzie, zdieľané bloky). Sú to len **zvyšky**
  z predlohy; postupne ich prepíšu naplnené sloty. Inštanciu z nich neodvodzuj.
- Pridanie nového klienta = iba prepnutie Elementor MCP. **Do n8n sa už nič nepridáva.**

## Tok (fáza Médiá)
1. Pre každý **image slot** (z blueprintu) zostav `item`: `slot_id`, `mode` (generate|edit|enhance),
   `prompt` (z briefu + kontextu sekcie + brand farby), `aspect_ratio`, `shot_type`, `seo_filename`, `alt`.
2. Zlož dávku `{ job_id, client, brand, defaults, reference_faces, items[] }` (viď SPEC 1.1). **Bez `wordpress`.**
3. `n8n: execute_workflow(workflow_id, executionMode="manual", inputs={ type:"webhook", webhookData:{ method:"POST", body:<dávka> } })` → `get_execution` (poll do dokončenia).
4. Pre každý výsledok so `status:"ok"`: `image_url` je verejná Drive URL →
   `elementor-mcp-sideload-image(image_url)` → media id →
   `elementor-mcp-update-element` priradí obrázok do image slotu (cez index-cestu z blueprintu).
   Alt/title nastav na slote z `result.alt` / `result.seo_filename`.
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
- **SEO filename:** `sideload-image` ťahá `…/d/<fileId>`, takže výsledný WP súbor sa môže pomenovať podľa Drive ID,
  nie podľa `seo_filename` (alt/title sa nastaví na slote z `result`). Malá SEO strata; ak `sideload-image` vie
  prijať želaný filename, doplň ho.
- **Junk na Drive:** každý beh pridá obrázky do `wp-autobuilder-media`; priečinok občas vyčisti.

## Hotfixy / poznámky k workflowu
- **Drive upload (od 29.6.2026):** chvost workflowu je *Decode → Has Image? → Convert to File → Upload to Drive
  → Make Public → Build Public URL → Map Result*. *Convert to File* zahadzuje JSON, preto *Upload to Drive*
  berie `name` z `$('Decode to Binary').item.json._filename`, *Build Public URL* berie `fileId` z
  `$('Upload to Drive').item.json.id` (a *Make Public* vracia objekt permissionu, nie súbor — neber `id` z neho).
- **Kvalita + timeout:** default `quality` je **`medium`** (`Validate & Defaults`: `defaults.quality || 'medium'`).
  Timeout na *OpenAI Generate* aj *OpenAI Edit* je **dynamický**: `quality:"high" → 300000 ms`, inak `120000 ms`
  (`={{ $json.quality === 'high' ? 300000 : 120000 }}`) — `high` totiž 120 s často prekročí („connection was aborted").
- **OpenAI „Bad request / Billing hard limit reached":** generácia padne na úrovni OpenAI uzla (nie chyba Drive
  vetvy) → výsledok `status:"error"`. Skontroluj kredit/limit na účte OpenAI (`openai-platform-netovapomoc6`).
- **`sideload-image` 404 z Drive URL:** obrázok nebol sprístupnený „anyone" (*Make Public* zlyhal) — over,
  že share uzol prešiel a `image_url` je `https://lh3.googleusercontent.com/d/<fileId>`.

## Prompty pre obrázky (zákazníkov štandard)
Prompty (`items[].prompt`) + `seo_filename` zostavuj **podľa `references/image_prompt_guide.md`** (verne prebratý zákazníkov prompt z `Prompt-obrázky.docx`). Vstup beriem z briefu + kontextu sekcie (Režim E), nepýtam sa, generujem presne toľko promptov koľko je image slotov. Per-stránka prompty (Prompt _HP_, _o nás_…) môžu doplniť.
