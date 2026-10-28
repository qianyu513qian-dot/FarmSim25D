# -*- coding: utf-8 -*-
"""SURGICAL WASD fix: MoveCharacter live MakeRotator must flatten camera YAW into Yaw pin (not Pitch).

Bug: BreakRotator.Yaw -> MakeRotator.Pitch  => forward becomes vertical; character barely/wrong moves.
Fix: BreakRotator.Yaw -> MakeRotator.Yaw, Pitch/Roll stay 0.

Also reaffirm OrientRotationToMovement=True, UseControllerRotationYaw=False.
Do NOT change SpringArm arm length / ortho (user-tuned). Do NOT wipe graphs.
"""
import unreal
from pathlib import Path
import json

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
REPORT = {"ok": True, "fixes": [], "verify": {}}

def log(m):
    unreal.log("[WASD_FIX] " + str(m)); print("[WASD_FIX] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(n, name, direction=None):
    want = name.lower().replace(" ", "")
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want == pn or want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.load_asset(CHAR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "MoveCharacter"))
nodes = list(ge.list_all_nodes())

# --- Fix every MakeRotator that has BreakRotator.Yaw wired into Pitch ---
fixed = 0
already_ok = 0
for n in nodes:
    if "MakeRotator" not in title(n):
        continue
    pitch = find_pin(n, "Pitch", "Input")
    yaw = find_pin(n, "Yaw", "Input")
    roll = find_pin(n, "Roll", "Input")
    if not pitch or not yaw:
        REPORT["fixes"].append("MakeRotator missing pitch/yaw pins")
        continue
    pitch_links = list(pitch.list_connected_pins())
    yaw_links = list(yaw.list_connected_pins())
    # Detect wrong: Pitch connected from BreakRotator.Yaw
    wrong_src = None
    for lp in pitch_links:
        if title(lp.get_owning_node()) == "BreakRotator" and str(lp.get_pin_name()) == "Yaw":
            wrong_src = lp
            break
    if wrong_src is not None:
        # Break wrong link
        try:
            pitch.break_pin_links()
        except Exception:
            pass
        # Ensure yaw not conflicting then connect
        try:
            if yaw_links:
                # If yaw already has something else, leave and report
                REPORT["fixes"].append("Yaw already linked: " + str([title(x.get_owning_node()) for x in yaw_links]))
            ok = wrong_src.try_create_connection(yaw)
            REPORT["fixes"].append("rewire Break.Yaw -> Make.Yaw ok={}".format(ok))
            if ok:
                fixed += 1
        except Exception as e:
            REPORT["fixes"].append("rewire fail " + str(e))
        # Force pitch/roll literal 0
        try:
            pitch.set_pin_value("0.0")
            if roll: roll.set_pin_value("0.0")
        except Exception:
            pass
    else:
        # Check correct path
        ok_yaw = any(title(lp.get_owning_node()) == "BreakRotator" and str(lp.get_pin_name()) == "Yaw" for lp in yaw_links)
        if ok_yaw:
            already_ok += 1
        else:
            REPORT["fixes"].append("MakeRotator neither wrong nor ok; yaw_links=" + str([(title(x.get_owning_node()), str(x.get_pin_name())) for x in yaw_links]))

REPORT["fixed_makerotators"] = fixed
REPORT["already_ok_makerotators"] = already_ok

# --- Also fix EventGraph MakeRotator if similarly wrong (orphan path) ---
ege = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
ev_fixed = 0
for n in ege.list_all_nodes():
    if "MakeRotator" not in title(n):
        continue
    pitch = find_pin(n, "Pitch", "Input")
    yaw = find_pin(n, "Yaw", "Input")
    if not pitch or not yaw:
        continue
    for lp in list(pitch.list_connected_pins()):
        if title(lp.get_owning_node()) == "BreakRotator" and str(lp.get_pin_name()) == "Yaw":
            pitch.break_pin_links()
            ok = lp.try_create_connection(yaw)
            try: pitch.set_pin_value("0.0")
            except Exception: pass
            REPORT["fixes"].append("EventGraph rewire Break.Yaw->Make.Yaw ok={}".format(ok))
            if ok: ev_fixed += 1
REPORT["eventgraph_fixed"] = ev_fixed

# --- Affirm face-move flags (do not touch camera distance) ---
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
cam_snap = {}
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj: continue
    cname = obj.get_class().get_name()
    if "CharacterMovement" in cname:
        for prop, val in (("orient_rotation_to_movement", True), ("use_controller_desired_rotation", False)):
            try:
                obj.set_editor_property(prop, val)
                REPORT["fixes"].append("{}={}".format(prop, obj.get_editor_property(prop)))
            except Exception as e:
                REPORT["fixes"].append("skip {} {}".format(prop, e))
        try:
            rr = obj.get_editor_property("rotation_rate")
            rr.yaw = 640.0
            obj.set_editor_property("rotation_rate", rr)
            REPORT["fixes"].append("RotationRate.Yaw=640")
        except Exception as e:
            REPORT["fixes"].append("rot rate " + str(e))
    if "SpringArm" in cname:
        try:
            r = obj.get_editor_property("relative_rotation")
            cam_snap["spring"] = {"pitch": r.pitch, "yaw": r.yaw, "arm": float(obj.get_editor_property("target_arm_length"))}
        except Exception as e:
            cam_snap["spring_err"] = str(e)
    if cname == "CameraComponent":
        try:
            cam_snap["cam"] = {
                "proj": str(obj.get_editor_property("projection_mode")),
                "ortho": float(obj.get_editor_property("ortho_width")),
            }
        except Exception:
            pass

cdo = unreal.get_default_object(bp.generated_class())
for prop, val in (("use_controller_rotation_yaw", False), ("use_controller_rotation_pitch", False), ("use_controller_rotation_roll", False)):
    try:
        cdo.set_editor_property(prop, val)
        REPORT["fixes"].append("CDO {}={}".format(prop, cdo.get_editor_property(prop)))
    except Exception as e:
        REPORT["fixes"].append("CDO {} {}".format(prop, e))

# --- Compile + verify live path ---
try:
    bel.compile_blueprint(bp)
    REPORT["compile"] = str(bp.status)
except Exception as e:
    REPORT["compile"] = str(e)

# Re-trace live MakeRotator
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "MoveCharacter"))
nodes = list(ge.list_all_nodes())
entry = next(n for n in nodes if n.get_class().get_name() == "K2Node_FunctionEntry" or title(n) == "MoveCharacter")
seen=set(); q=[]
for p in bel.list_all_pins(entry):
    if str(p.get_pin_name()) == "then":
        for c in p.list_connected_pins(): q.append(c.get_owning_node())
live_ami=[]
while q:
    n=q.pop(0)
    if id(n) in seen: continue
    seen.add(id(n))
    if "AddMovementInput" in title(n): live_ami.append(n)
    for p in bel.list_all_pins(n):
        if "OUTPUT" in str(p.get_pin_direction()):
            pn=str(p.get_pin_name()).lower()
            if pn in ("then","true","false","else") or "then" in pn:
                for c in p.list_connected_pins(): q.append(c.get_owning_node())

live_makes=[]
for ami in live_ami:
    wd = find_pin(ami, "WorldDirection", "Input")
    if not wd: continue
    for c in wd.list_connected_pins():
        # GetForward/GetRight -> MakeRotator
        vecn = c.get_owning_node()
        ir = find_pin(vecn, "InRot", "Input")
        if not ir: continue
        for c2 in ir.list_connected_pins():
            mn = c2.get_owning_node()
            if "MakeRotator" not in title(mn): continue
            pitch = find_pin(mn, "Pitch", "Input"); yaw = find_pin(mn, "Yaw", "Input")
            live_makes.append({
                "ami_scale": str(find_pin(ami,"ScaleValue","Input").list_connected_pins()[0].get_pin_name()) if find_pin(ami,"ScaleValue","Input").list_connected_pins() else "?",
                "pitch_links": [title(x.get_owning_node())+"."+str(x.get_pin_name()) for x in pitch.list_connected_pins()],
                "yaw_links": [title(x.get_owning_node())+"."+str(x.get_pin_name()) for x in yaw.list_connected_pins()],
            })

REPORT["verify"]["live_makes"] = live_makes
REPORT["verify"]["camera_untouched"] = cam_snap
ok_live = all(
    (not m["pitch_links"]) and any(l.startswith("BreakRotator.Yaw") for l in m["yaw_links"])
    for m in live_makes
) and len(live_makes) >= 1
REPORT["verify"]["live_flatten_ok"] = ok_live
REPORT["ok"] = bool(ok_live and fixed >= 1)

unreal.EditorAssetLibrary.save_asset(CHAR)
# Persist IMC too (no change) in case editor dirty
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Input/IMC_Default")

out = Path(unreal.Paths.project_saved_dir()) / "DayNight" / "wasd_fix.json"
out.write_text(json.dumps(REPORT, default=str, indent=2), encoding="utf-8")
log("fixed={} ok_live={} compile={}".format(fixed, ok_live, REPORT.get("compile")))
