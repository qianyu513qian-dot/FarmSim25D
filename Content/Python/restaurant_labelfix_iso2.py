# -*- coding: utf-8 -*-
"""Probe + hard-fix RestLabel TextRender world orientation for iso camera."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"labels": {}, "errors": [], "cam": {}}

FACE_PITCH = 50.0
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

def v3(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]

def r3(r):
    return [round(r.pitch, 2), round(r.yaw, 2), round(r.roll, 2)]

def get_rel_rot(tr):
    try:
        return tr.get_editor_property("relative_rotation")
    except Exception:
        try:
            return tr.relative_rotation
        except Exception:
            return unreal.Rotator(0, 0, 0)

def set_rel_rot(tr, rot):
    try:
        tr.set_editor_property("relative_rotation", rot)
        return True
    except Exception:
        pass
    try:
        tr.set_relative_rotation(rot, False, False)
        return True
    except Exception:
        pass
    try:
        tr.relative_rotation = rot
        return True
    except Exception as e:
        return False

font = unreal.EditorAssetLibrary.load_asset(FONT_PATH) if unreal.EditorAssetLibrary.does_asset_exist(FONT_PATH) else None
actors = { (a.get_actor_label() or ""): a for a in eas.get_all_level_actors() }

desired = unreal.Rotator(FACE_PITCH, FACE_YAW, 0.0)
REPORT["desired_fwd"] = v3(desired.get_forward_vector())
REPORT["desired_rot"] = r3(desired)

toward_cam = unreal.Vector(-0.542, 0.542, 0.643)

for key, cn in CN.items():
    name = "RestLabel_" + key
    tgt_name = TARGET[key]
    la = actors.get(name)
    tgt = actors.get(tgt_name)
    info = {"name": name}
    if not tgt:
        REPORT["errors"].append("no target " + tgt_name)
        continue
    if not la:
        REPORT["errors"].append("no label " + name)
        continue

    tr = la.get_component_by_class(unreal.TextRenderComponent)
    if not tr:
        comps = list(la.get_components_by_class(unreal.TextRenderComponent))
        tr = comps[0] if comps else None
    if not tr:
        REPORT["errors"].append("no tr " + name)
        continue

    info["before"] = {
        "actor_rot": r3(la.get_actor_rotation()),
        "actor_loc": v3(la.get_actor_location()),
        "comp_rel_rot": r3(get_rel_rot(tr)),
        "comp_world_rot": r3(tr.get_component_rotation()),
        "comp_fwd": v3(tr.get_forward_vector()),
        "world_size": float(tr.get_editor_property("world_size")),
        "text_cps": [hex(ord(c)) for c in str(tr.get_editor_property("text"))],
    }

    set_rel_rot(tr, unreal.Rotator(0, 0, 0))

    tloc = tgt.get_actor_location()
    new_loc = unreal.Vector(tloc.x, tloc.y, tloc.z + Z_OFF)
    la.set_actor_location(new_loc, False, False)
    la.set_actor_rotation(desired, False)

    try:
        tr.set_world_location(new_loc, False, False)
    except Exception:
        pass
    try:
        tr.set_world_rotation(desired, False, False)
    except Exception as e:
        info["world_rot_err"] = str(e)

    try:
        tr.set_editor_property("text", cn)
    except Exception:
        try:
            tr.set_text(cn)
        except Exception as e:
            REPORT["errors"].append(name + " text " + str(e))
    try:
        tr.set_editor_property("world_size", SIZE)
    except Exception:
        pass
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
    if font:
        try:
            tr.set_editor_property("font", font)
        except Exception:
            pass
    try:
        la.set_actor_hidden_in_game(False)
        la.set_is_temporarily_hidden_in_editor(False)
        tr.set_visibility(True, True)
        tr.set_hidden_in_game(False)
    except Exception:
        pass

    cf = tr.get_forward_vector()
    dot = cf.x * toward_cam.x + cf.y * toward_cam.y + cf.z * toward_cam.z
    info["dot_toward_cam"] = round(dot, 3)
    info["after"] = {
        "actor_rot": r3(la.get_actor_rotation()),
        "actor_loc": v3(la.get_actor_location()),
        "comp_rel_rot": r3(get_rel_rot(tr)),
        "comp_world_rot": r3(tr.get_component_rotation()),
        "comp_fwd": v3(cf),
        "world_size": float(tr.get_editor_property("world_size")),
        "text_cps": [hex(ord(c)) for c in str(tr.get_editor_property("text"))],
        "font": (tr.get_editor_property("font").get_path_name() if tr.get_editor_property("font") else None),
    }

    if dot < 0.2:
        flip = unreal.Rotator(FACE_PITCH, FACE_YAW + 180.0, 0.0)
        set_rel_rot(tr, unreal.Rotator(0, 0, 0))
        la.set_actor_rotation(flip, False)
        try:
            tr.set_world_rotation(flip, False, False)
        except Exception:
            pass
        cf2 = tr.get_forward_vector()
        dot2 = cf2.x * toward_cam.x + cf2.y * toward_cam.y + cf2.z * toward_cam.z
        info["flipped"] = True
        info["after_flip"] = {
            "actor_rot": r3(la.get_actor_rotation()),
            "comp_world_rot": r3(tr.get_component_rotation()),
            "comp_fwd": v3(cf2),
            "dot_toward_cam": round(dot2, 3),
        }
    else:
        info["flipped"] = False

    REPORT["labels"][name] = info

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

out = r"E:\UE\FarmSim25D\Saved\restaurant_labelfix_iso2.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))

def sum_one(v):
    final = v.get("after_flip") or v.get("after") or {}
    return {
        "dot": final.get("dot_toward_cam", v.get("dot_toward_cam")),
        "flipped": v.get("flipped"),
        "size": (v.get("after") or {}).get("world_size"),
        "loc": (v.get("after") or {}).get("actor_loc"),
        "rot": final.get("actor_rot") or (v.get("after") or {}).get("actor_rot"),
        "fwd": final.get("comp_fwd") or (v.get("after") or {}).get("comp_fwd"),
        "cps": (v.get("after") or {}).get("text_cps"),
        "before_rot": (v.get("before") or {}).get("actor_rot"),
    }

print(json.dumps({
    "level_saved": ok,
    "errors": REPORT["errors"],
    "desired_rot": REPORT["desired_rot"],
    "desired_fwd": REPORT["desired_fwd"],
    "summary": {k: sum_one(v) for k, v in REPORT["labels"].items()},
}, ensure_ascii=False, indent=2))
