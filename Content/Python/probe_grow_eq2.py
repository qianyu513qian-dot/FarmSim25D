# -*- coding: utf-8 -*-
"""Probe Equal pins in Plant/Water/Till/Harvest and enum names."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[P3] " + str(m)); print("[P3] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

bp = unreal.load_asset(MGR)

# Enum names via C++ style
e = unreal.load_asset("/Game/Farm/Grid/E_PlotState")
try:
    # UserDefinedEnum has GetDisplayNameTextByIndex or similar through Enum
    for i in range(0, 16):
        try:
            # try unreal.Enum
            name = unreal.Enum.get_display_name_text_by_value(e, i) if hasattr(unreal.Enum, "get_display_name_text_by_value") else None
        except: name = None
        try:
            n2 = e.get_name_string_by_value(i) if hasattr(e, "get_name_string_by_value") else None
        except: n2 = None
        try:
            n3 = e.get_name_by_value(i) if hasattr(e, "get_name_by_value") else None
        except: n3 = None
        if name or n2 or n3:
            log("enum[{}] name={} n2={} n3={}".format(i, name, n2, n3))
except Exception as ex:
    log("enum loop " + str(ex))

# dump methods
log("enum methods: " + str([m for m in dir(e) if not m.startswith("_") and ("name" in m.lower() or "enum" in m.lower() or "value" in m.lower() or "index" in m.lower())]))

for fname in ("PlantCell", "WaterCell", "TillCell", "HarvestCell", "GrowCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    log("==== " + fname + " ====")
    for n in ge.list_all_nodes():
        t = title(n)
        if "Equal" in t.lower() or "Set Array" in t or "Branch" in t:
            for p in bel.list_all_pins(n):
                try: v = p.get_pin_value()
                except: v = "?"
                cps = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
                pn = str(p.get_pin_name())
                if pn in ("A","B","Item","Condition","then","else","execute","ReturnValue") or cps:
                    log("  {}.{}={!r} -> {}".format(t, pn, v, cps))
