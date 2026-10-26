# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[GROW3] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
for fname in ("GrowCell", "HarvestCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    log("=== " + fname + " ===")
    entry_then = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            if pn.lower() in ("execute", "then", "else"):
                cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
                if cps:
                    log("  {}.{} -> {}".format(t, pn, cps))
        if "IsValidCell" in t:
            log("  IsValidCell exec_in=" + str([(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in find_pin(n, "execute", "Input").list_connected_pins()]))

# IMC via export / reflection
imc = unreal.load_asset("/Game/TopDown/Input/IMC_Default")
dkm = imc.get_editor_property("default_key_mappings")
log("DKM type=" + str(type(dkm)))
log("DKM dir=" + str([x for x in dir(dkm) if not x.startswith("_")][:40]))
for attr in ("mappings", "Mappings", "player_mappable_key_to_action", "key_mappings", "action_mappings"):
    if hasattr(dkm, attr):
        try:
            log("DKM.{}={}".format(attr, getattr(dkm, attr)))
        except Exception as e:
            log("DKM.{} err {}".format(attr, e))
try:
    # export text
    log("IMC export: " + str(imc.get_path_name()))
    # try get_mappings method
    for mname in dir(imc):
        if "map" in mname.lower() or "key" in mname.lower():
            if not mname.startswith("_"):
                log("imc has " + mname)
except Exception as e:
    log(str(e))

# Read uasset via AssetRegistry / enhanced input subsystem editor
try:
    mappings = unreal.InputMappingContext.get_editor_property(imc, "mappings")
except Exception:
    pass

# Use EditorAssetLibrary get_metadata or load as string from json
# Try: imc.get_mappings() 
for meth in ("get_mappings", "map_key", "unmap_key", "get_mapping_for_action"):
    if hasattr(imc, meth):
        log("has method " + meth)

# List IA assets and check if any MappingContext references via referencers
for ia in ("IA_Grow", "IA_Water", "IA_Plant", "IA_Interact", "IA_Harvest"):
    path = "/Game/TopDown/Input/Actions/" + ia
    a = unreal.load_asset(path)
    log("IA {} exists={}".format(ia, bool(a)))

# Character prints for Grow
char = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(char, "EventGraph"))
# Find nodes near GrowCell
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Grow" in t or ("Print" in t):
        # check if print is connected from Grow branch
        for p in bel.list_all_pins(n):
            cps = list(p.list_connected_pins())
            if cps and ("Grow" in t or any("Grow" in bel.get_node_title(c.get_owning_node()) for c in cps)):
                log("CHAR {} {} <-{}".format(t, p.get_pin_name(),
                    [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:5]))

# Mesh size compare
for name, path in (
    ("seed", "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling"),
    ("grow", "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing"),
    ("mature", "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature"),
):
    a = unreal.load_asset(path)
    b = a.get_bounds()
    log("{} extent={} origin={}".format(name, b.box_extent, b.origin))

log("done")
