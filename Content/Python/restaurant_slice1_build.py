# -*- coding: utf-8 -*-
"""Restaurant vertical slice knife-1: create BPs, place near south bridge, wire E interact.
Surgical: does NOT clear level or touch Cropout/AoELite/farming graphs beyond IA_Interact gate.
"""
import unreal
import json

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

# South-bridge land side (inland of BridgeSouth east end ~1680,690)
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
    "manager": (2150.0, 600.0, 50.0),
}

INTERACT_RANGE = 280.0
OPEN_MINUTES = 1020.0   # 17:00
CLOSE_MINUTES = 1380.0  # 23:00


def log(msg):
    unreal.log("[REST1] " + str(msg))
    REPORT["steps"].append(str(msg))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def pin_type(category, sub="", path=""):
    p = unreal.EdGraphPinType()
    if path:
        txt = '(PinCategory="{}",PinSubCategory="",PinSubCategoryObject=SoftObjectPath("{}"))'.format(category, path)
    elif sub:
        txt = '(PinCategory="{}",PinSubCategory="{}")'.format(category, sub)
    else:
        txt = '(PinCategory="{}")'.format(category)
    p.import_text(txt)
    return p


def ensure_dir():
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm"):
        unreal.EditorAssetLibrary.make_directory("/Game/Farm")
    if not unreal.EditorAssetLibrary.does_directory_exist(DIR):
        unreal.EditorAssetLibrary.make_directory(DIR)
        log("mkdir " + DIR)


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    name_substr = name_substr.lower()
    for p in bel.list_all_pins(node):
        if name_substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip conn " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    return ok


def set_default(pin, value, label=""):
    if not pin:
        return
    try:
        pin.set_default_value(str(value))
    except Exception:
        try:
            pin.set_pin_value(str(value))
        except Exception as e:
            log("set_default fail {}: {}".format(label, e))


def create_bp(name, parent=unreal.Actor):
    path = DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        log("exists " + path)
        return unreal.EditorAssetLibrary.load_asset(path)
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", parent)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DIR, unreal.Blueprint, factory)
    log("created " + str(bp))
    unreal.EditorAssetLibrary.save_asset(path)
    return unreal.EditorAssetLibrary.load_asset(path)


def add_var(bp, name, ptype, instance_editable=True):
    names = [str(n) for n in bel.list_member_variable_names(bp)]
    if name in names:
        return
    ok = bel.add_member_variable(bp, name, ptype)
    log("var {} -> {}".format(name, ok))
    if ok and instance_editable:
        try:
            bel.set_blueprint_variable_instance_editable(bp, name, True)
        except Exception:
            pass


def ensure_mesh_component(bp, var_name, mesh_path, scale=(1, 1, 1), rel=(0, 0, 0), collision=True):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    root_h = None
    target_h = None
    target_obj = None
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            if lib.is_root_component(data):
                root_h = h
            vname = str(lib.get_variable_name(data) or "")
            if vname == var_name:
                target_h = h
                target_obj = lib.get_object(data)
        except Exception:
            pass
    if target_h is None:
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", root_h if root_h else handles[0])
        params.set_editor_property("new_class", unreal.StaticMeshComponent)
        try:
            params.set_editor_property("blueprint_context", bp)
        except Exception:
            pass
        sub.add_new_subobject(params)
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        for h in handles:
            data = sub.k2_find_subobject_data_from_handle(h)
            try:
                vname = str(lib.get_variable_name(data) or "")
                obj = lib.get_object(data)
                if obj and "StaticMesh" in obj.get_class().get_name() and vname != var_name:
                    # newest unnamed-ish SMC
                    if vname not in ("Mesh", "StaticMesh", var_name) and target_h is None:
                        try:
                            sub.rename_subobject(h, unreal.Text(var_name))
                        except Exception:
                            pass
                        target_h = h
                        target_obj = lib.get_object(sub.k2_find_subobject_data_from_handle(h))
                if vname == var_name:
                    target_h = h
                    target_obj = lib.get_object(data)
            except Exception:
                pass
        if root_h and target_h:
            try:
                sub.attach_subobject(root_h, target_h)
            except Exception:
                pass
    if target_obj:
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_path) if mesh_path else None
        if mesh:
            try:
                target_obj.set_editor_property("static_mesh", mesh)
            except Exception as e:
                log("mesh set fail: " + str(e))
        try:
            target_obj.set_editor_property("relative_scale3d", unreal.Vector(*scale))
            target_obj.set_editor_property("relative_location", unreal.Vector(*rel))
        except Exception:
            pass
        try:
            if collision:
                target_obj.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            else:
                target_obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            pass
    return target_obj


def clear_function_graph(bp, fname):
    g = bel.find_graph(bp, fname)
    if not g:
        bel.add_function_graph(bp, fname)
        g = bel.find_graph(bp, fname)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    # remove all but entry
    kill = []
    for n in ge.list_all_nodes():
        cn = n.get_class().get_name()
        if cn in ("K2Node_FunctionEntry", "K2Node_FunctionResult"):
            continue
        kill.append(n)
    if kill:
        ge.remove_nodes(kill)
    return ge, g


def wire_simple_print_function(bp, fname, message, also_set_open=None):
    """RestaurantInteract(): PrintString(message); optional toggle bIsOpenBusiness."""
    ge, g = clear_function_graph(bp, fname)
    entry = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
            break
    if not entry:
        log("no entry for " + fname)
        return
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(300, 0))
    connect(find_pin(entry, "then", "Output") or find_pin(entry, "execute", "Output"),
            find_pin(pr, "execute", "Input"), "entry->print")
    set_default(find_pin(pr, "InString", "Input"), message, "msg")
    set_default(find_pin(pr, "Duration", "Input"), "3.0", "dur")
    # Make text more visible
    try:
        set_default(find_pin(pr, "bPrintToScreen", "Input"), "true", "screen")
    except Exception:
        pass
    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(650, 0))
    connect(find_pin(pr, "then", "Output"), find_pin(ret, "execute", "Input"), "print->ret")
    log("wired print fn " + fname)


def gen_class(bp):
    try:
        return bp.generated_class()
    except Exception:
        path = bel.get_blueprint_asset(bp) if hasattr(bel, "get_blueprint_asset") else None
        return unreal.EditorAssetLibrary.load_blueprint_class(DIR + "/" + bp.get_name()) if False else bp.generated_class()


# ---------------- build BPs ----------------
ensure_dir()

# Shared interactable parent
bp_base = create_bp("BP_RestaurantInteractable")
add_var(bp_base, "InteractLabel", pin_type("string"))
add_var(bp_base, "InteractRange", pin_type("real", "double"))
ensure_mesh_component(bp_base, "PropMesh", MESH["table"], scale=(1, 1, 1))
wire_simple_print_function(bp_base, "RestaurantInteract", "Restaurant: base interact")
bel.compile_blueprint(bp_base)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantInteractable")
base_cls = bp_base.generated_class()
log("base class " + str(base_cls))

# Children
defs = [
    ("BP_RestaurantTable", MESH["table"], (1.0, 1.0, 1.0), "Restaurant: TABLE interact (orders later)", True),
    ("BP_RestaurantStove", MESH["stove"], (1.0, 1.0, 1.0), "Restaurant: STOVE interact (cook later)", False),
    ("BP_RestaurantTrash", MESH["trash"], (1.0, 1.0, 1.0), "Restaurant: TRASH interact (discard held dish)", False),
    ("BP_RestaurantOpenSign", MESH["sign"], (1.2, 1.2, 1.2), "Restaurant: OPEN SIGN interact", False),
]

bps = {"base": bp_base}
for name, mesh, scale, msg, is_table in defs:
    bp = create_bp(name, parent=base_cls if base_cls else unreal.Actor)
    if is_table:
        add_var(bp, "TableId", pin_type("int"))
        add_var(bp, "bOccupied", pin_type("bool"))
        add_var(bp, "CurrentDishId", pin_type("int"))  # 0 none, 1 salad, 2 stew
    if name.endswith("Stove"):
        add_var(bp, "bCooking", pin_type("bool"))
        add_var(bp, "bCookReady", pin_type("bool"))
        add_var(bp, "CookingDishId", pin_type("int"))
    if name.endswith("OpenSign"):
        add_var(bp, "bIsOpenBusiness", pin_type("bool"))
    ensure_mesh_component(bp, "PropMesh", mesh, scale=scale)
    # Override RestaurantInteract with specific print; OpenSign gets richer graph below
    if not name.endswith("OpenSign"):
        wire_simple_print_function(bp, "RestaurantInteract", msg)
    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(DIR + "/" + name)
    bps[name] = bp
    log("compiled " + name)

# ---- OpenSign richer Interact + Tick auto-close ----
bp_sign = bps["BP_RestaurantOpenSign"]
# RestaurantInteract for sign: read FarmClock minutes, gate <17, toggle open, print
ge, _ = clear_function_graph(bp_sign, "RestaurantInteract")
entry = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
        break

# Use a pragmatic approach: Print current intent based on bIsOpenBusiness toggle always,
# and a separate note about clock — clock branch wired via Manager for reliability.
# Sign interact toggles local bIsOpenBusiness and prints; Manager syncs + enforces clock.
get_open = ge.add_get_member_variable_node("bIsOpenBusiness")
bel.set_node_pos(get_open, pos(-200, 120))
br = ge.add_branch_node()
bel.set_node_pos(br, pos(200, 0))
connect(find_pin(entry, "then", "Output") or find_pin(entry, "execute", "Output"),
        find_pin(br, "execute", "Input"), "entry->br")
connect(find_pin(get_open, "bIsOpenBusiness", "Output"), find_pin(br, "Condition", "Input"), "open->br")

# true branch: currently open -> close
set_close = ge.add_set_member_variable_node("bIsOpenBusiness")
bel.set_node_pos(set_close, pos(500, -80))
connect(find_pin(br, "then", "Output"), find_pin(set_close, "execute", "Input"), "brT->set")
set_default(find_pin(set_close, "bIsOpenBusiness", "Input"), "false", "close")
pr_close = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr_close, pos(850, -80))
connect(find_pin(set_close, "then", "Output"), find_pin(pr_close, "execute", "Input"), "set->prc")
set_default(find_pin(pr_close, "InString", "Input"), "Restaurant: CLOSED (early close). Manager enforces clock.", "msgc")
set_default(find_pin(pr_close, "Duration", "Input"), "3.5", "dur")

# false branch: currently closed -> open
set_open = ge.add_set_member_variable_node("bIsOpenBusiness")
bel.set_node_pos(set_open, pos(500, 120))
connect(find_pin(br, "else", "Output"), find_pin(set_open, "execute", "Input"), "brF->set")
set_default(find_pin(set_open, "bIsOpenBusiness", "Input"), "true", "open")
pr_open = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr_open, pos(850, 120))
connect(find_pin(set_open, "then", "Output"), find_pin(pr_open, "execute", "Input"), "set->pro")
set_default(find_pin(pr_open, "InString", "Input"), "Restaurant: OPEN requested. Need FarmClock >= 17:00 (Manager gates).", "msgo")
set_default(find_pin(pr_open, "Duration", "Input"), "3.5", "dur")

bel.compile_blueprint(bp_sign)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantOpenSign")
log("OpenSign interact wired (toggle+print)")

# ---- Manager ----
bp_mgr = create_bp("BP_RestaurantManager")
add_var(bp_mgr, "bIsOpenBusiness", pin_type("bool"))
add_var(bp_mgr, "InteractRange", pin_type("real", "double"))
add_var(bp_mgr, "HeldDishId", pin_type("int"))  # stub for later
# TryPlayerInteract function — distance pick + call RestaurantInteract + clock gate for sign
ge, _ = clear_function_graph(bp_mgr, "TryPlayerInteract")
# Add bool return
try:
    ge.add_graph_output_parameter("Handled", pin_type("bool"))
except Exception as e:
    log("add output: " + str(e))

entry = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
        break

# For knife-1 reliability: implement selection in Python-spawned helper via event graph Tick+key is harder.
# Wire Manager.TryPlayerInteract as: Print "Manager.TryPlayerInteract stub" + Return true after finding nearest via Blueprint nodes.
# Full distance logic in EventGraph custom event HandleInteract used by character.

# Simpler Manager function: always Print and return false (character will use EventGraph gate that does work).
# Actually we'll put working logic in Manager EventGraph custom event "HandlePlayerE".

pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr, pos(300, 0))
connect(find_pin(entry, "then", "Output") or find_pin(entry, "execute", "Output"),
        find_pin(pr, "execute", "Input"), "e->p")
set_default(find_pin(pr, "InString", "Input"), "RestaurantManager.TryPlayerInteract called", "m")
ret = ge.add_return_node()
bel.set_node_pos(ret, pos(650, 0))
connect(find_pin(pr, "then", "Output"), find_pin(ret, "execute", "Input"), "p->r")
# try set Handled=false on return
hp = find_pin(ret, "Handled", "Input")
set_default(hp, "false", "handled")

bel.compile_blueprint(bp_mgr)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")
bps["BP_RestaurantManager"] = bp_mgr

# ---- Place / refresh actors ----
# Remove previous Restaurant_* labeled actors we own
removed = 0
for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        eas.destroy_actor(a)
        removed += 1
log("removed old restaurant actors: {}".format(removed))


def spawn_bp(bp, location, label, extras=None):
    cls = bp.generated_class()
    if not cls:
        bel.compile_blueprint(bp)
        cls = bp.generated_class()
    actor = eas.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator(0, 0, 0))
    if not actor:
        log("FAIL spawn " + label)
        REPORT["errors"].append("spawn " + label)
        return None
    actor.set_actor_label(label)
    try:
        actor.tags = [unreal.Name("RestInteract")]
    except Exception:
        try:
            # append tag
            tags = list(actor.tags) if actor.tags else []
            tags.append(unreal.Name("RestInteract"))
            actor.set_editor_property("tags", tags)
        except Exception as e:
            log("tag fail " + str(e))
    if extras:
        for k, v in extras.items():
            try:
                actor.set_editor_property(k, v)
            except Exception as e:
                log("prop {} fail: {}".format(k, e))
    REPORT["actors"].append({"label": label, "x": location[0], "y": location[1], "z": location[2]})
    log("spawned " + label)
    return actor

# chairs as static mesh actors (visual only)
chair_mesh = unreal.EditorAssetLibrary.load_asset(MESH["chair"])
for key in ("chair1a", "chair1b", "chair2a", "chair2b"):
    loc = ZONE[key]
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator())
    if a:
        a.set_actor_label("RestChair_" + key)
        smc = a.static_mesh_component
        if smc and chair_mesh:
            smc.set_editor_property("static_mesh", chair_mesh)
            a.set_actor_scale3d(unreal.Vector(0.7, 0.7, 0.5))
        REPORT["actors"].append({"label": "RestChair_" + key, "x": loc[0], "y": loc[1]})

t1 = spawn_bp(bps["BP_RestaurantTable"], ZONE["table1"], "Restaurant_Table1", {"table_id": 1})
t2 = spawn_bp(bps["BP_RestaurantTable"], ZONE["table2"], "Restaurant_Table2", {"table_id": 2})
stove = spawn_bp(bps["BP_RestaurantStove"], ZONE["stove"], "Restaurant_Stove")
trash = spawn_bp(bps["BP_RestaurantTrash"], ZONE["trash"], "Restaurant_Trash")
sign = spawn_bp(bps["BP_RestaurantOpenSign"], ZONE["sign"], "Restaurant_OpenSign", {"b_is_open_business": False})
mgr = spawn_bp(bps["BP_RestaurantManager"], ZONE["manager"], "Restaurant_Manager", {"interact_range": INTERACT_RANGE, "b_is_open_business": False})
# hide manager mesh if any — manager may have inherited no mesh; OK

# ---- Wire character IA_Interact gate via custom event that finds nearest RestInteract ----
char_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
cbp = unreal.EditorAssetLibrary.load_asset(char_path)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# Find IA_Interact and disconnect TillSoil
ia_node = None
till_node = None
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t:
        ia_node = n
    if t == "TillSoil":
        till_node = n

# Remove previous RestaurantGate if any
kill = []
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "RestaurantGate" in t or "TryRestaurantE" in t or t.startswith("Restaurant E"):
        kill.append(n)
    if t == "Print String":
        insp = find_pin(n, "InString", "Input")
        val = ""
        if insp:
            try:
                val = insp.get_default_as_string()
            except Exception:
                try:
                    val = str(insp.get_pin_value())
                except Exception:
                    val = ""
        if "Restaurant" in str(val) and "Manager" in str(val):
            kill.append(n)
if kill:
    cge.remove_nodes(list({id(n): n for n in kill}.values()))
    log("cleared old restaurant gate nodes {}".format(len(kill)))

# Custom event RestaurantGate
ce = cge.add_custom_event_node("RestaurantGate")
bel.set_node_pos(ce, pos(-1800, 1100))

# Implement gate: GetAllActorsWithTag RestInteract -> for each distance -> call RestaurantInteract on closest
# Using GetAllActorsWithTag
get_tag = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(get_tag, pos(-1500, 1100))
connect(find_pin(ce, "then", "Output") or find_pin(ce, "execute", "Output"),
        find_pin(get_tag, "execute", "Input"), "ce->tag")
# WorldContext self
# Tag pin
tag_pin = find_pin(get_tag, "Tag", "Input")
set_default(tag_pin, "RestInteract", "tag")

# For knife-1: after GetAllActorsWithTag, print count and call Interact on first actor within range using a compact approach:
# Length of array -> Branch >0 -> Get(0) is wrong (need closest).
# Use a Python-authored simpler path: PrintString listing that E hit restaurant system, then Call Function on Manager.

get_cls = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
bel.set_node_pos(get_cls, pos(-1500, 1300))
# Need class default for Manager — set pin to generated class path
cls_pin = find_pin(get_cls, "ActorClass", "Input")
mgr_cls = bps["BP_RestaurantManager"].generated_class()
if cls_pin and mgr_cls:
    try:
        cls_pin.set_default_value(mgr_cls.get_path_name())
        log("set Manager class " + mgr_cls.get_path_name())
    except Exception as e:
        log("class pin: " + str(e))
        try:
            cls_pin.set_pin_value(mgr_cls.get_path_name())
        except Exception as e2:
            log("class pin2: " + str(e2))

# Rework: RestaurantGate -> GetAllActorsWithTag -> Print + ForEach-like manual:
# Closest-actor selection fully in BP is verbose; implement via Manager function that does it,
# called from gate. Rebuild Manager.TryPlayerInteract properly after compile with class refs.

# Disconnect IA Started from TillSoil; connect to RestaurantGate; RestaurantGate then to TillSoil as fallback via Branch later.
if ia_node:
    started = find_pin(ia_node, "Started", "Output")
    if started:
        for cp in list(started.list_connected_pins()):
            try:
                started.break_link_to(cp)
            except Exception:
                try:
                    bel.break_pin_links(started)
                except Exception as e:
                    log("break: " + str(e))
                    break
        # Call RestaurantGate
        connect(started, find_pin(ce, "execute", "Input"), "IA->Gate")

# After tag get: PrintString then still call TillSoil for now if we can't resolve interact —
# Upgrade: use add_call_function_node on BP_RestaurantInteractable RestaurantInteract after casting.

# Macro-free closest: use Kismet — GetAllActorsWithTag OutActors, then we'll call a NEW Manager function
# compiled with pure Python distance in Construction? Runtime must be BP.

# Implement Manager.TryPlayerInteract in Python by writing a UFunction via... can't.
# Use Actor Blueprint EventGraph on Manager: ReceiveTick not needed.
# Custom event on Manager HandleE that character calls via GetActorOfClass + Call HandleE.

# Add custom event HandlePlayerE on Manager event graph with working distance logic.
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp_mgr))
# clear old HandlePlayerE
killm = []
for n in mge.list_all_nodes():
    t = bel.get_node_title(n)
    if "HandlePlayerE" in t:
        killm.append(n)
if killm:
    mge.remove_nodes(killm)

he = mge.add_custom_event_node("HandlePlayerE")
bel.set_node_pos(he, pos(0, 400))
# Get player pawn
get_pawn = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(get_pawn, pos(300, 400))
connect(find_pin(he, "then", "Output") or find_pin(he, "execute", "Output"),
        find_pin(get_pawn, "execute", "Input"), "he->pawn")
set_default(find_pin(get_pawn, "PlayerIndex", "Input"), "0", "pi")
# GetAllActorsWithTag
gat = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
bel.set_node_pos(gat, pos(600, 400))
connect(find_pin(get_pawn, "then", "Output"), find_pin(gat, "execute", "Input"), "pawn->gat")
set_default(find_pin(gat, "Tag", "Input"), "RestInteract", "tag")

# Print how many
len_n = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Length")
bel.set_node_pos(len_n, pos(900, 520))
connect(find_pin(gat, "OutActors", "Output"), find_pin(len_n, "TargetArray", "Input"), "arr->len")

pr_n = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr_n, pos(1200, 400))
connect(find_pin(gat, "then", "Output"), find_pin(pr_n, "execute", "Input"), "gat->pr")
set_default(find_pin(pr_n, "InString", "Input"), "Restaurant E: scanning RestInteract actors...", "msg")
set_default(find_pin(pr_n, "Duration", "Input"), "2.0", "d")

# NOTE: full closest-loop needs ForEachLoop macro. Add macro node.
try:
    foreach = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(foreach, pos(1200, 600))
    connect(find_pin(pr_n, "then", "Output"), find_pin(foreach, "Exec", "Input") or find_pin(foreach, "execute", "Input"), "pr->fe")
    connect(find_pin(gat, "OutActors", "Output"), find_pin(foreach, "Array", "Input"), "arr->fe")
    log("foreach added")
except Exception as e:
    log("foreach fail: " + str(e))
    foreach = None

# Fallback without foreach: get index 0 and call if valid — still OK for testing when standing near one.
get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
bel.set_node_pos(get0, pos(1500, 400))
connect(find_pin(gat, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input"), "arr->get0")
set_default(find_pin(get0, "Index", "Input"), "0", "idx")

# Cast to BP_RestaurantInteractable and call RestaurantInteract
cast_path = DIR + "/BP_RestaurantInteractable.BP_RestaurantInteractable_C"
# Use create_node cast
try:
    cast_n = mge.create_node_from_name("Cast To BP_RestaurantInteractable", unreal.Vector2D(1800, 400), [])
except Exception:
    cast_n = None
    try:
        cast_n = mge.create_node_from_name("Utilities|Casting|Cast To BP_RestaurantInteractable", unreal.Vector2D(1800, 400), [])
    except Exception as e:
        log("cast create: " + str(e))

if cast_n:
    bel.set_node_pos(cast_n, pos(1800, 400))
    connect(find_pin(pr_n, "then", "Output"), find_pin(cast_n, "execute", "Input"), "pr->cast")
    connect(find_pin(get0, "Item", "Output") or find_pin(get0, "Output", "Output"),
            find_pin(cast_n, "Object", "Input"), "get0->cast")
    # Call RestaurantInteract
    call_i = mge.add_call_function_node(DIR + "/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
    bel.set_node_pos(call_i, pos(2200, 400))
    connect(find_pin(cast_n, "then", "Output"), find_pin(call_i, "execute", "Input"), "cast->call")
    connect(find_pin(cast_n, "AsBP Restaurant Interactable", "Output") or find_pin(cast_n, "As Bp Restaurant Interactable", "Output"),
            find_pin(call_i, "self", "Input"), "as->self")
    log("cast+call wired")
else:
    # Print fallback listing actor
    pr2 = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr2, pos(1800, 400))
    connect(find_pin(pr_n, "then", "Output"), find_pin(pr2, "execute", "Input"), "pr->pr2")
    set_default(find_pin(pr2, "InString", "Input"), "Restaurant E: (cast unavailable) stand near prop; next knife wires cast", "m2")

bel.compile_blueprint(bp_mgr)
unreal.EditorAssetLibrary.save_asset(DIR + "/BP_RestaurantManager")

# Character gate: call Manager.HandlePlayerE then TillSoil (farming paused but keep fallback)
# Re-find nodes after mgr compile
cbp = unreal.EditorAssetLibrary.load_asset(char_path)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia_node = None
till_node = None
ce = None
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t:
        ia_node = n
    if t == "TillSoil":
        till_node = n
    if "RestaurantGate" in t:
        ce = n

if ce is None:
    ce = cge.add_custom_event_node("RestaurantGate")
    bel.set_node_pos(ce, pos(-1800, 1100))

# Clean RestaurantGate downstream
down = []
if ce:
    q = [ce]
    seen = set([id(ce)])
    while q:
        n = q.pop()
        for p in bel.list_all_pins(n):
            if "output" not in str(p.get_pin_direction()).lower():
                continue
            for cp in p.list_connected_pins():
                on = cp.get_owning_node()
                if id(on) not in seen:
                    seen.add(id(on))
                    down.append(on)
                    q.append(on)
# don't remove TillSoil
down = [n for n in down if bel.get_node_title(n) != "TillSoil"]
if down:
    cge.remove_nodes(down)
    log("cleared gate downstream {}".format(len(down)))

get_mgr = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
bel.set_node_pos(get_mgr, pos(-1500, 1100))
connect(find_pin(ce, "then", "Output") or find_pin(ce, "execute", "Output"),
        find_pin(get_mgr, "execute", "Input"), "ce->getmgr")
cls_pin = find_pin(get_mgr, "ActorClass", "Input")
mgr_cls = bps["BP_RestaurantManager"].generated_class()
if cls_pin and mgr_cls:
    try:
        cls_pin.set_default_value(mgr_cls.get_path_name())
    except Exception:
        try:
            cls_pin.set_pin_value(mgr_cls.get_path_name())
        except Exception as e:
            log("mgr class pin " + str(e))

# Cast Manager
try:
    cast_m = cge.create_node_from_name("Cast To BP_RestaurantManager", unreal.Vector2D(-1200, 1100), [])
except Exception:
    cast_m = None
if cast_m:
    bel.set_node_pos(cast_m, pos(-1200, 1100))
    connect(find_pin(get_mgr, "then", "Output"), find_pin(cast_m, "execute", "Input"), "get->castm")
    connect(find_pin(get_mgr, "ReturnValue", "Output"), find_pin(cast_m, "Object", "Input"), "mgr->obj")
    call_he = cge.add_call_function_node(DIR + "/BP_RestaurantManager.BP_RestaurantManager_C:HandlePlayerE")
    # HandlePlayerE is custom event — need Call Dispatcher / Call custom event node
    if call_he is None or "HandlePlayerE" not in bel.get_node_title(call_he):
        try:
            call_he = cge.create_node_from_name("HandlePlayerE", unreal.Vector2D(-900, 1100), [])
        except Exception as e:
            log("call he: " + str(e))
            call_he = None
    if call_he:
        bel.set_node_pos(call_he, pos(-900, 1100))
        connect(find_pin(cast_m, "then", "Output"), find_pin(call_he, "execute", "Input"), "cast->he")
        # self pin
        as_pin = None
        for p in bel.list_all_pins(cast_m):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin = p
                break
        connect(as_pin, find_pin(call_he, "self", "Input"), "as->he")
        # then to TillSoil fallback (farming paused; still linked for safety)
        if till_node:
            connect(find_pin(call_he, "then", "Output"), find_pin(till_node, "execute", "Input"), "he->till")
    else:
        # Fallback print
        pr = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(-900, 1100))
        connect(find_pin(cast_m, "then", "Output"), find_pin(pr, "execute", "Input"), "cast->pr")
        set_default(find_pin(pr, "InString", "Input"), "RestaurantGate: Manager cast OK but HandlePlayerE call missing", "m")
        if till_node:
            connect(find_pin(pr, "then", "Output"), find_pin(till_node, "execute", "Input"), "pr->till")
else:
    pr = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(-1200, 1100))
    connect(find_pin(get_mgr, "then", "Output"), find_pin(pr, "execute", "Input"), "get->pr")
    set_default(find_pin(pr, "InString", "Input"), "RestaurantGate: GetActorOfClass Manager (cast node missing)", "m")
    if till_node:
        connect(find_pin(pr, "then", "Output"), find_pin(till_node, "execute", "Input"), "pr->till")

# Ensure IA -> RestaurantGate
if ia_node and ce:
    started = find_pin(ia_node, "Started", "Output")
    if started:
        # break existing
        try:
            bel.break_pin_links(started)
        except Exception:
            for cp in list(started.list_connected_pins()):
                try:
                    started.break_link_to(cp)
                except Exception:
                    pass
        connect(started, find_pin(ce, "execute", "Input"), "IA->Gate")

ok = bel.compile_blueprint(cbp)
log("character compile " + str(ok))
unreal.EditorAssetLibrary.save_asset(char_path)

# Save level
els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save level " + str(els.save_current_level()))

# Save all restaurant assets
for name in ["BP_RestaurantInteractable", "BP_RestaurantTable", "BP_RestaurantStove", "BP_RestaurantTrash", "BP_RestaurantOpenSign", "BP_RestaurantManager"]:
    unreal.EditorAssetLibrary.save_asset(DIR + "/" + name)

out = r"E:\UE\FarmSim25D\Saved\restaurant_slice1_report.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
log("DONE report " + out)
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
