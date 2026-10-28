# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary

def dump_graph(ge):
    nodes=[]
    for n in ge.list_all_nodes():
        pins={}
        for p in bel.list_all_pins(n):
            pins[str(p.get_pin_name())]={
                "dir": "out" if "OUTPUT" in str(p.get_pin_direction()) else "in",
                "val": p.get_pin_value(),
                "to": [bel.get_node_title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
            }
        nodes.append({"t":bel.get_node_title(n),"c":n.get_class().get_name(),"pins":pins})
    return nodes

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
nodes = dump_graph(mge)
# also check add_member_variable API
apis = [x for x in dir(mge) if "variable" in x.lower() or "member" in x.lower()]
bel_apis = [x for x in dir(bel) if "variable" in x.lower() or "member" in x.lower()]
# try add vars
ok_add = {}
for vn, vtype in [("bIsOpen","bool"),("GuestTimer","float"),("GuestInterval","float"),("bSeatedOnce","bool")]:
    try:
        r = mge.add_member_variable(vn)  # probe
        ok_add[vn] = {"r":str(r)[:80], "via":"noargs"}
    except Exception as e:
        ok_add[vn] = {"err1":str(e)[:120]}
        try:
            r = mge.add_member_variable(vn, unreal.BooleanProperty if vtype=="bool" else unreal.FloatProperty)
            ok_add[vn] = {"r":str(r)[:80],"via":"type"}
        except Exception as e2:
            ok_add[vn]["err2"]=str(e2)[:120]

# inspect signature via help text
help_txt = str(mge.add_member_variable.__doc__)

# table vars
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
tok={}
for vn in ["bOccupied","CurrentOrder","bHasOrder"]:
    try:
        r=tge.add_member_variable(vn)
        tok[vn]=str(r)[:80]
    except Exception as e:
        tok[vn]=str(e)[:150]

# Character tillsoil
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia_nodes=dump_graph(cge)
ia_only=[n for n in ia_nodes if "IA_Interact" in n["t"] or "TillSoil" in n["t"] or "Sphere" in n["t"] or "Restaurant" in n["t"] or "Handle" in n["t"]]

rep={"mgr":nodes,"add_apis":apis,"bel_apis":bel_apis,"help":help_txt,"ok_add":ok_add,"tok":tok,"ia":ia_only}
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_fulldump.json","w",encoding="utf-8").write(json.dumps(rep,indent=2,ensure_ascii=False))
print("mgr",len(nodes),"ok_add",ok_add,"tok",tok)
print("help",help_txt[:300])
