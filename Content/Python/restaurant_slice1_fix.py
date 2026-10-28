# -*- coding: utf-8 -*-
"""Verify restaurant placement, meshes, tags, vars, character IA links; fix wiring."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR="/Game/Farm/Restaurant"
out={"actors":[], "bp_vars":{}, "ia":{}, "fixes":[]}

def log(m):
    unreal.log("[REST_FIX] "+str(m)); out["fixes"].append(str(m))

def find_pin(node, name_substr, direction=None):
    if not node: return None
    name_substr=name_substr.lower()
    for p in bel.list_all_pins(node):
        if name_substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

# --- actors ---
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if not (lab.startswith("Restaurant_") or lab.startswith("RestChair_")): continue
    loc=a.get_actor_location()
    info={"label":lab,"class":a.get_class().get_name(),"x":loc.x,"y":loc.y,"z":loc.z,"tags":[str(t) for t in (a.get_editor_property("tags") or [])]}
    # meshes
    meshes=[]
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm=c.get_editor_property("static_mesh")
        meshes.append({"comp":c.get_name(),"mesh":sm.get_name() if sm else None,"hidden":c.is_visible()==False if hasattr(c,"is_visible") else None})
    info["meshes"]=meshes
    # list properties containing interact/table/open
    props=[]
    try:
        for p in a.get_class().property_iterator() if hasattr(a.get_class(),"property_iterator") else []:
            pass
    except Exception: pass
    # try common names
    for name in ("InteractLabel","interact_label","TableId","table_id","bIsOpenBusiness","b_is_open_business","BIsOpenBusiness"):
        try:
            v=a.get_editor_property(name)
            props.append({name:str(v)})
        except Exception:
            pass
    info["props"]=props
    out["actors"].append(info)

# --- BP member vars ---
for name in ("BP_RestaurantInteractable","BP_RestaurantTable","BP_RestaurantStove","BP_RestaurantTrash","BP_RestaurantOpenSign","BP_RestaurantManager"):
    path=DIR+"/"+name
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        out["bp_vars"][name]="MISSING"; continue
    bp=unreal.EditorAssetLibrary.load_asset(path)
    vars=[str(v) for v in bel.list_member_variable_names(bp)]
    out["bp_vars"][name]=vars
    # compile again
    bel.compile_blueprint(bp)
    cls=bp.generated_class()
    cdo=unreal.get_default_object(cls) if cls else None
    # dump editable props on CDO via dir-ish
    found={}
    if cdo:
        for vn in vars:
            for cand in (vn, vn[0].lower()+vn[1:] if vn else vn):
                try:
                    found[cand]=str(cdo.get_editor_property(cand))
                    break
                except Exception:
                    continue
    out["bp_vars"][name+"_cdo"]=found

# Set InteractLabel via correct property name after compile
LABELS={
    "Restaurant_Table1":"Restaurant: TABLE 1",
    "Restaurant_Table2":"Restaurant: TABLE 2",
    "Restaurant_Stove":"Restaurant: STOVE",
    "Restaurant_Trash":"Restaurant: TRASH",
    "Restaurant_OpenSign":"Restaurant: OPEN SIGN",
}
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab in LABELS:
        ok=False
        for pname in ("InteractLabel","interact_label"):
            try:
                a.set_editor_property(pname, LABELS[lab]); ok=True; log("set {} {}".format(lab,pname)); break
            except Exception as e:
                last=str(e)
        if not ok:
            # try reflection
            try:
                # Blueprint instance variables sometimes need lowercase with b prefix rules
                uobj=a
                # list via EditorActorSubsystem? use get_editor_property from generated
                log("FAIL set label {} last={}".format(lab,last))
            except Exception as e:
                log(str(e))
    if lab.startswith("Restaurant_") and lab!="Restaurant_Manager":
        # ensure tag
        try:
            tags=list(a.get_editor_property("tags") or [])
            n=unreal.Name("RestInteract")
            if n not in tags:
                tags.append(n); a.set_editor_property("tags", tags); log("tagged "+lab)
        except Exception as e:
            log("tag "+str(e))
    if lab=="Restaurant_Table1":
        for pname in ("TableId","table_id"):
            try: a.set_editor_property(pname,1); break
            except Exception: pass
    if lab=="Restaurant_Table2":
        for pname in ("TableId","table_id"):
            try: a.set_editor_property(pname,2); break
            except Exception: pass

# Ensure meshes assigned on instances if missing
MESH={
    "Restaurant_Table1":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Table2":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Stove":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "Restaurant_Trash":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "Restaurant_OpenSign":"/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab not in MESH: continue
    comps=a.get_components_by_class(unreal.StaticMeshComponent)
    need=unreal.EditorAssetLibrary.load_asset(MESH[lab])
    if not comps:
        log("NO SMC "+lab); continue
    for c in comps:
        sm=c.get_editor_property("static_mesh")
        if sm is None and need:
            c.set_editor_property("static_mesh", need); log("assigned mesh "+lab)
        # ensure visible / not tiny
        try: c.set_visibility(True)
        except Exception: pass

# --- Fix character IA wiring ---
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia=None; till=None; gate=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="TillSoil": till=n
    if "RestaurantGate" in t: gate=n

# dump pins of gate and ia
def dump_node(n, key):
    if not n: out[key]=None; return
    pins=[]
    for p in bel.list_all_pins(n):
        conns=[(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
        pins.append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"conns":conns})
    out[key]={"title":bel.get_node_title(n),"class":n.get_class().get_name(),"pins":pins}

dump_node(ia,"ia")
dump_node(gate,"gate")
dump_node(till,"till")

# Fix: IA Started -> RestaurantGate
# Custom event Output is often the left exec? Actually Custom Event has then output.
if ia and gate:
    started=find_pin(ia,"Started","Output")
    # custom event's input exec for CALLING it is on a Call node, not on the event definition!
    # RestaurantGate custom EVENT is the definition — to invoke it we need Call RestaurantGate from IA,
    # OR we treat RestaurantGate as the event that fires when... wait.
    # add_custom_event_node creates a DEFINITION that fires when called via Call node OR when we wrongly connected Started to its "execute" input which doesn't exist on definitions.
    # Correct pattern: IA Started -> nodes directly, OR IA Started -> Call Function.
    # Custom Event node has OUTPUT then (when event fires). It does NOT have execute input.
    # So connecting IA->Gate execute was wrong (skip IA->Gate).
    # Fix approach: remove Custom Event; put GetActorOfClass chain directly on IA Started.

# Rebuild: disconnect IA Started; wire directly to GetActorOfClass Manager chain
# Remove RestaurantGate custom event and its chain; build fresh from IA Started.

kill=[]
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "RestaurantGate" in t: kill.append(n)
    if "Cast To BP_RestaurantManager" in t: kill.append(n)
# kill GetActorOfClass / Print that are between restaurant area — identify by connection from gate
# safer: kill all nodes titled exactly our prints
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if t in ("Get Actor Of Class","GetActorOfClass"):
        # check if ActorClass points to restaurant manager
        cp=find_pin(n,"ActorClass","Input")
        val=""
        if cp:
            try: val=cp.get_default_as_string()
            except Exception:
                try: val=str(cp.get_pin_value())
                except Exception: val=""
        if "RestaurantManager" in str(val) or "Restaurant" in str(val):
            kill.append(n)
    if t=="Print String":
        insp=find_pin(n,"InString","Input")
        val=""
        if insp:
            try: val=insp.get_default_as_string()
            except Exception:
                try: val=str(insp.get_pin_value())
                except Exception: val=""
        if "RestaurantGate" in str(val) or "Restaurant E" in str(val) or "Manager" in str(val) and "Restaurant" in str(val):
            kill.append(n)

# Also remove HandlePlayerE call nodes
for n in cge.list_all_nodes():
    if "HandlePlayerE" in bel.get_node_title(n):
        kill.append(n)

if kill:
    kill=[n for n in kill if bel.get_node_title(n)!="TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
    cge.remove_nodes(list({id(n):n for n in kill}.values()))
    log("removed "+str(len(kill)))

# Fresh chain from IA Started:
# GetPlayerPawn -> GetActorLocation -> GetAllActorsWithTag RestInteract -> ForEach -> distance -> Cast -> RestaurantInteract
# AND also call TillSoil after (or only if none handled — keep simple: restaurant first then till)

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

gat=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gat, unreal.IntPoint(-1600,1100))
connect(started, find_pin(gat,"execute","Input"), "IA->gat")
set_default=lambda pin,val: (pin.set_default_value(str(val)) if pin else None)
try:
    find_pin(gat,"Tag","Input").set_default_value("RestInteract")
except Exception:
    try: find_pin(gat,"Tag","Input").set_pin_value("RestInteract")
    except Exception as e: log("tagpin "+str(e))

# Get pawn loc for distance
get_pawn=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(get_pawn, unreal.IntPoint(-1600,1300))
# pure get — connect exec through sequence: actually GetPlayerPawn is impure with exec
# Use Sequence: IA -> gat and also need pawn. Chain: IA->get_pawn->gat
# Reconnect: break IA->gat, do IA->pawn->gat
try: bel.break_pin_links(started)
except Exception: pass
connect(started, find_pin(get_pawn,"execute","Input"), "IA->pawn")
try: find_pin(get_pawn,"PlayerIndex","Input").set_default_value("0")
except Exception: pass
connect(find_pin(get_pawn,"then","Output"), find_pin(gat,"execute","Input"), "pawn->gat")
pawn_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(pawn_loc, unreal.IntPoint(-1300,1300))
connect(find_pin(get_pawn,"ReturnValue","Output"), find_pin(pawn_loc,"self","Input"), "pawn->loc")

foreach=None
try:
    foreach=cge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
except Exception as e:
    log("fe "+str(e))
if foreach:
    bel.set_node_pos(foreach, unreal.IntPoint(-1200,1100))
    connect(find_pin(gat,"then","Output"), find_pin(foreach,"Exec","Input") or find_pin(foreach,"execute","Input"), "gat->fe")
    connect(find_pin(gat,"OutActors","Output"), find_pin(foreach,"Array","Input"), "arr->fe")
    el=find_pin(foreach,"Array Element","Output") or find_pin(foreach,"Element","Output")
    act_loc=cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(act_loc, unreal.IntPoint(-900,980))
    connect(el, find_pin(act_loc,"self","Input"), "el->loc")
    dist=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, unreal.IntPoint(-650,1100))
    connect(find_pin(pawn_loc,"ReturnValue","Output"), find_pin(dist,"A","Input") or find_pin(dist,"V1","Input"), "A")
    connect(find_pin(act_loc,"ReturnValue","Output"), find_pin(dist,"B","Input") or find_pin(dist,"V2","Input"), "B")
    lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if not lt:
        lt=cge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(lt, unreal.IntPoint(-400,1100))
    connect(find_pin(dist,"ReturnValue","Output"), find_pin(lt,"A","Input"), "d")
    try: find_pin(lt,"B","Input").set_default_value("160.0")
    except Exception:
        try: find_pin(lt,"B","Input").set_pin_value("160.0")
        except Exception: pass
    br=cge.add_branch_node(); bel.set_node_pos(br, unreal.IntPoint(-150,1100))
    connect(find_pin(foreach,"LoopBody","Output") or find_pin(foreach,"Then","Output"), find_pin(br,"execute","Input"), "body->br")
    connect(find_pin(lt,"ReturnValue","Output"), find_pin(br,"Condition","Input"), "lt")
    cast_n=None
    for cname in ("Cast To BP_RestaurantInteractable","Utilities|Casting|Cast To BP_RestaurantInteractable"):
        try:
            cast_n=cge.create_node_from_name(cname, unreal.Vector2D(100,1000), [])
            if cast_n: break
        except Exception: pass
    if cast_n:
        bel.set_node_pos(cast_n, unreal.IntPoint(100,1000))
        connect(find_pin(br,"then","Output"), find_pin(cast_n,"execute","Input"), "br->cast")
        connect(el, find_pin(cast_n,"Object","Input"), "el->obj")
        call_i=cge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i, unreal.IntPoint(450,1000))
        connect(find_pin(cast_n,"then","Output"), find_pin(call_i,"execute","Input"), "cast->i")
        as_pin=None
        for p in bel.list_all_pins(cast_n):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin=p; break
        connect(as_pin, find_pin(call_i,"self","Input"), "as->i")
        log("character foreach interact wired")
    else:
        pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, unreal.IntPoint(100,1000))
        connect(find_pin(br,"then","Output"), find_pin(pr,"execute","Input"), "br->pr")
        try: find_pin(pr,"InString","Input").set_default_value("Restaurant E: near RestInteract (no cast)")
        except Exception: pass
        log("no cast node — print fallback")
    # Completed -> TillSoil (farming paused fallback)
    if till:
        connect(find_pin(foreach,"Completed","Output"), find_pin(till,"execute","Input"), "fe->till")
else:
    pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, unreal.IntPoint(-1200,1100))
    connect(find_pin(gat,"then","Output"), find_pin(pr,"execute","Input"), "gat->pr")
    try: find_pin(pr,"InString","Input").set_default_value("Restaurant E pressed (no foreach)")
    except Exception: pass
    if till:
        connect(find_pin(pr,"then","Output"), find_pin(till,"execute","Input"), "pr->till")

ok=bel.compile_blueprint(cbp)
log("char compile "+str(ok))
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# Re-dump IA
ia=None
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n): ia=n
dump_node(ia,"ia_after")

# Fix OpenSign: override RestaurantInteract with toggle + FarmClock check via new function graph
bp_sign=unreal.EditorAssetLibrary.load_asset(DIR+"/BP_RestaurantOpenSign")
# Try add_function_graph override
try:
    g=bel.find_graph(bp_sign,"RestaurantInteract")
    log("sign graph existing="+str(g))
    if g is None:
        bel.add_function_graph(bp_sign,"RestaurantInteract")
        g=bel.find_graph(bp_sign,"RestaurantInteract")
    ge=unreal.BlueprintGraphEditor.get_graph_editor(g) if g else None
    log("sign ge="+str(ge))
except Exception as e:
    log("sign override "+str(e))

# Soft: Manager Tick auto-close stub — add ReceiveTick print once? skip for knife-1; document.

els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save level "+str(els.save_current_level()))

# refresh actor mesh info
out["actors_after"]=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if not (lab.startswith("Restaurant_") or lab.startswith("RestChair_")): continue
    loc=a.get_actor_location()
    meshes=[]
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm=c.get_editor_property("static_mesh")
        meshes.append(sm.get_path_name() if sm else None)
    out["actors_after"].append({"label":lab,"meshes":meshes,"tags":[str(t) for t in (a.get_editor_property("tags") or [])], "x":loc.x,"y":loc.y})

path=r"E:\UE\FarmSim25D\Saved\restaurant_slice1_fix.json"
open(path,"w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
log("wrote "+path)
print(json.dumps({"actors":len(out["actors_after"]), "bp_vars":out["bp_vars"], "ia_after":out.get("ia_after"), "fixes":out["fixes"]}, ensure_ascii=False, indent=2))
