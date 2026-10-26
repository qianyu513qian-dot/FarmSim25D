# -*- coding: utf-8 -*-
"""Re-enable character facing along move direction. Do NOT touch SpringArm / ortho / camera yaw.

Re-run: python Content/Python/run_remote.py Content/Python/phase_face_move.py

On BP_TopDownCharacter:
  - CharacterMovement.bOrientRotationToMovement = True
  - CharacterMovement.RotationRate.Yaw ~= 640
  - CharacterMovement.bUseControllerDesiredRotation = False (typical with Orient)
  - Character.bUseControllerRotationYaw = False (so Orient owns yaw)
  - Character.bUseControllerRotationPitch/Roll = False
Camera / SpringArm / ortho left untouched.
"""
import unreal
import os
import time

TAG = "[FACE_MOVE] "


def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)


CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
CHAR_DISK = r"E:\UE\FarmSim25D\Content\TopDown\Blueprints\BP_TopDownCharacter.uasset"
ROT_YAW = 640.0


def _set_bool(obj, names, value, label, report):
    for prop in names:
        try:
            obj.set_editor_property(prop, value)
            got = obj.get_editor_property(prop)
            report.append("{}={} (via {})".format(label, got, prop))
            return True
        except Exception:
            continue
    report.append("{} FAILED names={}".format(label, names))
    return False


def _set_rot_rate(cmc, yaw, report):
    # UE: RotationRate is a Rotator on CharacterMovementComponent
    for prop in ("rotation_rate", "RotationRate"):
        try:
            rr = cmc.get_editor_property(prop)
            rr.yaw = float(yaw)
            # keep pitch/roll as-is (usually 0)
            cmc.set_editor_property(prop, rr)
            got = cmc.get_editor_property(prop)
            report.append("RotationRate yaw={:.1f} pitch={:.1f} roll={:.1f} (via {})".format(
                got.yaw, got.pitch, got.roll, prop))
            return True
        except Exception as e:
            last = str(e)
    # Fallback: construct fresh Rotator
    try:
        rr = unreal.Rotator(0.0, float(yaw), 0.0)  # pitch, yaw, roll order varies
        cmc.set_editor_property("rotation_rate", rr)
        got = cmc.get_editor_property("rotation_rate")
        report.append("RotationRate yaw={:.1f} (fresh Rotator)".format(got.yaw))
        return True
    except Exception as e:
        report.append("RotationRate FAILED: {} / {}".format(last if "last" in dir() else "", e))
        return False


def _read_cam_snapshot(bp, report):
    """Read-only: prove we did not change camera."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        if "SpringArm" in cname:
            try:
                r = obj.get_editor_property("relative_rotation")
                arm = obj.get_editor_property("target_arm_length")
                report.append("CAM_SNAP SpringArm p={:.0f} y={:.0f} arm={}".format(
                    r.pitch, r.yaw, arm))
            except Exception as e:
                report.append("CAM_SNAP SpringArm err " + str(e))
        if cname == "CameraComponent":
            try:
                report.append("CAM_SNAP ortho={}".format(
                    obj.get_editor_property("ortho_width")))
            except Exception:
                pass


def apply_face_move():
    report = []
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    if not bp:
        report.append("NO_BP")
        return report

    # Snapshot camera BEFORE (and we never write to it)
    _read_cam_snapshot(bp, report)

    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    cmc_hit = False
    char_cdo_hit = False

    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(h)
        obj = lib.get_object_for_blueprint(data, bp)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        name = str(lib.get_variable_name(data))

        # Character Movement Component
        if ("CharacterMovement" in cname) or name in ("CharacterMovement", "CharMoveComp"):
            cmc_hit = True
            _set_bool(
                obj,
                ("orient_rotation_to_movement", "b_orient_rotation_to_movement"),
                True,
                "OrientRotationToMovement",
                report,
            )
            _set_bool(
                obj,
                ("use_controller_desired_rotation", "b_use_controller_desired_rotation"),
                False,
                "UseControllerDesiredRotation",
                report,
            )
            _set_rot_rate(obj, ROT_YAW, report)

        # DefaultSceneRoot / self Character for UseControllerRotation*
        # On Blueprint Generated Class default object, these live on the Character itself.
        if name in ("DefaultSceneRoot", "CapsuleComponent", "CollisionCylinder") or cname in (
            "CapsuleComponent",
        ):
            pass  # not here

    # Character pawn class defaults: UseControllerRotationYaw etc.
    try:
        # Generated class CDO
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen) if gen else None
        if cdo is None:
            # alternate API
            try:
                cdo = unreal.get_default_object(bp.generated_class())
            except Exception:
                cdo = None
        if cdo is not None:
            char_cdo_hit = True
            _set_bool(
                cdo,
                ("use_controller_rotation_yaw", "b_use_controller_rotation_yaw"),
                False,
                "UseControllerRotationYaw",
                report,
            )
            _set_bool(
                cdo,
                ("use_controller_rotation_pitch", "b_use_controller_rotation_pitch"),
                False,
                "UseControllerRotationPitch",
                report,
            )
            _set_bool(
                cdo,
                ("use_controller_rotation_roll", "b_use_controller_rotation_roll"),
                False,
                "UseControllerRotationRoll",
                report,
            )
            # Also try CMC via CDO accessor
            try:
                cmc = cdo.get_editor_property("character_movement")
                if cmc is None:
                    cmc = getattr(cdo, "character_movement", None)
                if cmc is not None and not cmc_hit:
                    cmc_hit = True
                    _set_bool(
                        cmc,
                        ("orient_rotation_to_movement", "b_orient_rotation_to_movement"),
                        True,
                        "OrientRotationToMovement(CDO)",
                        report,
                    )
                    _set_rot_rate(cmc, ROT_YAW, report)
            except Exception as e:
                report.append("CDO.cmc access: " + str(e))
        else:
            report.append("CDO missing")
    except Exception as e:
        report.append("CDO exc: " + str(e))

    # Also try SimpleConstructionScript / Blueprint Editor Library path on self component
    # Some projects store UseControllerRotation* as SCS overrides on the root actor template.
    try:
        for h in sds.k2_gather_subobject_data_for_blueprint(bp):
            data = lib.get_data(h)
            obj = lib.get_object_for_blueprint(data, bp)
            if not obj:
                continue
            # Actor template often exposed as the Blueprint's "self" / class default via is_root
            try:
                is_root = bool(lib.is_handle_valid(h)) and (
                    str(lib.get_variable_name(data)) in ("DefaultSceneRoot", "None", "self", "")
                    or "Character" in obj.get_class().get_name()
                )
            except Exception:
                is_root = False
            cname = obj.get_class().get_name()
            if ("TopDownCharacter" in cname) or ("Character" == cname) or (
                "Character" in cname and "Movement" not in cname and "Mesh" not in cname
            ):
                if "Movement" in cname:
                    continue
                _set_bool(
                    obj,
                    ("use_controller_rotation_yaw", "b_use_controller_rotation_yaw"),
                    False,
                    "UseControllerRotationYaw(sub)",
                    report,
                )
    except Exception as e:
        report.append("sub self yaw: " + str(e))

    report.append("cmc_hit={} char_cdo_hit={}".format(cmc_hit, char_cdo_hit))

    try:
        bp.modify()
    except Exception as e:
        report.append("bp.modify " + str(e))

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        report.append("compiled=True")
    except Exception as e:
        report.append("compile " + str(e))

    ok = unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
    report.append("save_char only_if_is_dirty=False -> {}".format(ok))

    try:
        okd = unreal.EditorAssetLibrary.save_directory("/Game/TopDown/Blueprints", True, True)
        report.append("save_bp_dir={}".format(okd))
    except Exception as e:
        report.append("save_bp_dir " + str(e))

    try:
        okp = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        report.append("save_dirty={}".format(okp))
    except Exception as e:
        report.append("save_dirty " + str(e))

    # Re-read final values from CMC + CDO
    bp2 = unreal.EditorAssetLibrary.load_asset(CHAR)
    sds2 = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib2 = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sds2.k2_gather_subobject_data_for_blueprint(bp2):
        data = lib2.get_data(h)
        obj = lib2.get_object_for_blueprint(data, bp2)
        if not obj:
            continue
        cname = obj.get_class().get_name()
        if "CharacterMovement" in cname:
            for prop in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    report.append("VERIFY Orient={}".format(obj.get_editor_property(prop)))
                    break
                except Exception:
                    pass
            for prop in ("use_controller_desired_rotation", "b_use_controller_desired_rotation"):
                try:
                    report.append("VERIFY UseCtrlDesired={}".format(obj.get_editor_property(prop)))
                    break
                except Exception:
                    pass
            for prop in ("rotation_rate", "RotationRate"):
                try:
                    rr = obj.get_editor_property(prop)
                    report.append("VERIFY RotationRate yaw={:.1f}".format(rr.yaw))
                    break
                except Exception:
                    pass
        if "SpringArm" in cname:
            try:
                r = obj.get_editor_property("relative_rotation")
                arm = obj.get_editor_property("target_arm_length")
                report.append("VERIFY_CAM SpringArm p={:.0f} y={:.0f} arm={} (untouched)".format(
                    r.pitch, r.yaw, arm))
            except Exception:
                pass
        if cname == "CameraComponent":
            try:
                report.append("VERIFY_CAM ortho={} (untouched)".format(
                    obj.get_editor_property("ortho_width")))
            except Exception:
                pass

    try:
        gen = bp2.generated_class()
        cdo = unreal.get_default_object(gen) if gen else None
        if cdo is not None:
            for prop in ("use_controller_rotation_yaw", "b_use_controller_rotation_yaw"):
                try:
                    report.append("VERIFY UseControllerRotationYaw={}".format(
                        cdo.get_editor_property(prop)))
                    break
                except Exception:
                    pass
    except Exception as e:
        report.append("VERIFY CDO " + str(e))

    if os.path.exists(CHAR_DISK):
        ts = os.path.getmtime(CHAR_DISK)
        report.append("mtime BP_TopDownCharacter = {}".format(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))))
    else:
        report.append("MISSING disk asset")

    return report


def main():
    log("=== START ===")
    for line in apply_face_move():
        log(line)
    log("=== END ===")


main()
