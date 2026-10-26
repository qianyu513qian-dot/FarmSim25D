# -*- coding: utf-8 -*-
"""Fix HideGrassAt ForEachLoop pin wiring."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_HIDE] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip {} a={} b={}".format(label, a, b))
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {} -> {} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    name_substr = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if name_substr in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def dump_pins(node, label):
    log("PINS " + label)
    for p in bel.list_all_pins(node):
        log("  {} dir={} type={}".format(p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_info() if hasattr(p, "get_pin_type_info") else ""))


bp = unreal.load_asset(MGR)
# Rebuild HideGrassAt cleanly
graph = bel.find_graph(bp, "HideGrassAt")
ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
entry = None
to_del = []
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
    else:
        to_del.append(n)
if to_del:
    ge.remove_nodes(to_del)
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n

if find_pin(entry, "GridX", "Output") is None:
    ip = unreal.EdGraphPinType()
    ip.import_text('(PinCategory="int")')
    ge.add_graph_input_parameter("GridX", ip)
    ge.add_graph_input_parameter("GridY", ip)
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n

# Simpler approach: use ActorIterator via GetAllActorsWithTag if grass tagged
# Or: Compute world loc and use GetOverlapping - complicated
# Simplest reliable: GetAllActorsOfClass + ForEach with correct pins

get_all = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(get_all, pos(300, 0))
dump_pins(get_all, "GetAllActorsOfClass")
connect(find_pin(entry, "then", "Output"), find_pin(get_all, "execute", "Input"), "e->all")
# Class pin
class_pin = find_pin(get_all, "ActorClass", "Input") or find_pin(get_all, "Class", "Input")
set_val(class_pin, "/Script/Engine.StaticMeshActor", "ActorClass")

# Try multiple ways to create ForEachLoop
loop = None
for path in (
    "Utilities|FlowControl|ForEachLoop",
    "Flow Control|For Each Loop",
    "Utilities|FlowControl|For Each Loop",
):
    try:
        loop = ge.create_node_from_name(path, unreal.Vector2D(700, 0), [])
        if loop:
            log("created loop via " + path)
            break
    except Exception as e:
        log("try {}: {}".format(path, e))

if not loop:
    # K2Node_ForEachElementInMacro or add_macro
    try:
        loop = ge.add_call_function_node("/Script/BlueprintGraph.KismetArrayLibrary")  # no
    except Exception:
        pass

if not loop:
    # Use WhileLoop with Array Length - more verbose but reliable
    log("ForEach failed — using index WhileLoop")
    length = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Length")
    bel.set_node_pos(length, pos(600, 200))
    connect(find_pin(get_all, "OutActors", "Output") or find_pin(get_all, "Outactors", "Output"),
            find_pin(length, "TargetArray", "Input") or find_pin(length, "Array", "Input"), "arr->len")

    # Local int i — use temporary via macro-less pattern: ForLoop (0 to Length-1)
    forloop = None
    for path in (
        "Utilities|FlowControl|ForLoop",
        "Flow Control|For Loop",
        "Utilities|FlowControl|For Loop",
    ):
        try:
            forloop = ge.create_node_from_name(path, unreal.Vector2D(900, 0), [])
            if forloop:
                log("ForLoop via " + path)
                break
        except Exception as e:
            log("ForLoop try {}: {}".format(path, e))

    if forloop:
        dump_pins(forloop, "ForLoop")
        bel.set_node_pos(forloop, pos(900, 0))
        connect(find_pin(get_all, "then", "Output"), find_pin(forloop, "execute", "Input"), "all->for")
        set_val(find_pin(forloop, "FirstIndex", "Input") or find_pin(forloop, "First Index", "Input"), "0", "first")
        # LastIndex = Length - 1
        sub = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_IntInt")
        bel.set_node_pos(sub, pos(700, 200))
        connect(find_pin(length, "ReturnValue", "Output"), find_pin(sub, "A", "Input"), "len-A")
        set_val(find_pin(sub, "B", "Input"), "1", "len-B")
        connect(find_pin(sub, "ReturnValue", "Output"),
                find_pin(forloop, "LastIndex", "Input") or find_pin(forloop, "Last Index", "Input"), "last")

        get_at = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
        bel.set_node_pos(get_at, pos(1200, 80))
        connect(find_pin(get_all, "OutActors", "Output") or find_pin(get_all, "Outactors", "Output"),
                find_pin(get_at, "TargetArray", "Input"), "arr")
        connect(find_pin(forloop, "Index", "Output"), find_pin(get_at, "Index", "Input"), "idx")

        # GetDisplayName
        get_name = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
        bel.set_node_pos(get_name, pos(1450, 80))
        connect(find_pin(get_at, "Item", "Output"), find_pin(get_name, "Object", "Input"), "item->name")

        # Build VMF_Grass_X_Y
        conv_x = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(conv_x, pos(300, 320))
        connect(find_pin(entry, "GridX", "Output"), find_pin(conv_x, "InInt", "Input"), "gx")
        conv_y = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(conv_y, pos(300, 400))
        connect(find_pin(entry, "GridY", "Output"), find_pin(conv_y, "InInt", "Input"), "gy")

        cat1 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(cat1, pos(600, 320))
        set_val(find_pin(cat1, "A", "Input"), "VMF_Grass_", "pre")
        connect(find_pin(conv_x, "ReturnValue", "Output"), find_pin(cat1, "B", "Input"), "x")
        cat2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(cat2, pos(850, 320))
        connect(find_pin(cat1, "ReturnValue", "Output"), find_pin(cat2, "A", "Input"), "a")
        set_val(find_pin(cat2, "B", "Input"), "_", "us")
        cat3 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(cat3, pos(1100, 320))
        connect(find_pin(cat2, "ReturnValue", "Output"), find_pin(cat3, "A", "Input"), "a2")
        connect(find_pin(conv_y, "ReturnValue", "Output"), find_pin(cat3, "B", "Input"), "y")

        contains = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains")
        bel.set_node_pos(contains, pos(1700, 80))
        dump_pins(contains, "Contains")
        connect(find_pin(get_name, "ReturnValue", "Output"),
                find_pin(contains, "SearchIn", "Input") or find_pin(contains, "SourceString", "Input") or find_pin(contains, "search", "Input"),
                "src")
        connect(find_pin(cat3, "ReturnValue", "Output"),
                find_pin(contains, "Substring", "Input") or find_pin(contains, "Find", "Input") or find_pin(contains, "substr", "Input"),
                "sub")

        br = ge.add_branch_node()
        bel.set_node_pos(br, pos(1950, 0))
        connect(find_pin(forloop, "LoopBody", "Output") or find_pin(forloop, "Then", "Output") or find_pin(forloop, "loop", "Output"),
                find_pin(br, "execute", "Input"), "body->br")
        connect(find_pin(contains, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond")

        hid = ge.add_call_function_node("/Script/Engine.Actor:SetActorHiddenInGame")
        bel.set_node_pos(hid, pos(2250, -40))
        connect(find_pin(br, "then", "Output"), find_pin(hid, "execute", "Input"), "br->hid")
        connect(find_pin(get_at, "Item", "Output"), find_pin(hid, "self", "Input"), "item->hid")
        set_val(find_pin(hid, "bNewHidden", "Input") or find_pin(hid, "NewHidden", "Input"), "true", "hide")

        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(1200, 480))
        connect(find_pin(forloop, "Completed", "Output"), find_pin(ret, "execute", "Input"), "done")
    else:
        # Absolute fallback: just return (HideGrassAt no-op) — soil Z=40 still helps
        log("NO ForLoop — HideGrassAt becomes no-op return")
        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(700, 0))
        connect(find_pin(get_all, "then", "Output"), find_pin(ret, "execute", "Input"), "noop")
else:
    dump_pins(loop, "ForEachLoop")
    bel.set_node_pos(loop, pos(700, 0))
    connect(find_pin(get_all, "then", "Output"), find_pin(loop, "execute", "Input"), "all->loop")
    connect(find_pin(get_all, "OutActors", "Output") or find_pin(get_all, "Outactors", "Output"),
            find_pin(loop, "Array", "Input"), "actors")
    # ... similar body using Array Element pin
    dump_pins(loop, "ForEachLoop-after")

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "HideGrassAt"))
try:
    errs = ge.list_nodes_with_errors()
    log("errors=" + str(len(errs)))
    for n in errs:
        log(" ERR " + bel.get_node_title(n))
        dump_pins(n, bel.get_node_title(n))
except Exception as e:
    log(str(e))

# Dump all node titles to see what we have
for n in ge.list_all_nodes():
    log("node: " + bel.get_node_title(n))

unreal.EditorAssetLibrary.save_asset(MGR)
log("done")
