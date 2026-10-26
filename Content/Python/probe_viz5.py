# -*- coding: utf-8 -*-
import unreal
def log(m): unreal.log("[PROBE_ACTORS] " + str(m))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
counts = {}
samples = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    cls = a.get_class().get_name()
    counts[cls] = counts.get(cls, 0) + 1
    if any(k in lab for k in ("Soil", "Grass", "VMF", "Crop", "Path", "House", "Bridge", "Water", "Plot", "Grid")):
        loc = a.get_actor_location(); sc = a.get_actor_scale3d()
        samples.append((lab, cls, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z))
log("class counts=" + str(sorted(counts.items(), key=lambda x: -x[1])[:20]))
log("sample count=" + str(len(samples)))
for s in samples[:40]:
    log("  {} {} loc=({:.0f},{:.0f},{:.0f}) sc={:.4f}".format(s[0], s[1], s[2], s[3], s[4], s[5]))
# GetAllActorsWithTag call
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ege = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
created=[]
for path in [
    "/Script/Engine.GameplayStatics:GetAllActorsWithTag",
    "/Script/Engine.GameplayStatics:GetAllActorsOfClass",
    "/Script/Engine.KismetArrayLibrary:Array_Set",
    "/Script/Engine.KismetArrayLibrary:Array_Get",
    "/Script/Engine.KismetArrayLibrary:Array_Resize",
    "/Script/Engine.Actor:K2_SetActorLocation",
    "/Script/Engine.Actor:K2_SetActorTransform",
    "/Script/Engine.Actor:GetActorLocation",
]:
    try:
        n = ege.add_call_function_node(path)
        if n and len(bel.list_all_pins(n))>0:
            log("CALL OK {} {}".format(path.split(":")[-1], [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
            created.append(n)
        else:
            log("CALL empty "+path); 
            if n: created.append(n)
    except Exception as e:
        log("CALL FAIL {} {}".format(path, e))
if created: ege.remove_nodes(created)
# GridManager CDO defaults
gbp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
cdo = unreal.get_default_object(gbp.generated_class())
for p in ("cell_size","CellSize","grid_width","GridWidth","grid_height","GridHeight","grid_origin","GridOrigin"):
    try: log("CDO {}={}".format(p, cdo.get_editor_property(p)))
    except Exception: pass
