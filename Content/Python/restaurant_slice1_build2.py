# -*- coding: utf-8 -*-
"""Restaurant slice1 build v2 — parent InteractLabel print; children set label; place; wire E."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "actors": [], "errors": []}

MESH = {
    "table": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "chair": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate",
    "stove": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "trash": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "sign": "/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}
ZONE = {
    "table1": (2050.0, 450.0, 2.0),
    "table2": (2250.0, 450.0, 2.0),
    "chair1a": (2050.0, 380.0, 2.0),
    "chair1b": (2050.0, 520.0, 2.0),
    "chair2a": (2250.0, 380.0, 2.0),
    "chair2b": (2250.0, 520.0, 2.0),
    "stove": (2150.0, 700.0, 2.0),
    "trash": (2000.0, 700.0, 2.0),
    "sign": (1850.0, 550.0, 2.0),
    "manager": (2150.0, 600.0, 80.0),
}

def log(m):
    unreal.log("[REST1] " + str(m)); REPORT["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x), int(y))

def pin_type(category, sub=""):
    p = unreal.EdGraphPinType()
    if sub: p.import_text('(PinCategory="{}",PinSubCategory="{}")'.format(category, sub))
    else: p.import_text('(PinCategory="{}")'.format(category))
    return p

def find_pin(node, name_substr, direction=None):
    if not node: return None
    name_substr = name_substr.lower()
    for p in bel.list_all_pins(node):
        if name_substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

def set_default(pin, value, label=""):
    if not pin: return
    for fn in ("set_default_value","set_pin_value"):
        try:
            getattr(pin, fn)(str(value)); return
        except Exception as e:
            last=e
    log("set fail {}: {}".format(label,last))

def ensure_dir():
    for d in ("/Game/Farm", DIR):
        if not unreal.EditorAssetLibrary.does_directory_exist(d):
            unreal.EditorAssetLibrary.make_directory(d)

def create_bp(name, parent=unreal.Actor):
    path=DIR+"/"+name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    factory=unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", parent)
    bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DIR, unreal.Blueprint, factory)
    unreal.EditorAssetLibrary.save_asset(path)
    log("created "+name)
    return unreal.EditorAssetLibrary.load_asset(path)

def add_var(bp, name, ptype):
    names=[str(n) for n in bel.list_member_variable_names(bp)]
    if name in names: return
    ok=bel.add_member_variable(bp, name, ptype)
    log("var {} {}".format(name, ok))
    try: bel.set_blueprint_variable_instance_editable(bp, name, True)
    except Exception: pass

def ensure_mesh(bp, var_name, mesh_path, scale=(1,1,1)):
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=sub.k2_gather_subobject_data_for_blueprint(bp)
    root_h=None; target_h=None; target_obj=None
    for h in handles:
        data=sub.k2_find_subobject_data_from_handle(h)
        try:
            if lib.is_root_component(data): root_h=h
            vname=str(lib.get_variable_name(data) or "")
            obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
            if vname==var_name:
                target_h=h; target_obj=obj
        except Exception: pass
    if target_h is None:
        params=unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", root_h if root_h else handles[0])
        params.set_editor_property("new_class", unreal.StaticMeshComponent)
        try: params.set_editor_property("blueprint_context", bp)
        except Exception: pass
        sub.add_new_subobject(params)
        handles=sub.k2_gather_subobject_data_for_blueprint(bp)
        for h in handles:
            data=sub.k2_find_subobject_data_from_handle(h)
            try:
                vname=str(lib.get_variable_name(data) or "")
                obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
                if obj and "StaticMesh" in obj.get_class().get_name() and vname!=var_name:
                    try: sub.rename_subobject(h, unreal.Text(var_name))
                    except Exception: pass
                    target_h=h; target_obj=lib.get_associated_object(sub.k2_find_subobject_data_from_handle(h)) if hasattr(lib,"get_associated_object") else lib.get_object(sub.k2_find_subobject_data_from_handle(h))
                    break
            except Exception: pass
        if root_h and target_h:
            try: sub.attach_subobject(root_h, target_h)
            except Exception: pass
    if target_obj:
        mesh=unreal.EditorAssetLibrary.load_asset(mesh_path)
        if mesh:
            try: target_obj.set_editor_property("static_mesh", mesh)
            except Exception as e: log("mesh "+str(e))
        try:
            target_obj.set_editor_property("relative_scale3d", unreal.Vector(*scale))
        except Exception: pass
        try: target_obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
        except Exception: pass
    return target_obj

def graph_editor(bp, fname, create=True):
    g=bel.find_graph(bp, fname)
    if g is None and create:
        try:
            bel.add_function_graph(bp, fname)
        except Exception as e:
            log("add_function_graph "+str(e))
        g=bel.find_graph(bp, fname)
    if g is None:
        return None, None
    ge=unreal.BlueprintGraphEditor.get_graph_editor(g)
    if ge is None:
        # try create_and_edit
        try:
            eg=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
            eg.create_and_edit_function_graph(fname)
            g=bel.find_graph(bp, fname)
            ge=unreal.BlueprintGraphEditor.get_graph_editor(g)
        except Exception as e:
            log("create_and_edit "+str(e))
    return ge, g

def clear_fn_body(ge):
    kill=[]
    for n in ge.list_all_nodes():
        cn=n.get_class().get_name()
        if cn in ("K2Node_FunctionEntry","K2Node_FunctionResult"): continue
        kill.append(n)
    if kill: ge.remove_nodes(kill)

def wire_label_print(bp):
    """RestaurantInteract prints InteractLabel."""
    ge,g=graph_editor(bp,"RestaurantInteract", True)
    if not ge:
        log("NO GE for RestaurantInteract on "+bp.get_name()); return False
    clear_fn_body(ge)
    entry=None
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n
    getv=ge.add_get_member_variable_node("InteractLabel")
    bel.set_node_pos(getv, pos(0,120))
    pr=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(350,0))
    connect(find_pin(entry,"then","Output") or find_pin(entry,"execute","Output"), find_pin(pr,"execute","Input"), "e->p")
    connect(find_pin(getv,"InteractLabel","Output"), find_pin(pr,"InString","Input"), "label->str")
    set_default(find_pin(pr,"Duration","Input"), "3.0")
    ret=ge.add_return_node(); bel.set_node_pos(ret, pos(700,0))
    connect(find_pin(pr,"then","Output"), find_pin(ret,"execute","Input"), "p->r")
    return True

ensure_dir()

# Parent (may already exist from failed run)
bp_base=create_bp("BP_RestaurantInteractable")
add_var(bp_base,"InteractLabel", pin_type("string"))
add_var(bp_base,"InteractRange", pin_type("real","double"))
ensure_mesh(bp_base,"PropMesh", MESH["table"])
wire_label_print(bp_base)
bel.compile_blueprint(bp_base)
unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantInteractable")
base_cls=bp_base.generated_class()
log("base_cls="+str(base_cls))

# Set default InteractLabel on CDO
try:
    cdo=unreal.get_default_object(base_cls)
    cdo.set_editor_property("interact_label", "Restaurant: (base)")
    cdo.set_editor_property("interact_range", 280.0)
except Exception as e:
    log("cdo base "+str(e))

child_defs=[
    ("BP_RestaurantTable", MESH["table"], (1,1,1), "Restaurant: TABLE", {"table_id":0}, True),
    ("BP_RestaurantStove", MESH["stove"], (1,1,1), "Restaurant: STOVE", {}, False),
    ("BP_RestaurantTrash", MESH["trash"], (1,1,1), "Restaurant: TRASH", {}, False),
    ("BP_RestaurantOpenSign", MESH["sign"], (1.2,1.2,1.2), "Restaurant: OPEN SIGN", {}, False),
]
bps={"BP_RestaurantInteractable": bp_base}
for name, mesh, scale, label, extra_vars, is_table in child_defs:
    bp=create_bp(name, parent=base_cls if base_cls else unreal.Actor)
    if is_table:
        add_var(bp,"TableId", pin_type("int"))
        add_var(bp,"bOccupied", pin_type("bool"))
        add_var(bp,"CurrentDishId", pin_type("int"))
    if name.endswith("Stove"):
        add_var(bp,"bCooking", pin_type("bool"))
        add_var(bp,"bCookReady", pin_type("bool"))
        add_var(bp,"CookingDishId", pin_type("int"))
    if name.endswith("OpenSign"):
        add_var(bp,"bIsOpenBusiness", pin_type("bool"))
    ensure_mesh(bp,"PropMesh", mesh, scale)
    # do NOT re-wire inherited RestaurantInteract
    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR+"/"+name)
    try:
        cdo=unreal.get_default_object(bp.generated_class())
        cdo.set_editor_property("interact_label", label)
        cdo.set_editor_property("interact_range", 280.0)
    except Exception as e:
        log("cdo "+name+" "+str(e))
    bps[name]=bp
    log("ready "+name)

# Manager
bp_mgr=create_bp("BP_RestaurantManager")
add_var(bp_mgr,"bIsOpenBusiness", pin_type("bool"))
add_var(bp_mgr,"InteractRange", pin_type("real","double"))
add_var(bp_mgr,"HeldDishId", pin_type("int"))
bel.compile_blueprint(bp_mgr)
try:
    unreal.get_default_object(bp_mgr.generated_class()).set_editor_property("interact_range", 280.0)
except Exception: pass
unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantManager")
bps["BP_RestaurantManager"]=bp_mgr

# ---- Manager EventGraph: HandlePlayerE with GetAllActorsWithTag + distance pick via Python-free approach ----
# Use Receive any key? Custom event HandlePlayerE
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp_mgr))
# remove prior HandlePlayerE chains
kill=[]
for n in list(mge.list_all_nodes()):
    t=bel.get_node_title(n)
    if "HandlePlayerE" in t or (t=="Print String"):
        # only remove restaurant-related prints near HandlePlayerE later; for now remove all HandlePlayerE
        if "HandlePlayerE" in t:
            kill.append(n)
# remove downstream of HandlePlayerE
for n in list(mge.list_all_nodes()):
    if "HandlePlayerE" in bel.get_node_title(n):
        kill.append(n)
if kill:
    # also wipe nodes that look like our previous attempt by title keywords
    pass
# Aggressive cleanup of non-default event graph nodes except BeginPlay/Tick if any
keep_titles=("Event BeginPlay","ReceiveBeginPlay","Event Tick","ReceiveTick","Event ActorBeginOverlap")
kill2=[]
for n in mge.list_all_nodes():
    t=bel.get_node_title(n)
    cn=n.get_class().get_name()
    if cn.startswith("K2Node_Event") and any(k in t for k in ("BeginPlay","Tick")):
        continue
    if "HandlePlayerE" in t or "GetAllActorsWithTag" in t or "GetPlayerPawn" in t or "Cast To BP_Restaurant" in t or t=="RestaurantInteract" or "Array_Get" in t or "Array_Length" in t:
        kill2.append(n)
    if t=="Print String":
        kill2.append(n)
if kill2:
    mge.remove_nodes(list({id(x):x for x in kill2}.values()))
    log("mgr cleaned "+str(len(kill2)))

he=mge.add_custom_event_node("HandlePlayerE")
bel.set_node_pos(he, pos(0,200))

get_pawn=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(get_pawn, pos(280,200))
connect(find_pin(he,"then","Output") or find_pin(he,"execute","Output"), find_pin(get_pawn,"execute","Input"), "he->pawn")
set_default(find_pin(get_pawn,"PlayerIndex","Input"),"0")

pawn_loc=mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
bel.set_node_pos(pawn_loc, pos(560,320))
connect(find_pin(get_pawn,"ReturnValue","Output"), find_pin(pawn_loc,"self","Input"), "pawn->loc")

gat=mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gat, pos(560,200))
connect(find_pin(get_pawn,"then","Output"), find_pin(gat,"execute","Input"), "pawn->gat")
set_default(find_pin(gat,"Tag","Input"), "RestInteract")

# ForEachLoop macro
foreach=None
try:
    foreach=mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
except Exception as e:
    log("foreach1 "+str(e))
    try:
        foreach=mge.create_node_from_name("ForEachLoop", unreal.Vector2D(900,200), [])
    except Exception as e2:
        log("foreach2 "+str(e2))

best_msg_printed=False
if foreach:
    bel.set_node_pos(foreach, pos(900,200))
    connect(find_pin(gat,"then","Output"), find_pin(foreach,"Exec","Input") or find_pin(foreach,"execute","Input"), "gat->fe")
    connect(find_pin(gat,"OutActors","Output"), find_pin(foreach,"Array","Input"), "arr->fe")
    # On each: get loc, distance, branch if < range — full closest needs vars; knife-1: call interact if Dist2D < 280
    # Distance
    act_loc=mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(act_loc, pos(1200,120))
    connect(find_pin(foreach,"Array Element","Output") or find_pin(foreach,"Element","Output"), find_pin(act_loc,"self","Input"), "el->loc")
    dist=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance2D")
    bel.set_node_pos(dist, pos(1500,200))
    connect(find_pin(pawn_loc,"ReturnValue","Output"), find_pin(dist,"A","Input") or find_pin(dist,"V1","Input"), "p->d")
    connect(find_pin(act_loc,"ReturnValue","Output"), find_pin(dist,"B","Input") or find_pin(dist,"V2","Input"), "a->d")
    # Less than
    lt=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_DoubleDouble")
    if lt is None:
        lt=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    bel.set_node_pos(lt, pos(1750,200))
    connect(find_pin(dist,"ReturnValue","Output"), find_pin(lt,"A","Input"), "d->lt")
    set_default(find_pin(lt,"B","Input"), "280.0")
    br=mge.add_branch_node(); bel.set_node_pos(br, pos(2000,200))
    connect(find_pin(foreach,"LoopBody","Output") or find_pin(foreach,"Then","Output"), find_pin(br,"execute","Input"), "fe->br")
    connect(find_pin(lt,"ReturnValue","Output"), find_pin(br,"Condition","Input"), "lt->br")
    # Cast + Interact
    cast_n=None
    for cname in ("Cast To BP_RestaurantInteractable", "Utilities|Casting|Cast To BP_RestaurantInteractable"):
        try:
            cast_n=mge.create_node_from_name(cname, unreal.Vector2D(2300,150), [])
            if cast_n: break
        except Exception: pass
    if cast_n:
        bel.set_node_pos(cast_n, pos(2300,150))
        connect(find_pin(br,"then","Output"), find_pin(cast_n,"execute","Input"), "br->cast")
        connect(find_pin(foreach,"Array Element","Output") or find_pin(foreach,"Element","Output"), find_pin(cast_n,"Object","Input"), "el->cast")
        call_i=mge.add_call_function_node(DIR+"/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i, pos(2700,150))
        connect(find_pin(cast_n,"then","Output"), find_pin(call_i,"execute","Input"), "cast->i")
        as_pin=None
        for p in bel.list_all_pins(cast_n):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin=p; break
        connect(as_pin, find_pin(call_i,"self","Input"), "as->i")
        # BUG: foreach will call ALL in range; OK for knife-1 if props spaced >280 apart — our spacing is ~200 for some. Tables 200 apart!
        # Reduce range to 150 for call-all, or break after first. Without easy break, set range 120.
        set_default(find_pin(lt,"B","Input"), "150.0")
        log("foreach distance interact wired range=150")
    else:
        pr=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(2300,150))
        connect(find_pin(br,"then","Output"), find_pin(pr,"execute","Input"), "br->pr")
        set_default(find_pin(pr,"InString","Input"), "Restaurant: near a RestInteract prop (cast missing)")
else:
    # fallback Array_Get 0
    get0=mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(900,200))
    connect(find_pin(gat,"OutActors","Output"), find_pin(get0,"TargetArray","Input"), "a->0")
    set_default(find_pin(get0,"Index","Input"),"0")
    pr=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(1200,200))
    connect(find_pin(gat,"then","Output"), find_pin(pr,"execute","Input"), "gat->pr")
    set_default(find_pin(pr,"InString","Input"), "Restaurant E: actors tagged (foreach missing) — check first")
    set_default(find_pin(pr,"Duration","Input"),"2.5")

# Also add Completed print
if foreach:
    prc=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(prc, pos(1200,400))
    connect(find_pin(foreach,"Completed","Output"), find_pin(prc,"execute","Input"), "fe->done")
    set_default(find_pin(prc,"InString","Input"), "Restaurant E: scan done")
    set_default(find_pin(prc,"Duration","Input"),"1.5")

bel.compile_blueprint(bp_mgr)
unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantManager")
log("manager HandlePlayerE compiled")

# ---- Place actors ----
removed=0
for a in list(eas.get_all_level_actors()):
    lab=a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        eas.destroy_actor(a); removed+=1
log("removed "+str(removed))

def tag_rest(actor):
    try:
        tags=list(actor.get_editor_property("tags") or [])
    except Exception:
        tags=[]
    n=unreal.Name("RestInteract")
    if n not in tags:
        tags.append(n)
        try: actor.set_editor_property("tags", tags)
        except Exception as e: log("tag "+str(e))

def spawn_bp(bp, location, label, props=None):
    cls=bp.generated_class()
    if not cls:
        bel.compile_blueprint(bp); cls=bp.generated_class()
    actor=eas.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator())
    if not actor:
        REPORT["errors"].append("spawn "+label); return None
    actor.set_actor_label(label)
    tag_rest(actor)
    if props:
        for k,v in props.items():
            try: actor.set_editor_property(k,v)
            except Exception as e: log("prop {} {}".format(k,e))
    REPORT["actors"].append({"label":label,"loc":location})
    log("spawn "+label)
    return actor

chair_mesh=unreal.EditorAssetLibrary.load_asset(MESH["chair"])
for key in ("chair1a","chair1b","chair2a","chair2b"):
    loc=ZONE[key]
    a=eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator())
    if a:
        a.set_actor_label("RestChair_"+key)
        try:
            a.static_mesh_component.set_editor_property("static_mesh", chair_mesh)
            a.set_actor_scale3d(unreal.Vector(0.7,0.7,0.55))
        except Exception as e: log("chair "+str(e))
        REPORT["actors"].append({"label":"RestChair_"+key,"loc":loc})

spawn_bp(bps["BP_RestaurantTable"], ZONE["table1"], "Restaurant_Table1", {"table_id":1, "interact_label":"Restaurant: TABLE 1"})
spawn_bp(bps["BP_RestaurantTable"], ZONE["table2"], "Restaurant_Table2", {"table_id":2, "interact_label":"Restaurant: TABLE 2"})
spawn_bp(bps["BP_RestaurantStove"], ZONE["stove"], "Restaurant_Stove", {"interact_label":"Restaurant: STOVE"})
spawn_bp(bps["BP_RestaurantTrash"], ZONE["trash"], "Restaurant_Trash", {"interact_label":"Restaurant: TRASH"})
spawn_bp(bps["BP_RestaurantOpenSign"], ZONE["sign"], "Restaurant_OpenSign", {"interact_label":"Restaurant: OPEN SIGN (toggle local; clock gate next)", "b_is_open_business":False})
spawn_bp(bps["BP_RestaurantManager"], ZONE["manager"], "Restaurant_Manager", {"b_is_open_business":False, "interact_range":280.0})
# Manager should NOT be tagged RestInteract — remove tag
for a in eas.get_all_level_actors():
    if a.get_actor_label()=="Restaurant_Manager":
        try: a.set_editor_property("tags", [])
        except Exception: pass

# ---- Character wire ----
char_path="/Game/TopDown/Blueprints/BP_TopDownCharacter"
cbp=unreal.EditorAssetLibrary.load_asset(char_path)
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# cleanup old gate
kill=[]
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "RestaurantGate" in t or "Cast To BP_RestaurantManager" in t:
        kill.append(n)
# remove RestaurantGate downstream except TillSoil / IA
seeds=[n for n in cge.list_all_nodes() if "RestaurantGate" in bel.get_node_title(n)]
for seed in seeds:
    stack=[seed]; seen=set([id(seed)])
    while stack:
        n=stack.pop()
        if n is not seed: kill.append(n)
        for p in bel.list_all_pins(n):
            if "output" not in str(p.get_pin_direction()).lower(): continue
            for cp in p.list_connected_pins():
                on=cp.get_owning_node(); 
                if id(on) in seen: continue
                if bel.get_node_title(on) in ("TillSoil",) or "IA_Interact" in bel.get_node_title(on):
                    continue
                seen.add(id(on)); stack.append(on)
# also kill GetActorOfClass that feeds restaurant
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if t in ("Get Actor Of Class","GetActorOfClass") and id(n) in {id(x) for x in kill}:
        kill.append(n)
if kill:
    # filter TillSoil IA
    kill=[n for n in kill if bel.get_node_title(n)!="TillSoil" and "IA_Interact" not in bel.get_node_title(n)]
    cge.remove_nodes(list({id(n):n for n in kill}.values()))
    log("char cleaned "+str(len(kill)))

ia=None; till=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="TillSoil": till=n

ce=cge.add_custom_event_node("RestaurantGate")
bel.set_node_pos(ce, pos(-1800,1100))
get_mgr=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
bel.set_node_pos(get_mgr, pos(-1500,1100))
connect(find_pin(ce,"then","Output") or find_pin(ce,"execute","Output"), find_pin(get_mgr,"execute","Input"), "ce->gm")
cls_pin=find_pin(get_mgr,"ActorClass","Input")
mgr_cls=bps["BP_RestaurantManager"].generated_class()
if cls_pin and mgr_cls:
    try: cls_pin.set_default_value(mgr_cls.get_path_name())
    except Exception:
        try: cls_pin.set_pin_value(mgr_cls.get_path_name())
        except Exception as e: log("cls "+str(e))

cast_m=None
for cname in ("Cast To BP_RestaurantManager","Utilities|Casting|Cast To BP_RestaurantManager"):
    try:
        cast_m=cge.create_node_from_name(cname, unreal.Vector2D(-1200,1100), [])
        if cast_m: break
    except Exception: pass

if cast_m:
    bel.set_node_pos(cast_m, pos(-1200,1100))
    connect(find_pin(get_mgr,"then","Output"), find_pin(cast_m,"execute","Input"), "gm->cm")
    connect(find_pin(get_mgr,"ReturnValue","Output"), find_pin(cast_m,"Object","Input"), "rv->obj")
    # Call custom event HandlePlayerE — create from name
    call_he=None
    for cname in ("HandlePlayerE", "Call HandlePlayerE"):
        try:
            call_he=cge.create_node_from_name(cname, unreal.Vector2D(-850,1100), [])
            if call_he: break
        except Exception: pass
    if call_he is None:
        # try add_call_function — custom events sometimes appear as call
        try:
            call_he=cge.add_call_function_node(DIR+"/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
        except Exception as e:
            log("call_he "+str(e))
    if call_he:
        bel.set_node_pos(call_he, pos(-850,1100))
        connect(find_pin(cast_m,"then","Output"), find_pin(call_he,"execute","Input"), "cm->he")
        as_pin=None
        for p in bel.list_all_pins(cast_m):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin=p; break
        connect(as_pin, find_pin(call_he,"self","Input"), "as->he")
        if till:
            connect(find_pin(call_he,"then","Output"), find_pin(till,"execute","Input"), "he->till")
        log("wired HandlePlayerE")
    else:
        pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(-850,1100))
        connect(find_pin(cast_m,"then","Output"), find_pin(pr,"execute","Input"), "cm->pr")
        set_default(find_pin(pr,"InString","Input"), "RestaurantGate: cast Manager OK; call HandlePlayerE manually next")
        if till: connect(find_pin(pr,"then","Output"), find_pin(till,"execute","Input"), "pr->till")
else:
    pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(-1200,1100))
    connect(find_pin(get_mgr,"then","Output"), find_pin(pr,"execute","Input"), "gm->pr")
    set_default(find_pin(pr,"InString","Input"), "RestaurantGate: Manager lookup (no cast node)")
    if till: connect(find_pin(pr,"then","Output"), find_pin(till,"execute","Input"), "pr->till")

if ia:
    started=find_pin(ia,"Started","Output")
    if started:
        try: bel.break_pin_links(started)
        except Exception:
            for cp in list(started.list_connected_pins()):
                try: started.break_link_to(cp)
                except Exception: pass
        connect(started, find_pin(ce,"execute","Input"), "IA->Gate")

ok=bel.compile_blueprint(cbp)
log("char compile "+str(ok))
unreal.EditorAssetLibrary.save_asset(char_path)

els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save level "+str(els.save_current_level()))
for name in bps:
    unreal.EditorAssetLibrary.save_asset(DIR+"/"+name)

out=r"E:\UE\FarmSim25D\Saved\restaurant_slice1_report.json"
open(out,"w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
log("DONE")
print(json.dumps(REPORT,ensure_ascii=False,indent=2))
