#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py — synteticky overi retazec opravara BEZ ziveho webu:
  validate_changeset -> plan_changes -> diff_structure (brana) -> qa_fix_check.
Pouziva references/changeset.example.json + male in-memory fixtury struktury.
Navratovy kod 0 = vsetko OK, 1 = nejaky test zlyhal.
"""
import os, sys, json

try:  # Windows konzola (cp1252) inak padne na emoji vo vypise
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REF = os.path.join(HERE, "..", "references")

import validate_changeset as V
import plan_changes as P
import diff_structure as D
import qa_fix_check as Q

fails = []


def check(cond, msg):
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        fails.append(msg)


def main():
    cs = json.load(open(os.path.join(REF, "changeset.example.json"), encoding="utf-8"))

    print("== validate_changeset ==")
    enums = V.load_enums(os.path.join(REF, "changeset.schema.json"))
    errors, warns = V.validate(cs, enums)
    check(errors == [], f"changeset.example nema strukturalne chyby (mal {len(errors)})")

    # zla verzia: duplicitne id + neznamy type -> musi zlyhat
    bad = {"changes": [
        {"id": "x", "raw": "a", "type": "text", "scope": "page"},
        {"id": "x", "raw": "b", "type": "vymysleny", "scope": "page"},
    ]}
    berr, _ = V.validate(bad, enums)
    check(any("duplicitne" in e for e in berr), "zachytene duplicitne id")
    check(any("nie je platne" in e for e in berr), "zachyteny neplatny type")

    print("== plan_changes ==")
    plan = P.build_plan(cs)
    check("c3" in plan["kit"], "farby (c3) -> kit")
    check("c9" in plan["global"], "globalne prvky (c9) -> global")
    check("c8" in plan["media"] and "c10" in plan["media"], "obrazky (c8,c10) -> media davka")
    check("c4" in plan["media"], "mixed s obrazkovym pod-ukolom (c4) -> media davka")
    check("c1" not in plan["media"], "textova zmena (c1) nie je v media")
    check("c8" in plan["instance_rules"], "instance pravidlo (c8 dedup) -> instance_rules")
    check("c8" in plan["order"], "instance pravidlo (c8) JE v plan.order (Faza 4 ho nevynecha)")
    check(plan["order"][-1] in plan["kit"] + plan["global"], "kit/global su v poradi na konci")
    # konflikt: dve zmeny na ten isty slot na tej istej stranke (synteticky, nezavisi na example)
    conflict_cs = {"changes": [
        {"id": "k1", "raw": "x", "type": "text", "scope": "page", "page_type": "hp",
         "target_selector": {"slot_id": "hp.hero.h1"}},
        {"id": "k2", "raw": "y", "type": "text", "scope": "page", "page_type": "hp",
         "target_selector": {"slot_id": "hp.hero.h1"}},
    ]}
    check(len(P.build_plan(conflict_cs)["conflicts"]) >= 1,
          "konflikt: dve zmeny na ten isty slot/stranku zachytene")
    check(bool(plan["client_inputs_needed"]), "chybajuce klientske vstupy zozbierane")
    # regresia: zmena bez 'id' nesmie zhodit build_plan (KeyError None)
    try:
        P.build_plan({"changes": [{"raw": "x", "type": "text", "scope": "page", "page_type": "hp"}]})
        check(True, "build_plan zvladne zmenu bez id (ziadny KeyError)")
    except Exception as e:
        check(False, f"build_plan padol na zmene bez id: {e}")

    print("== diff_structure (brana) ==")
    before = [
        {"id": "A", "elType": "widget", "widgetType": "heading",
         "settings_summary": {"title": "Stary nadpis"}},
        {"id": "B", "elType": "widget", "widgetType": "text-editor",
         "settings_summary": {"editor": "<p>nezmeneny</p>"}},
    ]
    after_clean = [
        {"id": "A", "elType": "widget", "widgetType": "heading",
         "settings_summary": {"title": "Novy nadpis so SEO"}},
        {"id": "B", "elType": "widget", "widgetType": "text-editor",
         "settings_summary": {"editor": "<p>nezmeneny</p>"}},
    ]
    added, removed, changed, _, _ = D.diff(before, after_clean)
    check(changed == ["A"] and not added and not removed, "cista zmena: zmenene len A")

    after_collateral = [
        {"id": "A", "elType": "widget", "widgetType": "heading",
         "settings_summary": {"title": "Novy nadpis so SEO"}},
        {"id": "B", "elType": "widget", "widgetType": "text-editor",
         "settings_summary": {"editor": "<p>NECHCENA zmena</p>"}},
    ]
    _, _, changed2, _, _ = D.diff(before, after_collateral)
    coll, _ = D.gate(changed2, [], [], {"A"}, set(), set())
    check(coll == ["B"], "kolateral: zmena B mimo povolenych zachytena")
    # regresia: prazdny allowed + zmeny => FAIL-CLOSED (vsetko kolateral)
    coll_fc, _ = D.gate(["A", "B"], [], [], set(), set(), set())
    check(set(coll_fc) == {"A", "B"}, "diff FAIL-CLOSED pri prazdnom --allowed (nie fail-open)")
    check(D.gate(["A"], [], [], set(), set(), set(), allow_empty=True)[0] == [],
          "--allow-empty je vyslovny opt-out z fail-closed")
    # regresia: strukturalna zmena mimo whitelistu = problem; v ramci whitelistu = OK
    _, sp_bad = D.gate([], ["NEW"], [], {"A"}, set(), set())
    check(len(sp_bad) == 1, "neocakavany pridany prvok zachyteny (bez allow-structural)")
    _, sp_ok = D.gate([], ["NEW"], [], {"A"}, {"NEW"}, set())
    check(sp_ok == [], "ocakavany pridany prvok (--allow-added) prejde")

    print("== qa_fix_check ==")
    struct_ok = [
        {"id": "A", "elType": "widget", "widgetType": "heading",
         "settings_summary": {"title": "Novy nadpis so SEO"}},
        {"id": "C", "elType": "widget", "widgetType": "button",
         "settings_summary": {"text": "Chcem ponuku"}},
    ]
    e1, w1, v1 = Q.run_checks(struct_ok)
    check(e1 == [], "cista struktura: ziadne QA chyby")

    struct_ph = [{"id": "A", "elType": "widget", "widgetType": "text-editor",
                  "settings_summary": {"editor": "Lorem ipsum dolor"}}]
    e2, _, _ = Q.run_checks(struct_ph)
    check(len(e2) >= 1, "placeholder Lorem ipsum zachyteny ako chyba")

    struct_cta = [{"id": "C", "elType": "widget", "widgetType": "button",
                   "settings_summary": {"text": "Kliknite sem pre velmi dlhu vyzvu na akciu"}}]
    _, w3, _ = Q.run_checks(struct_cta)
    check(any("21" in w for w in w3), "prilis dlhe CTA (>21) zachytene ako varovanie")

    mini_cs = {"changes": [{"id": "t1", "raw": "x", "type": "text", "scope": "page",
                            "page_type": "hp", "desired": {"value": "Novy nadpis so SEO"}}]}
    _, _, v4 = Q.run_checks(struct_ok, mini_cs, "hp")
    check(any("t1" in v for v in v4), "desired hodnota najdena na stranke (page-level)")

    # regresia: token-based parovanie stranky — 'champhp' URL sa NESMIE zhodovat s page_type 'hp'
    leak_cs = {"changes": [{"id": "L1", "raw": "x", "type": "text", "scope": "page",
                            "page_type": "hp", "desired": {"value": "Novy nadpis so SEO"}}]}
    _, _, v_leak = Q.run_checks(struct_ok, leak_cs, "https://x.sk/champhp/")
    check(v_leak == [], "ziadny cross-page leak: 'champhp' URL != page_type 'hp'")
    _, _, v_hit = Q.run_checks(struct_ok, leak_cs, "hp")
    check(any("L1" in v for v in v_hit), "spravna zhoda: page_type 'hp' == '--page hp'")

    # regresia: agenturny/zakazany odkaz v url kluci sa zachyti (text_of ho preskakuje)
    struct_link = [{"id": "B", "elType": "widget", "widgetType": "button",
                    "settings_summary": {"text": "Chcem viac", "link_url": "/produktova-stranka/"}}]
    _, w_link, _ = Q.run_checks(struct_link)
    check(any("produktova-stranka" in w for w in w_link), "zakazany CTA ciel /produktova-stranka/ zachyteny")

    print("\n" + ("=" * 40))
    if fails:
        print(f"❌ SELFTEST FAILED: {len(fails)} testov zlyhalo")
        for f in fails:
            print("   -", f)
        sys.exit(1)
    print("✅ SELFTEST OK — vsetky kontroly presli.")
    sys.exit(0)


if __name__ == "__main__":
    main()
