# -*- coding: utf-8 -*-
"""Knife2 fix: OpenSign interact + character E with pure GetPlayerPawn + cast."""
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "errors": [], "fixes": {}}

def log(m):
    unreal.log("[REST_K2F] " + str(m)); REPORT["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

def setdef(pin,val):
    if not pin: return
    for fn in ("set_default_value","set_pin_value"):
        try: getattr(pin,fn)(str(val)); return
        except Exception: pass

def pin_type(category, sub=""):
    p=unreal.EdGraphPinType()
    if sub: p.import_text('(PinCategory="{}",PinSubCategory="{}")'.format(category,sub))
    else: p.import_text('(PinCategory="{}")'.format(category))
    return p

def dump_pins(node, label):
    pins=[]
    for p in bel.list_all_pins(node):
        pins.append("{}:{}".format(p.get_pin_name(), p.get_pin_direction()))
    log(label+" pins="+str(pins))
    return pins

def make_print(ge,x,y,text,dur="2.5"):
    pr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr,pos(x,y))
    setdef(find_pin(pr,"InString","Input"), text)
    setdef(find_pin(pr,"Duration","Input"), dur)
    return pr

def make_return(ge,x,y):
    try: r=ge.add_return_node()
    except Exception:
        r=ge.create_node_from_name("Return Node", unreal.Vector2D(x,y), [])
    bel.set_node_pos(r,pos(x,y)); return r

# ---- Fix OpenSign: create RestaurantInteract via event graph create_and_edit ----
def fix_opensign():
    bp=unreal.EditorAssetLibrary.load_asset(DIR+"/BP_RestaurantOpenSign")
    # ensure var
    names=[str(n) for n in bel.list_member_variable_names(bp)]
    if "bIsOpenBusiness" not in names:
        bel.add_member_variable(bp,"bIsOpenBusiness", pin_type("bool"))

    ge=None; g=bel.find_graph(bp,"RestaurantInteract")
    if g is None:
        try:
            eg=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            eg.create_and_edit_function_graph("RestaurantInteract")
            g=bel.find_graph(bp,"RestaurantInteract")
            log("created RestaurantInteract via create_and_edit")
        except Exception as e:
            try:
                bel.add_function_graph(bp,"RestaurantInteract")
                g=bel.find_graph(bp,"RestaurantInteract")
                log("created via add_function_graph")
            except Exception as e2:
                REPORT["errors"].append("opensign create "+str(e)+" / "+str(e2))
                return False
    ge=unreal.BlueprintGraphEditor.get_graph_editor(g) if g else None
    if not ge:
        REPORT["errors"].append("opensign no ge")
        return False

    # clear body
    kill=[]
    entry=None
    for n in ge.list_all_nodes():
        cn=n.get_class().get_name()
        if cn=="K2Node_FunctionEntry": entry=n; continue
        if cn=="K2Node_FunctionResult": continue
        kill.append(n)
    if kill: ge.remove_nodes(kill)

    then0=find_pin(entry,"then","Output") or find_pin(entry,"execute","Output")

    # Simpler OpenSign logic without fragile cast of Manager:
    # Get FarmClock -> GetDisplayMinutes -> branches -> set bIsOpenBusiness on self + Print
    # Manager sync: GetAllActorsOfClass Manager + ForEach Set via create_node

    gao=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao,pos(250,0))
    connect(then0, find_pin(gao,"execute","Input"), "e->gao")
    setdef(find_pin(gao,"ActorClass","Input") or find_pin(gao,"Class","Input"), "/Script/FarmSim25D.FarmClock")

    get0=ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0,pos(500,80))
    connect(find_pin(gao,"OutActors","Output"), find_pin(get0,"TargetArray","Input") or find_pin(get0,"Array","Input"), "arr")
    setdef(find_pin(get0,"Index","Input"),"0")
    dump_pins(get0,"Array_Get")

    cast_fc=None
    for cname in ("Cast To FarmClock",):
        try: cast_fc=ge.create_node_from_name(cname, unreal.Vector2D(750,0), [])
        except Exception as e: log("castfc "+str(e))
    if not cast_fc:
        # Fallback: Print minutes unavailable, still toggle with warning
        pr=make_print(ge,750,0,"Restaurant SIGN E: FarmClock cast missing — toggle local only")
        connect(find_pin(gao,"then","Output"), find_pin(pr,"execute","Input"), "fb")
        get_open=ge.add_get_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(get_open,pos(1000,80))
        notb=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
        bel.set_node_pos(notb,pos(1200,80))
        connect(find_pin(get_open,"bIsOpenBusiness","Output"), find_pin(notb,"A","Input"), "not")
        seto=ge.add_set_member_variable_node("bIsOpenBusiness")
        bel.set_node_pos(seto,pos(1450,0))
        connect(find_pin(pr,"then","Output"), find_pin(seto,"execute","Input"), "->set")
        connect(find_pin(notb,"ReturnValue","Output"), find_pin(seto,"bIsOpenBusiness","Input"), "val")
        ret=make_return(ge,1750,0)
        connect(find_pin(seto,"then","Output"), find_pin(ret,"execute","Input"), "ret")
        bel.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantOpenSign")
        REPORT["fixes"]["opensign"]="toggle_no_clock"
        return True

    bel.set_node_pos(cast_fc,pos(750,0))
    connect(find_pin(gao,"then","Output"), find_pin(cast_fc,"execute","Input"), "->cast")
    # Array_Get output pin name varies
    item=find_pin(get0,"Item","Output") or find_pin(get0,"Output","Output") or find_pin(get0,"ReturnValue","Output")
    if item is None:
        for p in bel.list_all_pins(get0):
            if "output" in str(p.get_pin_direction()).lower() and str(p.get_pin_name()).lower() not in ("self",):
                item=p; break
    connect(item, find_pin(cast_fc,"Object","Input"), "obj")

    gdm=ge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
    bel.set_node_pos(gdm,pos(1050,100))
    as_fc=None
    for p in bel.list_all_pins(cast_fc):
        if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
            as_fc=p; break
    connect(as_fc, find_pin(gdm,"self","Input"), "fc->gdm")

    get_open=ge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open,pos(1050,220))

    br_open=ge.add_branch_node(); bel.set_node_pos(br_open,pos(1350,0))
    connect(find_pin(cast_fc,"then","Output"), find_pin(br_open,"execute","Input"), "->brO")
    connect(find_pin(get_open,"bIsOpenBusiness","Output"), find_pin(br_open,"Condition","Input"), "open?")

    # CLOSE path
    set_c=ge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_c,pos(1650,-150))
    connect(find_pin(br_open,"then","Output"), find_pin(set_c,"execute","Input"), "close")
    setdef(find_pin(set_c,"bIsOpenBusiness","Input"),"false")
    pr_c=make_print(ge,1950,-150,"Restaurant: CLOSED (early). Seating stopped.")
    connect(find_pin(set_c,"then","Output"), find_pin(pr_c,"execute","Input"), "prc")
    # sync manager open=false
    _sync_mgr(ge, find_pin(pr_c,"then","Output"), 2250, -150, False)
    ret_c=make_return(ge,3200,-150)
    # connect ret from sync completed if available else pr
    connect(REPORT.get("_last_then") or find_pin(pr_c,"then","Output"), find_pin(ret_c,"execute","Input"), "retC")

    # LATE >=1380
    geq=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
    bel.set_node_pos(geq,pos(1650,80))
    connect(find_pin(gdm,"ReturnValue","Output"), find_pin(geq,"A","Input"), "m")
    setdef(find_pin(geq,"B","Input"),"1380")
    br_late=ge.add_branch_node(); bel.set_node_pos(br_late,pos(1900,80))
    connect(find_pin(br_open,"else","Output"), find_pin(br_late,"execute","Input"), "->late")
    connect(find_pin(geq,"ReturnValue","Output"), find_pin(br_late,"Condition","Input"), "late?")
    pr_l=make_print(ge,2200,40,"Restaurant: too late (>=23:00), cannot open")
    connect(find_pin(br_late,"then","Output"), find_pin(pr_l,"execute","Input"), "late")
    ret_l=make_return(ge,2500,40)
    connect(find_pin(pr_l,"then","Output"), find_pin(ret_l,"execute","Input"), "retL")

    # EARLY <1020
    lt=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_IntInt")
    bel.set_node_pos(lt,pos(2200,200))
    connect(find_pin(gdm,"ReturnValue","Output"), find_pin(lt,"A","Input"), "m")
    setdef(find_pin(lt,"B","Input"),"1020")
    br_e=ge.add_branch_node(); bel.set_node_pos(br_e,pos(2450,200))
    connect(find_pin(br_late,"else","Output"), find_pin(br_e,"execute","Input"), "->early")
    connect(find_pin(lt,"ReturnValue","Output"), find_pin(br_e,"Condition","Input"), "early?")
    pr_e=make_print(ge,2750,160,"Restaurant: too early (<17:00), cannot open")
    connect(find_pin(br_e,"then","Output"), find_pin(pr_e,"execute","Input"), "early")
    ret_e=make_return(ge,3050,160)
    connect(find_pin(pr_e,"then","Output"), find_pin(ret_e,"execute","Input"), "retE")

    # OPEN
    set_o=ge.add_set_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(set_o,pos(2750,320))
    connect(find_pin(br_e,"else","Output"), find_pin(set_o,"execute","Input"), "open")
    setdef(find_pin(set_o,"bIsOpenBusiness","Input"),"true")
    pr_o=make_print(ge,3050,320,"Restaurant: OPEN! Guests will arrive every ~4s if tables free.")
    connect(find_pin(set_o,"then","Output"), find_pin(pr_o,"execute","Input"), "pro")
    _sync_mgr(ge, find_pin(pr_o,"then","Output"), 3350, 320, True)
    ret_o=make_return(ge,4300,320)
    connect(REPORT.get("_last_then") or find_pin(pr_o,"then","Output"), find_pin(ret_o,"execute","Input"), "retO")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantOpenSign")
    REPORT["fixes"]["opensign"]="clock_gate_ok"
    log("OpenSign OK")
    return True

def _sync_mgr(ge, then_pin, x, y, open_val):
    """Sync Manager.bIsOpenBusiness; sets REPORT['_last_then'] to Completed/then."""
    REPORT["_last_then"]=then_pin
    gao=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao,pos(x,y))
    connect(then_pin, find_pin(gao,"execute","Input"), "->mgrs")
    setdef(find_pin(gao,"ActorClass","Input") or find_pin(gao,"Class","Input"),
           "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    fe=None
    try: fe=ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        try: fe=ge.create_node_from_name("ForEachLoop", unreal.Vector2D(x+280,y), [])
        except Exception as e: log("fe "+str(e)); REPORT["_last_then"]=find_pin(gao,"then","Output"); return
    bel.set_node_pos(fe,pos(x+280,y))
    connect(find_pin(gao,"then","Output"), find_pin(fe,"Exec","Input") or find_pin(fe,"execute","Input"), "fe")
    connect(find_pin(gao,"OutActors","Output"), find_pin(fe,"Array","Input"), "arr")
    cast_m=None
    try: cast_m=ge.create_node_from_name("Cast To BP_RestaurantManager", unreal.Vector2D(x+560,y-40), [])
    except Exception as e: log("castm "+str(e))
    if not cast_m:
        REPORT["_last_then"]=find_pin(fe,"Completed","Output") or find_pin(gao,"then","Output")
        return
    bel.set_node_pos(cast_m,pos(x+560,y-40))
    connect(find_pin(fe,"LoopBody","Output") or find_pin(fe,"Then","Output"), find_pin(cast_m,"execute","Input"), "body")
    connect(find_pin(fe,"Array Element","Output") or find_pin(fe,"Element","Output"), find_pin(cast_m,"Object","Input"), "el")
    setn=None
    try: setn=ge.create_node_from_name("Set bIsOpenBusiness", unreal.Vector2D(x+860,y-40), [])
    except Exception as e: log("setm "+str(e))
    if setn:
        bel.set_node_pos(setn,pos(x+860,y-40))
        connect(find_pin(cast_m,"then","Output"), find_pin(setn,"execute","Input"), "set")
        as_m=None
        for p in bel.list_all_pins(cast_m):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_m=p; break
        connect(as_m, find_pin(setn,"self","Input") or find_pin(setn,"Target","Input"), "as")
        setdef(find_pin(setn,"bIsOpenBusiness","Input"), "true" if open_val else "false")
    REPORT["_last_then"]=find_pin(fe,"Completed","Output") or find_pin(gao,"then","Output")


# ---- Fix character E: pure GetPlayerPawn ----
def fix_character():
    cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
    cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    ia=till=None
    for n in cge.list_all_nodes():
        t=bel.get_node_title(n)
        if "IA_Interact" in t: ia=n
        if t=="TillSoil": till=n
    started=find_pin(ia,"Started","Output")

    # wipe restaurant helpers again
    kill=[]
    if started:
        stack=list(started.list_connected_pins()); seen=set()
        while stack:
            p=stack.pop(0); n=p.get_owning_node()
            if id(n) in seen: continue
            seen.add(id(n)); t=bel.get_node_title(n)
            if t=="TillSoil" or "IA_Interact" in t: continue
            kill.append(n)
            for pp in bel.list_all_pins(n):
                for cp in pp.list_connected_pins(): stack.append(cp)
    for n in list(cge.list_all_nodes()):
        t=bel.get_node_title(n)
        if any(k in t for k in ("GetAllActorsWithTag","For Each Loop","Cast To BP_Restaurant","RestaurantInteract","bRestEHandled","Distance2D","GetPlayerPawn","Not_PreBool","Less_")):
            if t!="TillSoil" and "IA_Interact" not in t:
                kill.append(n)
    kill=[n for n in kill if bel.get_node_title(n)!="TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
    kill=list({id(n):n for n in kill}.values())
    if kill: cge.remove_nodes(kill); log("cleaned "+str(len(kill)))

    if started:
        for cp in list(started.list_connected_pins()):
            try: started.break_link_to(cp)
            except Exception: pass

    # Started -> Set false -> GetAllActorsWithTag (GetPlayerPawn PURE for loc)
    set_f=cge.add_set_member_variable_node("bRestEHandled"); bel.set_node_pos(set_f,pos(-2200,1000))
    connect(started, find_pin(set_f,"execute","Input"), "IA->setF")
    setdef(find_pin(set_f,"bRestEHandled","Input"),"false")

    get_pawn=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(get_pawn,pos(-1900,1200))
    dump_pins(get_pawn,"GetPlayerPawn")
    setdef(find_pin(get_pawn,"PlayerIndex","Input"),"0")
    # If it has execute, use it; else pure
    pawn_exec_in=find_pin(get_pawn,"execute","Input")
    pawn_then=find_pin(get_pawn,"then","Output")

    gat=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gat,pos(-1600,1000))
    setdef(find_pin(gat,"Tag","Input"),"RestInteract")

    if pawn_exec_in and pawn_then:
        connect(find_pin(set_f,"then","Output"), pawn_exec_in, "->pawn")
        connect(pawn_then, find_pin(gat,"execute","Input"), "pawn->gat")
    else:
        connect(find_pin(set_f,"then","Output"), find_pin(gat,"execute","Input"), "->gat (pawn pure)")

    pawn_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(pawn_loc,pos(-1600,1200))
    connect(find_pin(get_pawn,"ReturnValue","Output"), find_pin(pawn_loc,"self","Input"), "pawn.self")

    fe=None
    try: fe=cge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    except Exception:
        fe=cge.create_node_from_name("ForEachLoop", unreal.Vector2D(-1300,1000), [])
    if not fe:
        connect(started, find_pin(till,"execute","Input"), "ROLLBACK")
        REPORT["errors"].append("no foreach"); REPORT["fixes"]["e"]="rolled_back"
        bel.compile_blueprint(cbp); unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
        return False
    bel.set_node_pos(fe,pos(-1300,1000))
    connect(find_pin(gat,"then","Output"), find_pin(fe,"Exec","Input") or find_pin(fe,"execute","Input"), "gat->fe")
    connect(find_pin(gat,"OutActors","Output"), find_pin(fe,"Array","Input"), "arr")
    el=find_pin(fe,"Array Element","Output") or find_pin(fe,"Element","Output")
    body=find_pin(fe,"LoopBody","Output") or find_pin(fe,"Then","Output")
    done=find_pin(fe,"Completed","Output")

    act_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(act_loc,pos(-1000,850))
    connect(el, find_pin(act_loc,"self","Input"), "el")

    dist=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist,pos(-750,1000))
    connect(find_pin(pawn_loc,"ReturnValue","Output"), find_pin(dist,"A","Input") or find_pin(dist,"V1","Input"), "p")
    connect(find_pin(act_loc,"ReturnValue","Output"), find_pin(dist,"B","Input") or find_pin(dist,"V2","Input"), "a")

    lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if lt is None: lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(lt,pos(-500,1000))
    connect(find_pin(dist,"ReturnValue","Output"), find_pin(lt,"A","Input"), "d")
    setdef(find_pin(lt,"B","Input"),"200.0")

    br=cge.add_branch_node(); bel.set_node_pos(br,pos(-280,1000))
    connect(body, find_pin(br,"execute","Input"), "body")
    connect(find_pin(lt,"ReturnValue","Output"), find_pin(br,"Condition","Input"), "near")

    cast_n=None
    for cname in ("Cast To BP_RestaurantInteractable", "Cast To BP_RestaurantInteractable_C"):
        try:
            cast_n=cge.create_node_from_name(cname, unreal.Vector2D(0,900), [])
            if cast_n: break
        except Exception as e: log("cast try "+str(e))
    # also try from parent class path
    if cast_n is None:
        try:
            # spawn temporary call then? 
            pass
        except Exception: pass

    if cast_n:
        bel.set_node_pos(cast_n,pos(0,900))
        connect(find_pin(br,"then","Output"), find_pin(cast_n,"execute","Input"), "cast")
        connect(el, find_pin(cast_n,"Object","Input"), "el")
        call_i=cge.add_call_function_node(DIR+"/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i,pos(350,900))
        connect(find_pin(cast_n,"then","Output"), find_pin(call_i,"execute","Input"), "interact")
        as_pin=None
        for p in bel.list_all_pins(cast_n):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin=p; break
        connect(as_pin, find_pin(call_i,"self","Input"), "as")
        set_t=cge.add_set_member_variable_node("bRestEHandled"); bel.set_node_pos(set_t,pos(700,900))
        connect(find_pin(call_i,"then","Output"), find_pin(set_t,"execute","Input"), "handled")
        setdef(find_pin(set_t,"bRestEHandled","Input"),"true")
        REPORT["fixes"]["cast"]="interactable_ok"
    else:
        # Use GetDisplayName + Print as differentiated feedback; still mark handled
        gdn=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
        bel.set_node_pos(gdn,pos(0,850))
        connect(el, find_pin(gdn,"Object","Input") or find_pin(gdn,"self","Input"), "el->name")
        append=cge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(append,pos(250,850))
        setdef(find_pin(append,"A","Input"),"Restaurant E -> ")
        connect(find_pin(gdn,"ReturnValue","Output"), find_pin(append,"B","Input"), "name")
        pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr,pos(500,900))
        connect(find_pin(br,"then","Output"), find_pin(pr,"execute","Input"), "pr")
        connect(find_pin(append,"ReturnValue","Output"), find_pin(pr,"InString","Input"), "str")
        setdef(find_pin(pr,"Duration","Input"),"2.5")
        # Also try call RestaurantInteract via Interface? Direct call with self=el may work if we use add_call_function on parent and wire self
        call_i=cge.add_call_function_node(DIR+"/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i,pos(800,900))
        connect(find_pin(pr,"then","Output"), find_pin(call_i,"execute","Input"), "->ri")
        connect(el, find_pin(call_i,"self","Input"), "el->self")  # may fail type check
        set_t=cge.add_set_member_variable_node("bRestEHandled"); bel.set_node_pos(set_t,pos(1100,900))
        # Prefer call_i then, else pr then
        if find_pin(call_i,"self","Input") and find_pin(call_i,"self","Input").list_connected_pins():
            connect(find_pin(call_i,"then","Output"), find_pin(set_t,"execute","Input"), "handled")
            REPORT["fixes"]["cast"]="direct_call_self"
        else:
            connect(find_pin(pr,"then","Output"), find_pin(set_t,"execute","Input"), "handled_print_only")
            REPORT["fixes"]["cast"]="print_only"
        setdef(find_pin(set_t,"bRestEHandled","Input"),"true")

    get_h=cge.add_get_member_variable_node("bRestEHandled"); bel.set_node_pos(get_h,pos(-1000,1300))
    notb=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool"); bel.set_node_pos(notb,pos(-750,1300))
    connect(find_pin(get_h,"bRestEHandled","Output"), find_pin(notb,"A","Input"), "h")
    br_t=cge.add_branch_node(); bel.set_node_pos(br_t,pos(-500,1250))
    connect(done, find_pin(br_t,"execute","Input"), "done")
    connect(find_pin(notb,"ReturnValue","Output"), find_pin(br_t,"Condition","Input"), "!h")
    connect(find_pin(br_t,"then","Output"), find_pin(till,"execute","Input"), "TillSoil")

    bel.compile_blueprint(cbp)
    unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

    chain=[]
    for cp in started.list_connected_pins():
        chain.append(bel.get_node_title(cp.get_owning_node()))
    REPORT["ia_after"]=chain
    # verify gat is reachable
    REPORT["fixes"]["e_chain"]=chain
    log("E fixed "+str(chain))
    return True

try:
    REPORT["opensign_ok"]=fix_opensign()
except Exception:
    REPORT["errors"].append(traceback.format_exc())
    REPORT["opensign_ok"]=False

try:
    REPORT["e_ok"]=fix_character()
except Exception:
    REPORT["errors"].append(traceback.format_exc())
    REPORT["e_ok"]=False

# Ensure Manager GuestInterval on instance + sign/manager open false
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab=="Restaurant_Manager":
        for k,v in (("GuestInterval",4.0),("guest_interval",4.0),("GuestTimer",0.0),("guest_timer",0.0),
                    ("bIsOpenBusiness",False),("b_is_open_business",False)):
            try: a.set_editor_property(k,v)
            except Exception: pass
        try: a.set_actor_tick_enabled(True)
        except Exception: pass
    if lab=="Restaurant_OpenSign":
        for k,v in (("bIsOpenBusiness",False),("b_is_open_business",False)):
            try: a.set_editor_property(k,v)
            except Exception: pass

REPORT["actors"]=len(eas.get_all_level_actors())
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["saved"]=True
except Exception:
    unreal.EditorLevelLibrary.save_current_level(); REPORT["saved"]=True

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife2_fix.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps(REPORT,ensure_ascii=False,indent=2))
