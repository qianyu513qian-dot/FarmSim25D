# -*- coding: utf-8 -*-
"""Probe IMC keys, Interact pin wiring to TillCell, PlotVisual meshes."""
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[PROBE3] " + str(m))
    print("[PROBE3] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name())
        if name_substr.lower() in pn.lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
log("IMC class=" + imc.get_class().get_name())
mappings = imc.get_editor_property("mappings")
log("mappings n=" + str(len(mappings)))
for i, m in enumerate(mappings):
    try:
        action = m.get_editor_property("action")
    except Exception:
        action = getattr(m, "action", None)
    try:
        key = m.get_editor_property("key")
    except Exception:
        key = getattr(m, "key", None)
    an = action.get_path_name() if action else "?"
    kn = str(key)
    try:
        kn = key.to_display_name()
    except Exception:
        pass
    et = ""
    try:
        et = m.export_text()
    except Exception:
        et = ""
    log("[{}] action={} key={!r} export={!r}".format(i, an, kn, (et[:240] if et else "")))

bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
log("=== Interact TillCell pins ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if t == "WorldToGrid":
        ep = find_pin(n, "execute", "Input")
        srcs = [bel.get_node_title(c.get_owning_node()) for c in ep.list_connected_pins()] if ep else []
        thenp = find_pin(n, "then", "Output")
        dests = [bel.get_node_title(c.get_owning_node()) for c in thenp.list_connected_pins()] if thenp else []
        if not (any("Interact" in s for s in srcs) or "TillCell" in dests):
            continue
        log("WorldToGrid srcs={} dests={}".format(srcs, dests))
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  WTG.{} =[{}] <-{}".format(p.get_pin_name(), val, cps))
    if t == "TillCell":
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  Till.{} =[{}] <-{}".format(p.get_pin_name(), val, cps))

log("=== BeginPlay / GetActorOfClass ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "BeginPlay" in t or "GetActorOfClass" in t or t == "Set GridManagerRef":
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if val or cps:
                log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), val[:120], cps[:5]))

log("=== PlotVisual SMCs ===")
pv = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_PlotVisual")
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(pv):
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, pv)
    if obj and "StaticMesh" in obj.get_class().get_name():
        sm = obj.get_editor_property("static_mesh")
        rel = obj.get_editor_property("relative_location")
        sc = obj.get_editor_property("relative_scale3d")
        try:
            vis = obj.get_editor_property("visible")
        except Exception:
            vis = "?"
        log("SMC {} mesh={} path={} rel=({:.2f},{:.2f},{:.2f}) sc=({:.4f},{:.4f},{:.4f}) vis={}".format(
            name, sm.get_name() if sm else None, sm.get_path_name() if sm else None,
            rel.x, rel.y, rel.z, sc.x, sc.y, sc.z, vis))

age = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
log("ApplyState nodes:")
for n in age.list_all_nodes():
    t = bel.get_node_title(n)
    cn = n.get_class().get_name()
    if any(k in (t + cn) for k in ("SetStaticMesh", "Set Visibility", "SetVisibility", "Switch", "Branch", "Soil", "Mesh", "ApplyState", "Select")):
        pins = []
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if val or cps:
                pins.append("{}=[{}]<-{}".format(p.get_pin_name(), val[:60], cps[:2]))
        log("  {} | {}".format(t, pins[:8]))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("VMF_Grass_"):
        smc = a.static_mesh_component
        grass_mesh = smc.static_mesh
        grass_scale = a.get_actor_scale3d()
        log("sample grass {} mesh={} scale=({:.4f},{:.4f},{:.4f})".format(
            lab, grass_mesh.get_path_name() if grass_mesh else None,
            grass_scale.x, grass_scale.y, grass_scale.z))
        break

for path in (
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Untilled",
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
):
    log("asset {} exists={}".format(path, unreal.EditorAssetLibrary.does_asset_exist(path)))

ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets_by_path("/Game/Farm/VoxelMicroFarm/Models/Terrain", recursive=True)
log("Terrain assets n=" + str(len(assets)))
for a in assets:
    log("  " + str(a.asset_name))

mgr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
bge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mgr, "EventGraph"))
log("=== GridManager BeginPlay ===")
for n in bge.list_all_nodes():
    t = bel.get_node_title(n)
    if any(k in t for k in ("BeginPlay", "PlotStates", "PlotVisuals", "Resize", "ForLoop", "Clear", "Add")):
        pins = []
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if val or cps:
                pins.append("{}=[{}]<-{}".format(p.get_pin_name(), val[:40], cps[:3]))
        log("  {} | {}".format(t, pins[:6]))

log("=== DONE ===")
