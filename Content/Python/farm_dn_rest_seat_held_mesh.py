# -*- coding: utf-8 -*-
"""Held dish via Manager StaticMeshComponent (no Actor var). Keep chair seating.
Also purge orphan GetAllActors errors; wire SyncHeldMesh into RT/ClearHeld.
"""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
REPORT={"steps":[],"errors":[],"ok":[]}

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
MESH_SALAD="/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket"
MESH_STEW="/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"
mbp=unreal.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp,"EventGraph"))
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary

def log(m):
    unreal.log("[HELDMESH] "+str(m)); print("[HELDMESH] "+str(m)); REPORT["steps"].append(str(m))

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
    for name in ("ReturnValue","Return Value","HeldDishId","HeldDishMesh"):
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

def make_print(ge,x,y,text,dur="0.15",key=""):
    pr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr,pos(x,y))
    setdef(find_pin(pr,"InString","Input"),text)
    setdef(find_pin(pr,"Duration","Input"),dur)
    if key: setdef(find_pin(pr,"Key","Input"),key)
    return pr

# ---- 0) Add HeldDishMesh StaticMeshComponent on Manager ----
handles=list(sub.k2_gather_subobject_data_for_blueprint(mbp) or [])
root_h=None; mesh_obj=None
for h in handles:
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        if lib.is_root_component(data):
            root_h=h
        vname=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        if vname=="HeldDishMesh" or (obj and "StaticMeshComponent" in obj.get_class().get_name() and vname=="HeldDishMesh"):
            mesh_obj=obj
    except Exception as e:
        log("scan "+str(e)[:60])

if mesh_obj is None:
    params=unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", root_h if root_h else handles[0])
    params.set_editor_property("new_class", unreal.StaticMeshComponent)
    params.set_editor_property("blueprint_context", mbp)
    new_h, _fail = None, None
    try:
        res=sub.add_new_subobject(params)
        # return may be handle or tuple
        if isinstance(res, tuple):
            new_h=res[0]
        else:
            new_h=res
        try: sub.rename_subobject(new_h, unreal.Text("HeldDishMesh"))
        except Exception as e: log("rename "+str(e)[:60])
        data=sub.k2_find_subobject_data_from_handle(new_h)
        mesh_obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        log("added HeldDishMesh "+str(mesh_obj))
        REPORT["ok"].append("comp")
    except Exception as e:
        REPORT["errors"].append("addcomp "+str(e)[:120]); log("addcomp "+str(e)[:120])

if mesh_obj:
    basket=eas.load_asset(MESH_SALAD)
    try:
        mesh_obj.set_editor_property("static_mesh", basket)
    except Exception as e:
        log("mesh "+str(e)[:60])
    try:
        mesh_obj.set_editor_property("relative_scale3d", unreal.Vector(0.004,0.004,0.004))
    except Exception as e:
        log("scale "+str(e)[:60])
    try:
        mesh_obj.set_editor_property("visibility", False)
        mesh_obj.set_hidden_in_game(True)
    except Exception as e:
        log("vis "+str(e)[:60])
    try:
        mesh_obj.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception: pass

# ---- 1) Break orphan error nodes (GetAllActors / mismatched Get) ----
for n in list(mge.list_all_nodes()):
    try:
        em=n.get_editor_property("error_msg")
    except Exception:
        em=None
    if not em or not str(em).strip():
        continue
    t=title(n)
    if "GetAllActors" in t or t=="Get" or "HeldDishActor" in t:
        for p in bel.list_all_pins(n):
            try: p.break_pin_links()
            except Exception: pass
        log("broke orphan "+t+": "+str(em)[:80])
        REPORT["ok"].append("broke_"+t)

# Also break old SyncHeldVisual / SyncHeldVisual_v2 call chains from RT to avoid double
# We'll wire SyncHeldMesh instead.

# ---- 2) Build SyncHeldMesh custom event ----
NAME="SyncHeldMesh"
if find_custom(mge,NAME):
    log("SyncHeldMesh exists — skip rebuild")
else:
    sync=mge.add_custom_event_node(NAME)
    bel.set_node_pos(sync,pos(-1600,-3000))
    Y=-3000; X=-1300

    get_h=mge.add_get_member_variable_node("HeldDishId")
    bel.set_node_pos(get_h,pos(X,Y+100))
    ne=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
    bel.set_node_pos(ne,pos(X+220,Y+100))
    connect(out_data(get_h),find_pin(ne,"A","Input"),"hA")
    setdef(find_pin(ne,"B","Input"),"0")
    br=mge.add_branch_node(); bel.set_node_pos(br,pos(X+450,Y))
    connect(find_pin(sync,"then","Output"),find_pin(br,"execute","Input"),"ex")
    connect(out_data(ne),find_pin(br,"Condition","Input"),"cond")

    get_mesh=mge.add_get_member_variable_node("HeldDishMesh")
    bel.set_node_pos(get_mesh,pos(X+450,Y+200))

    # EMPTY: hide
    hide=mge.add_call_function_node("/Script/Engine.SceneComponent:SetVisibility")
    bel.set_node_pos(hide,pos(X+750,Y+220))
    connect(find_pin(br,"else","Output"),find_pin(hide,"execute","Input"),"empty->hide")
    connect(out_data(get_mesh),find_pin(hide,"self","Input"),"mesh->hide")
    setdef(find_pin(hide,"bNewVisibility","Input") or find_pin(hide,"NewVisibility","Input"),"false")
    setdef(find_pin(hide,"bPropagateToChildren","Input"),"false")
    pr0=make_print(mge,X+1050,Y+220," ",key="RestHeldMesh")
    connect(find_pin(hide,"then","Output"),find_pin(pr0,"execute","Input"),"hide->p")

    # HOLDING: show + set mesh + teleport to player
    get_mesh2=mge.add_get_member_variable_node("HeldDishMesh")
    bel.set_node_pos(get_mesh2,pos(X+700,Y+40))
    show=mge.add_call_function_node("/Script/Engine.SceneComponent:SetVisibility")
    bel.set_node_pos(show,pos(X+950,Y))
    connect(find_pin(br,"then","Output"),find_pin(show,"execute","Input"),"hold->show")
    connect(out_data(get_mesh2),find_pin(show,"self","Input"),"mesh->show")
    setdef(find_pin(show,"bNewVisibility","Input") or find_pin(show,"NewVisibility","Input"),"true")
    setdef(find_pin(show,"bPropagateToChildren","Input"),"false")

    # dish id -> mesh
    get_h2=mge.add_get_member_variable_node("HeldDishId")
    bel.set_node_pos(get_h2,pos(X+1200,Y+120))
    eq=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq,pos(X+1420,Y+120))
    connect(out_data(get_h2),find_pin(eq,"A","Input"),"eqA")
    setdef(find_pin(eq,"B","Input"),"1")
    brd=mge.add_branch_node(); bel.set_node_pos(brd,pos(X+1650,Y))
    connect(find_pin(show,"then","Output"),find_pin(brd,"execute","Input"),"show->dish")
    connect(out_data(eq),find_pin(brd,"Condition","Input"),"salad?")

    get_mesh3=mge.add_get_member_variable_node("HeldDishMesh")
    bel.set_node_pos(get_mesh3,pos(X+1650,Y+200))
    sets=mge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
    bel.set_node_pos(sets,pos(X+1900,Y-40))
    connect(find_pin(brd,"then","Output"),find_pin(sets,"execute","Input"),"salad")
    connect(out_data(get_mesh3),find_pin(sets,"self","Input"),"smcS")
    setdef(find_pin(sets,"NewMesh","Input") or find_pin(sets,"StaticMesh","Input"),MESH_SALAD)

    setw=mge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
    bel.set_node_pos(setw,pos(X+1900,Y+100))
    connect(find_pin(brd,"else","Output"),find_pin(setw,"execute","Input"),"stew")
    connect(out_data(get_mesh3),find_pin(setw,"self","Input"),"smcW")
    setdef(find_pin(setw,"NewMesh","Input") or find_pin(setw,"StaticMesh","Input"),MESH_STEW)

    # After either mesh set: move to player (duplicate teleport on both)
    def teleport(exec_pin, x, y, tag):
        gpp=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
        bel.set_node_pos(gpp,pos(x,y+40))
        setdef(find_pin(gpp,"PlayerIndex","Input"),"0")
        gal=mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
        bel.set_node_pos(gal,pos(x+250,y+40))
        connect(out_data(gpp),find_pin(gal,"self","Input"),tag+"pawn")
        off=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(off,pos(x+250,y+160))
        setdef(find_pin(off,"X","Input"),"40.0")
        setdef(find_pin(off,"Y","Input"),"0.0")
        setdef(find_pin(off,"Z","Input"),"70.0")
        addv=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
        bel.set_node_pos(addv,pos(x+500,y+80))
        connect(out_data(gal),find_pin(addv,"A","Input"),tag+"A")
        connect(out_data(off),find_pin(addv,"B","Input"),tag+"B")
        getm=mge.add_get_member_variable_node("HeldDishMesh")
        bel.set_node_pos(getm,pos(x+500,y+200))
        # SetWorldLocation on SceneComponent
        swl=mge.add_call_function_node("/Script/Engine.SceneComponent:K2_SetWorldLocation")
        bel.set_node_pos(swl,pos(x+750,y))
        connect(exec_pin,find_pin(swl,"execute","Input"),tag+"ex")
        connect(out_data(getm),find_pin(swl,"self","Input"),tag+"self")
        connect(out_data(addv),find_pin(swl,"NewLocation","Input"),tag+"loc")
        setdef(find_pin(swl,"bSweep","Input") or find_pin(swl,"Sweep","Input"),"false")
        # scale
        ssc=mge.add_call_function_node("/Script/Engine.SceneComponent:SetWorldScale3D")
        bel.set_node_pos(ssc,pos(x+1050,y))
        scv=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(scv,pos(x+1050,y+140))
        setdef(find_pin(scv,"X","Input"),"0.004")
        setdef(find_pin(scv,"Y","Input"),"0.004")
        setdef(find_pin(scv,"Z","Input"),"0.004")
        connect(find_pin(swl,"then","Output"),find_pin(ssc,"execute","Input"),tag+"->sc")
        connect(out_data(getm),find_pin(ssc,"self","Input"),tag+"scself")
        connect(out_data(scv),find_pin(ssc,"NewScale","Input") or find_pin(ssc,"Scale","Input"),tag+"scv")
        pr=make_print(mge,x+1350,y,"Held mesh",key="RestHeldMesh")
        connect(find_pin(ssc,"then","Output"),find_pin(pr,"execute","Input"),tag+"p")

    teleport(find_pin(sets,"then","Output"), X+2200, Y-40, "s")
    teleport(find_pin(setw,"then","Output"), X+2200, Y+140, "w")
    REPORT["ok"].append("SyncHeldMesh")

# ---- 3) Wire RestaurantTick: SyncHeldMesh -> RefreshOrderUI (and keep old FX) ----
rt=find_custom(mge,"RestaurantTick")
call=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldMesh")
bel.set_node_pos(call,pos(60,-1200))
thenp=find_pin(rt,"then","Output") if rt else None
# Find RefreshOrderUI
ref=None
for n in mge.list_all_nodes():
    if title(n)=="RefreshOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
        ref=n; break

if thenp:
    # Capture current first targets
    old=[c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
    log("RT was "+str([title(o) for o in old]))
    try: thenp.break_pin_links()
    except: pass
    connect(thenp,find_pin(call,"execute","Input"),"RT->Mesh")
    # Prefer: Mesh -> RefreshOrderUI if Refresh's execute is free or we steal it
    if ref:
        rex=find_pin(ref,"execute","Input")
        # Who feeds Refresh?
        feeders=[c.get_owning_node() for c in (rex.list_connected_pins() or [])] if rex else []
        log("Refresh feeders "+str([title(f) for f in feeders]))
        if rex:
            try: rex.break_pin_links()
            except: pass
        connect(find_pin(call,"then","Output"),rex,"Mesh->Refresh")
        # If old first was SyncHeldVisual and its then went to Refresh, done.
        # If old first was Refresh itself, also done.
        # If old first was something else (e.g. Branch held FX), chain Refresh.then -> that? 
        # Current verify had RT: Refresh -> Branch(held debug). So Refresh.then should already go to Branch.
        REPORT["ok"].append("RT_mesh")
    elif old:
        connect(find_pin(call,"then","Output"),find_pin(old[0],"execute","Input"),"Mesh->old")

# ClearHeld append SyncHeldMesh
ch=find_custom(mge,"ClearHeld")
if ch:
    cur=ch; seen=set(); term=find_pin(ch,"then","Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp=find_pin(cur,"then","Output")
        if not tp: break
        nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            term=tp; break
        # stop before old SyncHeld* calls
        if title(nxts[0]) in ("SyncHeldVisual","SyncHeldVisual_v2","SyncHeldMesh"):
            try: tp.break_pin_links()
            except: pass
            term=tp; break
        cur=nxts[0]
    call_c=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldMesh")
    bel.set_node_pos(call_c,pos(2100,-350))
    connect(term,find_pin(call_c,"execute","Input"),"Clear->Mesh")
    REPORT["ok"].append("Clear_mesh")

if not find_custom(mge,"SeatHeld_v3"):
    mk=mge.add_custom_event_node("SeatHeld_v3")
    bel.set_node_pos(mk,pos(-1800,-3200))

bel.compile_blueprint(mbp)
mst=str(mbp.get_editor_property("status"))
REPORT["mgr_status"]=mst
log("mgr "+mst)
errs=[]
for n in mge.list_all_nodes():
    try:
        em=n.get_editor_property("error_msg")
        if em and str(em).strip():
            errs.append(title(n)+":"+str(em)[:140])
    except: pass
REPORT["compile_errs"]=errs
if "ERROR" not in mst:
    eas.save_asset(MGR)
else:
    for e in errs: log("ERR "+e)

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
REPORT["sync"]=walk(NAME)

# Confirm chair offset still good
tbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp,"EventGraph"))
bel.compile_blueprint(tbp)
REPORT["table_status"]=str(tbp.get_editor_property("status"))
# Guest still ok
gbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestGuest")
bel.compile_blueprint(gbp)
REPORT["guest_status"]=str(gbp.get_editor_property("status"))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_seat_held_mesh.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str))
print(json.dumps(REPORT,indent=2,ensure_ascii=False,default=str)[:9000])
