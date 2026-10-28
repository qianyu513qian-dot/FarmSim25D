# -*- coding: utf-8 -*-
"""Fix RestLabel_* to face isometric camera. UE5.8 Rotator(pos) is (roll,pitch,yaw) — use keywords."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"steps": [], "errors": [], "labels": {}}

# Camera SpringArm ~ Pitch=-40 Yaw=-45 => toward-camera Pitch=+40..50 Yaw=+135
FACE_PITCH = 45.0
FACE_YAW = 135.0
SIZE = 180.0
Z_OFF = 150.0
FONT_PATH = "/Game/Farm/Restaurant/Font_SimHei_TR"

CN = {
    "OpenSign": "\u5f00\u4e1a\u724c",
    "Stove": "\u7076\u53f0",
    "Table1": "\u9910\u684c1",
    "Table2": "\u9910\u684c2",
    "Trash": "\u5783\u573e\u6876",
}
TARGET = {
    "OpenSign": "Restaurant_OpenSign",
    "Stove": "Restaurant_Stove",
    "Table1": "Restaurant_Table1",
    "Table2": "Restaurant_Table2",
    "Trash": "Restaurant_Trash",
}
COLORS = {
    "OpenSign": (255, 250, 40),
    "Stove": (255, 140, 30),
    "Table1": (50, 240, 255),
    "Table2": (80, 255, 120),
    "Trash": (255, 255, 255),
}

def log(m):
    unreal.log("[REST_ISO3] " + str(m))
    REPORT["steps"].append(str(m))

def rr(r):
    return [round(r.pitch, 2), round(r.yaw, 2), round(r.roll, 2)]

def vv(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]

def make_rot(pitch, yaw, roll=0.0):
    # CRITICAL: positional Rotator() in this engine build is (roll,pitch,yaw)
    return unreal.Rotator(pitch=float(pitch), yaw=float(yaw), roll=float(roll))

font = None
if unreal.EditorAssetLibrary.does_asset_exist(FONT_PATH):
    font = unreal.EditorAssetLibrary.load_asset(FONT_PATH)
    log("font " + FONT_PATH + " " + font.get_class().get_name())

actors = {(a.get_actor_label() or ""): a for a in eas.get_all_level_actors()}
desired = make_rot(FACE_PITCH, FACE_YAW, 0.0)
log("desired_rot(p,y,r)={} fwd={}".format(rr(desired), vv(desired.get_forward_vector())))

toward_cam = unreal.Vector(-0.542, 0.542, 0.643)

for key, cn in CN.items():
    name = "RestLabel_" + key
    tgt = actors.get(TARGET[key])
    la = actors.get(name)
    if not tgt:
        REPORT["errors"].append("missing " + TARGET[key])
        continue
    if not la:
        # spawn facing correctly
        tloc = tgt.get_actor_location()
        spawn_loc = unreal.Vector(tloc.x, tloc.y, tloc.z + Z_OFF)
        la = eas.spawn_actor_from_class(unreal.TextRenderActor, spawn_loc, desired)
        if not la:
            REPORT["errors"].append("spawn fail " + name)
            continue
        la.set_actor_label(name)
        try:
            la.set_folder_path("Restaurant/Labels")
        except Exception:
            pass
        actors[name] = la
        log("spawned " + name)

    tr = la.get_component_by_class(unreal.TextRenderComponent)
    if not tr:
        comps = list(la.get_components_by_class(unreal.TextRenderComponent))
        tr = comps[0] if comps else None
    if not tr:
        REPORT["errors"].append("no tr " + name)
        continue

    before = {"actor": rr(la.get_actor_rotation()), "fwd": vv(tr.get_forward_vector()),
              "size": float(tr.world_size), "cps": [hex(ord(c)) for c in str(tr.text)]}

    # Reset then apply keyword rotator
    try:
        tr.reset_relative_transform()
    except Exception:
        try:
            tr.set_relative_rotation(make_rot(0, 0, 0), False, True)
        except Exception:
            pass

    tloc = tgt.get_actor_location()
    new_loc = unreal.Vector(tloc.x, tloc.y, tloc.z + Z_OFF)
    # Prefer look-at for robust facing
    cam_approx = unreal.Vector(new_loc.x - 800.0, new_loc.y + 800.0, new_loc.z + 900.0)
    look = unreal.MathLibrary.find_look_at_rotation(new_loc, cam_approx)
    # Blend: use look but clamp pitch around FACE_PITCH
    face = make_rot(FACE_PITCH, look.yaw, 0.0)

    la.set_actor_location(new_loc, False, True)
    la.set_actor_rotation(face, True)
    try:
        tr.set_world_location_and_rotation(new_loc, face, False, True)
    except Exception:
        try:
            tr.set_world_rotation(face, False, True)
        except Exception as e:
            REPORT["errors"].append(name + " world_rot " + str(e))

    # Text / size / color / font
    try:
        tr.set_text(cn)
    except Exception:
        tr.set_editor_property("text", cn)
    try:
        tr.set_world_size(SIZE)
    except Exception:
        tr.set_editor_property("world_size", SIZE)
    try:
        tr.set_editor_property("horizontal_alignment", unreal.HorizontalTextAligment.HTA_CENTER)
    except Exception:
        pass
    try:
        tr.set_editor_property("vertical_alignment", unreal.VerticalTextAligment.VTT_CENTER)
    except Exception:
        pass
    rgb = COLORS[key]
    try:
        tr.set_text_render_color(unreal.Color(rgb[0], rgb[1], rgb[2], 255))
    except Exception:
        pass
    if font and font.get_class().get_name() == "Font":
        try:
            tr.set_font(font)
        except Exception:
            try:
                tr.set_editor_property("font", font)
            except Exception as e:
                REPORT["errors"].append(name + " font " + str(e))
    try:
        tr.always_render_as_text = True
    except Exception:
        try:
            tr.set_editor_property("always_render_as_text", True)
        except Exception:
            pass
    try:
        la.set_actor_hidden_in_game(False)
        la.set_is_temporarily_hidden_in_editor(False)
        tr.set_visibility(True, True)
        tr.set_hidden_in_game(False)
    except Exception:
        pass

    fwd = tr.get_forward_vector()
    dot = fwd.x * toward_cam.x + fwd.y * toward_cam.y + fwd.z * toward_cam.z
    # If facing away, yaw += 180
    flipped = False
    if dot < 0.15:
        flipped = True
        face2 = make_rot(FACE_PITCH, face.yaw + 180.0, 0.0)
        la.set_actor_rotation(face2, True)
        try:
            tr.set_world_rotation(face2, False, True)
        except Exception:
            pass
        fwd = tr.get_forward_vector()
        dot = fwd.x * toward_cam.x + fwd.y * toward_cam.y + fwd.z * toward_cam.z

    after = {
        "actor": rr(la.get_actor_rotation()),
        "world": rr(tr.get_world_rotation()),
        "fwd": vv(fwd),
        "dot_toward_cam": round(dot, 3),
        "flipped": flipped,
        "size": float(tr.world_size),
        "loc": [round(new_loc.x,1), round(new_loc.y,1), round(new_loc.z,1)],
        "cps": [hex(ord(c)) for c in str(tr.text)],
        "font": (tr.font.get_path_name() if tr.font else None),
        "visible": bool(tr.is_visible()),
    }
    REPORT["labels"][name] = {"before": before, "after": after}
    log("{} rot={} fwd={} dot={} size={}".format(name, after["actor"], after["fwd"], after["dot_toward_cam"], after["size"]))

ok = False
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    ok = True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        ok = True
    except Exception as e:
        REPORT["errors"].append("save " + str(e))
REPORT["level_saved"] = ok
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception:
    pass

tips = ["{}@{}".format(CN[k], REPORT["labels"]["RestLabel_"+k]["after"]["loc"]) for k in CN if "RestLabel_"+k in REPORT["labels"]]
log("LOOK south-bridge east: " + " | ".join(tips))

outp = r"E:\UE\FarmSim25D\Saved\restaurant_labelfix_iso3.json"
open(outp, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps({
    "level_saved": ok,
    "errors": REPORT["errors"],
    "desired": rr(desired),
    "summary": {k: v["after"] for k, v in REPORT["labels"].items()},
}, ensure_ascii=False, indent=2))
