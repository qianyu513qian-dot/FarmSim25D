# -*- coding: utf-8 -*-
"""Seat guests at RestChair_* + visible held-dish mesh prop.
Surgical: patch SpawnGuestVisual transform; GuestMesh sit offset;
Manager SyncHeldVisual spawn/attach/destroy. No cook/serve/E wipe.
"""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
REPORT = {"steps": [], "errors": [], "ok": []}

TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
MESH_SALAD = "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Basket"
MESH_STEW = "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"
MARKER = "SeatHeld_v1"

def log(m):
    unreal.log("[SEATHELD] " + str(m))
    print("[SEATHELD] " + str(m))
    REPORT["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def out_data(node):
    if not node: return None
    for name in ("ReturnValue", "Return Value", "HeldDishId", "HeldDishActor", "GuestActor",
                 "GuestMesh", "bOccupied", "TableId"):
        p = find_pin(node, name, "Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "else", "completed", "loopbody"):
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); REPORT["errors"].append("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    if not ok: REPORT["errors"].append("fail " + label)
    return ok

def setdef(pin, val):
    if not pin: return False
    try:
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef " + str(e)[:80]); return False

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def make_print(ge, x, y, text, dur="1.0", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key: setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        bel.add_member_variable(bp, name, t)
        log("add var " + name)
        return True
    return False

def walk_then_terminal(start):
    """Return last then-output pin with no connections along primary then chain."""
    cur = start
    seen = set()
    last_then = find_pin(start, "then", "Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp = find_pin(cur, "then", "Output")
        if not tp: break
        nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            return tp, cur
        cur = nxts[0]
        last_then = find_pin(cur, "then", "Output")
    return last_then, cur

# ============================================================================
# 0) Idempotency
# ============================================================================
tbp = unreal.load_asset(TBL)
mbp = unreal.load_asset(MGR)
gbp = unreal.load_asset(GUEST)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

if find_custom(mge, MARKER) or find_custom(tge, MARKER):
    log("already applied " + MARKER)
    REPORT["ok"].append("already")
    open(r"E:\UE\FarmSim25D\Saved\rest_seat_held.json", "w", encoding="utf-8").write(
        json.dumps(REPORT, indent=2, ensure_ascii=False))
    raise SystemExit(0)

# ============================================================================
# 1) Guest mesh sit offset (lower) + slight crouch scale
# ============================================================================
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
mesh_obj = None
for h in list(sub.k2_gather_subobject_data_for_blueprint(gbp) or []):
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        vname = str(lib.get_variable_name(data) or "")
        obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
        if obj and "SkeletalMesh" in obj.get_class().get_name() and (vname == "GuestMesh" or mesh_obj is None):
            mesh_obj = obj
    except Exception as e:
        log("guest sub " + str(e)[:60])
if mesh_obj:
    try:
        mesh_obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -118.0))
        log("GuestMesh Z=-118 sit")
        REPORT["ok"].append("guest_sit_z")
    except Exception as e:
        REPORT["errors"].append("sit_z " + str(e)[:80])
    try:
        # slight squash to read as seated
        mesh_obj.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 0.88))
        log("GuestMesh Z-scale 0.88")
        REPORT["ok"].append("guest_sit_scale")
    except Exception as e:
        log("scale " + str(e)[:60])
bel.compile_blueprint(gbp)
eas.save_asset(GUEST)

# ============================================================================
# 2) SpawnGuestVisual: seat at south chair offset + face table
#    Table chair tXa is (0,-70,-12) relative; yaw 90 faces +Y toward table
# ============================================================================
# Find MakeTransform used by BeginDeferred
make_tf = None
make_off = None
add_vec = None
get_loc = None
for n in tge.list_all_nodes():
    if title(n) == "MakeTransform":
        rv = find_pin(n, "ReturnValue", "Output")
        links = []
        if rv:
            for c in rv.list_connected_pins() or []:
                links.append(title(c.get_owning_node()))
        if any("BeginDeferred" in L or "FinishSpawning" in L for L in links):
            make_tf = n
            locp = find_pin(n, "Location", "Input")
            if locp:
                for c in locp.list_connected_pins() or []:
                    own = c.get_owning_node()
                    if "vector" in title(own).lower() or "Add_Vector" in title(own) or title(own) == "vector + vector":
                        add_vec = own
            break

if add_vec:
    # B pin should be MakeVector offset
    bp = find_pin(add_vec, "B", "Input")
    if bp:
        for c in bp.list_connected_pins() or []:
            if "MakeVector" in title(c.get_owning_node()):
                make_off = c.get_owning_node()
    ap = find_pin(add_vec, "A", "Input")
    if ap:
        for c in ap.list_connected_pins() or []:
            if "Location" in title(c.get_owning_node()) or "GetActorLocation" in title(c.get_owning_node()):
                get_loc = c.get_owning_node()

log("make_tf={} make_off={} add_vec={}".format(bool(make_tf), bool(make_off), bool(add_vec)))

if make_off:
    setdef(find_pin(make_off, "X", "Input"), "0.0")
    setdef(find_pin(make_off, "Y", "Input"), "-70.0")
    setdef(find_pin(make_off, "Z", "Input"), "-8.0")
    log("offset -> chair south (0,-70,-8)")
    REPORT["ok"].append("chair_offset")
else:
    REPORT["errors"].append("no MakeVector offset found")

# Rotation: MakeRotator Pitch=0 Yaw=90 Roll=0 into MakeTransform.Rotation
if make_tf:
    rot_pin = find_pin(make_tf, "Rotation", "Input")
    # break existing if any
    if rot_pin and (rot_pin.list_connected_pins() or []):
        try: rot_pin.break_pin_links()
        except Exception: pass
    # Prefer setting default rotator if possible
    ok_def = setdef(rot_pin, "0.000000,90.000000,0.000000")
    log("set rotation default yaw90 -> " + str(ok_def))
    if not ok_def:
        mkrot = tge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
        bel.set_node_pos(mkrot, pos(200, -200))
        setdef(find_pin(mkrot, "Roll", "Input") or find_pin(mkrot, "A", "Input"), "0.0")
        # MakeRotator pin names: Roll, Pitch, Yaw
        setdef(find_pin(mkrot, "Pitch", "Input"), "0.0")
        setdef(find_pin(mkrot, "Yaw", "Input"), "90.0")
        connect(out_data(mkrot), rot_pin, "rot->tf")
        REPORT["ok"].append("chair_yaw_node")
    else:
        REPORT["ok"].append("chair_yaw_def")

# Append print after SpawnGuestVisual tint chain terminal
sg = find_custom(tge, "SpawnGuestVisual")
if sg:
    term, _ = walk_then_terminal(sg)
    if term and not (term.list_connected_pins() or []):
        pr = make_print(tge, 3200, 200, "Guest seated (chair)", dur="1.2", key="RestSeat")
        connect(term, find_pin(pr, "execute", "Input"), "spawn->seatPrint")
        REPORT["ok"].append("seat_print")

bel.compile_blueprint(tbp)
tst = str(tbp.get_editor_property("status"))
REPORT["table_status"] = tst
log("table " + tst)
if "ERROR" not in tst:
    eas.save_asset(TBL)
else:
    for n in tge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                REPORT["errors"].append("tbl:" + title(n) + ":" + str(em)[:160])
        except Exception:
            pass

# ============================================================================
# 3) Manager: HeldDishActor + SyncHeldVisual + wire into RestaurantTick / ClearHeld
# ============================================================================
# Actor object reference variable
names = [str(n) for n in bel.list_member_variable_names(mbp, False)]
if "HeldDishActor" not in names:
    # Try object type
    try:
        t = bel.get_basic_type_by_name("object")
        bel.add_member_variable(mbp, "HeldDishActor", t)
        log("added HeldDishActor object")
    except Exception as e:
        log("add HeldDishActor fail " + str(e)[:80])
        # Fallback: try via change after adding actor soft?
        try:
            # Some projects use 'object' then change to Actor
            bel.add_member_variable(mbp, "HeldDishActor", bel.get_basic_type_by_name("object"))
        except Exception as e2:
            REPORT["errors"].append("HeldDishActor " + str(e2)[:80])

# Recompile to expose var
bel.compile_blueprint(mbp)

# Build SyncHeldVisual custom event if missing
sync = find_custom(mge, "SyncHeldVisual")
if sync:
    log("SyncHeldVisual exists — skip body rebuild")
else:
    sync = mge.add_custom_event_node("SyncHeldVisual")
    bel.set_node_pos(sync, pos(-800, -1400))
    Y = -1400
    X0 = -500

    # Branch: HeldDishId != 0
    get_h = mge.add_get_member_variable_node("HeldDishId")
    bel.set_node_pos(get_h, pos(X0, Y + 120))
    ne = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
    bel.set_node_pos(ne, pos(X0 + 220, Y + 120))
    connect(out_data(get_h), find_pin(ne, "A", "Input"), "hA")
    setdef(find_pin(ne, "B", "Input"), "0")
    br = mge.add_branch_node(); bel.set_node_pos(br, pos(X0 + 450, Y))
    connect(find_pin(sync, "then", "Output"), find_pin(br, "execute", "Input"), "sync->hold?")
    connect(out_data(ne), find_pin(br, "Condition", "Input"), "holding?")

    # ELSE (empty hands): destroy HeldDishActor if valid
    get_act = mge.add_get_member_variable_node("HeldDishActor")
    bel.set_node_pos(get_act, pos(X0 + 700, Y + 280))
    is_valid = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(is_valid, pos(X0 + 950, Y + 280))
    connect(out_data(get_act), find_pin(is_valid, "Object", "Input") or find_pin(is_valid, "self", "Input"), "act->valid")
    br_v = mge.add_branch_node(); bel.set_node_pos(br_v, pos(X0 + 1200, Y + 220))
    connect(find_pin(br, "else", "Output"), find_pin(br_v, "execute", "Input"), "empty->valid?")
    connect(out_data(is_valid), find_pin(br_v, "Condition", "Input"), "valid?")
    destroy = mge.add_call_function_node("/Script/Engine.Actor:K2_DestroyActor")
    bel.set_node_pos(destroy, pos(X0 + 1500, Y + 220))
    connect(find_pin(br_v, "then", "Output"), find_pin(destroy, "execute", "Input"), "valid->destroy")
    connect(out_data(get_act), find_pin(destroy, "self", "Input"), "act->self")
    # clear ref
    set_none = mge.add_set_member_variable_node("HeldDishActor")
    bel.set_node_pos(set_none, pos(X0 + 1800, Y + 220))
    connect(find_pin(destroy, "then", "Output"), find_pin(set_none, "execute", "Input"), "des->clr")
    # leave HeldDishActor input unconnected = None
    pr_e = make_print(mge, X0 + 2100, Y + 220, " ", dur="0.05", key="RestHeldMesh")
    connect(find_pin(set_none, "then", "Output"), find_pin(pr_e, "execute", "Input"), "clr->print")

    # THEN (holding): ensure actor exists
    get_act2 = mge.add_get_member_variable_node("HeldDishActor")
    bel.set_node_pos(get_act2, pos(X0 + 700, Y + 40))
    is_valid2 = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(is_valid2, pos(X0 + 950, Y + 40))
    connect(out_data(get_act2), find_pin(is_valid2, "Object", "Input") or find_pin(is_valid2, "self", "Input"), "act2->v")
    br_ex = mge.add_branch_node(); bel.set_node_pos(br_ex, pos(X0 + 1200, Y))
    connect(find_pin(br, "then", "Output"), find_pin(br_ex, "execute", "Input"), "hold->exists?")
    connect(out_data(is_valid2), find_pin(br_ex, "Condition", "Input"), "exists?")

    # If NOT valid: spawn StaticMeshActor at player, attach, set
    # GetPlayerPawn -> GetActorLocation -> MakeTransform
    gpp = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(gpp, pos(X0 + 1400, Y + 80))
    setdef(find_pin(gpp, "PlayerIndex", "Input"), "0")
    gal = mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(gal, pos(X0 + 1650, Y + 80))
    connect(out_data(gpp), find_pin(gal, "self", "Input"), "pawn->loc")
    off = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(off, pos(X0 + 1650, Y + 200))
    setdef(find_pin(off, "X", "Input"), "35.0")
    setdef(find_pin(off, "Y", "Input"), "0.0")
    setdef(find_pin(off, "Z", "Input"), "70.0")
    addv = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    bel.set_node_pos(addv, pos(X0 + 1900, Y + 120))
    connect(out_data(gal), find_pin(addv, "A", "Input"), "locA")
    connect(out_data(off), find_pin(addv, "B", "Input"), "locB")
    mktf = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeTransform")
    bel.set_node_pos(mktf, pos(X0 + 2150, Y + 120))
    connect(out_data(addv), find_pin(mktf, "Location", "Input"), "tfLoc")
    setdef(find_pin(mktf, "Scale", "Input"), "0.004000,0.004000,0.004000")

    # SpawnActorFromClass StaticMeshActor
    spawn = mge.add_call_function_node("/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass")
    bel.set_node_pos(spawn, pos(X0 + 2450, Y))
    # ActorClass: StaticMeshActor
    setdef(find_pin(spawn, "ActorClass", "Input"), "/Script/Engine.StaticMeshActor")
    connect(out_data(mktf), find_pin(spawn, "SpawnTransform", "Input") or find_pin(spawn, "Transform", "Input"), "tf->spawn")
    connect(find_pin(br_ex, "else", "Output"), find_pin(spawn, "execute", "Input"), "missing->spawn")

    finish = mge.add_call_function_node("/Script/Engine.GameplayStatics:FinishSpawningActor")
    bel.set_node_pos(finish, pos(X0 + 2750, Y))
    connect(find_pin(spawn, "then", "Output"), find_pin(finish, "execute", "Input"), "sp->fin")
    connect(out_data(spawn), find_pin(finish, "Actor", "Input"), "spA")
    connect(out_data(mktf), find_pin(finish, "SpawnTransform", "Input") or find_pin(finish, "Transform", "Input"), "tf->fin")

    set_act = mge.add_set_member_variable_node("HeldDishActor")
    bel.set_node_pos(set_act, pos(X0 + 3050, Y))
    connect(find_pin(finish, "then", "Output"), find_pin(set_act, "execute", "Input"), "fin->set")
    connect(out_data(finish), find_pin(set_act, "HeldDishActor", "Input"), "fin->var")

    # Attach to player pawn
    attach = mge.add_call_function_node("/Script/Engine.Actor:K2_AttachToActor")
    bel.set_node_pos(attach, pos(X0 + 3350, Y))
    connect(find_pin(set_act, "then", "Output"), find_pin(attach, "execute", "Input"), "set->att")
    connect(out_data(finish), find_pin(attach, "self", "Input"), "dish->self")
    connect(out_data(gpp), find_pin(attach, "ParentActor", "Input") or find_pin(attach, "Parent", "Input"), "pawn->parent")
    # Location/Rotation rules: SnapToTarget=0 KeepWorld=1 KeepRelative=2 — use KeepRelative via default if possible
    for pname, val in (("LocationRule", "KeepRelative"), ("RotationRule", "KeepRelative"), ("ScaleRule", "KeepWorld")):
        p = find_pin(attach, pname, "Input")
        if p: setdef(p, val)

    # Relative location in front of chest
    set_rel = mge.add_call_function_node("/Script/Engine.Actor:K2_SetActorRelativeLocation")
    bel.set_node_pos(set_rel, pos(X0 + 3650, Y))
    # May not exist — fallback SetActorRelativeTransform; try
    # Actually use SceneComponent: if fails we'll just leave world attach offset from spawn
    # Prefer: K2_SetActorRelativeLocation on Actor
    relv = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(relv, pos(X0 + 3650, Y + 160))
    setdef(find_pin(relv, "X", "Input"), "40.0")
    setdef(find_pin(relv, "Y", "Input"), "0.0")
    setdef(find_pin(relv, "Z", "Input"), "55.0")
    if find_pin(set_rel, "execute", "Input"):
        connect(find_pin(attach, "then", "Output"), find_pin(set_rel, "execute", "Input"), "att->rel")
        connect(out_data(finish), find_pin(set_rel, "self", "Input"), "dish->relself")
        connect(out_data(relv), find_pin(set_rel, "NewLocation", "Input") or find_pin(set_rel, "RelativeLocation", "Input"), "relV")
        setdef(find_pin(set_rel, "bSweep", "Input") or find_pin(set_rel, "Sweep", "Input"), "false")
        after_spawn_exec = find_pin(set_rel, "then", "Output")
    else:
        after_spawn_exec = find_pin(attach, "then", "Output")
        log("no SetActorRelativeLocation — keep attach only")

    # Merge path: after spawn OR already exists -> set mesh by dish id
    # Use Sequence-like: from br_ex.then (exists) and after_spawn both go to mesh select
    # Simplest: duplicate mesh set on both paths

    def wire_mesh_select(ge, exec_pin, x, y, dish_actor_src_node, label_prefix):
        get_h2 = ge.add_get_member_variable_node("HeldDishId")
        bel.set_node_pos(get_h2, pos(x, y + 120))
        eq1 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
        bel.set_node_pos(eq1, pos(x + 220, y + 120))
        connect(out_data(get_h2), find_pin(eq1, "A", "Input"), label_prefix + "eqA")
        setdef(find_pin(eq1, "B", "Input"), "1")
        brd = ge.add_branch_node(); bel.set_node_pos(brd, pos(x + 450, y))
        connect(exec_pin, find_pin(brd, "execute", "Input"), label_prefix + "->dish?")
        connect(out_data(eq1), find_pin(brd, "Condition", "Input"), label_prefix + "salad?")

        # Get StaticMeshComponent from actor
        get_smc = ge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
        bel.set_node_pos(get_smc, pos(x + 450, y + 200))
        setdef(find_pin(get_smc, "ComponentClass", "Input"), "/Script/Engine.StaticMeshComponent")
        connect(out_data(dish_actor_src_node), find_pin(get_smc, "self", "Input"), label_prefix + "act->smc")

        set_s = ge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(set_s, pos(x + 750, y - 40))
        connect(find_pin(brd, "then", "Output"), find_pin(set_s, "execute", "Input"), label_prefix + "salad")
        connect(out_data(get_smc), find_pin(set_s, "self", "Input"), label_prefix + "smcS")
        setdef(find_pin(set_s, "NewMesh", "Input") or find_pin(set_s, "StaticMesh", "Input"), MESH_SALAD)

        set_w = ge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(set_w, pos(x + 750, y + 100))
        connect(find_pin(brd, "else", "Output"), find_pin(set_w, "execute", "Input"), label_prefix + "stew")
        connect(out_data(get_smc), find_pin(set_w, "self", "Input"), label_prefix + "smcW")
        setdef(find_pin(set_w, "NewMesh", "Input") or find_pin(set_w, "StaticMesh", "Input"), MESH_STEW)

        pr = make_print(ge, x + 1050, y, "Holding dish mesh", dur="0.2", key="RestHeldMesh")
        # both paths to print — connect salad then; stew then also (second connect may need another print)
        connect(find_pin(set_s, "then", "Output"), find_pin(pr, "execute", "Input"), label_prefix + "ps")
        pr2 = make_print(ge, x + 1050, y + 100, "Holding dish mesh", dur="0.2", key="RestHeldMesh")
        connect(find_pin(set_w, "then", "Output"), find_pin(pr2, "execute", "Input"), label_prefix + "pw")
        return pr

    # Path A: newly spawned — use finish return as actor
    wire_mesh_select(mge, after_spawn_exec, X0 + 4000, Y, finish, "new")

    # Path B: already exists — use HeldDishActor get
    get_act3 = mge.add_get_member_variable_node("HeldDishActor")
    bel.set_node_pos(get_act3, pos(X0 + 1400, Y - 200))
    # For GetComponentByClass self we need the actor from get_act3 — wire_mesh_select uses dish_actor_src_node out_data
    wire_mesh_select(mge, find_pin(br_ex, "then", "Output"), X0 + 1700, Y - 280, get_act3, "ex")

    REPORT["ok"].append("SyncHeldVisual")
    log("built SyncHeldVisual")

# Wire SyncHeldVisual into RestaurantTick: after RefreshOrderUI
rt = find_custom(mge, "RestaurantTick")
if rt:
    # Find RefreshOrderUI call in chain
    thenp = find_pin(rt, "then", "Output")
    firsts = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    call_sync = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual")
    bel.set_node_pos(call_sync, pos(100, -1000))
    # Prepend: RT -> SyncHeldVisual -> previous first
    if firsts:
        # break RT then, connect RT->sync->old
        try: thenp.break_pin_links()
        except Exception: pass
        connect(thenp, find_pin(call_sync, "execute", "Input"), "RT->Sync")
        connect(find_pin(call_sync, "then", "Output"), find_pin(firsts[0], "execute", "Input"), "Sync->old")
        REPORT["ok"].append("RT_prepend_Sync")
    else:
        connect(thenp, find_pin(call_sync, "execute", "Input"), "RT->Sync")
        REPORT["ok"].append("RT_only_Sync")

# ClearHeld: append SyncHeldVisual so prop clears immediately when HeldDishId set 0
# ClearHeld order: Set HeldDishId ... then Sync
ch = find_custom(mge, "ClearHeld")
if ch:
    term, last = walk_then_terminal(ch)
    call_c = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SyncHeldVisual")
    bel.set_node_pos(call_c, pos(1600, -200))
    if term:
        connect(term, find_pin(call_c, "execute", "Input"), "ClearHeld->Sync")
        REPORT["ok"].append("ClearHeld_Sync")

# Marker
mk = mge.add_custom_event_node(MARKER)
bel.set_node_pos(mk, pos(-1000, -1600))

bel.compile_blueprint(mbp)
mst = str(mbp.get_editor_property("status"))
REPORT["mgr_status"] = mst
log("mgr " + mst)
if "ERROR" not in mst:
    eas.save_asset(MGR)
else:
    for n in mge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                REPORT["errors"].append("mgr:" + title(n) + ":" + str(em)[:180])
                log("ERR " + title(n) + ": " + str(em)[:120])
        except Exception:
            pass

# Final verify chains
def walk_titles(ge, name, maxd=30):
    ev = find_custom(ge, name)
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

REPORT["spawn_chain"] = walk_titles(tge, "SpawnGuestVisual")
REPORT["sync_chain"] = walk_titles(mge, "SyncHeldVisual")
REPORT["rt_chain"] = walk_titles(mge, "RestaurantTick")
REPORT["clear_chain"] = walk_titles(mge, "ClearHeld")

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e)[:60])
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

open(r"E:\UE\FarmSim25D\Saved\rest_seat_held.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, indent=2, ensure_ascii=False))
print(json.dumps(REPORT, indent=2, ensure_ascii=False)[:9000])
