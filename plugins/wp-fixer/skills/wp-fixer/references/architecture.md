# Architektúra wp-fixer (opravár)

`wp-fixer` je **sesterský skill k `wp-autobuilder`**. Kým autobuilder **stavia celú stránku z briefu**
(všetky sloty naplní podľa dotazníka), fixer **aplikuje cielené pripomienky** na **už postavený živý
web** — je to „opravár / revízia webu". Vstup nie je štruktúrovaný dotazník, ale **voľné pripomienky**
(čo treba na stránke zmeniť), ktoré Claude znormalizuje na `changeset.json` a autonómne vykoná.

## Rozdiel oproti autobuilderu (jedným pohľadom)
| | wp-autobuilder | **wp-fixer** |
|---|---|---|
| Vstup | dotazník (GDrive) → `brief.json` | **pripomienky (GDrive/chat) → `changeset.json`** |
| Model | blueprint-driven: naplň VŠETKY sloty | **change-driven: zmeň LEN to, čo je v pripomienke** |
| Lokalizácia | index-cesty blueprintu (klon má nové ID) | **hybrid: blueprint + find-element + štruktúra** (ID pri edite stabilné) |
| Bezpečnosť | QA že je stránka naplnená | **snapshot + diff (žiadny kolaterál) + QA zmien** |
| Rozsah | jeden beh = celý web | jeden beh = množina pripomienok (rôzne stránky/kit/global) |
| Publish | po QA publikuj (draft ak chyba) | **po QA + diff ulož naživo; pri chybe rollback zo snapshotu** |

## Znovupoužitie z autobuildera (NEDUPLIKUJ — referencuj sibling)
Fixer je v **rovnakom marketplace** ako autobuilder, preto **priamo používa jeho skripty a dáta** cez
`AB_DIR` (= priečinok skillu `wp-autobuilder`; postup nájdenia — nainštalovaný plugin / marketplace
repo / plochý layout — je v SKILL.md, sekcia „Pracovný priečinok a cesty").
NEklonuj ich do fixera (drift). Znovupoužité:
- **Skripty:** `AB_DIR/scripts/build_palette.py` (farby kit), `plan_media.py` (dedup/rozloženie fotiek),
  `resolve_slots.py` (blueprint path → element_id), `fill_globals.py` (agentúrne tokeny → klient),
  `extract_palette.py` (farby z loga).
- **Dáta:** `AB_DIR/references/<page>_slot_blueprint.json` (6 typov stránok + image sloty),
  `kit_colors.json`, `image_prompt_guide.md`, `global_tokens.json`, `globals_blueprint.json`,
  `media.md`, `colors.md`, `intake.md` (mapovanie dotazníka, ak treba dogenerovať copy).
- **n8n workflow** médiá: `execute_workflow(workflow_id="GtjjsjvLqPar2FwB")` + `get_execution`
  (Image 2.0), sideload cez `elementor-mcp-sideload-image` (viď `AB_DIR/references/media.md`).

> Fixer je distribuovaný ako plugin `wp-fixer` z marketplace `wp-skills` a **vyžaduje nainštalovaný
> plugin `wp-autobuilder`** z toho istého marketplace (inak `AB_DIR` chýba). Pri balení fixera ako
> samostatný `.skill` mimo marketplace treba tieto zdieľané zdroje priložiť.

## Vlastné (nové) časti fixera
- `references/changeset.schema.json` + `changeset.example.json` — kontrakt znormalizovaných pripomienok.
- `references/intake_notes.md` — ako z voľných pripomienok (GDrive/chat) spraviť `changeset.json`.
- `references/localization.md` — **hybridná lokalizácia cieľa** (jadro opravára).
- `references/change_types.md` — dispatch: pre každý typ zmeny KTORÝ nástroj/vzor + bezpečnostné pravidlá.
- `references/qa_fix.md` — QA orientovaná na zmeny + diff brána + rollback.
- `scripts/validate_changeset.py`, `plan_changes.py`, `diff_structure.py`, `qa_fix_check.py`, `selftest.py`.

## Fázy (jeden beh)
0. **Intake** — pripomienky (GDrive dokument alebo text v chate) → `changeset.json` → `validate_changeset.py`.
1. **Echo identity** — prečítaj živú doménu inštancie a spáruj s klientom (PRED prvým zápisom). Denylist agentúrneho hosta.
2. **Plan** — `plan_changes.py` → `plan.json` (zoskupenie per stránka / kit / global / media, poradie, konflikty).
3. **Snapshot** — `get-page-structure` pre každú dotknutú stránku (`snapshot_before_<page>.json`) + `get-global-settings` ak sa menia farby. Toto je **rollback base**.
4. **Lokalizuj + aplikuj** (hybrid, per zmena): 4a texty/linky/kontakt · 4b viditeľnosť/štruktúra · 4c farby (kit, RAZ) · 4d médiá (dedup dávka) · 4e globálne prvky (RAZ). Po každej zmene **over re-readom**.
5. **QA + diff + save/publish** (per stránka) — `diff_structure.py` (žiadny kolaterál) + `qa_fix_check.py` (žiadny nový placeholder, invarianty, cieľové hodnoty prítomné). Ak OK → ulož naživo; ak nie → **rollback zo snapshotu**.
6. **Report** — `instance_domain`, per zmena before→after + stav, nevyriešené pripomienky, chýbajúce klientske vstupy.

## Bezpečnostné princípy (prečo je fixer „opatrný")
1. **Meň len cielené prvky.** Snapshot + `diff_structure.py` porovná pred/po a každú zmenu prvku **mimo
   plánu** označí ako kolaterál → rollback. (Autobuilder toto nepotrebuje — stavia od nuly.)
2. **ID sú pri edite stabilné.** Na rozdiel od klonovania sa element_id po `update-*` nemení, takže
   cielime konkrétne ID a diff je spoľahlivý.
3. **Autonómne, ale nikdy naslepo.** Ak sa cieľ nedá jednoznačne lokalizovať (0 alebo viac zhôd),
   zmena sa **NEaplikuje**, označí `unresolved` a zapíše do reportu. Žiadne `AskUserQuestion`.
4. **Rovnaká inštancia-poistka ako autobuilder.** Zlá inštancia = najdrahšia chyba; echo identity (Fáza 1)
   a denylist agentúrneho hosta sú povinné pred akýmkoľvek zápisom.
5. **Honesty invarianty** (ceny/recenzie/mená/fakty len od klienta) platia rovnako ako v autobuilderi.
