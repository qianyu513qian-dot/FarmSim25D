# -*- coding: utf-8 -*-
"""Verify map build assets and key actors; save all dirty."""
import unreal

def log(m):
    unreal.log("[MAP_VERIFY] " + str(m))

for path in [
    "/Game/Farm/Map/MI_FarmDirt",
    "/Game/Farm/Map/MI_FarmBorder",
]:
    a = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    log("{} -> {}".format(path, a))
    if a:
        mel = unreal.MaterialEditingLibrary
        for pname in ["Base Color", "Color"]:
            try:
                v = mel.get_material_instance_vector_parameter_value(a, pname)
                log("  {}={}".format(pname, v))
            except Exception as e:
                log("  {} err {}".format(pname, e))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
wanted = ["FarmGround", "FarmBorder_W", "FarmBorder_E", "FarmBorder_S", "FarmBorder_N", "PlayerStart", "BP_GridManager"]
for label in wanted:
    found = False
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == label:
            loc = a.get_actor_location()
            log("ACTOR {} loc=({:.1f},{:.1f},{:.1f})".format(label, loc.x, loc.y, loc.z))
            found = True
            break
    if not found:
        log("MISSING " + label)

# Expected spawn grid
sx, sy = 1050.0, 1050.0
gx = int((sx - 0.0) // 100.0)
gy = int((sy - 0.0) // 100.0)
log("Expected spawn Grid {},{} (valid 0..19)".format(gx, gy))

try:
    els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    log("save_current_level -> {}".format(els.save_current_level()))
except Exception as e:
    log("save " + str(e))

# Save map assets
for path in ["/Game/Farm/Map/MI_FarmDirt", "/Game/Farm/Map/MI_FarmBorder"]:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.save_asset(path)
        log("saved " + path)

log("DONE")
