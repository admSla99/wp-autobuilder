# Vyčistenie produktového mastera — spec

## Čo to znamená (a prečo)
Master produktovej stránky (`new2`, post **17045**) **nie je čistá šablóna** — je to demo zložené z viacerých
odvetví (právnik, cestovný ruch, agentúra) s anglickým Lorem/demo textom a demo obrázkami z `newo.eshopion.sk`.
Autobuilder mapuje (a vypĺňa) len časť sekcií; **nemapované demo sekcie by sa na klientovej produktovej stránke
zobrazili tak ako sú** — „Featured stories", zoznam „Services / Visual identity / Branding…", „Our vision & mission",
výlety „Kam vyraziť / Výlety", image-carousel, demo recenzie „Vlado Mečiar", fotky vodopádov a Liptovskej Mary.

**Vyčistenie = spraviť z mastera neutrálnu, súdržnú produktovú šablónu** obsahujúcu IBA osnovu produktovej stránky
(podľa `product_copy_guide.md`): hero (kategória, H1, foto produktu, 3 benefit-stĺpce) → sekcia 2 fotky (voliteľná)
→ ikonková sekcia (3–6) → Google recenzie (link + rating + karty) → CTA → footer. Demo balast sa odstráni, zvyšné
placeholdery sa znetrálnia (SK/prázdne), demo obrázky sa nahradia neutrálnym placeholderom. Potom autobuilder vypĺňa
čistú kostru a na klientovej stránke nič cudzie „nepretečie".

## Keep / Remove / Neutralize (master 17045)
| Sekcia (top-level) | element id | Verdikt | Akcia |
|---|---|---|---|
| [0] Hero (kategória, foto, H1, 3 benefit-stĺpce) | feb114b | **KEEP** (jadro) | H1/kategória/stĺpce → SK placeholder/prázdne; foto → neutrálny placeholder |
| [1] „Featured stories" (2× promo-box) | 8f7f92c | **REMOVE** | anglické demo, mimo osnovy |
| [2] text + obrázok (cik-cak) | 469d965 | **KEEP (voliteľné)** = sekcia „2 fotky" | text/„Klikni tu"/obrázok → znetrálniť |
| [3] „Services" zoznam + „Our vision & mission" | 64107f8 | **REMOVE** | anglické agentúrne demo |
| [4] global CTA | 2246b51 | **KEEP** | zdieľaný global widget — nemeniť |
| [5] ikonková sekcia (3× icon-box) + CTA | a066804 | **KEEP** (jadro) | titulky/popisy → placeholder; **zelené pozadie → transparentná primárna** |
| [6] „Kam vyraziť / Výlety / Galéria" + 2 fotky | e0bdef1 | **REMOVE** | cestovné demo, galéria je samostatná stránka |
| [7] image-carousel | fca028e | **REMOVE** | prázdne/demo |
| [8] recenzie — intro + link tlačidlo | a96e4a3 | **KEEP** (jadro) | text/link → znetrálniť (vypĺňa content.reviews) |
| [9] recenzie — 3 karty | 83e046a | **KEEP** (jadro) | demo mená/texty „Vlado Mečiar" → prázdne (vypĺňa klient, inak skryť) |
| [10] footer (xpro-template) | 6863447 | **KEEP** | zdieľaná šablóna — nemeniť |

> Pozn.: `new3` (17051) je rovnaké demo, navyše BEZ kariet recenzií [9] → ako master nevhodný. Ostáva `new2`.

## DÔLEŽITÉ: po vyčistení sa zmenia index-cesty
Odstránením sekcií [1],[3],[6],[7] sa posunie poradie detí → **`products_slot_blueprint.json` sa musí
prederivovať** z vyčisteného mastera (get-page-structure → aktualizovať `path` + overiť `resolve_slots`).
Aktuálny blueprint je mapovaný na DNEŠNÍ (zaprataný) master.

## Bezpečný postup (NEdeštruktívne na zdieľanom masteri)
1. **Záloha:** `elementor-mcp-export-page(17045)` → ulož JSON export (rollback). Prípadne aj snapshot štruktúry.
2. **Pracuj na KÓPII:** duplikuj 17045 do novej stránky „Produktová stránka — MASTER (clean)" a uprav kópiu
   (nie zdieľaný live master), aby sa nerozbili iné závislosti. Po schválení sa kópia stane kanonickým masterom.
3. **Odstráň** demo sekcie: `elementor-mcp-remove-element` pre id `8f7f92c`, `64107f8`, `e0bdef1`, `fca028e`.
4. **Znetrálni** zvyšné placeholdery (anglické/Lorem → SK neutrálne alebo prázdne) a **demo obrázky** → neutrálny
   placeholder (hero foto = client_only, vypĺňa klient).
5. **Oprav** ikonkovú sekciu: zelené pozadie kontajnera [5] → transparentná primárna (rgba primárnej ~8–12 %).
6. **Preriv blueprint:** get-page-structure(clean master) → uprav `path` v `products_slot_blueprint.json` +
   `source_sample_post` = id čistého mastera → over `resolve_slots` (musí byť 100 % ok).
7. (voliteľné) ulož čistý master aj ako Elementor template pre `apply-template` pri klonovaní per produkt.

## Čo NErobiť
- Needitovať global widgety [4] ani footer [10] (zdieľané).
- Nemeniť farby per-widget (ikony/nadpisy dedia globálnu primárnu z Fázy 1b) — výnimka je len pozadie ikonkovej sekcie.
- Nevymýšľať recenzie (mená/texty/rating) — karty plní klient, inak sa skryjú.
