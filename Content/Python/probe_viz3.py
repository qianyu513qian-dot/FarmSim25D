# -*- coding: utf-8 -*-
"""Probe PlotVisual + GridManager viz readiness."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"

def log(m):
    unreal.log("[PROBE_VIZ3] " + str(m))

def main():
    log("=== start ===")
    for p in [
        PV, MGR,
        "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
        "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
        "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Untilled",
        "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling",
        "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing",
        "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature",
    ]:
        log("exist {} = {}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))

    # PlotVisual
    bp = unreal.load_asset(PV)
    log("PV funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    log("PV graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))
    try:
        log("PV vars=" + str([str(x) for x in bel.list_member_variable_names(bp)]))
    except Exception as e:
        log("PV vars: " + str(e))

    # SCS components
    try:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        log("PV subobjects=" + str(len(handles)))
        for h in handles:
            data = sub.k2_find_subobject_data_from_handle(h)
            try:
                vname = str(lib.get_variable_name(data) or "")
                obj = lib.get_object(data)
                cls = obj.get_class().get_name() if obj else "?"
                extra = ""
                if obj and "StaticMesh" in cls:
                    try:
                        sm = obj.get_editor_property("static_mesh")
                        extra = " mesh=" + str(sm)
                    except Exception:
                        pass
                log("  sub {} class={}{}".format(vname, cls, extra))
            except Exception as e:
                log("  sub err " + str(e))
    except Exception as e:
        log("sub fail: " + str(e))

    # Dump ApplyState if any
    for gname in bel.list_graph_names(bp):
        g = bel.find_graph(bp, str(gname))
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        titles = []
        for n in ge.list_all_nodes():
            try:
                titles.append(bel.get_node_title(n))
            except Exception:
                titles.append(n.get_class().get_name())
        log("PV graph {} nodes={}".format(gname, titles))

    # GridManager
    gbp = unreal.load_asset(MGR)
    log("MGR funcs=" + str([str(f.name) for f in bel.list_functions(gbp)]))
    log("MGR graphs=" + str([str(n) for n in bel.list_graph_names(gbp)]))
    try:
        log("MGR vars=" + str([str(x) for x in bel.list_member_variable_names(gbp)]))
    except Exception as e:
        log("MGR vars: " + str(e))

    for gname in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell", "VisualizeCell", "GridToWorld"):
        g = bel.find_graph(gbp, gname)
        if not g:
            log("NO " + gname)
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        titles = []
        for n in ge.list_all_nodes():
            try:
                titles.append(bel.get_node_title(n))
            except Exception:
                titles.append(n.get_class().get_name())
        log("{} nodes={}".format(gname, titles))

    # Sample soil mesh bounds / scale from scene
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    nsoil = 0
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("Soil_") and nsoil < 3:
            loc = a.get_actor_location()
            sc = a.get_actor_scale3d()
            log("scene {} loc=({:.1f},{:.1f},{:.1f}) scale=({:.4f},{:.4f},{:.4f})".format(
                lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))
            nsoil += 1
        if lab.startswith("Crop_") or "Tomato" in lab or "Seedling" in lab:
            if nsoil <= 5:
                loc = a.get_actor_location()
                sc = a.get_actor_scale3d()
                log("scene crop {} loc=({:.1f},{:.1f},{:.1f}) scale=({:.4f},{:.4f},{:.4f})".format(
                    lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))

    log("=== done ===")

if __name__ == "__main__":
    main()
