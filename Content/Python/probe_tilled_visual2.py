# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
ENUM = "/Game/Farm/Grid/E_PlotState"


def main():
    unreal.log("=== probe2 start ===")
    e = unreal.EditorAssetLibrary.load_asset(ENUM)
    for a in dir(e):
        if "name" in a.lower() or "enum" in a.lower() or "entr" in a.lower():
            if not a.startswith("_"):
                unreal.log("enum." + a)
    try:
        unreal.log("display=" + str(e.get_editor_property("display_name_map")))
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        # UE5 UserDefinedEnum
        opts = unreal.UserDefinedEnumEditorUtils.get_enumerator_names_as_string(e) if hasattr(unreal, "UserDefinedEnumEditorUtils") else None
        unreal.log("opts " + str(opts))
    except Exception as ex:
        unreal.log_warning(str(ex))

    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    for a in dir(bel):
        if "var" in a.lower() or "member" in a.lower():
            unreal.log("bel." + a)

    # get variables via Blueprint
    try:
        vs = bp.get_editor_property("new_variables")
        unreal.log("new_variables count " + str(len(vs)))
        for v in vs:
            unreal.log("  var " + str(v.var_name) + " type=" + str(v.var_type))
    except Exception as ex:
        unreal.log_warning("new_variables: " + str(ex))

    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    unreal.log("mgr EG nodes:")
    if ge:
        for n in ge.list_all_nodes():
            unreal.log("  " + bel.get_node_title(n))

    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    # Find DrawDebug in tick chain
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Debug" in t or "Print" in t or "WorldToGrid" in t or "GridToWorld" in t or "Tick" in t:
            unreal.log("char: " + t)
            if "Debug" in t:
                for p in bel.list_all_pins(n):
                    unreal.log("  {} | {}".format(p.get_pin_name(), p.get_pin_direction()))

    # Test DrawDebugBox pins
    n = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    unreal.log("DrawDebugBox pins:")
    for p in bel.list_all_pins(n):
        unreal.log("  " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))
    cge.remove_nodes([n])

    n = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSolidBox")
    if n:
        unreal.log("DrawDebugSolidBox pins:")
        for p in bel.list_all_pins(n):
            unreal.log("  " + str(p.get_pin_name()))
        cge.remove_nodes([n])

    # Equal enum compare - how TillCell does Equal (Byte)
    unreal.log("=== probe2 done ===")


if __name__ == "__main__":
    main()