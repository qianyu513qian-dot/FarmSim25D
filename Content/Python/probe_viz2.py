# -*- coding: utf-8 -*-
"""Probe vars, EventGraph, plane mesh path."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def main():
    unreal.log("=== probe_viz2 ===")
    bp = unreal.load_asset(MGR)
    try:
        names = bel.list_member_variable_names(bp)
        unreal.log("vars=" + str([str(n) for n in names]))
        for n in names:
            try:
                t = bel.get_member_variable_type(bp, str(n))
                unreal.log("  var {} type={}".format(n, t))
            except Exception as e:
                unreal.log("  var {} typefail={}".format(n, e))
    except Exception as e:
        unreal.log("list vars: " + str(e))

    eg = bel.find_event_graph(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    for n in ge.list_all_nodes():
        try:
            t = bel.get_node_title(n)
        except Exception:
            t = n.get_class().get_name()
        unreal.log("EG: " + str(t))

    # Engine plane
    for p in [
        "/Engine/BasicShapes/Plane",
        "/Engine/BasicShapes/Plane.Plane",
        "/Game/Farm/Art/Mats/M_Tilled",
    ]:
        unreal.log("asset {} exist={}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))
        a = unreal.load_asset(p)
        unreal.log("  load={}".format(a))

    # Check if BP_PlotVisual exists
    unreal.log("BP_PlotVisual exist=" + str(unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Art/BP_PlotVisual")))
    unreal.log("BP_PlotVisual2 exist=" + str(unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Grid/BP_PlotVisual")))

    # Dump TillCell DrawDebug then connections (for splice plan)
    g = bel.find_graph(bp, "TillCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    for n in ge.list_all_nodes():
        title = bel.get_node_title(n)
        if title not in ("DrawDebugBox", "Set Array Elem", "Return Node", "GridToWorld"):
            continue
        unreal.log("--- " + title + " ---")
        for p in bel.list_all_pins(n):
            cps = []
            try:
                for c in p.list_connected_pins():
                    cps.append("{}@{}".format(c.get_pin_name(), bel.get_node_title(c.get_owning_node())))
            except Exception:
                pass
            try:
                v = p.get_pin_value()
            except Exception:
                v = ""
            unreal.log("  {} {} val=[{}] -> {}".format(p.get_pin_direction(), p.get_pin_name(), v, cps))

    unreal.log("=== probe_viz2 done ===")

if __name__ == "__main__":
    main()
