# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
gdm = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
geq = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
lt = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
# pin types
def pinfo(n,label):
    rows=[]
    for p in bel.list_all_pins(n):
        rows.append({"n":str(p.get_pin_name()),"disp":str(p.get_pin_type_display_string()),"dir":str(p.get_pin_direction())})
    return {label:bel.get_node_title(n),"pins":rows}
rep={"gdm":pinfo(gdm,"gdm"),"geq":pinfo(geq,"geq"),"lt":pinfo(lt,"lt")}
# try connect gdm -> geq.A
a=None; rv=None
for p in bel.list_all_pins(gdm):
    if str(p.get_pin_name())=="ReturnValue": rv=p
for p in bel.list_all_pins(geq):
    if str(p.get_pin_name())=="A": a=p
ok1 = rv.try_create_connection(a) if rv and a else False
# try gdm -> lt.A
a2=None
for p in bel.list_all_pins(lt):
    if str(p.get_pin_name())=="A": a2=p
ok2 = rv.try_create_connection(a2) if rv and a2 else False
# try set B on geq
for p in bel.list_all_pins(geq):
    if str(p.get_pin_name())=="B":
        try: p.set_pin_value("1020"); rep["setB"]=p.get_pin_value()
        except Exception as e: rep["setB"]=str(e)
# Conv_IntToDouble?
conv=None
try:
    conv=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Conv_IntToDouble")
    rep["conv"]=pinfo(conv,"conv") if conv else None
    if conv:
        cin=None; cout=None
        for p in bel.list_all_pins(conv):
            if str(p.get_pin_name()) in ("InInt","Integer"): cin=p
            if str(p.get_pin_name())=="ReturnValue": cout=p
        # break previous?
        ok3 = rv.try_create_connection(cin) if cin else False
        ok4 = cout.try_create_connection(a2) if cout and a2 else False
        rep["ok_conv"]= [ok3,ok4]
except Exception as e:
    rep["conv_err"]=str(e)[:100]
rep["ok_geq"]=ok1; rep["ok_lt"]=ok2
# cleanup
kill=[gdm,geq,lt]
if conv: kill.append(conv)
mge.remove_nodes([x for x in kill if x])
print(json.dumps(rep,indent=2))
