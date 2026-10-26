# -*- coding: utf-8 -*-
"""Deeper probe: GridToWorld, spawn scale pins, live editor spawn test."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"


def log(m):
    unreal.log("[PROBE2] " + str(m))


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


# Dump ALL MakeVector values in VisualizeCell (scale + offset)
gbp = unreal.load_asset(MGR)
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "VisualizeCell"))
log("=== ALL VisualizeCell nodes (compact) ===")
for n in vge.list_all_nodes():
    t = bel.get_node_title(n)
    vals = []
    for p in bel.list_all_pins(n):
        d = str(p.get_pin_direction())
        if "INPUT" in d.upper() or "input" in d.lower():
            v = pin_val(p)
            cps = list(p.list_connected_pins())
            if v and v not in ("", "False", "0") or cps:
                vals.append("{}=[{}]c{}".format(p.get_pin_name(), v, len(cps)))
    log("  {} :: {}".format(t, "; ".join(vals[:8])))

# GridToWorld graph
log("=== GridToWorld ===")
g2 = bel.find_graph(gbp, "GridToWorld")
if g2:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g2)
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        for p in bel.list_all_pins(n):
            v = pin_val(p)
            cps = list(p.list_connected_pins())
            if cps or (v and v not in ("", "?")):
                log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), v,
                    [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:3]))

# WorldToGrid too
log("=== WorldToGrid ===")
wg = bel.find_graph(gbp, "WorldToGrid")
if wg:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(wg)
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        for p in bel.list_all_pins(n):
            v = pin_val(p)
            cps = list(p.list_connected_pins())
            if cps or (v and v not in ("", "?")):
                log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), v,
                    [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:3]))

# Live spawn a PlotVisual in editor at known grass cell and ApplyState
log("=== LIVE SPAWN TEST ===")
pv_cls = unreal.load_object(None, "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C")
log("pv_cls=" + str(pv_cls))
if pv_cls:
    # Place at Grid(18,18) center = (1850, 1850, 20)
    loc = unreal.Vector(1850.0, 1850.0, 20.0)
    sc = unreal.Vector(0.01, 0.01, 0.01)
    tf = unreal.Transform(unreal.Rotator(0, 0, 0), loc, sc)
    try:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(pv_cls, loc, unreal.Rotator(0, 0, 0))
        log("spawned actor=" + str(actor))
        if actor:
            actor.set_actor_scale3d(sc)
            actor.set_actor_location(loc, False, True)
            # Try call ApplyState via process_event if possible
            try:
                # Set meshes directly on components
                comps = actor.get_components_by_class(unreal.StaticMeshComponent)
                log("num SMC=" + str(len(comps)))
                dry = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry")
                seed = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling")
                for c in comps:
                    nm = c.get_name()
                    log("  comp {} mesh_before={}".format(nm, c.static_mesh.get_name() if c.static_mesh else None))
                    if "Plot" in nm or "plot" in nm or "PlotMesh" in str(c.get_editor_property("component_tags") if False else nm):
                        pass
                # Set by order: first PlotMesh-ish
                named = {}
                for c in comps:
                    named[c.get_name()] = c
                log("comp names=" + str(list(named.keys())))
                # Find PlotMesh / CropMesh by name substring
                for c in comps:
                    cn = c.get_name()
                    if "PlotMesh" in cn:
                        c.set_static_mesh(dry)
                        c.set_hidden_in_game(False, False)
                        c.set_visibility(True)
                        log("set PlotMesh dry")
                    elif "CropMesh" in cn:
                        c.set_static_mesh(seed)
                        c.set_hidden_in_game(False, False)
                        c.set_visibility(True)
                        log("set CropMesh seed")
                # If names are generated like StaticMeshComponent_0
                if not any("PlotMesh" in c.get_name() for c in comps):
                    if len(comps) >= 1:
                        comps[0].set_static_mesh(dry)
                        comps[0].set_hidden_in_game(False, False)
                        comps[0].set_visibility(True)
                        log("fallback set comps[0] dry")
                    if len(comps) >= 2:
                        comps[1].set_static_mesh(seed)
                        comps[1].set_hidden_in_game(False, False)
                        comps[1].set_visibility(True)
                        log("fallback set comps[1] seed")
                for c in comps:
                    log("  AFTER {} mesh={} hidden={} vis={} world_loc={}".format(
                        c.get_name(),
                        c.static_mesh.get_name() if c.static_mesh else None,
                        c.b_hidden_in_game if hasattr(c, "b_hidden_in_game") else "?",
                        c.is_visible() if hasattr(c, "is_visible") else "?",
                        c.get_world_location() if hasattr(c, "get_world_location") else actor.get_actor_location()))
                log("actor loc={} scale={}".format(actor.get_actor_location(), actor.get_actor_scale3d()))
                # bounds
                try:
                    origin, extent = actor.get_actor_bounds(False)
                    log("bounds origin={} extent={}".format(origin, extent))
                except Exception as e:
                    log("bounds err " + str(e))
            except Exception as e:
                import traceback
                log("apply err " + str(e) + "\n" + traceback.format_exc())
    except Exception as e:
        import traceback
        log("spawn err " + str(e) + "\n" + traceback.format_exc())

# Compare grass mesh bounds vs soil
grass = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass")
soil = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry")
if grass:
    b = grass.get_bounds()
    log("Grass bounds extent={} r={}".format(b.box_extent, b.sphere_radius))
if soil:
    b = soil.get_bounds()
    log("Soil bounds extent={} r={}".format(b.box_extent, b.sphere_radius))

# Check BeginPlay for PlotVisuals init
log("=== GridManager BeginPlay / EventGraph ===")
for gname in bel.list_graph_names(gbp):
    gs = str(gname)
    if "Event" in gs or "Begin" in gs or gs == "EventGraph":
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, gs))
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if any(k in t for k in ("Begin", "PlotVisual", "Array", "Resize", "Init", "Plots")):
                log("  [{}] {}".format(gs, t))

log("=== DONE ===")
