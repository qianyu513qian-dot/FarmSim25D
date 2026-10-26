# -*- coding: utf-8 -*-
"""Restore camera composition + IMC interact + force-persist after reopen.

Layout (NO scene rotate):
  House centroid ~ (2170, 3620) high Y
  Water centroid ~ (400, 2000) low X
  Tree centroid  ~ (3244, 1955) high X

With yaw=-90 (look -Y): house BOTTOM, water LEFT, trees RIGHT  (current bad)
With yaw=+90 (look +Y): house TOP,    water RIGHT, trees LEFT

House-top + water-left is geometrically impossible (orthogonal axes).
Priority: house TOP -> SpringArm yaw=+90 pitch=-40 ortho=2800.
W stays screen-up via existing cam-relative Move.

Also: remap IMC E/F/R/G/H, verify VisualizeCell, PlayerStart pitch0 on path,
FarmCollisionFloor, proto=0, force-save umap+ExternalActors+BPs.
"""
import unreal
import os
import time

TAG = "[RESTORE_PERSIST] "

def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
GM = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"
CELL = 100.0
FARM = 40
CAM_PITCH = -40.0
CAM_YAW = 90.0   # house TOP (high Y); water will be RIGHT, trees LEFT
CAM_ORTHO = 2800.0
CAM_ARM = 6500.0
FLOOR_LABEL = "FarmCollisionFloor"
# Path near grass / till fields (Grid 16,18 ~ path toward soil)
PS_X = 16.5 * CELL
PS_Y = 18.5 * CELL

IA_MAP = {
    "E": "/Game/TopDown/Input/Actions/IA_Interact",
    "F": "/Game/TopDown/Input/Actions/IA_Plant",
    "R": "/Game/TopDown/Input/Actions/IA_Water",
    "G": "/Game/TopDown/Input/Actions/IA_Grow",
    "H": "/Game/TopDown/Input/Actions/IA_Harvest",
}


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def fix_springarm():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    if not bp:
        return "NO BP"
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
            obj.set_editor_property("relative_rotation", rot)
            now = obj.get_editor_property("relative_rotation")
            detail.append("SpringArm p={:.0f} y={:.0f} arm={}".format(
                now.pitch, now.yaw, CAM_ARM))
        if cname == "CameraComponent" or name == "Camera":
            try:
                obj.set_editor_property("projection_mode", unreal.CameraProjectionMode.ORTHOGRAPHIC)
                obj.set_editor_property("ortho_width", CAM_ORTHO)
                zero = unreal.Rotator()
                zero.pitch = 0.0
                zero.yaw = 0.0
                zero.roll = 0.0
                obj.set_editor_property("relative_rotation", zero)
                detail.append("ortho={}".format(CAM_ORTHO))
            except Exception as e:
                detail.append("cam " + str(e))
        if "CharacterMovement" in cname:
            for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    obj.set_editor_property(prop, False)
                    detail.append("Orient=False")
                    break
                except Exception:
                    pass
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    ok = unreal.EditorAssetLibrary.save_asset(CHAR)
    detail.append("save_char=" + str(ok))
    return "; ".join(detail)


def ensure_imc():
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    if not imc:
        return {"ok": False, "detail": "NO IMC"}
    results = []
    for key_name, ia_path in IA_MAP.items():
        if not unreal.EditorAssetLibrary.does_asset_exist(ia_path):
            results.append("{}:MISSING_IA".format(key_name))
            continue
        ia = unreal.EditorAssetLibrary.load_asset(ia_path)
        k = unreal.Key()
        k.import_text(key_name)
        try:
            imc.unmap_all_keys_from_action(ia)
        except Exception:
            pass
        try:
            imc.map_key(ia, k)
            results.append("{}:ok".format(key_name))
        except Exception as e:
            results.append("{}:err:{}".format(key_name, e))
    saved = unreal.EditorAssetLibrary.save_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    status = {
        "E": "Key=E" in txt and "IA_Interact" in txt,
        "F": "Key=F" in txt and "IA_Plant" in txt,
        "R": "Key=R" in txt and "IA_Water" in txt,
        "G": "Key=G" in txt and "IA_Grow" in txt,
        "H": "Key=H" in txt and "IA_Harvest" in txt,
        "WASD": all(("Key=" + k) in txt for k in "WASD"),
        "saved": bool(saved),
        "maps": results,
    }
    return status


def verify_cam_relative():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    info = []
    ok = False
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "AddMovementInput":
            continue
        wd = None
        sc = None
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            if "WorldDirection" in pn:
                wd = p
            if "ScaleValue" in pn:
                sc = p
        wds = [bel.get_node_title(c.get_owning_node()) for c in wd.list_connected_pins()] if wd else []
        scs = [str(c.get_pin_name()) for c in sc.list_connected_pins()] if sc else []
        info.append((scs, wds))
        for t in wds:
            if any(k in t for k in ("Normal", "Forward", "Right", "Get World Rotation", "GetComponentRotation")):
                ok = True
    return ok, info


def verify_char_actions():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    needed = ("IA_Interact", "TillCell", "IA_Plant", "PlantCell", "IA_Water", "WaterCell",
              "IA_Grow", "GrowCell", "IA_Harvest", "HarvestCell", "VisualizeCell")
    found = {k: False for k in needed}
    titles = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        titles.append(t)
        for k in needed:
            if k in t:
                found[k] = True
    # Also check if VisualizeCell is called from somewhere in the Till/Plant chains
    # by scanning all pins' connected titles is heavy; just report found flags
    return found


def verify_visualize_cell():
    """Confirm BP_GridManager has VisualizeCell graph and TillCell calls it / PlotVisual."""
    out = {"gm_exists": False, "has_VisualizeCell_graph": False, "has_TillCell_graph": False,
           "TillCell_calls_Visualize": False, "PlotVisual_exists": False,
           "ApplyState": False, "char_calls_viz": False}
    if unreal.EditorAssetLibrary.does_asset_exist(PV):
        out["PlotVisual_exists"] = True
        try:
            pv = unreal.EditorAssetLibrary.load_asset(PV)
            g = bel.find_graph(pv, "ApplyState")
            out["ApplyState"] = g is not None
            # fallback: search any graph title
            if not out["ApplyState"]:
                # list via function graphs if possible
                try:
                    for fg in getattr(pv, "function_graphs", []) or []:
                        if "ApplyState" in str(fg.get_name()):
                            out["ApplyState"] = True
                except Exception:
                    pass
        except Exception as e:
            out["pv_err"] = str(e)

    if not unreal.EditorAssetLibrary.does_asset_exist(GM):
        return out
    out["gm_exists"] = True
    gm = unreal.EditorAssetLibrary.load_asset(GM)
    for gname in ("VisualizeCell", "TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
        g = bel.find_graph(gm, gname)
        if g is not None:
            out["has_{}_graph".format(gname)] = True
    g_till = bel.find_graph(gm, "TillCell")
    if g_till:
        out["has_TillCell_graph"] = True
        try:
            gge = unreal.BlueprintGraphEditor.get_graph_editor(g_till)
            for n in gge.list_all_nodes():
                t = bel.get_node_title(n)
                if "VisualizeCell" in t or "Visualize" in t:
                    out["TillCell_calls_Visualize"] = True
                if "PlotVisual" in t or "ApplyState" in t or "Soil" in t:
                    out["TillCell_hits"] = out.get("TillCell_hits", []) + [t]
        except Exception as e:
            out["till_scan_err"] = str(e)
    g_viz = bel.find_graph(gm, "VisualizeCell")
    if g_viz:
        out["has_VisualizeCell_graph"] = True
        try:
            gge = unreal.BlueprintGraphEditor.get_graph_editor(g_viz)
            hits = []
            for n in gge.list_all_nodes():
                t = bel.get_node_title(n)
                if any(k in t for k in ("PlotVisual", "ApplyState", "Spawn", "Soil", "Dry")):
                    hits.append(t)
            out["VisualizeCell_hits"] = hits[:20]
        except Exception as e:
            out["viz_scan_err"] = str(e)

    # Character: after TillCell success, does it call VisualizeCell?
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "VisualizeCell" in t:
            out["char_calls_viz"] = True
            break
    return out


def ensure_floor():
    mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    scale = unreal.Vector(float(FARM), float(FARM), 1.0)
    actor = None
    for a in eas().get_all_level_actors():
        if (a.get_actor_label() or "") == FLOOR_LABEL:
            actor = a
            break
    created = False
    if actor is None:
        actor = eas().spawn_actor_from_class(unreal.StaticMeshActor, center, unreal.Rotator())
        actor.set_actor_label(FLOOR_LABEL)
        created = True
    flat = unreal.Rotator()
    flat.pitch = 0.0
    flat.yaw = 0.0
    flat.roll = 0.0
    actor.set_actor_location(center, False, True)
    actor.set_actor_rotation(flat, False)
    actor.set_actor_scale3d(scale)
    smc = actor.static_mesh_component
    if mesh:
        smc.set_static_mesh(mesh)
    try:
        smc.set_visibility(False, True)
        actor.set_actor_hidden_in_game(True)
        actor.set_is_temporarily_hidden_in_editor(True)
        actor.set_actor_enable_collision(True)
        smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        smc.set_editor_property("collision_profile_name", "BlockAll")
    except Exception as e:
        log("floor props " + str(e))
    return {"created": created, "ok": True}


def ensure_playerstart():
    spawn = unreal.Vector(PS_X, PS_Y, 100.0)
    flat = unreal.Rotator()
    flat.pitch = 0.0
    flat.yaw = 0.0
    flat.roll = 0.0
    kept = None
    for a in list(eas().get_all_level_actors()):
        cn = a.get_class().get_name()
        lab = a.get_actor_label() or ""
        if cn == "PlayerStart" or lab == "PlayerStart" or "PlayerStart" in cn:
            if kept is None:
                kept = a
            else:
                try:
                    eas().destroy_actor(a)
                except Exception:
                    pass
    if kept is None:
        kept = eas().spawn_actor_from_class(unreal.PlayerStart, spawn, flat)
        kept.set_actor_label("PlayerStart")
        log("spawned PlayerStart")
    kept.set_actor_location(spawn, False, True)
    kept.set_actor_rotation(flat, False)
    try:
        kept.set_actor_label("PlayerStart")
        kept.set_actor_hidden_in_game(False)
        kept.set_is_temporarily_hidden_in_editor(False)
    except Exception:
        pass
    loc = kept.get_actor_location()
    rot = kept.get_actor_rotation()
    gx, gy = int(loc.x // CELL), int(loc.y // CELL)
    return {
        "world": (round(loc.x), round(loc.y), round(loc.z)),
        "grid": (gx, gy),
        "rot": (round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)),
    }


def count_proto():
    leftover = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab == FLOOR_LABEL:
            continue
        mesh_name = mesh_path = ""
        try:
            smc = a.static_mesh_component
            if smc and smc.static_mesh:
                mesh_name = smc.static_mesh.get_name()
                mesh_path = smc.static_mesh.get_path_name()
        except Exception:
            pass
        if ("LevelPrototyping" in mesh_path
                or mesh_name.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer", "SM_Template"))
                or lab.startswith(("SM_Cube", "SM_Ramp"))
                or lab == "Floor"
                or "Template_Map_Floor" in mesh_name):
            leftover.append(lab)
    return leftover


def mark_dirty():
    n = 0
    for a in eas().get_all_level_actors():
        try:
            a.modify()
            n += 1
        except Exception:
            pass
    try:
        unreal.EditorLevelLibrary.get_editor_world().modify()
    except Exception:
        pass
    return n


def force_save():
    results = {}
    try:
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        ok = les.save_current_level()
        results["save_current_level"] = bool(ok)
    except Exception as e:
        results["save_current_level"] = "exc:" + str(e)
        try:
            unreal.EditorLevelLibrary.save_current_level()
            results["save_current_level_ell"] = True
        except Exception as e2:
            results["save_current_level_ell"] = "exc:" + str(e2)

    try:
        ok2 = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        results["save_dirty_packages"] = bool(ok2) if ok2 is not None else True
    except Exception as e:
        results["save_dirty_packages"] = "exc:" + str(e)

    for dpath, key in (
        ("/Game/__ExternalActors__/TopDown/Lvl_TopDown", "save_ext_dir"),
        ("/Game/TopDown/Blueprints", "save_bp_dir"),
        ("/Game/TopDown/Input", "save_input_dir"),
        ("/Game/Farm/Grid", "save_farm_grid_dir"),
    ):
        try:
            ok = unreal.EditorAssetLibrary.save_directory(dpath, True, True)
            results[key] = bool(ok)
        except Exception as e:
            results[key] = "exc:" + str(e)

    for apath, key in (
        ("/Game/TopDown/Lvl_TopDown", "save_umap"),
        (CHAR, "save_char"),
        (IMC, "save_imc"),
        (GM, "save_gm"),
        (PV, "save_pv"),
    ):
        try:
            if unreal.EditorAssetLibrary.does_asset_exist(apath):
                results[key] = bool(unreal.EditorAssetLibrary.save_asset(apath))
            else:
                results[key] = "missing"
        except Exception as e:
            results[key] = "exc:" + str(e)
    return results


def file_mtimes():
    paths = [
        r"E:\UE\FarmSim25D\Content\TopDown\Lvl_TopDown.umap",
        r"E:\UE\FarmSim25D\Content\TopDown\Blueprints\BP_TopDownCharacter.uasset",
        r"E:\UE\FarmSim25D\Content\TopDown\Input\IMC_Default.uasset",
        r"E:\UE\FarmSim25D\Content\Farm\Grid\BP_GridManager.uasset",
        r"E:\UE\FarmSim25D\Content\Farm\Grid\BP_PlotVisual.uasset",
    ]
    out = {}
    for p in paths:
        if os.path.exists(p):
            ts = os.path.getmtime(p)
            out[os.path.basename(p)] = {
                "mtime_epoch": ts,
                "mtime_local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            }
        else:
            out[os.path.basename(p)] = "MISSING"
    return out


def focus_viewport():
    # Look toward +Y (house) to match play cam yaw=90
    center = unreal.Vector(FARM * CELL * 0.5, FARM * CELL * 0.5, 0.0)
    try:
        look_from = unreal.Vector(center.x, center.y - 2800.0, 2200.0)
        unreal.EditorLevelLibrary.set_level_viewport_camera_info(
            look_from, unreal.Rotator(-40.0, 90.0, 0.0))
        return True
    except Exception as e:
        log("viewport " + str(e))
        return False


def main():
    log("=== START restore layout+interact+persist ===")
    try:
        log("world=" + str(unreal.EditorLevelLibrary.get_editor_world().get_path_name()))
    except Exception as e:
        log("world fail " + str(e))

    cam = fix_springarm()
    log("cam: " + cam)

    imc = ensure_imc()
    log("imc: " + str(imc))

    cam_rel_ok, move_info = False, []
    try:
        cam_rel_ok, move_info = verify_cam_relative()
    except Exception as e:
        log("cam_relative FAIL " + str(e))
    log("cam_relative={} move={}".format(cam_rel_ok, move_info))

    char_actions = {}
    try:
        char_actions = verify_char_actions()
    except Exception as e:
        log("char_actions FAIL " + str(e))
    log("char_actions: " + str(char_actions))

    viz = {}
    try:
        viz = verify_visualize_cell()
    except Exception as e:
        log("visualize FAIL " + str(e))
    log("visualize: " + str(viz))

    floor = ensure_floor()
    log("floor: " + str(floor))

    ps = ensure_playerstart()
    log("PlayerStart: " + str(ps))

    leftover = count_proto()
    log("proto_leftover={} sample={}".format(len(leftover), leftover[:20]))

    focus_viewport()
    n = mark_dirty()
    log("mark_dirty actors=" + str(n))

    save1 = force_save()
    log("save1: " + str(save1))
    try:
        time.sleep(0.3)
    except Exception:
        pass
    save2 = force_save()
    log("save2: " + str(save2))

    # Re-verify camera + IMC after save
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    final_arm = "?"
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if obj and "SpringArm" in obj.get_class().get_name():
            r = obj.get_editor_property("relative_rotation")
            final_arm = "pitch={:.0f} yaw={:.0f} roll={:.0f} arm={} ortho={}".format(
                r.pitch, r.yaw, r.roll, CAM_ARM, CAM_ORTHO)

    imc2 = unreal.EditorAssetLibrary.load_asset(IMC)
    txt = imc2.get_editor_property("default_key_mappings").export_text()
    imc_final = {
        "E": "Key=E" in txt and "IA_Interact" in txt,
        "F": "Key=F" in txt and "IA_Plant" in txt,
        "R": "Key=R" in txt and "IA_Water" in txt,
        "G": "Key=G" in txt and "IA_Grow" in txt,
        "H": "Key=H" in txt and "IA_Harvest" in txt,
        "WASD": all(("Key=" + k) in txt for k in "WASD"),
    }

    mtimes = file_mtimes()
    vmf = sum(1 for a in eas().get_all_level_actors() if (a.get_actor_label() or "").startswith("VMF_"))
    floor_ok = any((a.get_actor_label() or "") == FLOOR_LABEL for a in eas().get_all_level_actors())

    summary = {
        "camera": final_arm,
        "compose_note": "yaw=+90 => house TOP (high Y); water RIGHT (low X); trees LEFT (high X). "
                        "house-top+water-left impossible without scene rotate.",
        "IMC": imc_final,
        "cam_relative_WASD": cam_rel_ok,
        "char_actions": char_actions,
        "VisualizeCell": viz,
        "PlayerStart": ps,
        "proto_leftover": len(leftover),
        "FarmCollisionFloor": floor_ok,
        "VMF": vmf,
        "save1": save1,
        "save2": save2,
        "mtimes": mtimes,
    }
    log("SUMMARY " + str(summary))
    log("USER: please File -> Save All once more after this script.")
    log("=== END ===")


if __name__ == "__main__":
    main()
else:
    main()
