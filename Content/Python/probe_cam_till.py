# -*- coding: utf-8 -*-
"""Probe camera, WASD-related BP, PlayerStart, and nearby VMF for till zone."""
import unreal
import math

def log(m):
    unreal.log("[PROBE_CAMTILL] " + str(m))
    print("[PROBE_CAMTILL] " + str(m))

CELL = 100.0
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# --- Camera ---
bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(bp_path)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cn = obj.get_class().get_name()
    if "SpringArm" in cn or name == "SpringArm":
        rr = obj.get_editor_property("relative_rotation")
        try:
            arm = obj.get_editor_property("target_arm_length")
        except Exception:
            arm = "?"
        log("SpringArm name={} pitch={} yaw={} roll={} arm={}".format(
            name, rr.pitch, rr.yaw, rr.roll, arm))
    if cn == "CameraComponent" or name == "Camera":
        try:
            ow = obj.get_editor_property("ortho_width")
            pm = obj.get_editor_property("projection_mode")
            log("Camera ortho={} proj={}".format(ow, pm))
        except Exception as e:
            log("Camera err " + str(e))
    if "CharacterMovement" in cn or name == "CharMoveComp" or "Movement" in cn:
        try:
            ort = obj.get_editor_property("orient_rotation_to_movement")
            log("CharMove {} orient_rot_to_move={}".format(name, ort))
        except Exception as e:
            log("CharMove {} {}".format(name, e))

# --- PlayerStart / GridManager ---
ps = None
gm = None
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    if cn == "PlayerStart" or lab == "PlayerStart":
        ps = a
        loc = a.get_actor_location()
        gx = int(loc.x // CELL)
        gy = int(loc.y // CELL)
        log("PlayerStart lab={} @ ({:.0f},{:.0f},{:.0f}) grid~({},{})".format(
            lab, loc.x, loc.y, loc.z, gx, gy))
    if lab == "BP_GridManager" or "GridManager" in cn:
        gm = a
        loc = a.get_actor_location()
        log("GridManager lab={} class={} @ ({:.0f},{:.0f},{:.0f})".format(
            lab, cn, loc.x, loc.y, loc.z))
        for prop in ("cell_size", "CellSize", "grid_width", "GridWidth",
                     "grid_height", "GridHeight", "grid_origin", "GridOrigin"):
            try:
                v = a.get_editor_property(prop)
                log("  GM.{}={}".format(prop, v))
            except Exception:
                pass

# --- Classify VMF near player ---
ps_loc = ps.get_actor_location() if ps else unreal.Vector(2250, 1650, 100)
counts = {}
near = []
soils = []
crops = []
trees = []
untilled = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_"):
        continue
    loc = a.get_actor_location()
    gx = int(loc.x // CELL)
    gy = int(loc.y // CELL)
    kind = "other"
    if "Soil" in lab or "Untilled" in lab or "Bed" in lab:
        kind = "soil"
        soils.append((lab, gx, gy, round(loc.x), round(loc.y)))
        if "Untilled" in lab or "Hoe" in lab:
            untilled.append((lab, gx, gy))
    elif any(k in lab for k in ("Corn", "Tomato", "Pumpkin", "Crop", "Wheat", "Carrot")):
        kind = "crop"
        crops.append((lab, gx, gy))
    elif "Tree" in lab or "Bush" in lab or "Rock" in lab:
        kind = "tree"
        trees.append((lab, gx, gy))
    elif "Grass" in lab or "Path" in lab or "Water" in lab or "House" or "Fence" in lab:
        kind = "env"
    counts[kind] = counts.get(kind, 0) + 1
    dx = loc.x - ps_loc.x
    dy = loc.y - ps_loc.y
    if abs(dx) < 600 and abs(dy) < 600:
        near.append((lab, gx, gy, round(dx), round(dy), kind))

log("VMF counts by kind: {}".format(counts))
log("Untilled/Hoe count={}: {}".format(len(untilled), untilled[:20]))
log("Soil sample (first 15): {}".format(soils[:15]))
log("Crops count={} sample: {}".format(len(crops), crops[:12]))
log("Near PlayerStart (+-6 cells) n={}:".format(len(near)))
for n in sorted(near, key=lambda t: (t[2], t[1]))[:60]:
    log("  NEAR {} grid({},{}) d=({},{}) kind={}".format(n[0], n[1], n[2], n[3], n[4], n[5]))

# Expected mirrored HOE zone 25-27,20-22
log("--- actors in expected HOE grid 24-28,19-23 ---")
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_"):
        continue
    loc = a.get_actor_location()
    gx = int(loc.x // CELL)
    gy = int(loc.y // CELL)
    if 24 <= gx <= 28 and 19 <= gy <= 23:
        log("  HOEZONE {} ({},{})".format(lab, gx, gy))

# House location
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if "House" in lab or "FarmShed" in lab:
        loc = a.get_actor_location()
        log("HOUSE {} @ ({:.0f},{:.0f}) grid~({},{})".format(
            lab, loc.x, loc.y, int(loc.x // CELL), int(loc.y // CELL)))

log("=== DONE PROBE ===")
