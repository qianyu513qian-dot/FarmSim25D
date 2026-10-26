# -*- coding: utf-8 -*-
"""Fix Play: W=screen-up camera, collision floor, spawn on grass; till stays any-Empty+VisualizeCell.

Re-run: python Content/Python/run_remote.py Content/Python/phase_fix_wasd_floor.py

A) SpringArm pitch=-40 yaw=180 ortho=2800 (yaw90 made W=+Y appear screen-LEFT; +90 deg -> W=screen-UP).
   WASD world axes UNCHANGED: W=+Y S=-Y A=-X D=+X; OrientRotationToMovement=False.
B) Invisible FarmCollisionFloor Plane covering [0..4000]^2 at Z=0 (QueryAndPhysics). Stops fall-through.
   Does NOT restore visible template gray walls.
C) PlayerStart -> Grid(23,16) solid grass beside path. Clear Flower/Crop/Hoe clutter near spawn.
D) Remove decorative VMF_Hoe_* (till is gameplay Empty->Tilled + VisualizeCell Soil_Dry, not Hoe markers).
E) Confirm: TillCell already chains DrawDebugBox -> VisualizeCell -> Return (Soil_Dry via ApplyState).
"""
import unreal

def log(m):
    unreal.log("[WASDFLOOR] " + str(m))
    print("[WASDFLOOR] " + str(m))

CELL = 100.0
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
FARM = 40
PS_CX, PS_CY = 23, 16  # grass east of path cols 21-22
CAM_PITCH = -40.0
CAM_YAW = 180.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
BP_PATH = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
PLANE_PATH = "/Engine/BasicShapes/Plane"
FLOOR_LABEL = "FarmCollisionFloor"


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def cell_center(cx, cy, z=0.0):
    return unreal.Vector(ORIGIN.x + (cx + 0.5) * CELL,
                         ORIGIN.y + (cy + 0.5) * CELL, z)


def grid_of_loc(loc):
    return int(loc.x // CELL), int(loc.y // CELL)


def fix_camera():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not bp:
        return "no bp"
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    detail = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        name = str(lib.get_variable_name(data))
        if "SpringArm" in cname or name == "SpringArm":
            try:
                obj.set_editor_property("target_arm_length", CAM_ARM)
            except Exception:
                pass
            for prop, val in (
                ("do_collision_test", False), ("b_do_collision_test", False),
                ("use_pawn_control_rotation", False), ("b_use_pawn_control_rotation", False),
                ("inherit_pitch", False), ("b_inherit_pitch", False),
                ("inherit_yaw", False), ("b_inherit_yaw", False),
                ("inherit_roll", False), ("b_inherit_roll", False),
            ):
                try:
                    obj.set_editor_property(prop, val)
                except Exception:
                    pass
            rot = unreal.Rotator()
            rot.pitch = CAM_PITCH
            rot.yaw = CAM_YAW
            rot.roll = 0.0
            try:
                obj.set_editor_property("relative_rotation", rot)
                now = obj.get_editor_property("relative_rotation")
                detail.append("SpringArm p={:.0f} y={:.0f}".format(now.pitch, now.yaw))
            except Exception as e:
                detail.append("SpringArm fail " + str(e))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                detail.append("ortho={}".format(CAM_ORTHO))
            except Exception as e:
                detail.append("cam " + str(e))
        if "CharacterMovement" in cname or name in ("CharacterMovement", "CharMoveComp"):
            for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    obj.set_editor_property(prop, False)
                    detail.append("OrientRotToMove=False")
                    break
                except Exception:
                    pass
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(BP_PATH)
    return "; ".join(detail)


def ensure_collision_floor():
    """Invisible walkable plane under entire 40x40 farm AABB."""
    mesh = unreal.EditorAssetLibrary.load_asset(PLANE_PATH)
    if not mesh:
        return "NO_PLANE_MESH"
    # Plane default 100x100; scale 40 => 4000x4000. Center at (2000,2000,0).
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    scale = unreal.Vector(float(FARM), float(FARM), 1.0)
    actor = None
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == FLOOR_LABEL:
            actor = a
            break
    if actor is None:
        actor = eas().spawn_actor_from_class(
            unreal.StaticMeshActor, center, unreal.Rotator(0, 0, 0))
        actor.set_actor_label(FLOOR_LABEL)
    actor.set_actor_location(center, False, True)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    smc.set_static_mesh(mesh)
    try:
        smc.set_visibility(False, True)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(True)
    except Exception:
        pass
    try:
        actor.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        pass
    try:
        actor.set_actor_enable_collision(True)
    except Exception:
        pass
    try:
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        try:
            smc.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception as e:
            return "collision set fail " + str(e)
    # Block all / WorldStatic profile if available
    for prop, val in (
        ("collision_profile_name", "BlockAll"),
        ("CollisionProfileName", "BlockAll"),
    ):
        try:
            smc.set_editor_property(prop, val)
            break
        except Exception:
            pass
    loc = actor.get_actor_location()
    sc = actor.get_actor_scale3d()
    return "ok loc=({:.0f},{:.0f},{:.0f}) scale=({:.0f},{:.0f},{:.0f})".format(
        loc.x, loc.y, loc.z, sc.x, sc.y, sc.z)


def clear_near_spawn_clutter():
    """Remove Hoe markers + flowers/crops near spawn so first till on grass is obvious."""
    removed = []
    keep_near = ("Grass", "Path", "Water", "Bridge", "House", "Fence", "Cliff",
                 "Bank", "Yard", "FarmShed", "Collision")
    kill_near = ("Hoe", "Flower", "Crop", "Corn", "Tomato", "Pumpkin", "Bush",
                 "Rock", "Clump", "Crate", "Chest")
    for a in list(eas().get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_Hoe_"):
            try:
                eas().destroy_actor(a)
                removed.append(lab)
            except Exception:
                pass
            continue
        if not lab.startswith("VMF_"):
            continue
        loc = a.get_actor_location()
        gx, gy = grid_of_loc(loc)
        # near spawn window
        if not (PS_CX - 4 <= gx <= PS_CX + 4 and PS_CY - 4 <= gy <= PS_CY + 4):
            continue
        if any(k in lab for k in keep_near):
            continue
        if any(k in lab for k in kill_near):
            try:
                eas().destroy_actor(a)
                removed.append(lab)
            except Exception:
                pass
    return removed


def fix_player_start():
    spawn = cell_center(PS_CX, PS_CY, 100.0)
    kept = None
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        lab = a.get_actor_label() or ""
        if cn == "PlayerStart" or lab == "PlayerStart" or "PlayerStart" in cn:
            if kept is None:
                kept = a
                a.set_actor_location(spawn, False, True)
                try:
                    a.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
                except Exception:
                    pass
                try:
                    a.set_actor_label("PlayerStart")
                except Exception:
                    pass
            else:
                try:
                    eas().destroy_actor(a)
                except Exception:
                    pass
    if kept is None:
        kept = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, unreal.Rotator())
        kept.set_actor_label("PlayerStart")
    loc = kept.get_actor_location()
    return (round(loc.x), round(loc.y), round(loc.z))


def verify_till_visualize():
    bel = unreal.BlueprintEditorLibrary
    bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    has_viz = False
    dbg_to_viz = False
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "VisualizeCell":
            has_viz = True
        if t == "DrawDebugBox":
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()).lower() == "then":
                    for c in p.list_connected_pins():
                        if bel.get_node_title(c.get_owning_node()) == "VisualizeCell":
                            dbg_to_viz = True
    return has_viz, dbg_to_viz


def grass_near_spawn():
    cells = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if not lab.startswith("VMF_Grass_"):
            continue
        gx, gy = grid_of_loc(a.get_actor_location())
        if PS_CX - 2 <= gx <= PS_CX + 2 and PS_CY - 2 <= gy <= PS_CY + 2:
            cells.append((gx, gy, lab))
    return sorted(cells)


def save_level():
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        return True
    except Exception:
        try:
            unreal.EditorLevelLibrary.save_current_level()
            return True
        except Exception as e:
            log("save fail " + str(e))
            return False


def main():
    log("=== START phase_fix_wasd_floor ===")
    cam = fix_camera()
    log("camera: " + cam)
    floor = ensure_collision_floor()
    log("floor: " + floor)
    removed = clear_near_spawn_clutter()
    log("cleared clutter n={} sample={}".format(len(removed), removed[:20]))
    ps = fix_player_start()
    log("PlayerStart Grid({},{}) world={}".format(PS_CX, PS_CY, ps))
    grass = grass_near_spawn()
    log("grass near spawn: " + str(grass))
    has_viz, dbg_to_viz = verify_till_visualize()
    log("TillCell has VisualizeCell={} dbg->viz={}".format(has_viz, dbg_to_viz))
    try:
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            unreal.Vector(2300.0, 1600.0, 1800.0),
            unreal.Rotator(-40.0, 180.0, 0.0))
    except Exception:
        pass
    save_level()
    log("SUMMARY pitch={} yaw={} ortho={}".format(CAM_PITCH, CAM_YAW, CAM_ORTHO))
    log("SUMMARY WASD kept W=+Y; yaw180 => expect W=screen-up (was left at yaw90)")
    log("SUMMARY collision={} covering 0..{} world units".format(FLOOR_LABEL, FARM * CELL))
    log("SUMMARY till: any Empty cell (incl grass); VisualizeCell->Soil_Dry; NOT Hoe-gated")
    log("SUMMARY blocked note: PlotStates init all Empty — paths/water not yet Blocked-enum")
    log("=== DONE ===")


if __name__ == "__main__":
    main()
