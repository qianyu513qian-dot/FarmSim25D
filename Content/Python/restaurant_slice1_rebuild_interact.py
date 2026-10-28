# -*- coding: utf-8 -*-
"""Rebuild restaurant E interact simply + force-correct meshes on instances."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT={"steps":[],"ia_chain":[],"actors":[]}

def log(m):
    unreal.log("[REST_R] "+str(m)); REPORT["steps"].append(str(m))

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

def setdef(pin, val):
    if not pin: return
    for fn in ("set_default_value","set_pin_value"):
        try: getattr(pin,fn)(str(val)); return
        except Exception: pass

MESH={
    "Restaurant_Table1":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Table2":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Stove":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "Restaurant_Trash":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "Restaurant_OpenSign":"/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}

# --- force meshes: put correct mesh on ALL SMC, then hide all but one ---
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab not in MESH: continue
    need=unreal.EditorAssetLibrary.load_asset(MESH[lab])
    comps=list(a.get_components_by_class(unreal.StaticMeshComponent))
    # pick best component name
    order=["PropMesh_0","PropMesh","StaticMeshComponent0","StaticMesh"]
    chosen=None
    for name in order:
        for c in comps:
            if c.get_name()==name:
                chosen=c; break
        if chosen: break
    if not chosen and comps: chosen=comps[0]
    for c in comps:
        if c is chosen:
            c.set_editor_property("static_mesh", need)
            try:
                c.set_visibility(True); c.set_hidden_in_game(False)
            except Exception: pass
        else:
            try: c.set_editor_property("static_mesh", None)
            except Exception: pass
            try:
                c.set_visibility(False); c.set_hidden_in_game(True)
            except Exception: pass
    try: a.set_editor_property("InteractLabel", {
        "Restaurant_Table1":"Restaurant: TABLE 1",
        "Restaurant_Table2":"Restaurant: TABLE 2",
        "Restaurant_Stove":"Restaurant: STOVE",
        "Restaurant_Trash":"Restaurant: TRASH",
        "Restaurant_OpenSign":"Restaurant: OPEN SIGN",
    }[lab])
    except Exception as e: log(str(e))
    log("mesh {} -> {} via {}".format(lab, need.get_name() if need else None, chosen.get_name() if chosen else None))

# --- Character: strip restaurant-related nodes from IA Started chain, rebuild simple ---
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

ia=None; till=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="TillSoil": till=n

# Collect nodes reachable from IA Started (except TillSoil itself kept)
kill=[]
if ia:
    started=find_pin(ia,"Started","Output")
    stack=[]
    if started:
        for cp in started.list_connected_pins():
            stack.append(cp.get_owning_node())
    seen=set()
    while stack:
        n=stack.pop()
        if id(n) in seen: continue
        seen.add(id(n))
        t=bel.get_node_title(n)
        if t=="TillSoil" or "IA_Interact" in t: continue
        kill.append(n)
        for p in bel.list_all_pins(n):
            if "output" not in str(p.get_pin_direction()).lower(): continue
            for cp in p.list_connected_pins():
                on=cp.get_owning_node()
                if id(on) not in seen:
                    stack.append(on)

# Also kill orphan restaurant helpers not linked (GetAllActorsWithTag etc left over)
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if t in ("GetAllActorsWithTag","Get Player Pawn","GetPlayerPawn","ForEachLoop","Branch") and n not in kill:
        # only if near our Y area? risky. Check connections to TillSoil/IA
        pass
    if "Restaurant" in t:
        kill.append(n)

# Kill GetAllActorsWithTag / ForEachLoop / Vector_Distance2D specifically if present
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    cn=n.get_class().get_name()
    if t in ("GetAllActorsWithTag","GetAllActorsOfClass","ForEachLoop","Vector Distance 2D","Vector_Distance2D","Less (Double)","Less (Float)","Get Display Name","GetActorLabel","Concat_StrStr","Append"):
        kill.append(n)
    if t=="Print String":
        insp=find_pin(n,"InString","Input")
        val=""
        if insp:
            try: val=insp.get_default_as_string()
            except Exception:
                try: val=str(insp.get_pin_value())
                except Exception: val=""
        if any(k in str(val) for k in ("Restaurant","RestInteract","near","OPEN","STOVE","TABLE","TRASH")):
            kill.append(n)
    if "Cast To BP_Restaurant" in t:
        kill.append(n)

kill=[n for n in kill if bel.get_node_title(n)!="TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
kill=list({id(n):n for n in kill}.values())
if kill:
    cge.remove_nodes(kill)
    log("removed {}".format(len(kill)))

# Rebuild SIMPLE chain:
# IA Started -> GetAllActorsWithTag(RestInteract) -> ForEachLoop
#   LoopBody -> GetDisplayName -> PrintString("Restaurant E: "+name)   [always print each — too spammy]
# Better: LoopBody -> Dist2D from player -> Branch < 200 -> Print InteractLabel via cast OR Print GetDisplayName
# Simplest reliable for knife-1:
# IA -> GetPlayerPawn -> GetAllActorsWithTag -> ForEach
#   body: Dist2D(pawn, element) < 200 -> PrintString with GetDisplayName(element)
# Completed -> TillSoil

ia=None; till=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="TillSoil": till=n
started=find_pin(ia,"Started","Output") if ia else None
if started:
    try: bel.break_pin_links(started)
    except Exception:
        for cp in list(started.list_connected_pins()):
            try: started.break_link_to(cp)
            except Exception: pass

get_pawn=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(get_pawn, unreal.IntPoint(-2000, 1050))
setdef(find_pin(get_pawn,"PlayerIndex","Input"), "0")
connect(started, find_pin(get_pawn,"execute","Input"), "IA->pawn")

pawn_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(pawn_loc, unreal.IntPoint(-1700, 1200))
connect(find_pin(get_pawn,"ReturnValue","Output"), find_pin(pawn_loc,"self","Input"), "pawn.self")

gat=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gat, unreal.IntPoint(-1700, 1050))
connect(find_pin(get_pawn,"then","Output"), find_pin(gat,"execute","Input"), "pawn->gat")
setdef(find_pin(gat,"Tag","Input"), "RestInteract")

fe=None
try:
    fe=cge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
except Exception as e:
    log("fe macro "+str(e))
if fe is None:
    try: fe=cge.create_node_from_name("For Each Loop", unreal.Vector2D(-1400,1050), [])
    except Exception as e: log("fe name "+str(e))
if fe is None:
    try: fe=cge.create_node_from_name("ForEachLoop", unreal.Vector2D(-1400,1050), [])
    except Exception as e: log("fe name2 "+str(e))

if fe:
    bel.set_node_pos(fe, unreal.IntPoint(-1400,1050))
    # dump fe pins for debug
    fe_pins=[str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(fe)]
    REPORT["fe_pins"]=fe_pins
    log("fe pins "+str(fe_pins))
    exec_in=find_pin(fe,"Exec","Input") or find_pin(fe,"execute","Input")
    arr_in=find_pin(fe,"Array","Input")
    connect(find_pin(gat,"then","Output"), exec_in, "gat->fe")
    connect(find_pin(gat,"OutActors","Output"), arr_in, "arr->fe")
    el=find_pin(fe,"Array Element","Output") or find_pin(fe,"Element","Output")
    body=find_pin(fe,"LoopBody","Output") or find_pin(fe,"Then","Output")
    done=find_pin(fe,"Completed","Output")

    act_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(act_loc, unreal.IntPoint(-1100,900))
    connect(el, find_pin(act_loc,"self","Input"), "el->loc")

    dist=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, unreal.IntPoint(-850,1050))
    connect(find_pin(pawn_loc,"ReturnValue","Output"), find_pin(dist,"A","Input") or find_pin(dist,"V1","Input"), "A")
    connect(find_pin(act_loc,"ReturnValue","Output"), find_pin(dist,"B","Input") or find_pin(dist,"V2","Input"), "B")

    lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if lt is None:
        lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(lt, unreal.IntPoint(-600,1050))
    connect(find_pin(dist,"ReturnValue","Output"), find_pin(lt,"A","Input"), "d->lt")
    setdef(find_pin(lt,"B","Input"), "200.0")

    br=cge.add_branch_node(); bel.set_node_pos(br, unreal.IntPoint(-350,1050))
    connect(body, find_pin(br,"execute","Input"), "body->br")
    connect(find_pin(lt,"ReturnValue","Output"), find_pin(br,"Condition","Input"), "lt->br")

    # Print display name
    gdn=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
    bel.set_node_pos(gdn, unreal.IntPoint(-100,900))
    connect(el, find_pin(gdn,"Object","Input") or find_pin(gdn,"self","Input"), "el->dn")

    cat=cge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat, unreal.IntPoint(150,900))
    setdef(find_pin(cat,"A","Input"), "Restaurant E -> ")
    connect(find_pin(gdn,"ReturnValue","Output"), find_pin(cat,"B","Input"), "dn->B")

    pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, unreal.IntPoint(450,1050))
    connect(find_pin(br,"then","Output"), find_pin(pr,"execute","Input"), "br->pr")
    connect(find_pin(cat,"ReturnValue","Output"), find_pin(pr,"InString","Input"), "cat->str")
    setdef(find_pin(pr,"Duration","Input"), "2.5")

    if till and done:
        connect(done, find_pin(till,"execute","Input"), "fe->till")
    log("simple foreach E interact rebuilt")
else:
    # absolute fallback
    pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, unreal.IntPoint(-1400,1050))
    connect(find_pin(gat,"then","Output"), find_pin(pr,"execute","Input"), "gat->pr")
    setdef(find_pin(pr,"InString","Input"), "Restaurant E: tag scan (no ForEach macro)")
    if till:
        connect(find_pin(pr,"then","Output"), find_pin(till,"execute","Input"), "pr->till")
    log("FALLBACK no foreach")

ok=bel.compile_blueprint(cbp)
log("compile "+str(ok))
try:
    REPORT["errors"]=[bel.get_node_title(n) for n in cge.list_nodes_with_errors()]
except Exception as e:
    REPORT["errors"]=str(e)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# dump IA chain
if ia:
    started=find_pin(ia,"Started","Output")
    chain=[]
    if started:
        q=[(cp.get_owning_node(),0) for cp in started.list_connected_pins()]
        seen=set()
        while q and len(chain)<25:
            n,d=q.pop(0)
            if id(n) in seen: continue
            seen.add(id(n))
            chain.append(bel.get_node_title(n))
            for p in bel.list_all_pins(n):
                if "output" not in str(p.get_pin_direction()).lower(): continue
                for cp in p.list_connected_pins():
                    q.append((cp.get_owning_node(), d+1))
    REPORT["ia_chain"]=chain

for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab not in MESH: continue
    meshes=[]
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm=c.get_editor_property("static_mesh")
        if sm:
            meshes.append(c.get_name()+":"+sm.get_name())
    REPORT["actors"].append({"label":lab,"meshes":meshes})

els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save "+str(els.save_current_level()))
open(r"E:\UE\FarmSim25D\Saved\restaurant_slice1_rebuild.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps(REPORT,ensure_ascii=False,indent=2))
