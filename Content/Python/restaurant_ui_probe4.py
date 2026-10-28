# -*- coding: utf-8 -*-
"""Probe fonts, WBP construction APIs, SCS via editor property, Table customs."""
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[UI_P4] " + str(m))
    print("[UI_P4] " + str(m))

# Font assets
for fp in ("/Game/Farm/Restaurant/Font_SimHei", "/Game/Farm/Restaurant/Font_SimHei_Offline", "/Game/Farm/Restaurant/Font_SimHei_TR"):
    a = unreal.load_asset(fp)
    log("{} -> {} path={}".format(fp, a.get_class().get_name() if a else None, a.get_path_name() if a else None))

# Search for Font class assets
ar = unreal.AssetRegistryHelpers.get_asset_registry()
fonts = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Font"), True)
log("Font assets count=" + str(len(list(fonts or []))))
for f in list(fonts or [])[:30]:
    log("  Font " + str(f.package_name) + "/" + str(f.asset_name))

faces = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "FontFace"), True)
log("FontFace count=" + str(len(list(faces or []))))
for f in list(faces or [])[:20]:
    log("  Face " + str(f.package_name) + "/" + str(f.asset_name))

# WidgetBlueprint factory - create temp and inspect
tools = unreal.AssetToolsHelpers.get_asset_tools()
UI_DIR = "/Game/Farm/UI"
tmp_name = "WBP_RestOrderList_TMP"
tmp_path = UI_DIR + "/" + tmp_name
if unreal.EditorAssetLibrary.does_asset_exist(tmp_path):
    unreal.EditorAssetLibrary.delete_asset(tmp_path)
factory = unreal.WidgetBlueprintFactory()
# Parent class?
try:
    factory.set_editor_property("parent_class", unreal.UserWidget)
    log("set parent_class ok")
except Exception as e:
    log("parent_class " + str(e))
wbp = tools.create_asset(tmp_name, UI_DIR, unreal.WidgetBlueprint, factory)
log("created " + str(wbp))
if wbp:
    tree = unreal.load_object(wbp, "WidgetTree")
    log("tree=" + str(tree))
    # construct_widget?
    log("has construct=" + str(hasattr(tree, "construct_widget")))
    # try call_method
    for meth in ("ConstructWidget", "construct_widget", "FindWidget", "find_widget", "RemoveWidget", "GetAllWidgets"):
        try:
            r = tree.call_method(meth) if False else None
        except Exception:
            pass
        log("method check " + meth + " in dir? skip")
    # BlueprintEditorLibrary helpers for widgets?
    bl_methods = [x for x in dir(bel) if "widget" in x.lower() or "umg" in x.lower()]
    log("bel widget methods=" + str(bl_methods))
    umg_ed = [x for x in dir(unreal) if "Widget" in x and ("Editor" in x or "Blueprint" in x or "Tree" in x)]
    log("unreal Widget*=" + str(umg_ed[:40]))

# Table SCS via get_editor_property
bp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
for prop in ("SimpleConstructionScript", "simple_construction_script"):
    try:
        scs = bp.get_editor_property(prop)
        log("scs via {} = {}".format(prop, scs))
        if scs:
            nodes = scs.get_all_nodes()
            log("nodes=" + str(len(list(nodes or []))))
            for n in list(nodes or []):
                log("  " + str(n.get_variable_name()) + " " + str(n.component_template.get_class().get_name() if n.component_template else None))
    except Exception as e:
        log("scs {} {}".format(prop, e))

# customs
for path, label in (("/Game/Farm/Restaurant/BP_RestaurantTable", "Table"), ("/Game/Farm/Restaurant/BP_RestaurantManager", "Mgr")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    customs = [str(bel.get_node_title(n)) for n in ge.list_all_nodes() if n.get_class().get_name()=="K2Node_CustomEvent"]
    log(label + " customs=" + str(customs))

# Character FarmHUD create?
cbp = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(cbp, "EventGraph"))
for n in cge.list_all_nodes():
    t = str(bel.get_node_title(n))
    cls = n.get_class().get_name()
    if any(k in t or k in cls for k in ("Widget", "HUD", "Viewport", "Create", "Print")):
        log("Char: {} | {}".format(t, cls))

# Patience default
cdo = unreal.get_default_object(bp.generated_class()) if False else None
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tcdo = unreal.get_default_object(tbp.generated_class())
for v in ("PatienceLeft", "EatLeft", "OrderPrice", "TableId", "bOccupied", "bHasOrder"):
    try:
        log("Table default {}={}".format(v, tcdo.get_editor_property(v)))
    except Exception as e:
        log("Table default {} {}".format(v, e))

log("DONE4")
