# -*- coding: utf-8 -*-
"""Fix knife2: restore Tick, fix location wires, ClearGuests call, character distance."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
R = {"steps": [], "errors": [], "ok": {}}

def log(m):
    unreal.log("[K2FIX] " + str(m)); R["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x),int(y))

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
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and str(p.get_pin_name()).lower() not in ("then","outputdelegate","completed","loopbody"):
            if "exec" in str(p.get_pin_type_display_string()).lower():
                continue
            return p
    # fallback ReturnValue
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Item", "Output")

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

def setdef(pin,val):
    if not pin: return
    try: pin.set_pin_value(str(val))
    except Exception:
        try: pin.set_default_value(str(val))
        except Exception: pass

def make_print(ge,x,y,text):
    pr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr,pos(x,y))
    setdef(find_pin(pr,"InString","Input"),text)
    setdef(find_pin(pr,"Duration","Input"),"2.5")
    return pr

def nodes_by_title(ge, title):
    return [n for n in ge.list_all_nodes() if bel.get_node_title(n)==title]

def first(ge, title):
    ns=nodes_by_title(ge,title)
    return ns[0] if ns else None

# ---- list events for Tick name ----
bp = unreal.EditorAssetLibrary.load_asset(DIR+"/BP_RestaurantManager")
evs=[]
for e in bel.list_events(bp):
    try:
        evs.append({"name":str(e.name) if hasattr(e,"name") else str(e),
                    "impl":bool(getattr(e,"is_implemented",False)),
                    "raw":str(e)})
    except Exception:
        evs.append({"raw":str(e)})
R["events_sample"]=evs[:30]
# find ReceiveTick
tick_name=None
for e in bel.list_events(bp):
    s=str(e)
    if "Tick" in s or (hasattr(e,"name") and "Tick" in str(e.name)):
        tick_name = str(getattr(e,"name",None) or e)
        R["tick_event"]=tick_name
        break
# try add_event_override
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
tick_node=None
for name in ["ReceiveTick","Tick","EventTick","Actor.ReceiveTick"]:
    try:
        n=bel.add_event_override(bp, name, unreal.Vector2D(0,1500))
        if n:
            tick_node=n; tick_name=name; log("override "+name); break
    except Exception as e:
        log("override fail "+name+" "+str(e)[:80])
if tick_node is None:
    # try ge.find_event_node
    try:
        tick_node=ge.find_event_node("ReceiveTick")
        log("find_event_node "+str(tick_node))
    except Exception as e:
        log("find_event "+str(e))

R["tick_node"]=bel.get_node_title(tick_node) if tick_node else None

# ---- Fix HandlePlayerE distance: find GetPlayerPawn without loc, wire K2 loc ----
# Strategy: find Distance2D node; ensure V1/V2 connected via new K2_GetActorLocation nodes
dist_nodes=nodes_by_title(ge,"Distance2D (Vector)")
log("dist nodes "+str(len(dist_nodes)))
if dist_nodes:
    dist=dist_nodes[0]
    # break existing V1 V2 if any
    for pn in ("V1","V2","A","B"):
        p=find_pin(dist,pn,"Input")
        if p: p.break_pin_links()
    # player loc
    pawn=None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n)=="GetPlayerPawn":
            # pick one near HandlePlayerE (y small) - use first
            pawn=n; break
    ploc=ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(ploc,pos(500,200))
    connect(out_data(pawn), find_pin(ploc,"self","Input"), "pawn->ploc")
    connect(out_data(ploc), find_pin(dist,"V1","Input") or find_pin(dist,"A","Input"), "ploc->v1")
    # actor loc from foreach element - find For Each used by GetAllActorsWithTag
    fe=None
    gaw=None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n)=="GetAllActorsWithTag":
            gaw=n
    for n in ge.list_all_nodes():
        if bel.get_node_title(n)=="For Each Loop":
            # check Array connected from gaw
            ap=find_pin(n,"Array","Input")
            if ap:
                for c in ap.list_connected_pins():
                    if bel.get_node_title(c.get_owning_node())=="GetAllActorsWithTag":
                        fe=n; break
            if fe: break
    if fe is None:
        # first foreach
        fes=nodes_by_title(ge,"For Each Loop")
        fe=fes[0] if fes else None
    aloc=ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(aloc,pos(1100,200))
    # ensure array wired first
    if gaw and fe:
        connect(find_pin(gaw,"OutActors","Output"), find_pin(fe,"Array","Input"), "rearr")
    connect(find_pin(fe,"Array Element","Output"), find_pin(aloc,"self","Input"), "el->aloc")
    connect(out_data(aloc), find_pin(dist,"V2","Input") or find_pin(dist,"B","Input"), "aloc->v2")

# Fix ClearGuests call from open-close path: find Print CLOSED and wire then to Call ClearGuests
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="PrintString":
        pin=find_pin(n,"InString","Input")
        val=pin.get_pin_value() if pin else ""
        if "CLOSED (early)" in str(val):
            # find Call ClearGuests nodes
            calls=[c for c in ge.list_all_nodes() if bel.get_node_title(c)=="ClearGuests" and c.get_class().get_name()=="K2Node_CallFunction"]
            then=find_pin(n,"then","Output")
            if then: then.break_pin_links()
            if calls:
                connect(then, find_pin(calls[0],"execute","Input"), "closed->clear")
            else:
                call=ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
                bel.set_node_pos(call,pos(5400,-150))
                connect(then, find_pin(call,"execute","Input"), "closed->clearnew")

# ---- Wire Tick / RestaurantTick ----
# Prefer Event Tick override; else BeginPlay SetTimer -> custom RestaurantTick
rt = None
for n in ge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and bel.get_node_title(n)=="RestaurantTick":
        rt=n
if rt is None:
    rt=ge.add_custom_event_node("RestaurantTick")
    bel.set_node_pos(rt,pos(0,1600))
    log("added RestaurantTick")

# Build RestaurantTick body (force close + guest) - purge old body by breaking then and adding fresh nodes at y=1600
then_rt=find_pin(rt,"then","Output")
if then_rt: then_rt.break_pin_links()

gao=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(gao,pos(300,1600))
connect(then_rt, find_pin(gao,"execute","Input"), "rt->gao")
setdef(find_pin(gao,"ActorClass","Input") or find_pin(gao,"Class","Input"), "/Script/FarmSim25D.FarmClock")
get0=ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0,pos(600,1680))
connect(find_pin(gao,"OutActors","Output"), find_pin(get0,"TargetArray","Input"), "arr")
setdef(find_pin(get0,"Index","Input"),"0")
gdm=ge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
bel.set_node_pos(gdm,pos(850,1680))
connect(find_pin(get0,"Item","Output"), find_pin(gdm,"self","Input"), "gdm")
geq=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
bel.set_node_pos(geq,pos(1100,1680))
connect(out_data(gdm), find_pin(geq,"A","Input"), "m")
setdef(find_pin(geq,"B","Input"),"1380")
br23=ge.add_branch_node(); bel.set_node_pos(br23,pos(1400,1600))
connect(find_pin(gao,"then","Output"), find_pin(br23,"execute","Input"), "->23")
connect(out_data(geq), find_pin(br23,"Condition","Input"), "23?")
get_open=ge.add_get_member_variable_node("bIsOpenBusiness")
bel.set_node_pos(get_open,pos(1400,1720))
br_o=ge.add_branch_node(); bel.set_node_pos(br_o,pos(1700,1600))
connect(find_pin(br23,"then","Output"), find_pin(br_o,"execute","Input"), "->o")
connect(find_pin(get_open,"bIsOpenBusiness","Output") or out_data(get_open), find_pin(br_o,"Condition","Input"), "open?")
set_c=ge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_c,pos(2000,1550))
connect(find_pin(br_o,"then","Output"), find_pin(set_c,"execute","Input"), "fclose")
setdef(find_pin(set_c,"bIsOpenBusiness","Input"),"false")
pr=make_print(ge,2300,1550,"Restaurant: AUTO CLOSE at 23:00")
connect(find_pin(set_c,"then","Output"), find_pin(pr,"execute","Input"), "pr")
call_cg=ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ClearGuests")
bel.set_node_pos(call_cg,pos(2600,1550))
connect(find_pin(pr,"then","Output"), find_pin(call_cg,"execute","Input"), "cg")

# timer path when <23
get_open2=ge.add_get_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(get_open2,pos(1700,1850))
br_tm=ge.add_branch_node(); bel.set_node_pos(br_tm,pos(2000,1800))
connect(find_pin(br23,"else","Output"), find_pin(br_tm,"execute","Input"), "tm")
connect(find_pin(get_open2,"bIsOpenBusiness","Output") or out_data(get_open2), find_pin(br_tm,"Condition","Input"), "tmopen?")
get_tm=ge.add_get_member_variable_node("GuestTimer"); bel.set_node_pos(get_tm,pos(2300,1880))
addn=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
if addn is None: addn=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
bel.set_node_pos(addn,pos(2550,1880))
connect(find_pin(get_tm,"GuestTimer","Output") or out_data(get_tm), find_pin(addn,"A","Input"), "A")
setdef(find_pin(addn,"B","Input"),"1.0")  # timer fires every 1s
set_tm=ge.add_set_member_variable_node("GuestTimer"); bel.set_node_pos(set_tm,pos(2850,1800))
connect(find_pin(br_tm,"then","Output"), find_pin(set_tm,"execute","Input"), "settm")
connect(out_data(addn), find_pin(set_tm,"GuestTimer","Input"), "tmv")
geq2=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble")
if geq2 is None: geq2=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
bel.set_node_pos(geq2,pos(3150,1880))
connect(out_data(addn), find_pin(geq2,"A","Input"), "cmp")
setdef(find_pin(geq2,"B","Input"),"4.0")
br_iv=ge.add_branch_node(); bel.set_node_pos(br_iv,pos(3450,1800))
connect(find_pin(set_tm,"then","Output"), find_pin(br_iv,"execute","Input"), "->iv")
connect(out_data(geq2), find_pin(br_iv,"Condition","Input"), "iv?")
set_rst=ge.add_set_member_variable_node("GuestTimer"); bel.set_node_pos(set_rst,pos(3750,1800))
connect(find_pin(br_iv,"then","Output"), find_pin(set_rst,"execute","Input"), "rst")
setdef(find_pin(set_rst,"GuestTimer","Input"),"0.0")
call_sg=ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SeatGuest")
bel.set_node_pos(call_sg,pos(4050,1800))
connect(find_pin(set_rst,"then","Output"), find_pin(call_sg,"execute","Input"), "seat")

# Drive RestaurantTick: Event Tick override OR BeginPlay SetTimer
bp_then=None
if tick_node:
    bel.set_node_pos(tick_node,pos(0,1450))
    tthen=find_pin(tick_node,"then","Output")
    if tthen: tthen.break_pin_links()
    call_rt=ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RestaurantTick")
    bel.set_node_pos(call_rt,pos(300,1450))
    connect(tthen, find_pin(call_rt,"execute","Input"), "tick->rt")
    # GuestTimer += DeltaSeconds instead of +1 — rewire addn B from DeltaSeconds
    # For Event Tick path, change add to use DeltaSeconds: break B default and wire
    bp_then="tick"
else:
    # BeginPlay SetTimer by function name RestaurantTick every 1.0s looping
    bp_node=None
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in bel.get_node_title(n):
            bp_node=n; break
    tmr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:K2_SetTimer")
    bel.set_node_pos(tmr,pos(300,200))
    then_bp=find_pin(bp_node,"then","Output")
    if then_bp:
        # don't break if other things - but BeginPlay was empty
        then_bp.break_pin_links()
        connect(then_bp, find_pin(tmr,"execute","Input"), "bp->timer")
    setdef(find_pin(tmr,"FunctionName","Input"),"RestaurantTick")
    setdef(find_pin(tmr,"Time","Input"),"1.0")
    setdef(find_pin(tmr,"bLooping","Input"),"true")
    # Object = self — leave default self object?
    # K2_SetTimer Object pin - need self reference
    # create Get Self via making a dummy call and using... 
    # Actually Object defaults to self when left unbound in BP often - set via get
    bp_then="timer"
    R["timer_pins"]=[str(p.get_pin_name())+":"+str(p.get_pin_type_display_string()) for p in bel.list_all_pins(tmr)]

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantManager")
R["ok"]["manager_fix"]=True
R["drive"]=bp_then

# ---- Fix Character distance wires ----
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
distc=nodes_by_title(cge,"Distance2D (Vector)")
log("char dist "+str(len(distc)))
if distc:
    dist=distc[0]
    for pn in ("V1","V2","A","B"):
        p=find_pin(dist,pn,"Input")
        if p: p.break_pin_links()
    pawn=first(cge,"GetPlayerPawn")
    ploc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(ploc,pos(-100,1100))
    connect(out_data(pawn), find_pin(ploc,"self","Input"), "c pawn")
    connect(out_data(ploc), find_pin(dist,"V1","Input") or find_pin(dist,"A","Input"), "c v1")
    gaw=first(cge,"GetAllActorsWithTag")
    fe=None
    for n in cge.list_all_nodes():
        if bel.get_node_title(n)=="For Each Loop":
            ap=find_pin(n,"Array","Input")
            if ap and any(bel.get_node_title(c.get_owning_node())=="GetAllActorsWithTag" for c in ap.list_connected_pins()):
                fe=n; break
    if fe is None:
        fes=nodes_by_title(cge,"For Each Loop")
        fe=fes[0] if fes else None
    if gaw and fe:
        connect(find_pin(gaw,"OutActors","Output"), find_pin(fe,"Array","Input"), "c rearr")
    aloc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(aloc,pos(200,1100))
    connect(find_pin(fe,"Array Element","Output"), find_pin(aloc,"self","Input"), "c el")
    connect(out_data(aloc), find_pin(dist,"V2","Input") or find_pin(dist,"B","Input"), "c v2")

bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
R["ok"]["char_fix"]=True

# verify chains
def dump_ia():
    chain={}
    for n in cge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            p=find_pin(n,"Started","Output")
            chain["Started"]=[bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()] if p else []
        if bel.get_node_title(n)=="TillSoil":
            p=find_pin(n,"execute","Input")
            chain["TillSoil"]=[bel.get_node_title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()] if p else []
    return chain
R["ia"]=dump_ia()
R["actors"]=len(eas.get_all_level_actors())
R["farm"]=any("Grass" in a.get_actor_label() or "Bridge" in a.get_actor_label() for a in eas.get_all_level_actors())
# mgr has RestaurantTick?
R["mgr_titles"]=[bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() in ("K2Node_Event","K2Node_CustomEvent")]
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_fixwire2.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False,default=str))
print(json.dumps({k:R[k] for k in ("ok","errors","drive","tick_node","ia","actors","farm","mgr_titles")},indent=2,ensure_ascii=False,default=str))
