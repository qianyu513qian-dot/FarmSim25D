# -*- coding: utf-8 -*-
"""Probe E_PlotState + TillCell graph for planting phase."""
import unreal

bel = unreal.BlueprintEditorLibrary
ENUM = "/Game/Farm/Grid/E_PlotState"
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def main():
    unreal.log("=== phase3_probe start ===")

    # Enum
    en = unreal.EditorAssetLibrary.load_asset(ENUM)
    unreal.log("enum asset=" + str(en))
    try:
        # UserDefinedEnum
        names = en.get_editor_property("display_name_map")
        unreal.log("display_name_map=" + str(names))
    except Exception as ex:
        unreal.log_warning("display_name_map: " + str(ex))
    for meth in ("get_names", "get_enumerator_names", "get_enums"):
        if hasattr(en, meth):
            try:
                unreal.log(meth + "=" + str(getattr(en, meth)()))
            except Exception as ex:
                unreal.log_warning(meth + ": " + str(ex))
    # Try UserDefinedEnum APIs
    try:
        ude = unreal.UserDefinedEnum.cast(en) if hasattr(unreal.UserDefinedEnum, "cast") else en
        unreal.log("ude=" + str(ude))
        for attr in dir(ude):
            if "enum" in attr.lower() or "name" in attr.lower() or "display" in attr.lower():
                if not attr.startswith("_"):
                    unreal.log("  ude." + attr)
    except Exception as ex:
        unreal.log_warning(str(ex))
    # Generated enum class
    try:
        gen = unreal.load_object(None, "/Game/Farm/Grid/E_PlotState.E_PlotState")
        unreal.log("gen=" + str(gen))
        if gen:
            for i in range(8):
                try:
                    n = unreal.Enum.get_name_by_value(gen, i) if hasattr(unreal, "Enum") else None
                    unreal.log("val{} name={}".format(i, n))
                except Exception as ex:
                    unreal.log_warning("val{}: {}".format(i, ex))
            # alternate
            try:
                for i in range(8):
                    n = gen.get_name_by_value(i)
                    unreal.log("gen.get_name_by_value({})={}".format(i, n))
            except Exception as ex:
                unreal.log_warning("get_name_by_value: " + str(ex))
            try:
                mx = gen.get_max_enum_value()
                unreal.log("max=" + str(mx))
            except Exception as ex:
                unreal.log_warning("max: " + str(ex))
    except Exception as ex:
        unreal.log_warning("gen load: " + str(ex))

    # GridManager graphs/funcs/vars
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    unreal.log("vars=" + str([str(x) for x in bel.list_member_variable_names(bp)]))

    # TillCell dump
    g = bel.find_graph(bp, "TillCell")
    if g:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        unreal.log("TillCell nodes:")
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            unreal.log("  NODE: " + t)
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = ""
                cps = list(p.list_connected_pins())
                unreal.log("    pin {} dir={} val=[{}] conn={}".format(
                    p.get_pin_name(), p.get_pin_direction(), v, len(cps)))

    # Character: IA nodes
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_" in t or t in ("TillCell", "PlantCell", "WorldToGrid"):
            unreal.log("CHAR NODE: " + t)

    # Input actions present
    for path in (
        "/Game/TopDown/Input/Actions/IA_Interact",
        "/Game/TopDown/Input/Actions/IA_Plant",
        "/Game/TopDown/Input/IMC_Default",
    ):
        unreal.log("exists {}: {}".format(path, unreal.EditorAssetLibrary.does_asset_exist(path)))

    unreal.log("=== phase3_probe done ===")


if __name__ == "__main__":
    main()
