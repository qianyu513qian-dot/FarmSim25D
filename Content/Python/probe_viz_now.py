# -*- coding: utf-8 -*-
"""Probe why PlotVisual meshes not visible after Till/Plant/etc."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"

MESHES = [
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
    "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling",
    "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing",
    "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature",
]


def log(m):
    unreal.log("[PROBE_VIZ] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


log("=== MESH ASSETS ===")
for mp in MESHES:
    a = unreal.load_asset(mp)
    log("mesh {} -> {}".format(mp, "OK" if a else "MISSING"))
    if a:
        try:
            bounds = a.get_bounds()
            log("  bounds box={} sphere_r={}".format(bounds.box_extent, bounds.sphere_radius))
        except Exception as e:
            log("  bounds err: " + str(e))

log("=== BP_PlotVisual comps ===")
bp = unreal.load_asset(PV)
if not bp:
    unreal.log_error("NO BP_PlotVisual")
else:
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            vname = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            cls = obj.get_class().get_name() if obj else "?"
            log("sub {} class={}".format(vname, cls))
            if obj and "StaticMesh" in cls:
                sm = obj.get_editor_property("static_mesh")
                rel = obj.get_editor_property("relative_location")
                sc = obj.get_editor_property("relative_scale3d")
                vis = None
                try:
                    vis = obj.get_editor_property("b_visible")
                except Exception:
                    try:
                        vis = obj.get_editor_property("visible")
                    except Exception:
                        pass
                hid = None
                try:
                    hid = obj.get_editor_property("b_hidden_in_game")
                except Exception:
                    pass
                log("  SMC mesh={} rel=({},{},{}) scale=({},{},{}) vis={} hidInGame={}".format(
                    sm.get_path_name() if sm else None,
                    rel.x, rel.y, rel.z, sc.x, sc.y, sc.z, vis, hid))
        except Exception as e:
            log("sub err: " + str(e))

    # ApplyState graph
    g = bel.find_graph(bp, "ApplyState")
    if not g:
        log("NO ApplyState graph!")
    else:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        try:
            errs = ge.list_nodes_with_errors()
            log("ApplyState errors=" + str(len(errs)))
            for n in errs:
                log("  ERR " + bel.get_node_title(n))
        except Exception as e:
            log("ApplyState err list: " + str(e))
        # Dump SetStaticMesh NewMesh pins
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if "SetStaticMesh" in t or "Set Hidden" in t or "SetHidden" in t.replace(" ", ""):
                for p in bel.list_all_pins(n):
                    if "INPUT" in str(p.get_pin_direction()).upper() or "input" in str(p.get_pin_direction()).lower():
                        cps = list(p.list_connected_pins())
                        log("  {}.{} val=[{}] conn={}".format(
                            t, p.get_pin_name(), pin_val(p),
                            [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps]))

log("=== BP_GridManager VisualizeCell + splices ===")
gbp = unreal.load_asset(MGR)
if not gbp:
    unreal.log_error("NO GridManager")
else:
    names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(gbp)]
    log("vars has PlotVisuals=" + str("PlotVisuals" in names))
    log("GridWidth/Height/CellSize present: " + str(
        ("GridWidth" in names, "GridHeight" in names, "CellSize" in names)))
    # Read CDO defaults for grid
    try:
        cdo = unreal.get_default_object(unreal.load_object(None, MGR + ".BP_GridManager_C"))
        if cdo:
            for prop in ("GridWidth", "GridHeight", "CellSize", "GridOrigin"):
                try:
                    log("CDO.{}={}".format(prop, cdo.get_editor_property(prop)))
                except Exception as e:
                    log("CDO.{} err {}".format(prop, e))
    except Exception as e:
        log("CDO: " + str(e))

    vg = bel.find_graph(gbp, "VisualizeCell")
    if not vg:
        log("NO VisualizeCell graph!")
    else:
        vge = unreal.BlueprintGraphEditor.get_graph_editor(vg)
        try:
            errs = vge.list_nodes_with_errors()
            log("VisualizeCell errors=" + str(len(errs)))
            for n in errs:
                log("  ERR " + bel.get_node_title(n))
                for p in bel.list_all_pins(n):
                    log("    pin {} dir={} val=[{}]".format(p.get_pin_name(), p.get_pin_direction(), pin_val(p)))
        except Exception as e:
            log("VC err list: " + str(e))
        for n in vge.list_all_nodes():
            t = bel.get_node_title(n)
            if "Spawn" in t or "Make Transform" in t or "Make Vector" in t or "GridToWorld" in t or "ApplyState" in t or "Array_Set" in t or "Array_Get" in t:
                for p in bel.list_all_pins(n):
                    d = str(p.get_pin_direction())
                    if "INPUT" in d.upper() or "input" in d.lower() or "OUTPUT" in d.upper():
                        cps = list(p.list_connected_pins())
                        val = pin_val(p)
                        if cps or (val and val not in ("", "0", "False", "None", "?")):
                            log("  {}.{} dir={} val=[{}] conn={}".format(
                                t, p.get_pin_name(), d, val,
                                [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:4]))

    for fname in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
        g = bel.find_graph(gbp, fname)
        if not g:
            log(fname + " MISSING graph")
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        dbg = viz = None
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if t == "DrawDebugBox":
                dbg = n
            if "VisualizeCell" in t:
                viz = n
        log("{} dbg={} viz={}".format(fname, bool(dbg), bool(viz)))
        if dbg:
            thenp = find_pin(dbg, "then", "Output")
            cps = list(thenp.list_connected_pins()) if thenp else []
            log("  dbg.then -> " + str([(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps]))
        if viz:
            for pname in ("State", "GridX", "Grid X", "GridY", "Grid Y", "execute"):
                p = find_pin(viz, pname, "Input")
                if p:
                    cps = list(p.list_connected_pins())
                    log("  viz.{} val=[{}] <- {}".format(
                        p.get_pin_name(), pin_val(p),
                        [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps]))
            vt = find_pin(viz, "then", "Output")
            if vt:
                log("  viz.then -> " + str([(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in vt.list_connected_pins()]))

    # Scene scale sample: find a VMF grass actor scale
    log("=== SCENE SCALE SAMPLE ===")
    try:
        actors = unreal.EditorLevelLibrary.get_all_level_actors()
        samples = 0
        for a in actors:
            n = a.get_actor_label() if hasattr(a, "get_actor_label") else a.get_name()
            if "Grass" in str(n) or "Soil" in str(n) or "VMF" in str(n):
                try:
                    t = a.get_actor_transform()
                    log("actor {} loc=({},{},{}) scale=({},{},{})".format(
                        n, t.translation.x, t.translation.y, t.translation.z,
                        t.scale3d.x, t.scale3d.y, t.scale3d.z))
                    samples += 1
                    if samples >= 8:
                        break
                except Exception as e:
                    log("actor err " + str(e))
    except Exception as e:
        log("level actors: " + str(e))

log("=== DONE ===")
