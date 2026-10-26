# -*- coding: utf-8 -*-
"""Probe GridManager funcs, vars, mats, FarmGround."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def main():
    unreal.log("=== probe_viz start ===")
    for p in [
        "/Game/Farm/Art/Mats/M_Grass",
        "/Game/Farm/Art/Mats/M_Tilled",
        "/Game/Farm/Art/Mats/M_Planted",
        "/Game/Farm/Art/Mats/M_Watered",
        "/Game/Farm/Art/Mats/M_Ready",
        "/Game/Farm/Art/T_Tilled",
        "/Game/Farm/Grid/BP_GridManager",
        "/Game/Farm/Grid/E_PlotState",
    ]:
        unreal.log("exist {} = {}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))

    bp = unreal.load_asset(MGR)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    unreal.log("graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))
    try:
        unreal.log("vars=" + str([str(v.var_name) for v in bel.get_variables(bp)]))
    except Exception as e:
        unreal.log("vars fail: " + str(e))
        try:
            for meth in dir(bel):
                if "var" in meth.lower() and not meth.startswith("_"):
                    unreal.log("bel." + meth)
        except Exception:
            pass

    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab in ("FarmGround", "BP_GridManager", "GridManager") or "Grid" in lab or "Farm" in lab:
            loc = a.get_actor_location()
            sc = a.get_actor_scale3d()
            unreal.log("actor {} class={} loc=({:.1f},{:.1f},{:.1f}) scale=({:.2f},{:.2f},{:.2f})".format(
                lab, a.get_class().get_name(), loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))

    # Dump TillCell success chain titles near DrawDebug
    for gname in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
        g = bel.find_graph(bp, gname)
        if not g:
            unreal.log("NO graph " + gname)
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        titles = []
        for n in ge.list_all_nodes():
            try:
                titles.append(bel.get_node_title(n))
            except Exception:
                titles.append(n.get_class().get_name())
        unreal.log(gname + " nodes=" + str(titles))

    unreal.log("=== probe_viz done ===")

if __name__ == "__main__":
    main()
