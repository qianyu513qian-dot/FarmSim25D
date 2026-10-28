# -*- coding: utf-8 -*-
"""Repair SeatHeld: fix HeldDishActor type, rewire RT/ClearHeld SyncHeldVisual."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={"steps":[],"errors":[],"ok":[]}

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
mbp=unreal.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))

def log(m):
    unreal.log("[SEATFIX] "+str(m)); print("[SEATFIX] "+str(m)); REPORT["steps"].append(str(m))

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

def out_data(node):
    if not node: return None
    for name in ("ReturnValue","Return Value","HeldDishActor","HeldDishId"):
        p=find_pin(node,name,"Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n=str(p.get_pin_name()).lower()
            if n not in ("outputdelegate","then","else","completed","loopbody"):
                return p
    return None

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

def setdef(pin,val):
    if not pin: return False
    try: pin.set_pin_value(str(val)); return True
    except:
        try: pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef "+str(e)[:60]); return False

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def dump_pins(n):
    rows=[]
    for p in bel.list_all_pins(n):
        rows.append("{} {} type={} links={}".format(
            p.get_pin_name(), p.get_pin_direction(),
            p.get_pin_type_display_string(),
            [title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        ))
    return rows

# Inspect HeldDishActor get/set nodes and IsValid
for n in mge.list_all_nodes():
    t=title(n)
    if "HeldDishActor" in t or t in ("IsValid","Destroy Actor","K2_DestroyActor"):
        REPORT.setdefault("inspect",[]).append({"title":t,"class":n.get_class().get_name(),"pins":dump_pins(n)})

# Try change variable type to Actor
try:
    # BlueprintEditorLibrary.change_member_variable_type
    actor_t = None
    for cand in ("actor","object","Actor"):
        try:
            actor_t = bel.get_basic_type_by_name(cand)
            log("type {} -> {}".format(cand, actor_t))
        except Exception as e:
            log("type fail "+cand+" "+str(e)[:40])
    # Use more specific API if available
    if hasattr(bel, "change_member_variable_type"):
        # Need EdGraphPinType
        try:
            pin_type = unreal.EdGraphPinType()
            pin_type.set_editor_property("pin_category", unreal.Name("object"))
            pin_type.set_editor_property("pin_sub_category_object", unreal.Actor.static_class())
            bel.change_member_variable_type(mbp, "HeldDishActor", pin_type)
            log("changed HeldDishActor to Actor ref via EdGraphPinType")
            REPORT["ok"].append("type_actor")
        except Exception as e:
            log("change type "+str(e)[:120])
            REPORT["errors"].append("type "+str(e)[:120])
except Exception as e:
    log("type block "+str(e)[:80])

bel.compile_blueprint(mbp)

# Re-inspect Get HeldDishActor pin type after change
for n in mge.list_all_nodes():
    if title(n) in ("Get HeldDishActor","Set HeldDishActor"):
        REPORT.setdefault("after_type",[]).append({"title":title(n),"pins":dump_pins(n)})

# Fix IsValid / Destroy / Set connections inside SyncHeldVisual
sync=find_custom(mge,"SyncHeldVisual")
# Find Get HeldDishActor nodes and reconnect
gets=[]; sets=[]; valids=[]; destroys=[]; finishes=[]
for n in mge.list_all_nodes():
    t=title(n)
    if t=="Get HeldDishActor": gets.append(n)
    if t=="Set HeldDishActor": sets.append(n)
    if t=="IsValid": valids.append(n)
    if "Destroy" in t: destroys.append(n)
    if t=="FinishSpawningActor": finishes.append(n)

log("gets={} sets={} valids={} destroys={} finishes={}".format(len(gets),len(sets),len(valids),len(destroys),len(finishes)))

# Reconnect each Get -> nearest IsValid Object and Destroy self by graph proximity (node pos)
def npos(n):
    try: return bel.get_node_pos(n)
    except: return unreal.IntPoint(0,0)

for g in gets:
    gp=out_data(g)
    gx=npos(g).x; gy=npos(g).y
    # nearest IsValid
    best=None; bestd=1e18
    for v in valids:
        dx=npos(v).x-gx; dy=npos(v).y-gy; d=dx*dx+dy*dy
        if d<bestd: bestd=d; best=v
    if best and gp:
        objp=find_pin(best,"Object","Input") or find_pin(best,"self","Input")
        if objp:
            try: objp.break_pin_links()
            except: pass
            connect(gp,objp,"fix get->IsValid")
    # nearest Destroy within y band
    best=None; bestd=1e18
    for dnode in destroys:
        dx=npos(dnode).x-gx; dy=npos(dnode).y-gy; d=dx*dx+dy*dy
        if d<bestd: bestd=d; best=dnode
    if best and gp and bestd<500000:  # only if close
        sp=find_pin(best,"self","Input") or find_pin(best,"Target","Input")
        if sp:
            try: sp.break_pin_links()
            except: pass
            connect(gp,sp,"fix get->Destroy")

# FinishSpawning -> Set HeldDishActor value pin
for f in finishes:
    fp=out_data(f)
    fx=npos(f).x; fy=npos(f).y
    best=None; bestd=1e18
    for s in sets:
        dx=npos(s).x-fx; dy=npos(s).y-fy; d=dx*dx+dy*dy
        if d<bestd and npos(s).x>=fx-50: bestd=d; best=s
    if best and fp:
        vp=find_pin(best,"HeldDishActor","Input")
        # list pins
        REPORT.setdefault("set_pins",[]).append(dump_pins(best))
        if vp:
            try: vp.break_pin_links()
            except: pass
            connect(fp,vp,"fix fin->SetHeld")
        else:
            # try any non-exec input data pin
            for p in bel.list_all_pins(best):
                if "INPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
                    if str(p.get_pin_name()).lower() not in ("execute","self"):
                        try: p.break_pin_links()
                        except: pass
                        connect(fp,p,"fix fin->SetHeldAny")
                        break

# GetComponentByClass self from Get HeldDishActor for "ex" path
for n in mge.list_all_nodes():
    if title(n)=="GetComponentByClass":
        selfp=find_pin(n,"self","Input")
        if selfp and not (selfp.list_connected_pins() or []):
            # find nearby Get HeldDishActor
            nx=npos(n).x; ny=npos(n).y
            best=None; bestd=1e18
            for g in gets:
                dx=npos(g).x-nx; dy=npos(g).y-ny; d=dx*dx+dy*dy
                if d<bestd: bestd=d; best=g
            if best:
                connect(out_data(best), selfp, "fix get->GetComp")

# ---- Rewire RestaurantTick ----
rt=find_custom(mge,"RestaurantTick")
# Find existing SyncHeldVisual call nodes
sync_calls=[]
for n in mge.list_all_nodes():
    if title(n)=="SyncHeldVisual" and n.get_class().get_name()=="K2Node_CallFunction":
        sync_calls.append(n)
    if "SyncHeldVisual" in title(n) and "CustomEvent" not in n.get_class().get_name():
        sync_calls.append(n)
log("sync_calls="+str([n.get_class().get_name()+":"+title(n) for n in sync_calls]))

# Also find by function name in CallFunction
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CallFunction":
        try:
            fn=n.get_editor_property("function_reference")
        except: fn=None
        if fn and "SyncHeld" in str(fn):
            sync_calls.append(n)
            log("found via funcref "+str(fn)[:80])

# RestaurantTick then targets
thenp=find_pin(rt,"then","Output") if rt else None
targets=[c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
log("RT then -> "+str([title(t) for t in targets]))

# Ensure a call node exists
call_sync=None
for n in sync_calls:
    # prefer ones already partially wired
    call_sync=n; break
if call_sync is None:
    call_sync=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual")
    bel.set_node_pos(call_sync, pos(120,-1000))
    log("added SyncHeldVisual call")
    REPORT["ok"].append("add_sync_call")
else:
    log("reuse sync call "+call_sync.get_class().get_name())

# Dump call_sync pins
REPORT["call_sync_pins"]=dump_pins(call_sync)

# If RT then empty or doesn't include sync, wire RT -> Sync -> RefreshOrderUI (or old first)
# Find RefreshOrderUI call
ref_call=None
for n in mge.list_all_nodes():
    if title(n)=="RefreshOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
        ref_call=n; break
log("ref_call="+str(ref_call is not None))

# Break RT then and rebuild: RT -> SyncHeldVisual -> RefreshOrderUI -> (rest of old Refresh then if any)
if thenp:
    old_targets=list(thenp.list_connected_pins() or [])
    try: thenp.break_pin_links()
    except Exception as e: log("break RT "+str(e))
    connect(thenp, find_pin(call_sync,"execute","Input"), "RT->Sync")
    # If Sync already linked to something, keep; else link to RefreshOrderUI
    sync_then=find_pin(call_sync,"then","Output")
    sync_then_tgts=list(sync_then.list_connected_pins() or []) if sync_then else []
    if not sync_then_tgts:
        if ref_call:
            # If Refresh was previously first, its execute may be dangling
            connect(sync_then, find_pin(ref_call,"execute","Input"), "Sync->Refresh")
        elif old_targets:
            connect(sync_then, old_targets[0], "Sync->old")
    REPORT["ok"].append("RT_rewired")

# ClearHeld terminal -> SyncHeldVisual (second call node to avoid exec contention)
ch=find_custom(mge,"ClearHeld")
def walk_term(start):
    cur=start; seen=set(); last=find_pin(start,"then","Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp=find_pin(cur,"then","Output")
        if not tp: break
        nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts: return tp, cur
        cur=nxts[0]
    return last, cur
if ch:
    term, last=walk_term(ch)
    log("ClearHeld term from "+title(last))
    # check if already calls Sync
    already=False
    # walk
    q=[ch]; seen=set()
    while q:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        if title(cur)=="SyncHeldVisual" and cur.get_class().get_name()=="K2Node_CallFunction":
            already=True
        tp=find_pin(cur,"then","Output")
        if tp:
            for c in tp.list_connected_pins() or []:
                q.append(c.get_owning_node())
    if not already and term:
        call_c=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual")
        bel.set_node_pos(call_c, pos(1800,-250))
        connect(term, find_pin(call_c,"execute","Input"), "ClearHeld->Sync")
        REPORT["ok"].append("ClearHeld_Sync")
    else:
        log("ClearHeld already has sync or no term")

bel.compile_blueprint(mbp)
mst=str(mbp.get_editor_property("status"))
REPORT["mgr_status"]=mst
log("mgr "+mst)
if "ERROR" not in mst:
    eas.save_asset(MGR)
else:
    for n in mge.list_all_nodes():
        try:
            em=n.get_editor_property("error_msg")
            if em and str(em).strip():
                REPORT["errors"].append(title(n)+":"+str(em)[:160])
        except: pass

def walk_titles(name,maxd=35):
    ev=find_custom(mge,name)
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
REPORT["rt"]=walk_titles("RestaurantTick")
REPORT["clear"]=walk_titles("ClearHeld")
REPORT["sync"]=walk_titles("SyncHeldVisual")

# Verify chair offset still set
tbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp,"EventGraph"))
offs=[]
for n in tge.list_all_nodes():
    if title(n)=="MakeVector":
        xd=find_pin(n,"X","Input"); yd=find_pin(n,"Y","Input"); zd=find_pin(n,"Z","Input")
        def gd(p):
            for fn in ("get_default_as_string","get_default_value"):
                if hasattr(p,fn):
                    try: return str(getattr(p,fn)())
                    except: pass
            return "?"
        offs.append((gd(xd),gd(yd),gd(zd)))
REPORT["makevectors"]=offs

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_seat_held_fix.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str)[:10000])
