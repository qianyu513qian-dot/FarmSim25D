# -*- coding: utf-8 -*-
"""Revert VectoRaith scene to FLAT top-down tiles; fix spawn at (-5000,-5000); camera pitch -45."""
import unreal

SCENE_PREFIX = "Scene_"
CELL = 100.0
ORIGIN = unreal.Vector(0.0, 0.0, 0.0)
WIDTH = 28
HEIGHT = 28

# Z layers (flat tilemap)
Z = {
    "Water_Left": 2.0, "Water_Bottom": 2.0, "Pond_NE": 2.0,
    "Path_V": 3.0, "Path_H": 3.0,
    "Tilled": 3.5,
    "Terrace": 4.0, "Cliff_S": 4.2,
    "Bridge": 5.0, "Stairs": 5.0,
    "Crop_TL": 5.0, "Crop_TR": 5.0, "Crop_BL": 5.0,
    "House": 7.0,
    "Fence_N": 6.0, "Fence_W": 6.0, "Fence_E": 6.0,
    "Lamp": 6.0, "Crate": 6.0, "Sign": 6.0,
    "Tree_NE": 6.0, "Tree_E": 6.0, "Tree_SE": 6.0, "Tree_NW": 6.0,
    "Tree_W": 6.0, "Tree_SW_Island": 6.0, "Tree_S": 6.0, "Tree_PathR": 6.0,
    "Rock_1": 6.0, "Rock_2": 6.0, "Rock_3": 6.0, "Stump_1": 6.0,
    "Flower_1": 6.0, "Flower_2": 6.0, "Flower_3": 6.0, "Flower_4": 6.0,
    "Reed_1": 6.0, "Reed_2": 6.0, "Reed_3": 6.0,
}

# (cx, cy, tw, th) cell layout — must match phase_scene_build
LAYOUT = {
    "Water_Left": (0, 0, 3, 28),
    "Water_Bottom": (3, 0, 25, 3),
    "Path_V": (12, 3, 2, 17),
    "Path_H": (14, 12, 9, 2),
    "Bridge": (11, 1, 4, 2),
    "Tilled": (4, 8, 7, 9),
    "Crop_TL": (4, 14, 3, 3),
    "Crop_TR": (7, 14, 3, 3),
    "Crop_BL": (4, 9, 3, 3),
    "Terrace": (9, 20, 9, 7),
    "Cliff_S": (9, 19, 9, 1),
    "Stairs": (12, 19, 2, 1),
    "House": (11, 21, 5, 6),
    "Fence_N": (9, 26, 9, 1),
    "Fence_W": (9, 20, 1, 6),
    "Fence_E": (17, 20, 1, 6),
    "Lamp": (14, 18, 1, 2),
    "Crate": (14, 14, 1, 2),
    "Sign": (15, 11, 1, 2),
    "Tree_NE": (22, 22, 3, 3),
    "Tree_E": (24, 16, 3, 3),
    "Tree_SE": (22, 6, 3, 3),
    "Tree_NW": (4, 22, 3, 3),
    "Tree_W": (3, 17, 3, 3),
    "Tree_SW_Island": (1, 1, 3, 3),
    "Tree_S": (18, 4, 3, 3),
    "Tree_PathR": (20, 14, 3, 3),
    "Rock_1": (20, 20, 2, 2),
    "Rock_2": (8, 18, 1, 1),
    "Rock_3": (23, 10, 1, 1),
    "Stump_1": (19, 8, 2, 2),
    "Flower_1": (16, 16, 1, 2),
    "Flower_2": (21, 18, 1, 1),
    "Flower_3": (8, 6, 1, 1),
    "Flower_4": (25, 12, 1, 2),
    "Reed_1": (3, 5, 1, 1),
    "Reed_2": (3, 12, 1, 1),
    "Reed_3": (6, 3, 1, 1),
    "Pond_NE": (24, 24, 3, 3),
}

SPAWN_XY = (1250.0, 1050.0, 100.0)  # Grid(12,10) on path by tilled


def log(m):
    unreal.log("[FLATFIX] " + str(m))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def rect_center(cx, cy, tw, th, z):
    return unreal.Vector(ORIGIN.x + (cx + tw * 0.5) * CELL,
                         ORIGIN.y + (cy + th * 0.5) * CELL, z)


def zero_rot():
    return unreal.Rotator()  # identity; avoid ctor ambiguity


def find_label(label):
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == label:
            return a
    return None


def flatten_scene():
    flat_n = 0
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        if not lab.startswith(SCENE_PREFIX):
            continue
        key = lab[len(SCENE_PREFIX):]
        if key not in LAYOUT:
            # unknown scene actor: force flat at current XY, z=6
            loc = a.get_actor_location()
            a.set_actor_rotation(zero_rot(), False)
            a.set_actor_location(unreal.Vector(loc.x, loc.y, 6.0), False, True)
            log("FLAT-unknown {} z=6".format(lab))
            flat_n += 1
            continue
        cx, cy, tw, th = LAYOUT[key]
        z = Z.get(key, 6.0)
        loc = rect_center(cx, cy, tw, th, z)
        scale = unreal.Vector(float(tw), float(th), 1.0)
        a.set_actor_rotation(zero_rot(), False)
        a.set_actor_location(loc, False, True)
        a.set_actor_scale3d(scale)
        try:
            a.set_actor_hidden_in_game(False)
            a.set_is_temporarily_hidden_in_editor(False)
        except Exception:
            pass
        # ensure no collision on overlays
        try:
            smc = a.static_mesh_component
            smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
        rr = a.get_actor_rotation()
        log("FLAT {} loc=({},{},{}) sc=({},{}) rot=({},{},{})".format(
            lab, round(loc.x), round(loc.y), round(loc.z),
            tw, th, round(rr.pitch, 1), round(rr.yaw, 1), round(rr.roll, 1)))
        flat_n += 1
    return flat_n


def fix_spawn():
    # Move placed BP_TopDownCharacter from (-5000,-5000) onto farm
    moved = 0
    for a in eas().get_all_level_actors():
        cn = a.get_class().get_name()
        lab = a.get_actor_label()
        if "TopDownCharacter" in cn or lab == "BP_TopDownCharacter":
            old = a.get_actor_location()
            a.set_actor_location(unreal.Vector(*SPAWN_XY), False, True)
            a.set_actor_rotation(zero_rot(), False)
            log("MOVE {} from ({},{},{}) -> {}".format(
                lab, round(old.x), round(old.y), round(old.z), SPAWN_XY))
            moved += 1
    ps = find_label("PlayerStart")
    if ps:
        ps.set_actor_location(unreal.Vector(*SPAWN_XY), False, True)
        log("PlayerStart -> {}".format(SPAWN_XY))
    else:
        log("WARN no PlayerStart")
    return moved


def fix_grid():
    gm = find_label("BP_GridManager")
    if not gm:
        log("ERROR no GridManager")
        return
    gm.set_editor_property("GridWidth", WIDTH)
    gm.set_editor_property("GridHeight", HEIGHT)
    gm.set_editor_property("CellSize", CELL)
    gm.set_editor_property("GridOrigin", ORIGIN)
    log("GridManager {}x{} Cell={} Origin=(0,0,0)".format(WIDTH, HEIGHT, CELL))


def fix_farmground():
    fg = find_label("FarmGround")
    if not fg:
        log("WARN no FarmGround")
        return
    center = unreal.Vector(WIDTH * CELL * 0.5, HEIGHT * CELL * 0.5, 1.0)
    fg.set_actor_location(center, False, True)
    fg.set_actor_rotation(zero_rot(), False)
    fg.set_actor_scale3d(unreal.Vector(float(WIDTH), float(HEIGHT), 1.0))
    log("FarmGround center=({},{}) scale={}x{}".format(center.x, center.y, WIDTH, HEIGHT))


def fix_camera():
    bp_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cn = obj.get_class().get_name()
        if "SpringArm" in cn:
            r = unreal.Rotator()
            r.pitch = -45.0
            r.yaw = 0.0
            r.roll = 0.0
            obj.set_editor_property("relative_rotation", r)
            try:
                obj.set_editor_property("target_arm_length", 2500.0)
            except Exception:
                pass
            now = obj.get_editor_property("relative_rotation")
            log("SpringArm pitch={} yaw={} roll={}".format(now.pitch, now.yaw, now.roll))
        if cn == "CameraComponent":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", 1800.0)
                log("Camera ortho=1800 ORTHOGRAPHIC")
            except Exception as e:
                log("cam " + str(e))
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as e:
        log("compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(bp_path)

    # Also fix placed instance SpringArm if possible
    for a in eas().get_all_level_actors():
        if "TopDownCharacter" not in a.get_class().get_name():
            continue
        for c in a.get_components_by_class(unreal.SceneComponent):
            if "SpringArm" in c.get_class().get_name():
                r = unreal.Rotator()
                r.pitch = -45.0
                r.yaw = 0.0
                r.roll = 0.0
                try:
                    c.set_editor_property("relative_rotation", r)
                    c.set_editor_property("target_arm_length", 2500.0)
                except Exception as e:
                    log("instance arm " + str(e))
                rr = c.get_editor_property("relative_rotation")
                log("placed SpringArm p={} y={} r={}".format(rr.pitch, rr.yaw, rr.roll))


def fix_water_material_tiling():
    """Ensure water materials use sensible tiling; keep FLAT (already)."""
    for mat_name, tiling in (("M_Water", 8.0), ("M_Grass", 14.0)):
        path = "/Game/Farm/Art/Mats/" + mat_name
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            continue
        mat = unreal.EditorAssetLibrary.load_asset(path)
        mel = unreal.MaterialEditingLibrary
        try:
            exprs = mel.get_material_expressions(mat) if hasattr(mel, "get_material_expressions") else []
        except Exception:
            exprs = []
        # Try set tiling on TextureCoordinate exprs
        changed = False
        try:
            # UE API: get_material_expression_count / get_by_index variants
            if hasattr(mel, "get_number_material_expressions"):
                n = mel.get_number_material_expressions(mat)
                for i in range(n):
                    ex = mel.get_material_expression_by_index(mat, i) if hasattr(mel, "get_material_expression_by_index") else None
                    if ex and "TextureCoordinate" in ex.get_class().get_name():
                        ex.set_editor_property("u_tiling", float(tiling))
                        ex.set_editor_property("v_tiling", float(tiling))
                        changed = True
                        log("{} texcoord tiling={}".format(mat_name, tiling))
        except Exception as e:
            log("tiling scan " + str(e))
        if changed:
            try:
                mel.recompile_material(mat)
            except Exception:
                pass
            unreal.EditorAssetLibrary.save_asset(path)


def hide_prototypes():
    for lab in ("Floor", "PrototypeFloor", "SM_PrototypeFloor", "Arena", "Wall",
                "SkySphere", "AtmosphericFog"):
        # only hide obvious greybox; keep Sky
        pass
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label()
        cn = a.get_class().get_name()
        name = a.get_name()
        if any(k in lab or k in name for k in ("Prototype", "Blockout", "Cube_Floor", "SM_Cube")):
            try:
                a.set_actor_hidden_in_game(True)
                a.set_is_temporarily_hidden_in_editor(True)
                log("hid prototype " + lab)
            except Exception:
                pass


def verify():
    log("=== VERIFY ===")
    for lab in ("BP_TopDownCharacter", "PlayerStart", "BP_GridManager", "FarmGround",
                "Scene_House", "Scene_Tree_NE", "Scene_Tree_NW", "Scene_Fence_W",
                "Scene_Water_Left", "Scene_Path_V", "Scene_Tilled"):
        a = find_label(lab)
        if not a:
            # TopDownCharacter may have generated label
            if lab == "BP_TopDownCharacter":
                for x in eas().get_all_level_actors():
                    if "TopDownCharacter" in x.get_class().get_name():
                        a = x
                        break
            if not a:
                log("MISSING " + lab)
                continue
        loc = a.get_actor_location()
        rr = a.get_actor_rotation()
        sc = a.get_actor_scale3d()
        gx = int(loc.x // 100) if lab in ("BP_TopDownCharacter", "PlayerStart") or "TopDown" in a.get_class().get_name() else None
        extra = " grid~({},{})".format(int(loc.x // 100), int(loc.y // 100)) if gx is not None else ""
        log("{} loc=({},{},{}) rot=({},{},{}) sc=({},{}){}".format(
            a.get_actor_label(), round(loc.x), round(loc.y), round(loc.z),
            round(rr.pitch, 1), round(rr.yaw, 1), round(rr.roll, 1),
            round(sc.x, 2), round(sc.y, 2), extra))
    # House bounds should be flat (large XY, small Z)
    house = find_label("Scene_House")
    if house:
        try:
            origin, extent = house.get_actor_bounds(False)
            log("House bounds origin=({},{},{}) extent=({},{},{})".format(
                round(origin.x), round(origin.y), round(origin.z),
                round(extent.x), round(extent.y), round(extent.z)))
        except Exception as e:
            log("house bounds " + str(e))
    nonzero = 0
    for a in eas().get_all_level_actors():
        if not a.get_actor_label().startswith(SCENE_PREFIX):
            continue
        rr = a.get_actor_rotation()
        if abs(rr.pitch) > 0.1 or abs(rr.yaw) > 0.1 or abs(rr.roll) > 0.1:
            nonzero += 1
            log("STILL-ROT " + a.get_actor_label())
    log("nonzero_rot_Scene={}".format(nonzero))


def main():
    log("=== START flat revert + spawn fix ===")
    n = flatten_scene()
    log("flattened={}".format(n))
    moved = fix_spawn()
    log("chars_moved={}".format(moved))
    fix_grid()
    fix_farmground()
    fix_camera()
    fix_water_material_tiling()
    hide_prototypes()
    try:
        ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("save level " + str(ok))
    except Exception as e:
        log("save " + str(e))
    verify()
    log("DONE — Play Lvl_TopDown; expect Grid ~12,10; flat house/trees; no black slab")


main()