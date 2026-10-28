# -*- coding: utf-8 -*-
"""Reposition restaurant furniture + add in-world Chinese name labels (TextRender).
Surgical: move existing Restaurant_* / RestChair_* only; no BP graph wipe; no farm actors.
"""
import unreal
import json
import os

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"steps": [], "moved": [], "labels": [], "errors": [], "font": None}

FONT_PATH = "/Game/Farm/Restaurant/Font_SimHei"
FONT_SRC = r"C:\Windows\Fonts\simhei.ttf"
LABEL_ACTORS = {
    "Restaurant_OpenSign": ("开业牌", (1.0, 0.95, 0.2)),   # yellow
    "Restaurant_Stove": ("灶台", (1.0, 0.45, 0.15)),       # orange
    "Restaurant_Table1": ("餐桌1", (0.35, 0.85, 1.0)),     # cyan
    "Restaurant_Table2": ("餐桌2", (0.35, 1.0, 0.55)),     # green
    "Restaurant_Trash": ("垃圾桶", (0.75, 0.75, 0.75)),    # gray
}
# Spaced south-dock strip: OpenSign west(门口), dining south, kitchen north
# Centers >= ~230 apart so E range 200 is less ambiguous when standing at a prop.
NEW_LOC = {
    "Restaurant_OpenSign": (1680.0, 500.0),   # 门口 / bridge approach
    "Restaurant_Table1":   (1820.0, 300.0),   # dining south
    "Restaurant_Table2":   (2080.0, 300.0),   # dining SE
    "Restaurant_Stove":    (2080.0, 700.0),   # kitchen NE
    "Restaurant_Trash":    (1780.0, 700.0),   # kitchen NW, clear of stove
    "Restaurant_Manager":  (1900.0, 500.0),   # hidden logic
    "RestChair_t1a":       (1820.0, 230.0),
    "RestChair_t1b":       (1740.0, 300.0),
    "RestChair_t2a":       (2080.0, 230.0),
    "RestChair_t2b":       (2160.0, 300.0),
}
INTERACT_CN = {
    "Restaurant_OpenSign": "开业牌",
    "Restaurant_Stove": "灶台",
    "Restaurant_Table1": "餐桌1",
    "Restaurant_Table2": "餐桌2",
    "Restaurant_Trash": "垃圾桶",
}
TEXT_WORLD_SIZE = 48.0
TEXT_Z_OFFSET = 90.0  # float above prop

def log(m):
    unreal.log("[REST_LAYOUT] " + str(m))
    REPORT["steps"].append(str(m))

def ensure_font():
    if unreal.EditorAssetLibrary.does_asset_exist(FONT_PATH):
        font = unreal.EditorAssetLibrary.load_asset(FONT_PATH)
        REPORT["font"] = FONT_PATH + " (existing)"
        log("font_existing")
        return font
    if not os.path.isfile(FONT_SRC):
        REPORT["errors"].append("missing font file " + FONT_SRC)
        return None
    task = unreal.AssetImportTask()
    task.filename = FONT_SRC
    task.destination_path = "/Game/Farm/Restaurant"
    task.destination_name = "Font_SimHei"
    task.replace_existing = True
    task.automated = True
    task.save = True
    try:
        task.options = None
    except Exception:
        pass
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    # Font import may create FontFace + Font; try several paths
    candidates = [
        FONT_PATH,
        "/Game/Farm/Restaurant/Font_SimHei",
        "/Game/Farm/Restaurant/simhei",
        "/Game/Farm/Restaurant/SimHei",
    ]
    # also scan folder
    try:
        assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant", recursive=False)
        for a in assets:
            if "simhei" in a.lower() or "SimHei" in a or "Font_SimHei" in a:
                candidates.append(a.split(".")[0])
    except Exception as e:
        log("list_assets " + str(e))
    for p in candidates:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            font = unreal.EditorAssetLibrary.load_asset(p)
            # Prefer actual Font over FontFace
            cn = font.get_class().get_name() if font else ""
            REPORT["font_candidates"] = candidates
            if "Font" in cn and "Face" not in cn:
                REPORT["font"] = p + " class=" + cn
                log("font_imported " + p)
                return font
    # fallback: first existing
    for p in candidates:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            font = unreal.EditorAssetLibrary.load_asset(p)
            REPORT["font"] = p + " class=" + (font.get_class().get_name() if font else "?")
            log("font_fallback " + p)
            return font
    REPORT["errors"].append("font import failed; will use default TextRender font")
    return None

def find_actors():
    by_label = {}
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("Restaurant_") or lab.startswith("RestChair_") or lab.startswith("RestLabel_"):
            by_label[lab] = a
    return by_label

def set_interact_label(actor, text):
    for k in ("InteractLabel", "interact_label"):
        try:
            actor.set_editor_property(k, text)
            return True
        except Exception:
            pass
    return False

def move_keep_z(actor, xy, z_override=None):
    loc = actor.get_actor_location()
    z = loc.z if z_override is None else z_override
    # Manager stays elevated
    lab = actor.get_actor_label() or ""
    if lab == "Restaurant_Manager" and z_override is None:
        z = max(loc.z, 80.0)
    new = unreal.Vector(xy[0], xy[1], z)
    actor.set_actor_location(new, False, False)
    return [round(new.x,1), round(new.y,1), round(new.z,1)]

def destroy_old_labels(by_label):
    n = 0
    for lab, a in list(by_label.items()):
        if lab.startswith("RestLabel_"):
            eas.destroy_actor(a)
            n += 1
            del by_label[lab]
    log("cleared_old_labels={}".format(n))

def spawn_or_update_label(target_actor, key, cn_text, rgb, font):
    loc = target_actor.get_actor_location()
    label_loc = unreal.Vector(loc.x, loc.y, loc.z + TEXT_Z_OFFSET)
    label_name = "RestLabel_" + key.replace("Restaurant_", "")
    # Spawn TextRenderActor
    actor = eas.spawn_actor_from_class(unreal.TextRenderActor, label_loc, unreal.Rotator(0, 0, 0))
    if not actor:
        REPORT["errors"].append("spawn label fail " + label_name)
        return None
    actor.set_actor_label(label_name)
    actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
    tr = None
    try:
        tr = actor.get_component_by_class(unreal.TextRenderComponent)
    except Exception:
        pass
    if tr is None:
        try:
            tr = actor.text_render
        except Exception:
            pass
    if tr is None:
        comps = list(actor.get_components_by_class(unreal.TextRenderComponent))
        tr = comps[0] if comps else None
    if not tr:
        REPORT["errors"].append("no TextRenderComponent on " + label_name)
        return actor

    # Readable under ortho ~2800; horizontal facing camera-ish (yaw 0 is fine for top-down)
    try:
        tr.set_editor_property("text", cn_text)
    except Exception:
        try:
            tr.set_text(cn_text)
        except Exception as e:
            REPORT["errors"].append("set_text " + str(e))
    try:
        tr.set_editor_property("world_size", TEXT_WORLD_SIZE)
    except Exception:
        try:
            tr.set_world_size(TEXT_WORLD_SIZE)
        except Exception:
            pass
    try:
        tr.set_editor_property("horizontal_alignment", unreal.HorizontalTextAligment.HTA_CENTER)
    except Exception:
        try:
            tr.set_horizontal_alignment(unreal.HorizontalTextAligment.HTA_CENTER)
        except Exception:
            pass
    try:
        tr.set_editor_property("vertical_alignment", unreal.VerticalTextAligment.VTT_CENTER)
    except Exception:
        pass
    color = unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0)
    try:
        tr.set_editor_property("text_render_color", unreal.Color(
            int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255))
    except Exception:
        try:
            tr.set_text_render_color(unreal.Color(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255))
        except Exception:
            pass
    if font:
        try:
            tr.set_editor_property("font", font)
        except Exception as e:
            log("set font fail: " + str(e))
    # Face upward-ish for top-down: pitch -90 so text lies readable from above? 
    # For isometric top-down, text standing upright (default) with slight yaw often works.
    # Use billboard-like: rotate pitch so it's horizontal on ground plane facing up
    try:
        actor.set_actor_rotation(unreal.Rotator(90.0, 0.0, 0.0), False)
    except Exception:
        pass
    # Also try component relative
    try:
        tr.set_world_rotation(unreal.Rotator(90.0, 0.0, 0.0), False, False)
    except Exception:
        pass

    REPORT["labels"].append({
        "label": label_name, "text": cn_text,
        "loc": [round(label_loc.x,1), round(label_loc.y,1), round(label_loc.z,1)],
        "color": list(rgb),
    })
    log("label " + label_name + "=" + cn_text)
    return actor

# ---- run ----
log("start")
font = ensure_font()
by_label = find_actors()
REPORT["before"] = {k: [round(v.get_actor_location().x,1), round(v.get_actor_location().y,1), round(v.get_actor_location().z,1)]
                    for k, v in by_label.items() if not k.startswith("RestLabel_")}

destroy_old_labels(by_label)

# Move furniture
for key, xy in NEW_LOC.items():
    a = by_label.get(key)
    if not a:
        REPORT["errors"].append("missing actor " + key)
        continue
    newloc = move_keep_z(a, xy)
    REPORT["moved"].append({"label": key, "to": newloc})
    log("move {} -> {}".format(key, newloc))

# Refresh after move
by_label = find_actors()

# Chinese InteractLabel on interactables
for key, cn in INTERACT_CN.items():
    a = by_label.get(key)
    if not a:
        continue
    ok = set_interact_label(a, cn)
    log("InteractLabel {}={} ok={}".format(key, cn, ok))

# Spawn floating name labels
for key, (cn, rgb) in LABEL_ACTORS.items():
    a = by_label.get(key)
    if not a:
        REPORT["errors"].append("no target for label " + key)
        continue
    spawn_or_update_label(a, key, cn, rgb, font)

# Folder paths in outliner if supported
try:
    for key in list(NEW_LOC.keys()) + ["RestLabel_" + k.replace("Restaurant_", "") for k in LABEL_ACTORS]:
        a = find_actors().get(key)
        if not a:
            continue
        try:
            a.set_folder_path("Restaurant")
        except Exception:
            pass
except Exception as e:
    log("folder " + str(e))

# Final census
final = find_actors()
REPORT["after"] = {k: [round(v.get_actor_location().x,1), round(v.get_actor_location().y,1), round(v.get_actor_location().z,1)]
                   for k, v in final.items()}

# Save level
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["level_saved"] = True
    log("level_saved")
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        REPORT["level_saved"] = True
        log("level_saved_legacy")
    except Exception as e2:
        REPORT["level_saved"] = False
        REPORT["errors"].append("save fail " + str(e2))

# Save font asset if any
try:
    if font:
        unreal.EditorAssetLibrary.save_asset(font.get_path_name().split(".")[0])
except Exception:
    pass

out = r"E:\UE\FarmSim25D\Saved\restaurant_layout_labels.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
