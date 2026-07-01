#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test: synteticky postaví strom KAŽDEJ pokrytej stránky podľa jej blueprintu
a overí reťazec resolve_slots -> build_ops -> (apply) -> qa_check, bez živého webu.
Pokryté: hp, about, services, contact, pricing."""
import os, sys, json, re, itertools
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import resolve_slots, build_ops, qa_check, plan_media, fill_globals

brief = json.load(open(os.path.join(ROOT, "references/brief.example.json"), encoding="utf-8"))

# stránka -> (blueprint, minimum textových operácií)
PAGES = {
    "hp": ("hp_slot_blueprint.json", 24),
    "about": ("about_slot_blueprint.json", 25),
    "services": ("services_slot_blueprint.json", 12),
    "contact": ("contact_slot_blueprint.json", 10),
    "pricing": ("pricing_slot_blueprint.json", 35),
    "gallery": ("gallery_slot_blueprint.json", 8),
}

ids = ("id%04d" % i for i in itertools.count())
STRUCT_TYPES = ("section", "container", "column")


def placeholder(widget, slot_id):
    if widget == "heading":
        if "card1" in slot_id: return {"title": "Služba 1"}
        if "card2" in slot_id: return {"title": "Služba 2"}
        if "card3" in slot_id: return {"title": "Služba 3"}
        return {"title": "Lorem ipsum nadpis"}
    if widget == "text-editor":
        return {"editor": "<p>Lorem ipsum dolor sit amet</p>"}
    if widget == "button":
        return {"text": "Chcem viac informácii"}
    if widget == "counter":
        return {"ending_number": 0, "suffix": "", "title": "<p>Lorem ipsum</p>"}
    if widget == "google_maps":
        return {"address": "Lorem ipsum adresa"}
    if widget == "xpro-icon-box":
        return {"title": "Lorem ipsum benefit"}
    if widget == "xpro-simple-gallery":
        return {"gallery": [{"filter": "Filter 1", "_id": "deadgal", "images": []}]}
    if widget == "nested-accordion":
        return {"items": [{"item_title": "Lorem ipsum?", "_id": "deadbe%d" % i} for i in range(4)]}
    return {}


def ensure(struct, path, widget, slot_id):
    nodes = struct
    node = None
    for d, idx in enumerate(path):
        while len(nodes) <= idx:
            nodes.append({"id": next(ids), "elType": "container", "elements": []})
        node = nodes[idx]
        if d == len(path) - 1:
            if widget in STRUCT_TYPES:
                node["elType"] = widget
            else:
                node["elType"] = "widget"
                node["widgetType"] = widget
                cur = node.setdefault("settings_summary", {})
                if not cur:
                    node["settings_summary"] = placeholder(widget, slot_id)
            node.setdefault("elements", [])
        else:
            node.setdefault("elements", [])
            nodes = node["elements"]
    return node


def flatten(nodes):
    for n in nodes:
        yield n
        yield from flatten(n.get("elements", []))


def slot_value(node, slot):
    s = node.get("settings_summary", {})
    if slot["setting"] in s:
        return str(s[slot["setting"]]).strip()
    return qa_check.text_of(node).strip()


total_ok = True
for page, (bp_file, min_ops) in PAGES.items():
    bp = json.load(open(os.path.join(ROOT, "references", bp_file), encoding="utf-8"))
    structure = []
    for slot in bp["slots"] + bp.get("image_slots", []):
        ensure(structure, slot["path"], slot["widget"], slot["slot_id"])

    # 1) resolve
    slotmap, warns = resolve_slots.resolve(structure, bp)
    assert all(v["ok"] for v in slotmap.values()), f"[{page}] resolve zlyhal: {warns}"
    assert len(slotmap) == len(bp["slots"]) + len(bp.get("image_slots", []))

    # 2) build_ops
    ops, skipped, opwarn = build_ops.build(brief, slotmap, bp)
    assert len(ops) >= min_ops, f"[{page}] čakal som >= {min_ops} operácií, mám {len(ops)}; skipped={skipped}"
    assert not opwarn, f"[{page}] neočakávané varovania: {opwarn}"
    bp_by_id = {s["slot_id"]: s for s in bp["slots"]}
    for sid, why in skipped:
        spec = bp_by_id.get(sid, {})
        assert spec.get("repeater") or spec.get("optional"), f"[{page}] neočakávaný skip povinného slotu: {sid} ({why})"

    # 3) qa PRED naplnením -> má vidieť placeholdery
    pre = [n["id"] for n in flatten(structure)
           if any(re.search(p, qa_check.text_of(n).lower()) for p in qa_check.PLACEHOLDERS)]
    assert pre, f"[{page}] QA mala pred naplnením nájsť placeholdery"

    # 4) apply ops (merge, nie replace — viac op môže mieriť na ten istý element)
    by_id = {n["id"]: n for n in flatten(structure)}
    for op in ops:
        by_id[op["element_id"]].setdefault("settings_summary", {}).update(op["settings"])

    # 5) qa PO naplnení — ignoruj skryté vetvy (hide_desktop)
    def visible(nodes):
        for n in nodes:
            if n.get("settings_summary", {}).get("hide_desktop") == "hidden":
                continue
            yield n
            yield from visible(n.get("elements", []))
    post = [n["id"] for n in visible(structure)
            if any(re.search(p, qa_check.text_of(n).lower()) for p in qa_check.PLACEHOLDERS)]
    assert not post, f"[{page}] QA po naplnení ešte vidí placeholdery: {post}"

    # 6) per-slot pravidlá
    for slot in bp["slots"]:
        if slot.get("repeater") or slot["widget"] in STRUCT_TYPES:
            continue
        n = resolve_slots.get_node(structure, slot["path"])
        val = slot_value(n, slot)
        if not val:
            assert slot.get("optional"), f"[{page}] povinný slot prázdny: {slot['slot_id']}"
            continue
        if slot.get("rule") == "must_be_number":
            assert val[:1].isdigit(), f"[{page}] {slot['slot_id']} nezačína číslom: {val}"
        if slot.get("rule") == "cta_max_21":
            assert len(re.sub(r"<[^>]+>", "", val)) <= 21, f"[{page}] {slot['slot_id']} CTA dlhé: {val}"

    n_img = len(bp.get("image_slots", []))
    print(f"OK [{page}] resolve {len(slotmap)} slotov ({len(bp['slots'])} text + {n_img} image), "
          f"{len(ops)} ops, {len(skipped)} skip, QA čistá")

# --- synteticky test: zovšeobecnené auto-skrytie sekcie (list-based prítomnosť) ---
def test_section_hide():
    # blueprint: sekcia sa skryje, ak je content.refs prázdny zoznam; child text sa vyčistí
    bp = {"slots": [
        {"slot_id": "x.refs.section", "path": [0], "widget": "section", "setting": "_row",
         "brief": "content.refs", "hide_if_missing": True, "optional": True},
        {"slot_id": "x.refs.title", "path": [0, 0], "widget": "heading", "setting": "title",
         "brief": "content.refs_title", "clear_if_missing": True, "optional": True},
    ]}
    slotmap = {
        "x.refs.section": {"element_id": "secA", "widget": "section", "ok": True, "setting": "_row", "brief": "content.refs"},
        "x.refs.title": {"element_id": "headA", "widget": "heading", "ok": True, "setting": "title", "brief": "content.refs_title"},
    }
    # a) prázdny zoznam refs -> hide sekcie + clear nadpisu
    ops, _, _ = build_ops.build({"content": {"refs": [], "refs_title": ""}}, slotmap, bp)
    by = {o["element_id"]: o["settings"] for o in ops}
    assert by.get("secA", {}).get("hide_desktop") == "hidden", "prázdny zoznam mal sekciu skryť"
    assert by.get("headA", {}).get("title") == "", "prázdny nadpis sa mal vyčistiť"
    # b) neprázdny zoznam refs -> sekcia ostáva (žiadny hide op)
    ops2, _, _ = build_ops.build({"content": {"refs": ["logo1", "logo2"], "refs_title": "Referencie"}}, slotmap, bp)
    by2 = {o["element_id"]: o["settings"] for o in ops2}
    assert "hide_desktop" not in by2.get("secA", {}), "neprázdny zoznam nemal sekciu skryť"
    print("OK [section-hide] list-based prítomnosť: prázdny -> skryť+clear, neprázdny -> ponechať")


test_section_hide()


# --- test: plánovač médií (dedup + osoby ≥50 % + client_only sa negeneruje) ---
def test_plan_media():
    for page in ("hp", "about", "services", "contact"):
        bp = json.load(open(os.path.join(ROOT, "references", page + "_slot_blueprint.json"), encoding="utf-8"))
        im = bp.get("image_slots", [])
        for source, cc in (("generated", 0), ("mix", 3), ("client", 2)):
            plan, rep = plan_media.build_plan(im, source, cc)
            errs = plan_media.validate(plan, rep, cc)
            assert not errs, f"[{page}/{source}] plan_media chyby: {errs}"
            idxs = [p["client_index"] for p in plan if p["mode"] == "client"]
            assert len(idxs) == len(set(idxs)), f"[{page}/{source}] dedup zlyhal: {idxs}"
            assert all(p["mode"] != "generate" for p in plan if p["source_policy"] == "client_only"), \
                f"[{page}/{source}] client_only sa generuje"
            if rep["filled"]:
                assert rep["person_ratio"] >= 0.5, f"[{page}/{source}] osoby < 50 %: {rep['person_ratio']}"
    print("OK [plan-media] dedup + osoby ≥50 % + client_only bez generovania (hp/about/services/contact)")


test_plan_media()


# --- test: fill_globals (agentúrne tokeny -> klient, žiadny zvyšok) ---
def test_fill_globals():
    tokens = json.load(open(os.path.join(ROOT, "references", "global_tokens.json"), encoding="utf-8"))
    src = ("Netova pomoc s. r. o., IČO: 54 630 649, DIČ: 2121741941, www.netovapomoc.sk, "
           "jan@netovapomoc.sk, +421 950 555 7777, info@fajne-weby.cz, Copyright Netovapomoc.sk")
    brief = {"content": {"legal": {
        "company_name": "Drevko s.r.o.", "company_short": "Drevko", "brand_label": "Drevko.sk",
        "address": "Hlavná 12, Žilina", "register": "OR Žilina, vložka 1/L",
        "ico": "12345678", "dic": "2020202020", "ic_dph": "SK2020202020",
        "domain": "www.drevko.sk", "email": "info@drevko.sk", "phone": "+421 911 222 333"}}}
    pairs, missing = fill_globals.resolve_pairs(brief, tokens)
    new, n = fill_globals.substitute(src, pairs)
    leftovers = fill_globals.find_leftovers(new, tokens["leftover_markers"])
    assert not leftovers, f"fill_globals: ostali agentúrne zvyšky {leftovers}"
    assert "netovapomoc" not in new.lower() and "fajne-weby" not in new.lower()
    assert "Drevko s.r.o." in new and "info@drevko.sk" in new and "12345678" in new
    print(f"OK [fill-globals] {n} tokenov nahradených, žiadny agentúrny zvyšok")


test_fill_globals()

print("\n✅ SELF-TEST PREŠIEL (stránky + section-hide + plan-media + fill-globals)")
