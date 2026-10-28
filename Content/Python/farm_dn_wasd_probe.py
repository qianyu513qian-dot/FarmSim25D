# -*- coding: utf-8 -*-
"""Dump WASD/Move/IMC/SpringArm/Orient state for FarmSim25D."""
import unreal
import json

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
REPORT = {"ok": True}

def log(m):
    unreal.log("[WASD_PROBE] " + str(m))
    print("[WASD_PROBE] " + str(m))

bp = unreal.load_asset(CHAR)
imc = unreal.load_asset(IMC)
REPORT["char_status"] = str(bp.status) if bp else "MISSING"
REPORT["imc"] = bool(imc)

# IMC mappings text
try:
    mappings = imc.get_editor_property("mappings")
    rows = []
    for m in mappings:
        try:
            action = m.get_editor_property("action")
            key = m.get_editor_property("key")
            mods = m.get_editor_property("modifiers")
            mod_names = []
            for md in (mods or []):
                mod_names.append(md.get_class().get_name())
                try:
                    if hasattr(md, "get_editor_property"):
                        for pn in ("order", "Order"):
                            try:
                                mod_names[-1] += ":" + str(md.get_editor_property(pn))
                                break
                            except Exception:
                                pass
                except Exception:
                    pass
            an = action.get_name() if action else "?"
            rows.append({"action": an, "key": str(key), "mods": mod_names})
        except Exception as e:
            rows.append({"error": str(e)})
    REPORT["imc_mappings"] = rows
    # also export_text fallback
    try:
        REPORT["imc_export_has"] = {
            k: (("Key=" + k) in imc.get_editor_property("mappings").export_text() if False else None)
            for k in []
        }
    except Exception:
        pass
    txt = ""
    try:
        txt = imc.get_editor_property("mappings").export_text()
    except Exception:
        try:
            txt = str(mappings)
        except Exception:
            txt = ""
    REPORT["imc_keys"] = {k: (("Key=" + k) in txt or ("'" + k + "'") in txt or ('"' + k + '"') in txt) for k in list("WASDEFGH") + ["Up", "Down", "Left", "Right"]}
    REPORT["imc_txt_snip"] = txt[:1500]
except Exception as e:
    REPORT["imc_error"] = str(e)

# Subobjects: SpringArm, Camera, CMC, Character flags
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
subs = []
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    name = str(lib.get_variable_name(data))
    row = {"name": name, "class": cname}
    if "SpringArm" in cname:
        for p in ("relative_rotation", "target_arm_length", "use_pawn_control_rotation", "do_collision_test",
                  "inherit_pitch", "inherit_yaw", "inherit_roll"):
            try:
                v = obj.get_editor_property(p)
                row[p] = str(v)
            except Exception:
                pass
    if cname == "CameraComponent" or name == "Camera":
        for p in ("projection_mode", "ortho_width", "field_of_view", "relative_rotation"):
            try:
                row[p] = str(obj.get_editor_property(p))
            except Exception:
                pass
    if "CharacterMovement" in cname:
        for p in ("orient_rotation_to_movement", "use_controller_desired_rotation", "rotation_rate",
                  "max_walk_speed", "gravity_scale"):
            try:
                row[p] = str(obj.get_editor_property(p))
            except Exception:
                pass
    if cname.endswith("Character") or name in ("DefaultSceneRoot", "BP_TopDownCharacter_C", "Character"):
        for p in ("use_controller_rotation_yaw", "use_controller_rotation_pitch", "use_controller_rotation_roll"):
            try:
                row[p] = str(obj.get_editor_property(p))
            except Exception:
                pass
    if len(row) > 2:
        subs.append(row)
REPORT["subobjects"] = subs

# CDO flags
try:
    cdo = unreal.get_default_object(bp.generated_class())
    cdo_row = {}
    for p in ("use_controller_rotation_yaw", "use_controller_rotation_pitch", "use_controller_rotation_roll"):
        try:
            cdo_row[p] = str(cdo.get_editor_property(p))
        except Exception:
            pass
    cmc = cdo.get_component_by_class(unreal.CharacterMovementComponent)
    if cmc:
        for p in ("orient_rotation_to_movement", "use_controller_desired_rotation", "rotation_rate"):
            try:
                cdo_row["cmc_" + p] = str(cmc.get_editor_property(p))
            except Exception:
                pass
    REPORT["cdo"] = cdo_row
except Exception as e:
    REPORT["cdo_error"] = str(e)

# EventGraph Move / Enhanced Input
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
move_nodes = []
for n in ge.list_all_nodes():
    t = str(bel.get_node_title(n))
    interesting = any(s in t for s in (
        "Move", "IA_Move", "AddMovementInput", "Get Right Vector", "Get Forward Vector",
        "GetActorForward", "GetActorRight", "Break Vector", "Make Vector", "Get Control Rotation",
        "Get Camera", "SpringArm", "Enhanced Input", "InputAction", "Multiply", "Normalize",
        "Orient", "Set Actor Rotation"
    ))
    if not interesting:
        continue
    pins = []
    for p in bel.list_all_pins(n):
        try:
            val = p.get_pin_value()
        except Exception:
            val = ""
        links = []
        for c in p.list_connected_pins():
            try:
                links.append(str(bel.get_node_title(c.get_owning_node())) + "." + str(c.get_pin_name()))
            except Exception:
                links.append("?")
        pins.append({"name": str(p.get_pin_name()), "dir": str(p.get_pin_direction()), "value": str(val)[:80], "links": links})
    move_nodes.append({"title": t, "class": n.get_class().get_name(), "pins": pins})
REPORT["move_nodes"] = move_nodes

# FarmClock input steal?
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    clocks = [a for a in actors if a.get_class().get_name().startswith("FarmClock")]
    REPORT["farmclock_count"] = len(clocks)
except Exception as e:
    REPORT["farmclock_error"] = str(e)

out = unreal.Paths.project_saved_dir() + "/DayNight/wasd_probe.json"
unreal.Paths.make_standard_filename(out)
from pathlib import Path
Path(out).parent.mkdir(parents=True, exist_ok=True)
Path(out).write_text(json.dumps(REPORT, default=str, indent=2), encoding="utf-8")
REPORT = {"report_file": out, "imc_keys": REPORT.get("imc_keys"), "cdo": REPORT.get("cdo"),
          "sub_summary": [{k: v for k, v in s.items() if k in ("name", "class", "relative_rotation", "target_arm_length", "projection_mode", "ortho_width", "field_of_view", "orient_rotation_to_movement", "use_controller_rotation_yaw")} for s in REPORT.get("subobjects", [])],
          "move_titles": [m["title"] for m in REPORT.get("move_nodes", [])],
          "imc_mapping_count": len(REPORT.get("imc_mappings", [])),
          "farmclock_count": REPORT.get("farmclock_count")}
log("DONE " + str(REPORT.get("move_titles")))
