# Architektúra wp-autobuilder

Tento skill je **orchestrátor** z návrhového dokumentu (Navrh_systemu_WP_autobuilder.docx).
Spúšťa sa z jedného vstupu a vo vnútri prechádza fázy. Pokryté stránky: **HP, O nás, Služby, Kontakt, Cenník, Galéria** (fázy 2–5 v slučke per stránka).

## Trojvrstvový model pravidiel
1. **Autorská vrstva** — `01_SABLONA_v2.xlsx` (edituje človek).
2. **Kompilát** — `references/rules.json` (z `scripts/compile_rules.py`). Skill číta toto.
3. **Skill** — procedúra + nemenné invarianty (tento priečinok).

## Fázy (z návrhu) a stav v MVP
| Fáza | Návrh | Stav v tomto skille |
|---|---|---|
| 0 Intake | brief z dotazníka + GDrive | brief.json (zatiaľ ručne/ukážka) |
| 1 Brand/farby | globálne farby z briefu | ✅ build_palette (read-merge-write) → update-page-settings na kit (default `apply_global_colors=true`); `false` len pri zdieľanom kite = iba color plan |
| 2 Cieľové stránky | priamo stránky inštancie | ✅ list-pages → Hp / O nás / Služby / Kontakt / cenník podľa `page_title_candidates` blueprintov (na dev webe sa cielia draft kópie, klon sa v skille NEROBÍ) |
| 3 Texty | naplnenie slotov | ✅ resolve_slots → build_ops → batch-update; per stránka. Navyše: hide_if_missing (cenník), clear_if_missing, cast int (countery), link.url, repeater (FAQ) cez read-merge-write |
| 4 Médiá | Image 2.0 / Runway cez n8n | ✅ OBRÁZKY: Fáza 4b → n8n „Image 2.0" (id GtjjsjvLqPar2FwB) → sideload/wp_media_id → update-element (ak media.source≠placeholder; image_slots path treba doplniť z get-page-structure). Video (Runway) zatiaľ placeholder; konzistentné tváre zatiaľ neriešené |
| 5 Sekcie | header/footer/CTA/pop-up/kontakt | GLOBÁLNE (theme templates) — samostatná fáza, nie HP |
| 6 Galéria | jedno-/viacúrovňová | ĎALŠÍ REZ |
| 7 QA | predpublikačná kontrola | ✅ qa_check |
| 8 Publish | po schválení | manuálne (stránka ostáva draft) |

## Rozšírenie na ďalšie stránky
Pridať blueprint `references/<page>_slot_blueprint.json` (index-cesty + mapovanie na brief)
a v `rules.json` existuje zodpovedajúca stránka. Procedúra je rovnaká.
Hotové blueprinty: `hp`, `about` (13109), `services` (12842), `contact` (13359), `pricing` (15389), `gallery` (897)
— čísla = master post_id na dev webe, z ktorého boli index-cesty odčítané.
Zostáva: blog (šablóna článku, iný charakter), products/product_page, area. team_refs zámerne nie (Google Reviews API).

## Prečo index-cesty (a nie natvrdo ID)
Pri klonovaní Elementor pridelí nové element ID, ale poradie a štruktúra ostávajú.
Blueprint preto adresuje sloty cez index-cestu v strome; `resolve_slots.py` ich
premapuje na aktuálne ID a overí typ widgetu. Žiadny zásah do master šablóny netreba.
