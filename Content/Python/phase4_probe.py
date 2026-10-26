# -*- coding: utf-8 -*-
"""Probe for phase4 watering."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"


def main():
    unreal.log("=== phase4_probe start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    unreal.log("graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))

    for fname in ("TillCell", "PlantCell", "WaterCell"):
        g = bel.find_graph(bp, fname)
        if not g:
            unreal.log(fname + " MISSING")
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        unreal.log("--- " + fname)
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if "equal" in t.lower():
                for p in bel.list_all_pins(n):
                    if str(p.get_pin_name()) == "B":
                        unreal.log("  Equal.B=" + str(p.get_pin_value()))
            if "Set Array" in t:
                for p in bel.list_all_pins(n):
                    if str(p.get_pin_name()) == "Item":
                        unreal.log("  Set.Item=" + str(p.get_pin_value()))
            if "DrawDebug" in t:
                for p in bel.list_all_pins(n):
                    if "Color" in str(p.get_pin_name()) or "Duration" in str(p.get_pin_name()):
                        unreal.log("  dbg {}={}".format(p.get_pin_name(), p.get_pin_value()))

    # IMC keys
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("IMC=" + txt)
    for path in (
        "/Game/TopDown/Input/Actions/IA_Interact",
        "/Game/TopDown/Input/Actions/IA_Plant",
        "/Game/TopDown/Input/Actions/IA_Water",
    ):
        unreal.log("exists {}={}".format(path, unreal.EditorAssetLibrary.does_asset_exist(path)))

    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_" in t or t in ("TillCell", "PlantCell", "WaterCell"):
            unreal.log("CHAR " + t)

    # Enum asset size/strings
    en = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
    unreal.log("enum=" + str(en))
    unreal.log("=== phase4_probe done ===")


if __name__ == "__main__":
    main()
