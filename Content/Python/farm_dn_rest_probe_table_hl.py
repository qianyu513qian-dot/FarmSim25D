# -*- coding: utf-8 -*-
"""Probe: RestaurantTick chain, Held* vars, table actors/tags. REPORT filled for farm_dn runner."""
import unreal, json
REPORT = {}
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def walk(start, limit=40):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else","LoopBody","Completed"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
vars=[]
try:
    for v in bel.get_blueprint_variable_list(mbp) or []:
        vars.append(str(v))
except Exception as e:
    # fallback
    try:
        generated = mbp.generated_class
        vars = [str(p.get_name()) for p in generated.get_editor_property("properties") or []]
    except Exception as e2:
        vars = ["err:"+str(e)[:40]]

# list member vars via nodes
get_names=set()
for n in mge.list_all_nodes():
    t=title(n)
    if "Get Held" in t or "Get Restaurant" in t or t.startswith("Get "):
        if "Held" in t or "Active" in t:
            get_names.add(t)
customs=[title(n) for n in mge.list_all_nodes() if n.get_class().get_name()=="K2Node_CustomEvent"]
rt=None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        rt=n
REPORT["RestaurantTick"]=walk(rt,35) if rt else []
REPORT["has_TableHL"]=any("TableHL" in c or "SyncHeldTable" in c for c in customs)
REPORT["customs_sample"]=sorted([c for c in customs if any(k in c for k in ("Held","Clear","Receive","Refresh","Sync","TableHL","Tick","Apply"))])[:40]
REPORT["held_gets"]=sorted(get_names)

# level actors
actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tables=[]
marks=[]
for a in actor_sub.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if "Table" in lab or "RestMark" in lab or "Restaurant_" in lab:
        try: tags=[str(t) for t in (a.tags or [])]
        except: tags=[]
        loc=a.get_actor_location()
        entry={"label":lab,"class":a.get_class().get_name(),"tags":tags,"loc":[round(loc.x,1),round(loc.y,1),round(loc.z,1)]}
        if "Table" in lab:
            tables.append(entry)
        if "RestMark" in lab:
            marks.append(entry)
REPORT["tables"]=tables
REPORT["marks"]=marks
REPORT["mgr_status"]=str(mbp.get_editor_property("status"))
open(r"E:\UE\FarmSim25D\Saved\restaurant_probe_table_hl.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:6000])
