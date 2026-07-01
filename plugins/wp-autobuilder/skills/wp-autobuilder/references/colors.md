# Brand / Farby - bezpecne prefarbenie kitu

## Pravidlo (01_SABLONA_v2)
Farby su v stlpci "AI NESMIE menit" v kazdej sekcii. AI ich nikdy nemeni po sekciach -
brand farba sa nastavi RAZ globalne (Elementor kit) a sekcie ju dedia cez premenne
`--e-global-color-*`. Preto je toto samostatna brand faza, nie sucast textov.

## KRITICKE ZISTENIE (overene testom)
- Zapisy do kitu su "partial-replace" = DESTRUKTIVNE. `update-page-settings` aj `add-custom-css`
  prepisu CELY kit; vsetko, co nie je v payloade, resetnu na Elementor defaulty
  (typografia -> Roboto, paleta -> prazdna, custom CSS -> prec).
- `update-global-colors`: nedestruktivny, ale pise LEN custom paletu (nie system_colors)
  a nuluje 8-miestny hex (alfa). NEPOUZIVAT na brand farby.
- `add-custom-css` na kit: tiez resetne kit na defaulty. NEPOUZIVAT na kit.

## Bezpecny vzor: read-merge-write (atomicky)
1. Najdi kit id: `elementor-mcp-list-templates(template_type="kit")` -> post_id (napr. 6 "Vychozi sada").
2. `elementor-mcp-get-global-settings` -> uloz `kit_current.json` (CELY kit; sluzi aj ako ZALOHA).
3. `python SKILL_DIR/scripts/build_palette.py --brief brief.json --current kit_current.json --kit SKILL_DIR/references/kit_colors.json -o kit_new.json`
   (vlozi system + odvodene custom; ZACHOVA typografiu, custom CSS, vsetky ostatne polia).
4. Zapis CELY objekt JEDNYM volanim:
   `elementor-mcp-update-page-settings(post_id=<kit_id>, settings=<kit_new.json>)`.
   NIKDY ciastocne. NIKDY potom `update-global-colors` ani `add-custom-css` na kit (resetli by ho).
5. Overenie: `get-global-settings` -> system_colors = brand, custom_typography neprazdne, custom_css pritomne.

## Rollback (obnova)
`elementor-mcp-update-page-settings(post_id=<kit_id>, settings=<kit_current.json>)` -
zapis ulozeny cely kit naspat (jeden atomicky zapis).

## Aplikovanie (flag apply_global_colors)
- DEFAULT `true`: krok 4 vykonaj - farby sa ZAPISU do kitu. `kit_current.json` (krok 2) drz ako zalohu pre rollback.
- `false` IBA ak je kit zdielany s inymi klientmi/masterom (site-wide) - vtedy by zapis prepisal aj ich;
  vtedy kit NEMENIT, vygeneruj len `kit_new.json` + "color plan" do reportu.

## Mapovanie a odvodenie
system: primary<-brand.primary, secondary<-brand.secondary, accent<-brand.accent, text ostava.
custom odtiene (Primary light/dark/transparent, Secondary light/dark, Oddelovac, Form...) sa
dopocitaju z primary/secondary podla `references/kit_colors.json` (lighten/darken/alpha).
Neznáme custom farby klienta sa zachovaju. Typografiu needitovat (iba ak brief ziada font).

## Test logiky (bezpecny, bez dotyku webu)
`python SKILL_DIR/scripts/palette_selftest.py` - overi merge: brand farby nastavene,
typografia + custom CSS + ostatne polia zachovane.
