# -*- coding: utf-8 -*-
"""Read IMC DefaultKeyMappings + VisualizeCell transform scale + PlotVisuals init."""
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[PROBE4] " + str(m))
    print("[PROBE4] " + str(m))

imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
# list all editor properties that look like mapping
try:
    for prop in imc.get_editor_property("default_key_mappings") if False else []:
        pass
except Exception as e:
    log("dkm " + str(e))

# Try common property names
for pname in ("default_key_mappings", "DefaultKeyMappings", "mappings", "Mappings",
              "key_mappings", "KeyMappings", "enhanced_action_mappings"):
    try:
        v = imc.get_editor_property(pname)
        log("prop {} type={} len={}".format(pname, type(v).__name__, (len(v) if hasattr(v, "__len__") else "n/a")))
        if hasattr(v, "__len__") and len(v) > 0:
            for i, m in enumerate(list(v)[:40]):
                try:
                    action = m.get_editor_property("action")
                except Exception:
                    action = getattr(m, "action", None)
                try:
                    key = m.get_editor_property("key")
                except Exception:
                    key = getattr(m, "key", None)
                an = action.get_name() if action else "?"
                kn = str(key)
                try:
                    kn = key.to_display_name()
                except Exception:
                    pass
                et = ""
                try:
                    et = m.export_text()
                except Exception:
                    pass
                log("  [{}] {} <= {} | {}".format(i, an, kn, et[:160] if et else ""))
    except Exception as e:
        log("no {} ({})".format(pname, e))

# Inspect InputMappingContext CDO / export
try:
    # unreal.InputMappingContext methods
    log("dir has map_key=" + str(hasattr(imc, "map_key")))
    log("dir has unmap_all=" + str(hasattr(imc, "unmap_all")))
except Exception as e:
    log(str(e))

# Try AssetEditor / dump via get_editor_property on all
try:
    # Use python reflection via _post_init or export
    text = unreal.EditorAssetLibrary.duplicate_asset  # noop
except Exception:
    pass

# Read from .uasset JSON? Use Config
# Try EnhancedInputLibrary
try:
    # iterate with blueprint
    dkm = None
    for attr in dir(imc):
        if "map" in attr.lower() or "key" in attr.lower():
            log("imc.attr " + attr)
except Exception as e:
    log(str(e))

# VisualizeCell MakeTransform / MakeVector scale
mgr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mgr, "VisualizeCell"))
log("=== VisualizeCell transforms ===")
for n in vge.list_all_nodes():
    t = bel.get_node_title(n)
    if t in ("Make Transform", "MakeTransform", "Make Vector", "MakeVector", "vector + vector", "SpawnActor BP Plot Visual"):
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), val, cps[:3]))

# Check if PlotVisuals resized anywhere
log("=== PlotVisuals mentions in all GM graphs ===")
for gname in bel.list_graph_names(mgr):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mgr, str(gname)))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        blob = t
        if "PlotVisual" in blob or "Resize" in blob:
            log("  graph={} node={}".format(gname, t))
            for p in bel.list_all_pins(n):
                val = ""
                try:
                    val = str(p.get_pin_value())
                except Exception:
                    pass
                cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
                if val or cps:
                    log("    {}.{} =[{}] <-{}".format(t, p.get_pin_name(), val[:50], cps[:3]))

# Check soil mesh bounds vs grass
for path in (
    "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "/Game/Farm/VoxelMicroFarm/Models/Expansion02/GroundStudy/SM_VMF_GroundStudy_Grass_B",
):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if mesh:
        box = mesh.get_bounding_box()
        log("mesh {} size=({:.1f},{:.1f},{:.1f})".format(
            path.split("/")[-1],
            abs(box.max.x - box.min.x), abs(box.max.y - box.min.y), abs(box.max.z - box.min.z)))

# PlayerController IMC assignment?
pc_paths = [
    "/Game/TopDown/Blueprints/BP_TopDownPlayerController",
    "/Game/TopDown/Blueprints/BP_TopDownController",
]
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/TopDown", recursive=True):
    name = str(a.asset_name)
    if "Controller" in name or "IMC" in name or "Input" in name:
        log("asset {} / {}".format(a.package_name, a.asset_class_path))

log("=== DONE ===")
