# -*- coding: utf-8 -*-
"""Clean restaurant debug clutter: hide identity RestMark cubes + RestDebugLabels.
Keep OpenSign mark (open/closed color), SyncHeldTableHL DrawDebug, cook/held/bubble.
Adds Manager.bShowRestDebugLabels default false.
"""
import unreal
import json

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
REPORT = {"steps": [], "errors": [], "hidden": [], "kept": [], "ok": []}

def log(m):
    unreal.log("[REST_CLEAN] " + str(m))
    REPORT["steps"].append(str(m))

def ensure_bool(bp, name, default=False):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    if name not in names:
        t = bel.get_basic_type_by_name("bool")
        ok = bel.add_member_variable(bp, name, t)
        log("add {} -> {}".format(name, ok))
    else:
        log("exists " + name)
    bel.compile_blueprint(bp)
    try:
        cdo = unreal.get_default_object(bp.generated_class())
        cdo.set_editor_property(name, bool(default))
        got = bool(cdo.get_editor_property(name))
        log("CDO.{}={}".format(name, got))
        REPORT["ok"].append("CDO.{}={}".format(name, got))
    except Exception as e:
        REPORT["errors"].append("CDO " + str(e)[:120])
        log("CDO fail " + str(e)[:120])

# ---- 1) Manager bool ----
mbp = unreal.EditorAssetLibrary.load_asset(MGR)
if not mbp:
    REPORT["errors"].append("no manager")
else:
    ensure_bool(mbp, "bShowRestDebugLabels", False)
    unreal.EditorAssetLibrary.save_asset(MGR)
    st = str(mbp.get_editor_property("status"))
    REPORT["mgr_status"] = st
    log("mgr " + st)

# ---- 2) Level actors: hide identity marks + RestDebugLabels; keep OpenSign smaller ----
SHOW = False  # prefer clean look; bool default false
KEEP_OPEN = "RestMark_OpenSign"
HIDE_MARKS = ("RestMark_Stove", "RestMark_Table1", "RestMark_Table2", "RestMark_Trash")

for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    try:
        if lab == "RestDebugLabels" or lab.startswith("RestDebug"):
            a.set_actor_hidden_in_game(True)
            try:
                a.set_actor_tick_enabled(False)
            except Exception:
                pass
            try:
                a.set_is_temporarily_hidden_in_editor(True)
            except Exception:
                pass
            # also hide components
            try:
                for c in a.get_components_by_class(unreal.ActorComponent):
                    if hasattr(c, "set_visibility"):
                        c.set_visibility(False, True)
                    if hasattr(c, "set_hidden_in_game"):
                        c.set_hidden_in_game(True)
            except Exception:
                pass
            REPORT["hidden"].append(lab)
            log("hide debug actor " + lab)
            continue

        if lab in HIDE_MARKS:
            a.set_actor_hidden_in_game(True)
            try:
                smc = a.static_mesh_component
                smc.set_visibility(False, True)
                smc.set_hidden_in_game(True)
            except Exception:
                pass
            try:
                a.set_is_temporarily_hidden_in_editor(True)
            except Exception:
                pass
            REPORT["hidden"].append(lab)
            log("hide identity " + lab)
            continue

        if lab == KEEP_OPEN:
            # gameplay open/closed color — keep visible, make smaller
            a.set_actor_hidden_in_game(False)
            try:
                smc = a.static_mesh_component
                smc.set_visibility(True, True)
                smc.set_hidden_in_game(False)
            except Exception:
                pass
            a.set_actor_scale3d(unreal.Vector(0.22, 0.22, 0.22))
            REPORT["kept"].append({"lab": lab, "scale": 0.22, "reason": "open_closed_color"})
            log("keep OpenSign mark smaller")
            continue
    except Exception as e:
        REPORT["errors"].append(lab + ":" + str(e)[:100])

# ---- 3) Save level ----
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["level_saved"] = True
    log("level saved")
except Exception as e:
    REPORT["level_saved"] = False
    REPORT["errors"].append("level " + str(e)[:100])

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception:
    pass

out = r"E:\UE\FarmSim25D\Saved\restaurant_debug_cleanup.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
