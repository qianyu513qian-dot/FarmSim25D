# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
for fname in ("TillCell", "PlantCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    unreal.log("== " + fname)
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "equal" in t.lower() or "==" in t:
            unreal.log("NODE " + t)
            for p in bel.list_all_pins(n):
                unreal.log("  {} = [{}]".format(p.get_pin_name(), p.get_pin_value()))
        if "Set Array" in t:
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "Item":
                    unreal.log("Set.Item=[{}]".format(p.get_pin_value()))
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
for n in cge.list_all_nodes():
    if bel.get_node_title(n) == "Print String":
        for p in bel.list_all_pins(n):
            if "string" in str(p.get_pin_name()).lower():
                try:
                    unreal.log("PRINT={!r}".format(p.get_pin_value()))
                except Exception as ex:
                    unreal.log_warning(str(ex))
