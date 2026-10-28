# -*- coding: utf-8 -*-
"""Wire SyncHeldMesh into RestaurantTick + ClearHeld; purge stale error nodes; verify seat."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={"steps":[],"errors":[],"ok":[]}

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
mbp=unreal.load_asset(MGR)
tbp=unreal.load_asset(TBL)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp,"EventGraph"))

def log(m):
    unreal.log("[WIRE3] "+str(m)); print("[WIRE3] "+str(m)); REPORT["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower(); cands=[]
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                cands.append(p)
    return cands[0] if cands else None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); REPORT["errors"].append("skip "+label); return False
    ok=a.try_create_connection(b)
    log("conn[{}] {}".format(label,ok))
    if not ok: REPORT["errors"].append("fail "+label)
    return ok

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def dump_pins(n):
    return ["{} {} {}".format(p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_display_string()) for p in bel.list_all_pins(n)]

# Delete/disconnect stale error nodes completely by breaking all links (already done) — try remove via graph editor if available
removed=0
for n in list(mge.list_all_nodes()):
    try: em=n.get_editor_property("error_msg")
    except: em=None
    if not em or not str(em).strip():
        continue
    t=title(n)
    if "GetAllActors" in t or t=="Get" or "HeldDishActor" in t:
        # try destroy node
        for fn in ("remove_node","delete_node","destroy_node"):
            if hasattr(mge, fn):
                try:
                    getattr(mge,fn)(n); removed+=1; log("removed "+t); break
                except Exception as e:
                    log(fn+" "+str(e)[:60])
        else:
            if hasattr(bel,"remove_node"):
                try: bel.remove_node(n); removed+=1; log("bel.remove "+t)
                except Exception as e: log("bel.remove fail "+str(e)[:60])
REPORT["removed"]=removed

# Ensure SyncHeldMesh exists
sync=find_custom(mge,"SyncHeldMesh")
log("SyncHeldMesh="+str(sync is not None))

# Create call via add_call_function_node — dump pins
call=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldMesh")
bel.set_node_pos(call,pos(40,-1300))
REPORT["call_pins"]=dump_pins(call)
log("call pins "+str(REPORT["call_pins"]))

# If no execute pin, try CallFunction on custom event differently — use add_custom_event and ProcessEvent? 
# Alternative: use K2Node_CallParentFunction / CallFunction with member name
ex=find_pin(call,"execute","Input")
th=find_pin(call,"then","Output")
if ex is None:
    # Maybe it's a CustomEvent-only and needs to be called as BlueprintCallable — custom events ARE callable if not latent
    log("NO execute on SyncHeldMesh call — listing class "+call.get_class().get_name())
    # Try CallFunction node with function name SyncHeldMesh from self
    # Search existing working call patterns: RefreshOrderUI
    for n in mge.list_all_nodes():
        if title(n)=="RefreshOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
            REPORT["refresh_pins"]=dump_pins(n)
            log("Refresh pins "+str(REPORT["refresh_pins"]))
            break

rt=find_custom(mge,"RestaurantTick")
thenp=find_pin(rt,"then","Output")
log("RT then connected="+str([title(c.get_owning_node()) for c in (thenp.list_connected_pins() or [])] if thenp else None))

# Find RefreshOrderUI and DrawDebugSphere (held fx start)
ref=None; dds=None
for n in mge.list_all_nodes():
    if title(n)=="RefreshOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
        ref=n
    if title(n)=="DrawDebugSphere" and dds is None:
        # check if in held path near RestHeld
        dds=n

# Reconstruct: RT -> SyncHeldMesh -> RefreshOrderUI
# RefreshOrderUI should already chain to held debug Branch if previously wired
if thenp and ex and ref:
    try: thenp.break_pin_links()
    except: pass
    rex=find_pin(ref,"execute","Input")
    # preserve Refresh.then targets
    connect(thenp, ex, "RT->Mesh")
    if rex:
        feed=[title(c.get_owning_node()) for c in (rex.list_connected_pins() or [])]
        log("Refresh was fed by "+str(feed))
        try: rex.break_pin_links()
        except: pass
        connect(th, rex, "Mesh->Refresh")
    REPORT["ok"].append("RT_wired")
elif thenp and ex is None:
    # Fallback: call SyncHeldMesh by embedding its body start — use CustomEvent as latent? 
    # Instead: from RT then call a MACRO or just Print and manually duplicate hide/show — too heavy.
    # Try BlueprintEditorLibrary create call from event
    log("attempt alternate call")
    # K2Node_CallFunction with MemberName
    if hasattr(mge,"add_node"):
        try:
            cls=unreal.K2Node_CallFunction
            alt=mge.add_node(cls.static_class())
            log("alt node "+str(alt))
        except Exception as e:
            log("alt "+str(e)[:80])

# ClearHeld
ch=find_custom(mge,"ClearHeld")
call2=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldMesh")
bel.set_node_pos(call2,pos(2200,-400))
REPORT["call2_pins"]=dump_pins(call2)
ex2=find_pin(call2,"execute","Input")
if ch and ex2:
    cur=ch; seen=set(); term=find_pin(ch,"then","Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp=find_pin(cur,"then","Output")
        if not tp: break
        nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            term=tp; break
        if title(nxts[0]) in ("SyncHeldVisual","SyncHeldVisual_v2","SyncHeldMesh"):
            try: tp.break_pin_links()
            except: pass
            term=tp; break
        cur=nxts[0]
    connect(term, ex2, "Clear->Mesh")
    REPORT["ok"].append("Clear_wired")

# If SyncHeldMesh call has no pins, Custom Event might not be BlueprintCallable until compiled — compile first then recreate calls
bel.compile_blueprint(mbp)
mst=str(mbp.get_editor_property("status"))
log("mid compile "+mst)

# Recreate calls after compile if needed
if ex is None or not find_pin(call,"execute","Input"):
    # destroy empty call nodes? 
    call=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldMesh")
    bel.set_node_pos(call,pos(40,-1300))
    REPORT["call_pins_after"]=dump_pins(call)
    log("after compile call "+str(REPORT["call_pins_after"]))
    ex=find_pin(call,"execute","Input"); th=find_pin(call,"then","Output")
    thenp=find_pin(rt,"then","Output")
    if thenp and ex and ref:
        try: thenp.break_pin_links()
        except: pass
        connect(thenp,ex,"RT->Mesh2")
        rex=find_pin(ref,"execute","Input")
        if rex:
            try: rex.break_pin_links()
            except: pass
            connect(th,rex,"Mesh->Refresh2")
        REPORT["ok"].append("RT_rewire2")

bel.compile_blueprint(mbp)
mst=str(mbp.get_editor_property("status"))
REPORT["mgr_status"]=mst
log("final "+mst)
errs=[]
for n in mge.list_all_nodes():
    try:
        em=n.get_editor_property("error_msg")
        if em and str(em).strip():
            errs.append(title(n)+":"+str(em)[:120])
    except: pass
REPORT["errs"]=errs

def walk(ge,name,maxd=40):
    ev=find_custom(ge,name)
    if not ev: return []
    out=[]; thenp=find_pin(ev,"then","Output")
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
REPORT["rt"]=walk(mge,"RestaurantTick")
REPORT["clear"]=walk(mge,"ClearHeld")
REPORT["sync"]=walk(mge,"SyncHeldMesh")
REPORT["spawn"]=walk(tge,"SpawnGuestVisual")

# Chair offset verify
offs=[]
for n in tge.list_all_nodes():
    if title(n)=="MakeVector":
        def gd(pin):
            if not pin: return None
            for fn in ("get_default_as_string","get_default_value"):
                if hasattr(pin,fn):
                    try: return str(getattr(pin,fn)())
                    except: pass
            return None
        offs.append({"X":gd(find_pin(n,"X","Input")),"Y":gd(find_pin(n,"Y","Input")),"Z":gd(find_pin(n,"Z","Input")),
                     "to":[title(c.get_owning_node()) for c in ((find_pin(n,"ReturnValue","Output").list_connected_pins() or []) if find_pin(n,"ReturnValue","Output") else [])]})
REPORT["offsets"]=offs

# MakeTransform rotation
for n in tge.list_all_nodes():
    if title(n)=="MakeTransform":
        rp=find_pin(n,"Rotation","Input")
        REPORT["tf_rot"]=gd(rp) if rp else None
        REPORT["tf_rot_links"]=[title(c.get_owning_node()) for c in (rp.list_connected_pins() or [])] if rp else []

if "ERROR" not in mst:
    eas.save_asset(MGR)
eas.save_asset(TBL)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_seat_held_wire3.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str)[:10000])
