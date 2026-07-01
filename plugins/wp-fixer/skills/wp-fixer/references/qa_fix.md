# QA orientovaná na zmeny + diff brána + rollback

Fixer edituje **živé stránky** a mení **iba to, čo je v pripomienke**. Preto QA nie je „je stránka
naplnená" (to je autobuilder), ale **dvojica bezpečnostných kontrol**: (1) žiadny kolaterál,
(2) zmeny sú korektne aplikované a neporušili invarianty. Až po ich úspechu sa ukladá naživo.

## 1) Snapshot pred zápisom (rollback base) — Fáza 3
- **Per stránka:** `get-page-structure(post_id)` → `snapshot_before_<page>.json` (na diff-bránu).
- **Per cielený prvok:** `get-element-settings(element_id)` → `element_before_<element_id>.json` — **PLNÉ
  nastavenia** (nie iba `settings_summary`, ktoré je podmnožina) = verný rollback base pre daný prvok.
- **Farby:** `get-global-settings` → `kit_before.json` (celý kit).
- **Globálne prvky (Fáza 4e — footer/CTA bublina/popup/GDPR/cookies):** tieto sú **inštancia-wide** (najdrahšie
  na chybu, viď CLAUDE.md), preto ich tiež zálohuj — pre každý dotknutý theme widget / právnu stránku
  `get-element-settings`/`get-page-structure` → `global_before_<id>.json`. Bez tejto zálohy globálny prvok needituj.
- Tieto súbory sú **záloha** — pri zlyhaní QA/diff/re-readu sa nimi vracia stav späť.

## 2) Diff brána — `diff_structure.py` (žiadny kolaterál)
Po aplikovaní všetkých zmien danej stránky:
- `get-page-structure(post_id)` → `snapshot_after_<page>.json`.
- `python SKILL_DIR/scripts/diff_structure.py --before snapshot_before_<page>.json --after snapshot_after_<page>.json --allowed <cielené element_id oddelené čiarkou>`
  (pri štruktúrnych/visibility zmenách pridaj **`--allow-added`/`--allow-removed`** s očakávanými id — radšej
  než blanket `--allow-structural`, aby sa stále zachytili **neočakávané** pridania/odobrania inde).
- **FAIL-CLOSED:** ak `--allowed` necháš prázdny a niečo sa zmenilo, brána berie **všetko ako kolaterál**
  (exit 1) — nie fail-open. Prázdny `--allowed` má zmysel len s výslovným `--allow-empty`.
- **Výsledok:** vypíše zmenené / pridané / odobrané `element_id`. Kolaterál (mimo `--allowed`) alebo neočakávaná
  štruktúrna zmena → **exit 1 → ROLLBACK** (nižšie, sekcia 4) a zapíš do reportu (nepublikuj).
- `--allowed` je zoznam cielených ID z lokalizácie (Krok C v `localization.md`) + kontajnery pri štruktúre.
- **Slepé miesta brány** (`settings_summary` je len podmnožina): (a) **obrázkové** zmeny — over **re-readom**
  cieľového image slotu; (b) **skrytie sekcie** (`hide_*` sa v summary nemusí prejaviť) — over **re-readom**
  `get-element-settings` kontajnera; (c) **globálne prvky** (Fáza 4e) — nie sú v page štruktúre, over ich
  re-readom proti `global_before_<id>.json`. Brána spoľahlivo chytá **textové/viditeľné** kolaterály.

## 3) QA zmien — `qa_fix_check.py`
- `python SKILL_DIR/scripts/qa_fix_check.py --structure snapshot_after_<page>.json --changeset changeset.json --page <page_type_alebo_hint>`.
- Kontroluje:
  1. **Žiadny NOVÝ placeholder** (Lorem ipsum, „Služba 1–6", „Item One…", „Obrázok 1–9", `[DOPLNIŤ]`) —
     ak by zmena zaviedla placeholder → **chyba** (exit 1).
  2. **Cieľové hodnoty prítomné:** pre zmeny s literálom (`desired.value`/`text_spec.contains`) over,
     že sa text nachádza v štruktúre (verifikácia aplikovania). Chýba → varovanie „over aplikovanie".
  3. **Invarianty:** CTA ≤ 21 znakov na tlačidlách (okrem zdieľaného „Chcem viac informácii");
     agentúrne zvyšky (`netovapomoc`/`fajne-weby`) → varovanie (rieši Fáza 4e Global).
- **Pravidlové zmeny bez literálu** (dĺžka textu, farebnosť fotky, pomer) sa cez text nedajú overiť —
  over ich **re-readom prvku** a vizuálne v reporte (before→after).

## 4) Publish gate + rollback — Fáza 5
- **QA + diff OK** (diff exit 0, qa exit 0, re-ready sedia) a `publish_after_fix=true` (default) → stránka je už
  publikovaná, takže úprava je naživo; ak bola stránka draft, nastav status `publish`
  (`update-page-settings`, post status `publish`).
- **QA / diff / re-read ZLYHÁ:** stránku **nepublikuj** a vykonaj **ROLLBACK**:
  - **In-place zmeny** (text/link/contact/farba pozadia): zapíš späť **plné** `element_before_<id>.json`
    cez `update-element`/`update-widget` (nie summary — to je podmnožina). Kit z `kit_before.json`.
  - **Globálne prvky (4e):** zapíš späť `global_before_<id>.json`.
  - **Štruktúrne zmeny** (pridaný/odobraný podstrom): rollback = **zmazať pridané** / **znova vytvoriť odobrané**
    (nie zápis starých hodnôt). Ak sa to nedá spoľahlivo, štruktúrnu zmenu vôbec nerob (viď `change_types.md`).
- `publish_after_fix=false` → zmeny nechaj, ale needituj status; report + preview URL na ručnú kontrolu.

## 5) Selftest (bez živého webu)
`python SKILL_DIR/scripts/selftest.py` — synteticky overí reťazec
`validate_changeset → plan_changes → diff_structure → qa_fix_check` (vrátane detekcie kolaterálu a
placeholderu) na fixtúrach. Spusti po zmene skriptov.
