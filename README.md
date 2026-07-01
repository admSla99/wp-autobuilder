# wp-skills — Claude Code plugin marketplace

Marketplace pluginov pre **automatizáciu WordPress webov cez Elementor MCP**. Obsahuje dva
sesterské skilly balené ako pluginy:

| Plugin | Verzia | Účel |
|---|---|---|
| [`wp-autobuilder`](plugins/wp-autobuilder/skills/wp-autobuilder/) | 1.4.0 | **Staviteľ** — autonómne poskladá stránky webu (HP, O nás, Služby, Kontakt, Cenník, Galéria, produkty) z podkladov klienta na Google Drive: intake → farby → sloty → texty → médiá → QA → publish. |
| [`wp-fixer`](plugins/wp-fixer/skills/wp-fixer/) | 1.0.0 | **Opravár** — aplikuje cielené pripomienky na už postavený živý web: changeset → snapshot → úpravy → QA + diff gate → uloženie naživo / rollback. |

`wp-fixer` **vyžaduje nainštalovaný `wp-autobuilder`** — znovupoužíva jeho blueprinty a skripty
(`AB_DIR`, viď [architecture.md](plugins/wp-fixer/skills/wp-fixer/references/architecture.md)).

## Inštalácia

```bash
# 1. pridaj marketplace (GitHub repo alebo lokálna cesta)
claude plugin marketplace add admSla99/wp-autobuilder

# 2. nainštaluj pluginy (fixer potrebuje aj autobuilder)
claude plugin install wp-autobuilder@wp-skills
claude plugin install wp-fixer@wp-skills
```

## Použitie (nová session)

> „Použi **wp-autobuilder**. Podklady klienta sú v GDrive priečinku `test1`. Spusti celý proces."

> „Použi **wp-fixer**. Pripomienky sú v GDrive priečinku klienta `test1` (dokument `pripomienky`)."

Oba skilly bežia autonómne (bez doplňujúcich otázok) a potrebujú konektory: **Elementor MCP**
(inštancia klienta), **Google Drive MCP** (podklady/pripomienky) a **n8n built-in connector**
(generovanie médií, Image 2.0).

## Štruktúra repa

```
.claude-plugin/marketplace.json        ← manifest marketplace (wp-skills)
plugins/
  wp-autobuilder/
    .claude-plugin/plugin.json
    skills/wp-autobuilder/             ← SKILL.md + references/ + scripts/ (+ README, CHANGELOG)
  wp-fixer/
    .claude-plugin/plugin.json
    skills/wp-fixer/                   ← SKILL.md + references/ + scripts/
```

Detailná dokumentácia autobuilder pipeline (dátový tok, fázy, blueprinty, farby, médiá):
[plugins/wp-autobuilder/skills/wp-autobuilder/README.md](plugins/wp-autobuilder/skills/wp-autobuilder/README.md).

## Self-testy (bez živého webu)

```bash
python plugins/wp-autobuilder/skills/wp-autobuilder/scripts/selftest.py
python plugins/wp-autobuilder/skills/wp-autobuilder/scripts/palette_selftest.py
python plugins/wp-fixer/skills/wp-fixer/scripts/selftest.py
```
