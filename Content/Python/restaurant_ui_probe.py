# -*- coding: utf-8 -*-
"""Probe restaurant Manager/Table vars and FarmHUD for order UI."""
import unreal

bel = unreal.BlueprintEditorLibrary
paths = [
    "/Game/Farm/Restaurant/BP_RestaurantManager",
    "/Game/Farm/Restaurant/BP_RestaurantTable",
    "/Game/Farm/Restaurant/BP_RestaurantStove",
    "/Game/Farm/UI/WBP_FarmHUD",
    "/Game/TopDown/Blueprints/BP_TopDownCharacter",
]

def log(m):
    unreal.log("[UI_PROBE] " + str(m))
    print("[UI_PROBE] " + str(m))

for p in paths:
    exists = unreal.EditorAssetLibrary.does_asset_exist(p)
    log("=== {} exists={} ===".format(p, exists))
    if not exists:
        continue
    asset = unreal.load_asset(p)
    log("class=" + asset.get_class().get_name())
    if "Blueprint" in asset.get_class().get_name() and "Widget" not in asset.get_class().get_name():
        try:
            names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(asset)]
            log("vars=" + ", ".join(names))
        except Exception as e:
            log("vars err " + str(e))
        try:
            graphs = bel.list_graphs(asset) if hasattr(bel, "list_graphs") else []
            log("graphs via list_graphs=" + str(graphs))
        except Exception as e:
            log("list_graphs " + str(e))
        # try common graph names
        for gname in ("EventGraph", "UpdateFarmHUD", "HandlePlayerE", "RefreshOrders", "Tick"):
            try:
                g = bel.find_graph(asset, gname)
                if g:
                    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
                    nodes = list(ge.list_all_nodes())
                    log("graph {} nodes={}".format(gname, len(nodes)))
            except Exception as e:
                pass
    if "WidgetBlueprint" in asset.get_class().get_name() or p.endswith("WBP_FarmHUD"):
        try:
            tree = unreal.load_object(asset, "WidgetTree")
            log("tree=" + str(tree))
            try:
                root = tree.get_editor_property("root_widget")
                log("root=" + str(root))
            except Exception as e:
                log("root err " + str(e))
            try:
                allw = tree.get_editor_property("all_widgets")
                log("widgets=" + str([(w.get_name(), w.get_class().get_name()) for w in (allw or [])]))
            except Exception as e:
                log("all_widgets " + str(e))
        except Exception as e:
            log("wbp " + str(e))

# Font assets
for fp in ("/Game/Farm/Restaurant/Font_SimHei", "/Game/Farm/Restaurant/Font_SimHei_Offline", "/Game/Farm/Restaurant/Font_SimHei_TR"):
    log("font {} exist={}".format(fp, unreal.EditorAssetLibrary.does_asset_exist(fp)))

# Check WidgetBlueprint factory availability
log("WidgetBlueprint=" + str(getattr(unreal, "WidgetBlueprint", None)))
log("WidgetBlueprintFactory=" + str(getattr(unreal, "WidgetBlueprintFactory", None)))
log("DONE")
