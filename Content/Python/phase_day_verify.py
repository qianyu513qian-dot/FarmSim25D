# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
def log(m):
    unreal.log("[DAY_V] "+str(m)); print("[DAY_V] "+str(m))
bp = unreal.load_asset(MGR)
try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile FAIL "+str(e))
# status
try:
    st = bp.status
    log("bp.status="+str(st))
except Exception as e:
    log("status "+str(e))
names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
for v in ("CurrentDay","TimeOfDay","DayLengthSeconds","SunActor","SkyLightActor"):
    log("var {}={}".format(v, v in names))
graphs = [str(g) for g in bel.list_graph_names(bp)]
log("AdvanceDayGrowth="+str("AdvanceDayGrowth" in graphs))
log("ApplyDayNightVisuals="+str("ApplyDayNightVisuals" in graphs))
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,"EventGraph"))
for n in ge.list_all_nodes():
    if n.get_class().get_name()!="K2Node_Event": continue
    t=str(bel.get_node_title(n))
    then=None
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name())=="then":
            then=p; break
    links=[]
    if then:
        links=[str(bel.get_node_title(c.get_owning_node())) for c in (then.list_connected_pins() or [])]
    log("EVENT {} -> {}".format(t, links))
log("DONE")