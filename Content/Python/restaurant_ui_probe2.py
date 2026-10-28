# -*- coding: utf-8 -*-
"""Deep probe: Table/Manager EventGraph highlights + FarmHUD tree + SCS components."""
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[UI_PROBE2] " + str(m))
    print("[UI_PROBE2] " + str(m))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def dump_graph(bp_path, gname, limit=80):
    bp = unreal.load_asset(bp_path)
    g = bel.find_graph(bp, gname)
    if not g:
        log("{} missing {}".format(bp_path, gname)); return
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    nodes = list(ge.list_all_nodes())
    log("=== {} {} count={} ===".format(bp_path.split("/")[-1], gname, len(nodes)))
    # categorize interesting
    keys = ("Print", "Patience", "Order", "Eat", "Branch", "Set", "Get", "Timer", "Create", "Widget", "Add to", "Receive", "Custom", "Cast", "ForEach", "Guest", "Spawn", "Serve", "Cook", "Timeout", "Money", "PAY", "Tick")
    for n in nodes:
        t = title(n)
        cls = n.get_class().get_name()
        interesting = any(k.lower() in t.lower() or k.lower() in cls.lower() for k in keys)
        if interesting or True:
            # only print first limit interesting-ish
            pass
    # print all titles condensed
    titles = [title(n) + "|" + n.get_class().get_name() for n in nodes]
    for i, t in enumerate(titles[:limit]):
        log("  [{}] {}".format(i, t))
    if len(titles) > limit:
        log("  ... +{} more".format(len(titles)-limit))

# FarmHUD
wbp = unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD")
log("WBP class=" + wbp.get_class().get_name())
tree = unreal.load_object(wbp, "WidgetTree")
log("tree=" + str(tree))
try:
    root = tree.get_editor_property("root_widget")
    log("root=" + str(root) + (" name="+root.get_name() if root else ""))
except Exception as e:
    log("root " + str(e))
try:
    allw = list(tree.get_editor_property("all_widgets") or [])
    log("all_widgets count=" + str(len(allw)))
    for w in allw:
        log("  w={} {}".format(w.get_name(), w.get_class().get_name()))
except Exception as e:
    log("allw " + str(e))

# Character UpdateFarmHUD
dump_graph("/Game/TopDown/Blueprints/BP_TopDownCharacter", "UpdateFarmHUD", 40)

# Table EventGraph - look for patience/order
dump_graph("/Game/Farm/Restaurant/BP_RestaurantTable", "EventGraph", 100)

# Manager - look for guest/order
dump_graph("/Game/Farm/Restaurant/BP_RestaurantManager", "EventGraph", 100)

# SCS components on Table
bp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
try:
    scs = bp.simple_construction_script
    log("SCS=" + str(scs))
    nodes = scs.get_all_nodes() if scs else []
    log("SCS nodes=" + str(len(list(nodes or []))))
    for n in (nodes or []):
        try:
            log("  scs {} tmpl={}".format(n.get_variable_name(), n.component_template.get_class().get_name() if n.component_template else None))
        except Exception as e:
            log("  scs err " + str(e))
except Exception as e:
    log("scs " + str(e))

# Font type
for fp in ("/Game/Farm/Restaurant/Font_SimHei", "/Game/Farm/Restaurant/Font_SimHei_Offline"):
    a = unreal.load_asset(fp)
    log("font {} class={}".format(fp, a.get_class().get_name() if a else None))

# WidgetComponent available?
log("WidgetComponent=" + str(getattr(unreal, "WidgetComponent", None)))
log("DONE2")
