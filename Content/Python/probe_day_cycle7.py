# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
def log(m):
    unreal.log("[P7] "+str(m)); print("[P7] "+str(m))

# cast node APIs
for name in dir(ge):
    if "cast" in name.lower() and not name.startswith("_"):
        log("ge."+name+" doc="+str(getattr(getattr(ge,name),'__doc__',None))[:200])

# try create cast via name
for name in [
    "Utilities|Casting|Cast To LightComponent",
    "Cast To Light Component",
    "Cast To Directional Light Component",
    "Class Casting|Cast To LightComponent",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        log("create cast {} -> {}".format(name, bel.get_node_title(n) if n else None))
        if n:
            for p in bel.list_all_pins(n):
                log("  {} {}".format(p.get_pin_name(), p.get_pin_direction()))
            ge.remove_nodes([n])
    except Exception as e:
        log("cast name {} {}".format(name, e))

# Array_Get pins
n = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
if n:
    log("Array_Get title="+str(bel.get_node_title(n)))
    for p in bel.list_all_pins(n):
        log("  {} {}".format(p.get_pin_name(), p.get_pin_direction()))
    ge.remove_nodes([n])

# SetActorRotation pins
n = ge.add_call_function_node("/Script/Engine.Actor:K2_SetActorRotation")
if n:
    for p in bel.list_all_pins(n):
        log("SetRot {} {}".format(p.get_pin_name(), p.get_pin_direction()))
    ge.remove_nodes([n])

# SetIntensity / SetLightColor pins
for path in ["/Script/Engine.LightComponent:SetIntensity", "/Script/Engine.LightComponent:SetLightColor"]:
    n = ge.add_call_function_node(path)
    if n:
        for p in bel.list_all_pins(n):
            log("{} {} {}".format(path.split(':')[-1], p.get_pin_name(), p.get_pin_direction()))
        ge.remove_nodes([n])

# Does Add have Class default for DirectionalLight via soft object path on pin?
n = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
ac = None
for p in bel.list_all_pins(n):
    if "ActorClass" in str(p.get_pin_name()):
        ac = p
ac.set_pin_value("/Script/Engine.DirectionalLight")
log("ActorClass after set={!r}".format(ac.get_pin_value()))
# also try without /Script
ge.remove_nodes([n])

n = ge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
cp=None
for p in bel.list_all_pins(n):
    if "ComponentClass" in str(p.get_pin_name()):
        cp=p
cp.set_pin_value("/Script/Engine.LightComponent")
log("CompClass after={!r}".format(cp.get_pin_value()))
cp.set_pin_value("/Script/Engine.DirectionalLightComponent")
log("CompClass DL after={!r}".format(cp.get_pin_value()))
ge.remove_nodes([n])

log("DONE")
