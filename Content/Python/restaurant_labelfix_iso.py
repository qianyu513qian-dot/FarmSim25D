# -*- coding: utf-8 -*-
"""Surgical fix: reorient RestLabel_* TextRenders to face isometric camera.
Does NOT move furniture or touch cook/serve BPs.
Camera: SpringArm pitch ~-40, yaw ~-45, ortho ~2800.
TextRender faces local +X; face-up (pitch 90) is edge-on / invisible from iso.
"""
import unreal
import json
import math

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"steps": [], "errors": [], "labels": [], "before": {}, "after": {}}

# Unicode escapes — never rely on source file encoding
CN = {
    "OpenSign": "\u5f00\u4e1a\u724c",
    "Stove": "\u7076\u53f0",
    "Table1": "\u9910\u684c1",
    "Table2": "\u9910\u684c2",
    "Trash": "\u5783\u573e\u6876",
}
COLORS = {
    "OpenSign": (1.0, 0.98, 0.15),   # bright yellow
    "Stove": (1.0, 0.55, 0.1),
    "Table1": (0.2, 0.95, 1.0),
    "Table2": (0.3, 1.0, 0.45),
    "Trash": (1.0, 1.0, 1.0),
}
TARGET = {
    "OpenSign": "Restaurant_OpenSign",
    "Stove": "Restaurant_Stove",
    "Table1": "Restaurant_Table1",
    "Table2": "Restaurant_Table2",
    "Trash": "Restaurant_Trash",
}

# Face camera: cam look Pitch=-40 Yaw=-45 => toward-cam Pitch=+40 Yaw=+135
# Bump pitch a bit so glyphs read clearer under ortho
FACE_PITCH = 50.0
FACE_YAW = 135.0
FACE_ROLL = 0.0
TEXT_WORLD_SIZE = 160.0
TEXT_Z_OFFSET = 140.0
FONT_PATH = "/Game/Farm/Restaurant/Font_SimHei_TR"

def log(m):
    unreal.log("[REST_ISO_LABEL] " + str(m))
    REPORT["steps"].append(str(m))

def find_by_label():
    d = {}
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab:
            d[lab] = a
    return d

def get_tr(actor):
    try:
        tr = actor.get_component_by_class(unreal.TextRenderComponent)
    except Exception:
        tr = None
    if tr is None:
        comps = list(actor.get_components_by_class(unreal.TextRenderComponent))
        tr = comps[0] if comps else None
    return tr

def read_label_info(actor, tr):
    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    info = {
        "loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
        "rot": [round(rot.pitch, 1), round(rot.yaw, 1), round(rot.roll, 1)],
    }
    if tr:
        try:
            t = str(tr.get_editor_property("text"))
            info["text"] = t
            info["cps"] = [hex(ord(c)) for c in t]
        except Exception as e:
            info["text_err"] = str(e)
        try:
            info["world_size"] = float(tr.get_editor_property("world_size"))
        except Exception:
            pass
        try:
            f = tr.get_editor_property("font")
            info["font"] = f.get_path_name() if f else None
        except Exception:
            pass
        try:
            cr = tr.get_component_rotation()
            info["comp_rot"] = [round(cr.pitch, 1), round(cr.yaw, 1), round(cr.roll, 1)]
        except Exception:
            pass
    return info

actors = find_by_label()
font = None
if unreal.EditorAssetLibrary.does_asset_exist(FONT_PATH):
    font = unreal.EditorAssetLibrary.load_asset(FONT_PATH)
    log("font_loaded " + FONT_PATH + " class=" + (font.get_class().get_name() if font else "?"))
else:
    REPORT["errors"].append("missing font " + FONT_PATH)
    # try fallbacks
    for p in ("/Game/Farm/Restaurant/Font_SimHei", "/Game/Farm/Restaurant/Font_SimHei_Offline"):
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            font = unreal.EditorAssetLibrary.load_asset(p)
            log("font_fallback " + p)
            break

face_rot = unreal.Rotator(FACE_PITCH, FACE_YAW, FACE_ROLL)
log("face_rot P={} Y={} R={} world_size={} z_off={}".format(
    FACE_PITCH, FACE_YAW, FACE_ROLL, TEXT_WORLD_SIZE, TEXT_Z_OFFSET))

for key, cn in CN.items():
    label_name = "RestLabel_" + key
    target_name = TARGET[key]
    target = actors.get(target_name)
    la = actors.get(label_name)

    if not target:
        REPORT["errors"].append("missing target " + target_name)
        continue

    tloc = target.get_actor_location()
    desired_loc = unreal.Vector(tloc.x, tloc.y, tloc.z + TEXT_Z_OFFSET)

    # Snapshot before
    if la:
        tr0 = get_tr(la)
        REPORT["before"][label_name] = read_label_info(la, tr0)
    else:
        REPORT["before"][label_name] = None
        log("missing label, will spawn " + label_name)

    # Ensure actor exists
    if not la:
        la = eas.spawn_actor_from_class(unreal.TextRenderActor, desired_loc, face_rot)
        if not la:
            REPORT["errors"].append("spawn fail " + label_name)
            continue
        la.set_actor_label(label_name)
        try:
            la.set_folder_path("Restaurant/Labels")
        except Exception:
            pass
        actors[label_name] = la
        log("spawned " + label_name)
    else:
        la.set_actor_location(desired_loc, False, False)

    # Force actor + component rotation to face camera
    la.set_actor_rotation(face_rot, False)
    tr = get_tr(la)
    if not tr:
        REPORT["errors"].append("no TextRenderComponent " + label_name)
        continue

    try:
        tr.set_world_location_and_rotation(desired_loc, face_rot, False, False)
    except Exception:
        try:
            tr.set_world_rotation(face_rot, False, False)
        except Exception as e:
            REPORT["errors"].append("set_world_rotation " + label_name + " " + str(e))

    # Text content (unicode escapes)
    ok_text = False
    for setter in (
        lambda: tr.set_editor_property("text", cn),
        lambda: tr.set_text(cn),
    ):
        try:
            setter()
            ok_text = True
            break
        except Exception:
            pass

    try:
        tr.set_editor_property("world_size", TEXT_WORLD_SIZE)
    except Exception:
        try:
            tr.set_world_size(TEXT_WORLD_SIZE)
        except Exception as e:
            REPORT["errors"].append("world_size " + label_name + " " + str(e))

    try:
        tr.set_editor_property("horizontal_alignment", unreal.HorizontalTextAligment.HTA_CENTER)
    except Exception:
        pass
    try:
        tr.set_editor_property("vertical_alignment", unreal.VerticalTextAligment.VTT_CENTER)
    except Exception:
        pass

    # Bright color
    rgb = COLORS[key]
    col = unreal.Color(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255)
    try:
        tr.set_text_render_color(col)
    except Exception:
        try:
            tr.set_editor_property("text_render_color", col)
        except Exception as e:
            REPORT["errors"].append("color " + label_name + " " + str(e))

    if font and font.get_class().get_name() == "Font":
        try:
            tr.set_editor_property("font", font)
        except Exception as e:
            REPORT["errors"].append("font_set " + label_name + " " + str(e))

    # Ensure visible / not hidden
    try:
        la.set_actor_hidden_in_game(False)
        tr.set_visibility(True, True)
        tr.set_hidden_in_game(False, True)
    except Exception:
        pass

    # Try make material unlit bright if possible (skip if fails)
    try:
        # XAxis direction of text after rotation should roughly face camera
        fwd = face_rot.get_forward_vector()
        REPORT.setdefault("face_forward", [round(fwd.x, 3), round(fwd.y, 3), round(fwd.z, 3)])
    except Exception:
        pass

    info = read_label_info(la, tr)
    info["ok_text"] = ok_text
    info["cn"] = cn
    info["cn_cps"] = [hex(ord(c)) for c in cn]
    REPORT["after"][label_name] = info
    log("fixed {} rot=({},{},{}) size={} loc={}".format(
        label_name, FACE_PITCH, FACE_YAW, FACE_ROLL, TEXT_WORLD_SIZE, info["loc"]))

# Mark package dirty + save level
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception:
    pass

level_saved = False
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    level_saved = True
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        level_saved = True
    except Exception as e2:
        REPORT["errors"].append("save " + str(e) + " / " + str(e2))
REPORT["level_saved"] = level_saved

# One-shot editor log of look-here coords (PIE print would need BP; keep surgical)
tips = []
for key in CN:
    info = REPORT["after"].get("RestLabel_" + key) or {}
    tips.append("{} @ {}".format(CN[key], info.get("loc")))
log("LOOK_SOUTH_BRIDGE_EAST: " + " | ".join(tips))
unreal.log("[REST_ISO_LABEL] === Labels reoriented for iso cam. Look south-bridge restaurant zone. ===")

out = r"E:\UE\FarmSim25D\Saved\restaurant_labelfix_iso.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps({
    "level_saved": level_saved,
    "errors": REPORT["errors"],
    "face_rot": [FACE_PITCH, FACE_YAW, FACE_ROLL],
    "world_size": TEXT_WORLD_SIZE,
    "z_offset": TEXT_Z_OFFSET,
    "before": REPORT["before"],
    "after": REPORT["after"],
    "steps": REPORT["steps"][-12:],
}, ensure_ascii=False, indent=2))
