# -*- coding: utf-8 -*-
"""Fix HeldDishActor to Actor type (copy from GuestActor); rebuild SyncHeldVisual cleanly."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={"steps":[],"errors":[],"ok":[]}

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST="/Game/Farm/Restaurant/BP_RestGuest"
MESH_SALAD="/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket"
MESH_STEW="/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"

mbp=unreal.load_asset(MGR)
tbp=unreal.load_asset(TBL)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))

def log(m):
    unreal.log("[HELDFIX2] "+str(m)); print("[HELDFIX2] "+str(m)); REPORT["steps"].append(str(m))

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
    for name in ("ReturnValue","Return Value","HeldDishActor","HeldDishId","GuestActor"):
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

def setdef(pin,val):
    if not pin: return False
    try: pin.set_pin_value(str(val)); return True
    except:
        try: pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef "+str(e)[:60]); return False

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def make_print(ge,x,y,text,dur="0.2",key=""):
    pr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr,pos(x,y))
    setdef(find_pin(pr,"InString","Input"),text)
    setdef(find_pin(pr,"Duration","Input"),dur)
    if key: setdef(find_pin(pr,"Key","Input"),key)
    return pr

# 1) Fix variable type by copying GuestActor's pin type
guest_type=bel.get_member_variable_type(tbp,"GuestActor")
log("guest_type ok")
try:
    schema=bel.pin_type_to_json_schema(mbp, guest_type)
    REPORT["guest_schema"]=str(schema)[:500]
except Exception as e:
    try:
        schema=guest_type.pin_type_to_json_schema()
        REPORT["guest_schema"]=str(schema)[:500]
    except Exception as e2:
        REPORT["guest_schema_err"]=str(e)+" | "+str(e2)

try:
    ok=bel.change_member_variable_type(mbp,"HeldDishActor",guest_type)
    log("change_member_variable_type -> "+str(ok))
    REPORT["ok"].append("type_changed")
except Exception as e:
    log("change fail "+str(e)[:120])
    # remove + readd
    try:
        # No remove API — use replace by adding HeldDishProp with correct type
        ok=bel.add_member_variable(mbp,"HeldDishProp",guest_type)
        log("add HeldDishProp -> "+str(ok))
        REPORT["ok"].append("HeldDishProp")
        VAR="HeldDishProp"
    except Exception as e2:
        REPORT["errors"].append(str(e2)); VAR="HeldDishActor"
else:
    VAR="HeldDishActor"

bel.compile_blueprint(mbp)
# verify type
try:
    ht=bel.get_member_variable_type(mbp,VAR)
    REPORT["held_schema"]=str(ht)
    log("held schema "+str(REPORT["held_schema"])[:200])
except Exception as e:
    log("verify "+str(e)[:80])

# 2) Purge broken SyncHeldVisual body: remove old custom event nodes by breaking links
# and create SyncHeldVisual_v2 with clean graph; retarget RT/ClearHeld calls.

# Remove marker SeatHeld_v1? keep. Add SeatHeld_v2.

# Delete approach: break all pins on nodes that are ONLY in SyncHeldVisual chain, then add new event.
old_sync=find_custom(mge,"SyncHeldVisual")
# We'll leave old orphaned and add SyncHeldVisual_v2, then point calls there.

NEW="SyncHeldVisual_v2"
if find_custom(mge,NEW):
    log("v2 exists")
else:
    sync=mge.add_custom_event_node(NEW)
    bel.set_node_pos(sync,pos(-1200,-2200))
    Y=-2200; X=-900

    get_h=mge.add_get_member_variable_node("HeldDishId")
    bel.set_node_pos(get_h,pos(X,Y+100))
    ne=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
    bel.set_node_pos(ne,pos(X+220,Y+100))
    connect(out_data(get_h),find_pin(ne,"A","Input"),"hA")
    setdef(find_pin(ne,"B","Input"),"0")
    br=mge.add_branch_node(); bel.set_node_pos(br,pos(X+450,Y))
    connect(find_pin(sync,"then","Output"),find_pin(br,"execute","Input"),"ex")
    connect(out_data(ne),find_pin(br,"Condition","Input"),"cond")

    # EMPTY: destroy if valid
    get_a=mge.add_get_member_variable_node(VAR)
    bel.set_node_pos(get_a,pos(X+700,Y+260))
    isv=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(isv,pos(X+950,Y+260))
    connect(out_data(get_a),find_pin(isv,"Object","Input"),"a->v")
    brv=mge.add_branch_node(); bel.set_node_pos(brv,pos(X+1200,Y+220))
    connect(find_pin(br,"else","Output"),find_pin(brv,"execute","Input"),"empty")
    connect(out_data(isv),find_pin(brv,"Condition","Input"),"v?")
    dest=mge.add_call_function_node("/Script/Engine.Actor:K2_DestroyActor")
    bel.set_node_pos(dest,pos(X+1450,Y+220))
    connect(find_pin(brv,"then","Output"),find_pin(dest,"execute","Input"),"->des")
    connect(out_data(get_a),find_pin(dest,"self","Input"),"a->des")
    set0=mge.add_set_member_variable_node(VAR)
    bel.set_node_pos(set0,pos(X+1750,Y+220))
    connect(find_pin(dest,"then","Output"),find_pin(set0,"execute","Input"),"des->clr")
    pr0=make_print(mge,X+2050,Y+220," ",dur="0.05",key="RestHeldMesh")
    connect(find_pin(set0,"then","Output"),find_pin(pr0,"execute","Input"),"clr->p")

    # HOLDING: if not valid spawn else update mesh
    get_a2=mge.add_get_member_variable_node(VAR)
    bel.set_node_pos(get_a2,pos(X+700,Y+40))
    isv2=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(isv2,pos(X+950,Y+40))
    connect(out_data(get_a2),find_pin(isv2,"Object","Input"),"a2->v")
    bre=mge.add_branch_node(); bel.set_node_pos(bre,pos(X+1200,Y))
    connect(find_pin(br,"then","Output"),find_pin(bre,"execute","Input"),"hold")
    connect(out_data(isv2),find_pin(bre,"Condition","Input"),"ex?")

    gpp=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(gpp,pos(X+1450,Y+60))
    setdef(find_pin(gpp,"PlayerIndex","Input"),"0")
    gal=mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(gal,pos(X+1700,Y+60))
    connect(out_data(gpp),find_pin(gal,"self","Input"),"pawn->loc")
    off=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(off,pos(X+1700,Y+180))
    setdef(find_pin(off,"X","Input"),"40.0")
    setdef(find_pin(off,"Y","Input"),"0.0")
    setdef(find_pin(off,"Z","Input"),"55.0")
    addv=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    bel.set_node_pos(addv,pos(X+1950,Y+100))
    connect(out_data(gal),find_pin(addv,"A","Input"),"A")
    connect(out_data(off),find_pin(addv,"B","Input"),"B")
    mktf=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeTransform")
    bel.set_node_pos(mktf,pos(X+2200,Y+100))
    connect(out_data(addv),find_pin(mktf,"Location","Input"),"tfL")
    setdef(find_pin(mktf,"Scale","Input"),"0.004000,0.004000,0.004000")

    spawn=mge.add_call_function_node("/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass")
    bel.set_node_pos(spawn,pos(X+2500,Y))
    setdef(find_pin(spawn,"ActorClass","Input"),"/Script/Engine.StaticMeshActor")
    connect(out_data(mktf),find_pin(spawn,"SpawnTransform","Input"),"tf->sp")
    connect(find_pin(bre,"else","Output"),find_pin(spawn,"execute","Input"),"miss->sp")

    finish=mge.add_call_function_node("/Script/Engine.GameplayStatics:FinishSpawningActor")
    bel.set_node_pos(finish,pos(X+2800,Y))
    connect(find_pin(spawn,"then","Output"),find_pin(finish,"execute","Input"),"sp->fi")
    connect(out_data(spawn),find_pin(finish,"Actor","Input"),"spA")
    connect(out_data(mktf),find_pin(finish,"SpawnTransform","Input"),"tf->fi")

    set_a=mge.add_set_member_variable_node(VAR)
    bel.set_node_pos(set_a,pos(X+3100,Y))
    connect(find_pin(finish,"then","Output"),find_pin(set_a,"execute","Input"),"fi->set")
    vp=find_pin(set_a,VAR,"Input")
    connect(out_data(finish),vp,"fi->var")
    log("set pin type="+str(vp.get_pin_type_display_string() if vp else None))

    attach=mge.add_call_function_node("/Script/Engine.Actor:K2_AttachToActor")
    bel.set_node_pos(attach,pos(X+3400,Y))
    connect(find_pin(set_a,"then","Output"),find_pin(attach,"execute","Input"),"set->att")
    connect(out_data(finish),find_pin(attach,"self","Input"),"dish")
    connect(out_data(gpp),find_pin(attach,"ParentActor","Input"),"parent")
    for pname,val in (("LocationRule","KeepRelative"),("RotationRule","KeepRelative"),("ScaleRule","KeepWorld")):
        p=find_pin(attach,pname,"Input")
        if p: setdef(p,val)

    set_rel=mge.add_call_function_node("/Script/Engine.Actor:K2_SetActorRelativeLocation")
    bel.set_node_pos(set_rel,pos(X+3700,Y))
    relv=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(relv,pos(X+3700,Y+140))
    setdef(find_pin(relv,"X","Input"),"40.0")
    setdef(find_pin(relv,"Y","Input"),"0.0")
    setdef(find_pin(relv,"Z","Input"),"55.0")
    connect(find_pin(attach,"then","Output"),find_pin(set_rel,"execute","Input"),"att->rel")
    connect(out_data(finish),find_pin(set_rel,"self","Input"),"relself")
    connect(out_data(relv),find_pin(set_rel,"NewLocation","Input") or find_pin(set_rel,"RelativeLocation","Input"),"relV")
    setdef(find_pin(set_rel,"bSweep","Input") or find_pin(set_rel,"Sweep","Input"),"false")

    def mesh_path(exec_pin, actor_node, x, y, tag):
        get_h2=mge.add_get_member_variable_node("HeldDishId")
        bel.set_node_pos(get_h2,pos(x,y+100))
        eq=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
        bel.set_node_pos(eq,pos(x+200,y+100))
        connect(out_data(get_h2),find_pin(eq,"A","Input"),tag+"A")
        setdef(find_pin(eq,"B","Input"),"1")
        brd=mge.add_branch_node(); bel.set_node_pos(brd,pos(x+420,y))
        connect(exec_pin,find_pin(brd,"execute","Input"),tag+"ex")
        connect(out_data(eq),find_pin(brd,"Condition","Input"),tag+"c")
        getc=mge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
        bel.set_node_pos(getc,pos(x+420,y+180))
        setdef(find_pin(getc,"ComponentClass","Input"),"/Script/Engine.StaticMeshComponent")
        connect(out_data(actor_node),find_pin(getc,"self","Input"),tag+"act")
        sets=mge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(sets,pos(x+700,y-40))
        connect(find_pin(brd,"then","Output"),find_pin(sets,"execute","Input"),tag+"sal")
        connect(out_data(getc),find_pin(sets,"self","Input"),tag+"smcS")
        setdef(find_pin(sets,"NewMesh","Input") or find_pin(sets,"StaticMesh","Input"),MESH_SALAD)
        setw=mge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(setw,pos(x+700,y+100))
        connect(find_pin(brd,"else","Output"),find_pin(setw,"execute","Input"),tag+"stew")
        connect(out_data(getc),find_pin(setw,"self","Input"),tag+"smcW")
        setdef(find_pin(setw,"NewMesh","Input") or find_pin(setw,"StaticMesh","Input"),MESH_STEW)
        pr=make_print(mge,x+1000,y,"Held mesh",dur="0.15",key="RestHeldMesh")
        connect(find_pin(sets,"then","Output"),find_pin(pr,"execute","Input"),tag+"ps")
        pr2=make_print(mge,x+1000,y+100,"Held mesh",dur="0.15",key="RestHeldMesh")
        connect(find_pin(setw,"then","Output"),find_pin(pr2,"execute","Input"),tag+"pw")

    mesh_path(find_pin(set_rel,"then","Output"), finish, X+4000, Y, "n")
    get_a3=mge.add_get_member_variable_node(VAR)
    bel.set_node_pos(get_a3,pos(X+1450,Y-220))
    mesh_path(find_pin(bre,"then","Output"), get_a3, X+1750, Y-280, "e")
    REPORT["ok"].append("v2_built")
    REPORT["var"]=VAR

# Retarget RestaurantTick and ClearHeld to call SyncHeldVisual_v2
def retarget_calls():
    # Find all CallFunction SyncHeldVisual (old) and SyncHeldVisual_v2
    rt=find_custom(mge,"RestaurantTick")
    ch=find_custom(mge,"ClearHeld")
    # Replace call nodes: add new calls
    call_rt=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual_v2")
    bel.set_node_pos(call_rt,pos(80,-1100))
    thenp=find_pin(rt,"then","Output")
    # Current: SyncHeldVisual -> RefreshOrderUI
    old_first=[c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
    log("RT old "+str([title(n) for n in old_first]))
    # If first is SyncHeldVisual (old), replace: break, RT->v2->(old's then target or Refresh)
    if thenp:
        try: thenp.break_pin_links()
        except: pass
        connect(thenp,find_pin(call_rt,"execute","Input"),"RT->v2")
        # Find RefreshOrderUI
        ref=None
        for n in mge.list_all_nodes():
            if title(n)=="RefreshOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
                ref=n; break
        if ref:
            # disconnect whatever feeds Refresh execute, then v2->Refresh
            ex=find_pin(ref,"execute","Input")
            if ex:
                try: ex.break_pin_links()
                except: pass
            connect(find_pin(call_rt,"then","Output"),ex,"v2->Refresh")
            REPORT["ok"].append("RT_v2")
        elif old_first:
            # follow old_first then
            old=old_first[0]
            otp=find_pin(old,"then","Output")
            tgts=list(otp.list_connected_pins() or []) if otp else []
            if tgts:
                connect(find_pin(call_rt,"then","Output"),tgts[0],"v2->oldNext")
            else:
                connect(find_pin(call_rt,"then","Output"),find_pin(old,"execute","Input"),"v2->old")

    # ClearHeld: append v2 at end (or replace old Sync)
    term=None; cur=ch; seen=set()
    last=find_pin(ch,"then","Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp=find_pin(cur,"then","Output")
        if not tp: break
        nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            term=tp; break
        # if next is SyncHeldVisual call, stop before it and replace
        if title(nxts[0])=="SyncHeldVisual":
            try: tp.break_pin_links()
            except: pass
            term=tp; break
        cur=nxts[0]
        last=tp
    if term is None:
        term=last
    call_c=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual_v2")
    bel.set_node_pos(call_c,pos(2000,-300))
    connect(term,find_pin(call_c,"execute","Input"),"Clear->v2")
    REPORT["ok"].append("Clear_v2")

retarget_calls()

# marker
if not find_custom(mge,"SeatHeld_v2"):
    mk=mge.add_custom_event_node("SeatHeld_v2")
    bel.set_node_pos(mk,pos(-1400,-2400))

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
                log("ERR "+title(n)+": "+str(em)[:100])
        except: pass

def walk(name,maxd=40):
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
REPORT["rt"]=walk("RestaurantTick")
REPORT["clear"]=walk("ClearHeld")
REPORT["v2"]=walk(NEW)

# Verify get pin type for VAR
for n in mge.list_all_nodes():
    if title(n)=="Get "+VAR:
        for p in bel.list_all_pins(n):
            REPORT.setdefault("get_pins",[]).append(str(p.get_pin_name())+" "+str(p.get_pin_type_display_string()))
        break

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_seat_held_fix2.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str)[:10000])
