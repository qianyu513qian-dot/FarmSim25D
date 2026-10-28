# -*- coding: utf-8 -*-
"""Set DayLengthSeconds default on BP_GridManager (not instance)."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[DN_DAYLEN] " + str(m)); print("[DN_DAYLEN] " + str(m))

bp = unreal.load_asset(MGR)
# Try generated class CDO
gc = bp.generated_class()
cdo = unreal.get_default_object(gc)
log("CDO class={}".format(gc.get_name()))
try:
    cur = cdo.get_editor_property("DayLengthSeconds")
    log("CDO DayLengthSeconds={}".format(cur))
except Exception as e:
    log("get CDO " + str(e))
    cur = None

# Blueprint variable default via EditorSubsystem / BlueprintEditorLibrary
ok = False
try:
    cdo.set_editor_property("DayLengthSeconds", 75.0)
    log("set CDO DayLengthSeconds=75")
    ok = True
except Exception as e:
    log("set CDO fail " + str(e))

# Alternate: modify blueprint variable default value string
try:
    # UE5.8 may expose via BlueprintEditorLibrary.set_blueprint_variable_default_value
    if hasattr(bel, "set_blueprint_variable_default_value"):
        bel.set_blueprint_variable_default_value(bp, "DayLengthSeconds", "75.0")
        log("set via bel.set_blueprint_variable_default_value")
        ok = True
except Exception as e:
    log("bel default " + str(e))

try:
    # Some versions: unreal.BlueprintEditorLibrary.find_event_graph
    vars_api = getattr(unreal, "BlueprintVariableHelper", None)
    log("helper={}".format(vars_api))
except Exception:
    pass

# Inspect all properties containing Day/Length/Time
for p in dir(cdo):
    if "day" in p.lower() or "time" in p.lower() or "length" in p.lower():
        try:
            log("attr {}={}".format(p, getattr(cdo, p)))
        except Exception:
            pass

try:
    bel.compile_blueprint(bp)
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

try:
    cur2 = unreal.get_default_object(bp.generated_class()).get_editor_property("DayLengthSeconds")
    log("after DayLengthSeconds={}".format(cur2))
except Exception as e:
    log("after get " + str(e))
log("DONE ok={}".format(ok))
