# -*- coding: utf-8 -*-
"""Deep probe: GrowCell Set Item / Equal / enum; WaterCell; VisualizeCell state pin."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[P2] " + str(m)); print("[P2] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

bp = unreal.load_asset(MGR)

# Enum values
e = unreal.load_asset("/Game/Farm/Grid/E_PlotState")
if e:
    try:
        names = e.get_editor_property("display_name_map")
        log("enum display_name_map=" + str(names))
    except Exception as ex:
        log("enum map err " + str(ex))
    try:
        # UE5 UserDefinedEnum
        for attr in ("names", "Entries", "Enums", "enum_display_name_map"):
            if hasattr(e, attr):
                log("enum.{}={}".format(attr, getattr(e, attr)))
    except Exception as ex:
        log(str(ex))
    # Try get_names via reflection
    try:
        data = unreal.EditorAssetLibrary.find_asset_data("/Game/Farm/Grid/E_PlotState")
        log("asset_data=" + str(data))
    except Exception as ex:
        log(str(ex))

# Dump ALL pins on Equal and Set Array Elem and VisualizeCell in GrowCell
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = title(n)
    if t in ("Equal (Byte)", "Equal (Byte)", "EqualEqual_ByteByte") or "Equal" in t.lower() or "Set Array" in t or "Visualize" in t or "Return" in t:
        log("--- " + t + " ---")
        for p in bel.list_all_pins(n):
            try: v = p.get_pin_value()
            except: v = "?"
            # also pin type
            try:
                pt = p.get_pin_type()
                cat = str(pt.pin_category) if pt else "?"
                sub = str(pt.pin_sub_category_object) if pt else "?"
            except Exception as ex:
                cat, sub = "?", str(ex)
            cps = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  {} [{}] val={!r} type={}/{} -> {}".format(p.get_pin_name(), p.get_pin_direction(), v, cat, sub, cps))

# Also check WaterCell Equal B
graphs = [str(g) for g in bel.list_graph_names(bp)]
log("graphs=" + str(graphs))
for fname in ("WaterCell", "PlantCell", "TillCell"):
    if fname not in graphs:
        continue
    ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    for n in ge2.list_all_nodes():
        t = title(n)
        if "Equal" in t.lower() or "Set Array" in t:
            for p in bel.list_all_pins(n):
                try: v = p.get_pin_value()
                except: v = "?"
                if str(p.get_pin_name()) in ("A", "B", "Item", "ReturnValue"):
                    log("{} {}.{}={!r}".format(fname, t, p.get_pin_name(), v))

# Check Tick / day wrap calling AdvanceDayGrowth
ge3 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for n in ge3.list_all_nodes():
    t = title(n)
    if "Advance" in t or "Grow" in t or "Day" in t or "TimeOfDay" in t:
        log("EG: " + t)
        for p in bel.list_all_pins(n):
            cps = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if cps and str(p.get_pin_name()).lower() in ("execute","then","else","loopbody","completed","condition"):
                log("  {}.{} -> {}".format(t, p.get_pin_name(), cps))
