# -*- coding: utf-8 -*-
"""Inspect DayLengthSeconds defaults, Atmosphere count, ApplyDayNight all node titles."""
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[DN_CHK] " + str(m)); print("[DN_CHK] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

bp = unreal.load_asset(MGR)
# list new variables
try:
    for v in bp.new_variables:
        n = str(v.var_name)
        if any(k in n.lower() for k in ("day", "time", "sun", "moon", "sky", "tod")):
            dv = None
            try: dv = v.default_value
            except Exception: pass
            log("VAR {} type={} default={!r}".format(n, v.var_type, dv))
except Exception as e:
    log("vars err " + str(e))

# Atmosphere count
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
atms = [a for a in actors if a.get_class().get_name() == "SkyAtmosphere"]
log("SkyAtmosphere count={}".format(len(atms)))
for a in atms:
    try: log("  atm label={} loc={}".format(a.get_actor_label(), a.get_actor_location()))
    except Exception as e: log("  atm " + str(e))

# All nodes in ApplyDayNightVisuals
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
titles = sorted(title(n) for n in ge.list_all_nodes())
log("node_count={}".format(len(titles)))
for t in titles:
    log("  N: " + t)

# BeginPlay / FindActor refs
for gname in ("EventGraph", "ReceiveBeginPlay", "BeginPlay"):
    g = bel.find_graph(bp, gname)
    if g:
        log("found graph " + gname)
