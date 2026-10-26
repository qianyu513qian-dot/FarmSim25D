# -*- coding: utf-8 -*-
"""Finalize viz fix: sync grid CDO 40, raise soil, hide grass under cell, verify graphs, save."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"


def log(m):
    unreal.log("[FIX_VIZ4] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}]: {}".format(label, ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


# Sync CDO to match level instance 40x40
gen = unreal.load_object(None, MGR + ".BP_GridManager_C")
cdo = unreal.get_default_object(gen) if gen else None
if cdo:
    try:
        cdo.set_editor_property("GridWidth", 40)
        cdo.set_editor_property("GridHeight", 40)
        cdo.set_editor_property("CellSize", 100.0)
        log("CDO set W=40 H=40 CellSize=100")
    except Exception as e:
        log("CDO set fail " + str(e))

# Bump Z offset to 40, scale to 0.012 (slightly larger than grass to cover)
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Make Vector" in t or t == "MakeVector":
        xv = pin_val(find_pin(n, "X", "Input"))
        zv = pin_val(find_pin(n, "Z", "Input"))
        if "0.01" in xv:
            set_val(find_pin(n, "X", "Input"), "0.012", "sc.X")
            set_val(find_pin(n, "Y", "Input"), "0.012", "sc.Y")
            set_val(find_pin(n, "Z", "Input"), "0.012", "sc.Z")
        elif "25" in zv or "3" in zv or "40" in zv or "5" in zv:
            set_val(find_pin(n, "Z", "Input"), "40.0", "off.Z")

# Also update post-spawn SetActorScale3D MakeVector if present
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Make Vector" in t or t == "MakeVector":
        # if connected to SetActorScale3D
        rp = find_pin(n, "ReturnValue", "Output")
        if not rp:
            continue
        for cp in rp.list_connected_pins():
            ot = bel.get_node_title(cp.get_owning_node())
            if "Scale" in ot or "SetActorScale" in ot.replace(" ", ""):
                set_val(find_pin(n, "X", "Input"), "0.012", "postsc.X")
                set_val(find_pin(n, "Y", "Input"), "0.012", "postsc.Y")
                set_val(find_pin(n, "Z", "Input"), "0.012", "postsc.Z")

# Add HideGrassAt helper as inline nodes in VisualizeCell spawn path:
# After GridToWorld, before spawn: we can't easily find by label in pure BP without ForLoop.
# Instead add a function HideGrassAt on GridManager.

def ensure_hide_grass_func(bp):
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    if "HideGrassAt" in graphs:
        log("HideGrassAt exists")
        return True
    bel.add_function_graph(bp, "HideGrassAt")
    graph = bel.find_graph(bp, "HideGrassAt")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    entry = None
    for n in list(ge.list_all_nodes()):
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            ge.remove_nodes([n])
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    # inputs GridX, GridY
    if find_pin(entry, "GridX", "Output") is None:
        ip = unreal.EdGraphPinType()
        ip.import_text('(PinCategory="int")')
        ge.add_graph_input_parameter("GridX", ip)
        ge.add_graph_input_parameter("GridY", ip)
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n

    # GetAllActorsOfClass StaticMeshActor
    get_all = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(get_all, pos(400, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(get_all, "execute", "Input"), "e->getall")
    set_val(find_pin(get_all, "ActorClass", "Input") or find_pin(get_all, "Class", "Input"),
            "/Script/Engine.StaticMeshActor", "class")

    # ForEachLoop
    loop = ge.create_node_from_name("Utilities|FlowControl|ForEachLoop", unreal.Vector2D(700, 0), [])
    bel.set_node_pos(loop, pos(700, 0))
    connect(find_pin(get_all, "then", "Output"), find_pin(loop, "execute", "Input"), "get->loop")
    connect(find_pin(get_all, "OutActors", "Output") or find_pin(get_all, "Out Actors", "Output"),
            find_pin(loop, "Array", "Input"), "actors")

    # GetActorLabel / Get Display Name - compare contains "VMF_Grass_{x}_{y}"
    # Build expected label string: "VMF_Grass_" + X + "_" + Y
    # Format: use BuildString_IntInt or Concat

    # Get actor label
    # Actor:GetActorNameOrLabel or KismetSystemLibrary.GetDisplayName
    get_name = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
    bel.set_node_pos(get_name, pos(1000, 80))
    connect(find_pin(loop, "Array Element", "Output") or find_pin(loop, "Element", "Output"),
            find_pin(get_name, "Object", "Input"), "el->name")

    # Build "VMF_Grass_" + GridX + "_" + GridY  using Format or Concat
    # Conv int to string
    conv_x = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(conv_x, pos(400, 200))
    connect(find_pin(entry, "GridX", "Output"), find_pin(conv_x, "InInt", "Input"), "gx->str")

    conv_y = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(conv_y, pos(400, 280))
    connect(find_pin(entry, "GridY", "Output"), find_pin(conv_y, "InInt", "Input"), "gy->str")

    # Concat: "VMF_Grass_" + X
    cat1 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat1, pos(700, 200))
    set_val(find_pin(cat1, "A", "Input"), "VMF_Grass_", "pre")
    connect(find_pin(conv_x, "ReturnValue", "Output"), find_pin(cat1, "B", "Input"), "x")

    # Concat: result + "_"
    cat2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat2, pos(950, 200))
    connect(find_pin(cat1, "ReturnValue", "Output"), find_pin(cat2, "A", "Input"), "a")
    set_val(find_pin(cat2, "B", "Input"), "_", "us")

    # Concat: result + Y
    cat3 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(cat3, pos(1200, 200))
    connect(find_pin(cat2, "ReturnValue", "Output"), find_pin(cat3, "A", "Input"), "a2")
    connect(find_pin(conv_y, "ReturnValue", "Output"), find_pin(cat3, "B", "Input"), "y")

    # Contains display name the target? Or Equal
    # GetActorLabel might be better - try Actor.GetActorLabel if available
    # Use Contains(DisplayName, "VMF_Grass_X_Y") 
    contains = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
    bel.set_node_pos(contains, pos(1450, 80))
    connect(find_pin(get_name, "ReturnValue", "Output"), find_pin(contains, "SearchIn", "Input") or find_pin(contains, "Source", "Input"), "src")
    connect(find_pin(cat3, "ReturnValue", "Output"), find_pin(contains, "Substring", "Input") or find_pin(contains, "Find", "Input"), "sub")

    br = ge.add_branch_node()
    bel.set_node_pos(br, pos(1700, 0))
    connect(find_pin(loop, "LoopBody", "Output") or find_pin(loop, "Then", "Output"),
            find_pin(br, "execute", "Input"), "body->br")
    connect(find_pin(contains, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond")

    # SetActorHiddenInGame true
    hid = ge.add_call_function_node("/Script/Engine.Actor:SetActorHiddenInGame")
    bel.set_node_pos(hid, pos(2000, -40))
    connect(find_pin(br, "then", "Output"), find_pin(hid, "execute", "Input"), "br->hid")
    connect(find_pin(loop, "Array Element", "Output") or find_pin(loop, "Element", "Output"),
            find_pin(hid, "self", "Input"), "el->hid")
    set_val(find_pin(hid, "bNewHidden", "Input") or find_pin(hid, "NewHidden", "Input"), "true", "hide")

    # Completed -> Return
    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(1000, 400))
    connect(find_pin(loop, "Completed", "Output"), find_pin(ret, "execute", "Input"), "done")

    try:
        bel.compile_blueprint(bp)
        log("HideGrassAt compile ok")
    except Exception as e:
        log("HideGrassAt compile " + str(e))
    return True


def splice_hide_grass(bp):
    """Call HideGrassAt at start of VisualizeCell when State != 0."""
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
    # Already have HideGrassAt call?
    for n in ge.list_all_nodes():
        if "HideGrassAt" in bel.get_node_title(n):
            log("HideGrassAt already in VisualizeCell")
            return True

    entry = None
    first_br = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    # Find first Branch (IsValid branch) - its execute comes from entry
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "Branch":
            ep = find_pin(n, "execute", "Input")
            if ep:
                for cp in ep.list_connected_pins():
                    if cp.get_owning_node() == entry or bel.get_node_title(cp.get_owning_node()) in ("VisualizeCell",):
                        first_br = n
                        break
            if first_br:
                break
    # Broader: first branch whose execute connects from entry.then
    if not first_br and entry:
        thenp = find_pin(entry, "then", "Output")
        if thenp:
            for cp in thenp.list_connected_pins():
                if bel.get_node_title(cp.get_owning_node()) == "Branch":
                    first_br = cp.get_owning_node()

    if not entry or not first_br:
        log("cannot find entry/first_br for hide splice")
        return False

    then_entry = find_pin(entry, "then", "Output")
    br_exec = find_pin(first_br, "execute", "Input")
    try:
        then_entry.break_pin_links(False)
    except Exception:
        try:
            then_entry.break_pin_links()
        except Exception as e:
            log("break entry.then " + str(e))

    hide = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:HideGrassAt")
    bel.set_node_pos(hide, pos(900, -120))
    connect(then_entry, find_pin(hide, "execute", "Input"), "entry->hide")
    connect(find_pin(hide, "then", "Output"), br_exec, "hide->br")
    connect(find_pin(entry, "GridX", "Output"), find_pin(hide, "Grid X", "Input") or find_pin(hide, "GridX", "Input"), "gx")
    connect(find_pin(entry, "GridY", "Output"), find_pin(hide, "Grid Y", "Input") or find_pin(hide, "GridY", "Input"), "gy")
    log("spliced HideGrassAt at VisualizeCell start")
    return True


log("=== START ===")
ensure_hide_grass_func(bp)
bp = unreal.load_asset(MGR)
splice_hide_grass(bp)

try:
    bel.compile_blueprint(bp)
    log("final GM compile ok")
except Exception as e:
    log("final compile " + str(e))

# Verify errors
for gname in ("VisualizeCell", "HideGrassAt", "TillCell"):
    g = bel.find_graph(bp, gname)
    if not g:
        log("missing " + gname)
        continue
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    try:
        errs = ge.list_nodes_with_errors()
        log("{} errors={}".format(gname, len(errs)))
        for n in errs[:8]:
            log("  ERR " + bel.get_node_title(n))
    except Exception as e:
        log(gname + " " + str(e))

pv = unreal.load_asset(PV)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
try:
    errs = ge.list_nodes_with_errors()
    log("ApplyState errors=" + str(len(errs)))
    for n in errs[:8]:
        log("  ERR " + bel.get_node_title(n))
except Exception as e:
    log(str(e))

# Verify mesh vars on CDO
pv_gen = unreal.load_object(None, PV + ".BP_PlotVisual_C")
pv_cdo = unreal.get_default_object(pv_gen) if pv_gen else None
if pv_cdo:
    for vn in ("Mesh_SoilDry", "Mesh_SoilWet", "Mesh_Seed", "Mesh_Grow", "Mesh_Mature"):
        try:
            v = pv_cdo.get_editor_property(vn)
            log("PV.{}={}".format(vn, v.get_name() if v else None))
        except Exception as e:
            log("PV.{} err {}".format(vn, e))

unreal.EditorAssetLibrary.save_asset(MGR)
unreal.EditorAssetLibrary.save_asset(PV)
try:
    unreal.EditorAssetLibrary.save_directory("/Game/Farm/Grid")
except Exception:
    pass
# Save level so DEBUG actor + any changes persist? User may not want DEBUG - delete it
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for a in actors:
        try:
            lab = a.get_actor_label()
        except Exception:
            continue
        if lab == "DEBUG_PlotVisual_Test":
            # Keep it as visual proof near grid 18,18 — or destroy to avoid confusion
            # Leave it; user can see brown soil tile as reference
            log("DEBUG actor still at " + str(a.get_actor_location()))
except Exception as e:
    log("debug cleanup " + str(e))

try:
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
except Exception as e:
    log("level save " + str(e))

log("=== END ===")
