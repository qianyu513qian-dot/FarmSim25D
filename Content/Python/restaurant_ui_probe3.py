# -*- coding: utf-8 -*-
"""Write probe results to Saved file; inspect WidgetTree attrs and Font."""
import unreal, json, os

bel = unreal.BlueprintEditorLibrary
out = []

def log(m):
    out.append(str(m))
    unreal.log("[UI_P3] " + str(m))
    print("[UI_P3] " + str(m))

# WidgetTree attrs
wbp = unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD")
tree = unreal.load_object(wbp, "WidgetTree")
log("tree dirs sample=" + str([x for x in dir(tree) if not x.startswith("_")]))
for attr in ("RootWidget", "root_widget", "AllWidgets", "all_widgets"):
    if hasattr(tree, attr):
        try:
            v = getattr(tree, attr)
            log("attr {}={}".format(attr, v))
        except Exception as e:
            log("attr {} err {}".format(attr, e))

# try get_editor_property with RootWidget
for prop in ("RootWidget", "AllWidgets"):
    try:
        log("gep {}={}".format(prop, tree.get_editor_property(prop)))
    except Exception as e:
        log("gep {} {}".format(prop, e))

# Font asset details
font = unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei")
log("Font class=" + font.get_class().get_name())
log("Font dirs=" + str([x for x in dir(font) if "face" in x.lower() or "font" in x.lower() or "slate" in x.lower()][:40]))

# Table SCS
bp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
scs = bp.simple_construction_script
nodes = list(scs.get_all_nodes() or [])
log("Table SCS count=" + str(len(nodes)))
for n in nodes:
    try:
        vn = n.get_variable_name()
        tmpl = n.component_template
        log("  {} -> {}".format(vn, tmpl.get_class().get_name() if tmpl else None))
    except Exception as e:
        log("  err " + str(e))

# Custom events on Table
g = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
customs = []
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent":
        customs.append(str(bel.get_node_title(n)))
log("Table custom events=" + str(customs))

# Manager custom events
mbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mg = bel.find_graph(mbp, "EventGraph")
mge = unreal.BlueprintGraphEditor.get_graph_editor(mg)
mc = []
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent":
        mc.append(str(bel.get_node_title(n)))
log("Manager customs=" + str(mc))

# Tick chain on Table - follow from Event Tick
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in str(bel.get_node_title(n)):
        tick = n
        break
log("Tick=" + str(bel.get_node_title(tick) if tick else None))

# Character: how FarmHUD created?
cbp = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cg = bel.find_graph(cbp, "EventGraph")
cge = unreal.BlueprintGraphEditor.get_graph_editor(cg)
for n in cge.list_all_nodes():
    t = str(bel.get_node_title(n))
    if "Widget" in t or "HUD" in t or "Viewport" in t or "Create" in t:
        log("Char node: " + t + " | " + n.get_class().get_name())

# Factory create test path check
log("AssetTools=" + str(unreal.AssetToolsHelpers.get_asset_tools()))

path = unreal.Paths.project_saved_dir() + "RestaurantUI_probe3.txt"
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
log("wrote " + path)
log("DONE3")
