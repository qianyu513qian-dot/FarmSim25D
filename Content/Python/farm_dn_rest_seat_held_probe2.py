# -*- coding: utf-8 -*-
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string","get_default_value","get_pin_value"):
        if hasattr(p,fn):
            try: return str(getattr(p,fn)())
            except: pass
    return None

def dump_node(n):
    info={"title":title(n),"class":n.get_class().get_name(),"pins":[]}
    for p in bel.list_all_pins(n):
        links=[]
        for c in (p.list_connected_pins() or []):
            links.append(title(c.get_owning_node())+"."+str(c.get_pin_name()))
        d=pin_def(p)
        info["pins"].append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"def":d,"links":links})
    return info

TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
tbp=unreal.load_asset(TBL)
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp,"EventGraph"))
spawn=find_custom(tge,"SpawnGuestVisual")
# Find MakeVector / MakeTransform / GetActorLocation near spawn by walking
nodes=[]
thenp=find_pin(spawn,"then","Output")
# Also scan ALL nodes for MakeVector with 40
for n in tge.list_all_nodes():
    if title(n) in ("MakeVector","Make Transform","MakeTransform","K2_GetActorLocation","BeginDeferredActorSpawnFromClass","FinishSpawningActor","Add_VectorVector"):
        nodes.append(dump_node(n))
    # check MakeVector defs for 40
    if "MakeVector" in title(n) or n.get_class().get_name()=="K2Node_CallFunction" and "MakeVector" in title(n):
        nodes.append(dump_node(n))
REPORT["table_tf_nodes"]=nodes

# Walk spawn predecessors for transform - nodes feeding BeginDeferred
beg=None
for n in tge.list_all_nodes():
    if title(n)=="BeginDeferredActorSpawnFromClass":
        beg=n; break
if beg:
    REPORT["begin"]=dump_node(beg)
    # find connected MakeTransform
    sp=find_pin(beg,"SpawnTransform","Input") or find_pin(beg,"Transform","Input")
    if sp:
        for c in sp.list_connected_pins() or []:
            REPORT["spawn_tf_src"]=dump_node(c.get_owning_node())

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
mbp=unreal.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))
rt=find_custom(mge,"RestaurantTick")
ch=find_custom(mge,"ClearHeld")
def walk(start, maxd=25):
    out=[]; thenp=find_pin(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in seen or d>maxd: continue
        seen.add(id(cur)); out.append(title(cur))
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return out
REPORT["RestaurantTick"]=walk(rt) if rt else []
REPORT["ClearHeld"]=walk(ch) if ch else []

# markers
REPORT["has_SeatHeld_v1"]=any(title(n)=="SeatHeld_v1" for n in mge.list_all_nodes()) or any(title(n)=="SeatHeld_v1" for n in tge.list_all_nodes())

# mesh bounds for basket/crate
for path in ["/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket","/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"]:
    m=eas.load_asset(path)
    if m:
        try:
            b=m.get_editor_property("extended_bounds") if False else None
        except: pass
        try:
            bounds=m.get_bounds()
            REPORT[path]=str(bounds)
        except Exception as e:
            REPORT[path]="err "+str(e)
            try:
                REPORT[path+"_box"]=str(m.get_bounding_box())
            except Exception as e2:
                REPORT[path+"_e2"]=str(e2)

# Player pawn class for attach
REPORT["player_bps"]=list(eas.list_assets("/Game/TopDown", recursive=True) or [])[:30]
REPORT["chars"]= [p for p in (eas.list_assets("/Game/Characters", recursive=False) or [])]

out=unreal.Paths.project_saved_dir()+"rest_seat_held_probe2.json"
open(out,"w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2,default=str))
print(out)
print(json.dumps(REPORT,ensure_ascii=False,default=str)[:7000])
