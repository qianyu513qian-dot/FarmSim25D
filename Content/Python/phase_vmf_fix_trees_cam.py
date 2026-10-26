# -*- coding: utf-8 -*-
"""Fix white tree canopies + flip view so house reads TOP like isometric reference.

1) Reassign Expansion02/Nature meshes from M_VMF_Palette -> M_VMF_Expansion02_Nature
   (leaf UVs sample green on Nature palette, cream/white on base palette).
2) SpringArm yaw -45 -> 135 (house/+Y to top of screen).
3) Mirror all VMF_*/Scene_* actors on X so water stays screen-LEFT and forest screen-RIGHT
   after the yaw flip. PlayerStart mirrored too. FarmGround stays hidden.
No open_editor. Saves level + BP.
"""
import unreal
import math

def log(m):
    unreal.log("[VMF_FIX] " + str(m))
    print("[VMF_FIX] " + str(m))

CELL = 100.0
WIDTH = 40
MAP_W = WIDTH * CELL  # 4000
NATURE_MAT = "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02_Nature"
NATURE_FOLDER = "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature"
BP_PATH = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
CAM_PITCH = -40.0
CAM_YAW = 135.0
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0


def apply_mat_to_mesh(mesh, mat):
    try:
        slots = list(mesh.static_materials)
        if not slots:
            return False
        new_slots = []
        for i, slot in enumerate(slots):
            ns = unreal.StaticMaterial()
            try:
                ns.set_editor_property(
                    "material_interface", mat if i == 0 else slot.material_interface)
            except Exception:
                pass
            try:
                ns.set_editor_property("material_slot_name", slot.material_slot_name)
            except Exception:
                pass
            try:
                ns.set_editor_property(
                    "imported_material_slot_name", slot.imported_material_slot_name)
            except Exception:
                pass
            new_slots.append(ns)
        mesh.set_editor_property("static_materials", new_slots)
        return True
    except Exception as e:
        log("mesh mat fail {}: {}".format(mesh.get_name(), e))
        try:
            unreal.EditorStaticMeshLibrary.set_material(mesh, 0, mat)
            return True
        except Exception:
            return False


def fix_nature_materials():
    mat = unreal.EditorAssetLibrary.load_asset(NATURE_MAT)
    if not mat:
        log("MISSING " + NATURE_MAT)
        return 0
    fixed = 0
    for a in unreal.EditorAssetLibrary.list_assets(NATURE_FOLDER, recursive=True):
        path = a.split(".")[0]
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            continue
        old = None
        try:
            old = mesh.static_materials[0].material_interface
        except Exception:
            pass
        if old and old.get_name() == "M_VMF_Expansion02_Nature":
            continue
        if apply_mat_to_mesh(mesh, mat):
            unreal.EditorAssetLibrary.save_asset(path)
            fixed += 1
            log("mesh {} {} -> M_VMF_Expansion02_Nature".format(
                mesh.get_name(), old.get_name() if old else "?"))
    # push onto placed actors
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n_act = 0
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.static_mesh
            if not sm:
                continue
            if "/Expansion02/Nature/" not in sm.get_path_name():
                continue
            c.set_material(0, mat)
            n_act += 1
    log("nature meshes fixed={} actor comps retouched={}".format(fixed, n_act))
    return fixed


def set_camera_iso():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not bp:
        log("NO BP")
        return False
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    ok = False
    for h in handles:
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        if "SpringArm" in cname or name == "SpringArm":
            try:
                obj.set_editor_property("target_arm_length", CAM_ARM)
            except Exception:
                pass
            for prop, val in (
                ("do_collision_test", False),
                ("use_pawn_control_rotation", False),
                ("inherit_pitch", False),
                ("inherit_yaw", False),
                ("inherit_roll", False),
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
                log("SpringArm p={} y={} r={} arm={}".format(
                    now.pitch, now.yaw, now.roll, CAM_ARM))
                ok = True
            except Exception as e:
                log("relrot fail " + str(e))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property(
                    "projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                z = unreal.Rotator()
                z.pitch = 0.0
                z.yaw = 0.0
                z.roll = 0.0
                obj.set_editor_property("relative_rotation", z)
                log("Camera ORTHO w={}".format(CAM_ORTHO))
            except Exception as e:
                log("cam fail " + str(e))
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        log("compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(BP_PATH)
    return ok


def mirror_x_actors():
    """Mirror VMF_/Scene_/PlayerStart on X about map center so after yaw=135
    water (was low X) becomes high X -> screen left; forest low X -> screen right.
    """
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    moved = 0
    skipped = 0
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        cn = a.get_class().get_name()
        is_ps = cn == "PlayerStart" or lab == "PlayerStart"
        is_vmf = lab.startswith("VMF_") or lab.startswith("Scene_")
        if not (is_ps or is_vmf):
            skipped += 1
            continue
        # skip FarmGround if somehow labeled
        if "FarmGround" in lab:
            continue
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        new_x = MAP_W - loc.x
        new_yaw = -rot.yaw  # mirror facing across X
        new_loc = unreal.Vector(new_x, loc.y, loc.z)
        new_rot = unreal.Rotator()
        new_rot.pitch = rot.pitch
        new_rot.yaw = new_yaw
        new_rot.roll = rot.roll
        try:
            a.set_actor_location(new_loc, False, True)
            a.set_actor_rotation(new_rot, False)
            moved += 1
        except Exception as e:
            log("move fail {}: {}".format(lab, e))
    log("mirrored_x actors={} (skipped_other={}) map_w={}".format(moved, skipped, MAP_W))
    return moved


def hide_farmground():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if "FarmGround" in lab or lab == "FarmGround":
            try:
                a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_hidden_in_game(True)
                log("hid " + lab)
            except Exception as e:
                log("hide fail " + str(e))


def verify():
    tall = unreal.EditorAssetLibrary.load_asset(
        NATURE_FOLDER + "/SM_VMF_Nature_Tree_Tall")
    mi = tall.static_materials[0].material_interface if tall else None
    log("VERIFY Tree_Tall mat={}".format(mi.get_name() if mi else None))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    house = None
    waterish = 0
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab == "VMF_House_FarmShed":
            house = a.get_actor_location()
            log("HOUSE loc=({:.0f},{:.0f},{:.0f})".format(house.x, house.y, house.z))
        if "Water" in lab or "Cliff" in lab:
            waterish += 1
        if lab == "PlayerStart":
            p = a.get_actor_location()
            log("PlayerStart loc=({:.0f},{:.0f}) grid~({:.0f},{:.0f})".format(
                p.x, p.y, p.x / CELL - 0.5, p.y / CELL - 0.5))
    # sample one tree mat on actor
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if not lab.startswith("VMF_Tree_"):
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            m0 = c.get_material(0)
            log("ACTOR {} mat0={}".format(lab, m0.get_name() if m0 else None))
            return


def main():
    log("=== START nature mats + cam yaw135 + mirror X ===")
    fix_nature_materials()
    set_camera_iso()
    mirror_x_actors()
    hide_farmground()
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved")
    except Exception as e:
        log("save level " + str(e))
    verify()
    log("=== DONE ===")
    log("Play Lvl_TopDown: trees should be GREEN; house toward TOP of view; water LEFT; forest RIGHT.")

main()
