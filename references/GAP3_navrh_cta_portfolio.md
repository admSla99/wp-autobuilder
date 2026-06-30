# Gap 3 — návrh: CTA odkazy + HP portfolio (do_not_touch widgety s agentúrnym obsahom)

Rovnaká trieda problému ako G1–G3 (recenzie/blog/icon-list): widget, ktorý skill needituje, nesie agentúrny
obsah a **nemá napĺňaciu cestu**. Riešenie ostáva v už zavedených vzoroch — **kontajnerový hide-slot** (ako
`hp.reviews.*`, `hp.blog.section`) a **globálne napĺňanie cez Fázu 6** (ako footer/popup). Žiadna nová mechanika.

---

## 3a — CTA odkazy (link targets)

### Problém (overené z reálnej štruktúry HP 17992)
Skill plní CTA **text**, ale nie **link**. Všetky CTA na HP odkazujú na agentúrny lievik:
- `global` widgety „Chcem viac informácii" (`26c3b89a`, `38bd5b25`, `7c9e77dc`, `35376492`, `69d8142a`, `6749c986`) → `/produktova-stranka/`
- hero buttony (`3b4caaa5`, `3276d2e1`) a block button (`13db4f86`) → `/produktova-stranka-new2/`

Na vlastnej inštancii klienta je cieľ cudzí/neexistujúci.

### Návrh
**Brief:** pridať `content.cta_target` (default klientova konverzná stránka, napr. `/kontakt/`, príp. `tel:<phone>`).
Voliteľne `content.cta_target_secondary`.

**Editovateľné buttony (build_ops, deterministicky):** k CTA slotom v blueprintoch pridať mapovanie linku —
nový leaf slot so `setting:"link.url"`, `brief:"content.cta_target"` (build_ops `link.url` už podporuje, vrátane
default `is_external/nofollow`). Týka sa: `hp.hero.cta_primary(.link)`, `hp.hero.cta_secondary(.link)`,
`hp.block1.cta(.link)`, `services.hero.cta(.link)`.

**`global` CTA widgety (zdieľané v rámci inštancie) → Fáza 6:** global widget = jedna definícia pre celý web,
preto raz na inštanciu:
1. `find-element(widget_type="global")` resp. `search_text="/produktova-stranka"` → element_id.
2. `update-widget(settings={"link":{"url": content.cta_target, ...}})`.
Pridať do `globals_blueprint.json` položku `cta_global` (search hint + `setting:"link.url"`).

**Invariant (`rules.json` → global_invariants):** „CTA cieľ = klientova stránka; nikdy agentúrny `/produktova-stranka/`."

**QA:** do `qa_check.py` AGENCY_LEFTOVERS pridať `(r"/produktova-stranka", "agentúrny CTA cieľ")` ako VAROVANIE
→ po behu musí zmiznúť (rovnako ako `netovapomoc`).

---

## 3b — HP portfólio (variant služieb)

### Problém
HP má v sekcii služieb `[1]` (kontajner `137251a3`) widget `xpro-simple-portfolio` (`3ac7420d`) s **demo portfóliom**
+ duplicitný nadpis „NAŠE SLUŽBY / Čomu se venujeme". Reálne služby plníme v **kartovej** sekcii `[2]` (`29c44c46`).
Takže `[1]` ostáva demo a nadpis je zdvojený.

### Návrh (jeden variant, druhý skry — ako galéria/recenzie)
Default **skryť portfóliovú sekciu `[1]`** (kartová sekcia `[2]` plne pokrýva služby). Pridať do
`hp_slot_blueprint.json` hide-slot:
```json
{ "slot_id": "hp.services.portfolio_section", "path": [1], "widget": "container", "setting": "_hide",
  "brief": "content.sections.use_portfolio", "hide_if_missing": true, "optional": true,
  "_note": "Skry portfóliovú sekciu (demo + duplicitný nadpis), ak klient nechce variant portfólia" }
```
- `content.sections.use_portfolio` v briefe chýba → sekcia sa **auto-skryje** (default).
- Ak by klient chcel portfólio NAMIESTO kariet: intake nastaví `use_portfolio` (≠ prázdne) → sekcia ostane a
  doplní sa populácia `xpro-simple-portfolio` klientovými fotkami (rovnaký read-merge-write ako galéria) +
  skryje sa kartová sekcia `[2]`.
- **Pozn.:** po default-skrytí `[1]` sú sloty `hp.services.eyebrow/heading` redundantné (nadpis nesie `[2]`) —
  možno ich z blueprintu odstrániť.
- `path:[1]` **over resolverom** proti živej štruktúre (ako pri reviews/blog).

---

## Rozsah
- 3a buttony: ~4 link-sloty (HP+Služby) + 1 brief pole — malé.
- 3a global: 1 položka v `globals_blueprint.json` + krok vo Fáze 6 — malé.
- 3b: 1 hide-slot + 1 brief flag (+ voliteľná populácia portfólia) — malé až stredné.
- QA: +1 leftover vzor (`/produktova-stranka`).

Po implementácii spustiť `selftest.py` + `resolve_slots` proti živej štruktúre (validácia `path`), ako pri G1/G2.
