# -*- coding: utf-8 -*-
"""Verify inventory wiring + fix CreateWidget class / FarmHUDWidget set."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[INV_V] " + str(m))
    print("[INV_V] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok))
    return ok

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

# Find BeginPlay and walk
begin = None
for n in nodes:
    if n.get_class().get_name() == "K2Node_Event" and not any(str(p.get_pin_name())=="DeltaSeconds" for p in bel.list_all_pins(n)):
        begin = n
        break

def label(n):
    cn = n.get_class().get_name()
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        try:
            pv = p.get_pin_value() or ""
        except Exception:
            pv = ""
        if pn == "InString" and pv:
            return "Print({!r})".format(pv)
        if pn == "Class" and pv:
            return "Create({!r})".format(pv)
        if "FarmHUDWidget" in pn:
            return "Set/Get FarmHUDWidget"
        if pn == "SeedCount" or (cn == "K2Node_VariableSet" and "Seed" in str(n.get_name())):
            pass
    if cn == "K2Node_VariableSet":
        for p in bel.list_all_pins(n):
            if "input" in str(p.get_pin_direction()).lower() and str(p.get_pin_name()) not in ("execute", "self"):
                return "SET " + str(p.get_pin_name())
    if cn == "K2Node_VariableGet":
        for p in bel.list_all_pins(n):
            if "output" in str(p.get_pin_direction()).lower():
                return "GET " + str(p.get_pin_name())
    if cn == "K2Node_IfThenElse":
        return "Branch"
    # function name via pins
    pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
    if "Success" in pins and "GridX" in pins:
        return "CellOp"
    if "WorldLocation" in pins and "GridX" in pins:
        return "WorldToGrid"
    if "UpdateFarmHUD" in str(n.get_name()) or (cn=="K2Node_CallFunction" and not pins):
        pass
    # try title
    try:
        t = bel.get_node_title(n)
        return str(t)
    except Exception:
        return cn

log("=== BeginPlay ===")
thenp = find_pin(begin, "then", "Output")
queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
seen = set()
while queue:
    cur, d = queue.pop(0)
    if id(cur) in seen or d > 20:
        continue
    seen.add(id(cur))
    log("  "*d + label(cur))
    # dump class pin if create
    for p in bel.list_all_pins(cur):
        if str(p.get_pin_name()) == "Class":
            try:
                log("  "*d + "  Class val={!r} links={}".format(p.get_pin_value(), len(conn(p))))
            except Exception as e:
                log(str(e))
    for cp in bel.list_all_pins(cur):
        if str(cp.get_pin_name()) == "then":
            for c in conn(cp):
                queue.append((c.get_owning_node(), d+1))

# Fix CreateWidget class + FarmHUDWidget
create_node = None
set_hud = None
for n in nodes:
    # Create is K2Node_CreateWidget or CallFunction Create
    cn = n.get_class().get_name()
    if cn == "K2Node_CreateWidget":
        create_node = n
        log("found K2Node_CreateWidget")
    if "Create" in label(n) or (find_pin(n, "Class", "Input") and find_pin(n, "ReturnValue", "Output") and find_pin(n, "execute", "Input")):
        if find_pin(n, "Class", "Input"):
            create_node = n
            log("found create-like " + cn)
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "FarmHUDWidget" and "input" in str(p.get_pin_direction()).lower() and find_pin(n, "execute"):
            set_hud = n
            log("found Set FarmHUDWidget")

if create_node:
    class_pin = find_pin(create_node, "Class", "Input")
    log("Create pins=" + str([str(p.get_pin_name())+":"+str(p.get_pin_direction()) for p in bel.list_all_pins(create_node)]))
    # Try set class via select class / pin value
    for val in (
        "/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD_C",
        "WBP_FarmHUD_C'/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD_C'",
        "BlueprintGeneratedClass'/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD_C'",
    ):
        try:
            class_pin.set_pin_value(val)
            log("set class try {!r} -> {!r}".format(val, class_pin.get_pin_value()))
            if class_pin.get_pin_value():
                break
        except Exception as e:
            log("set class {}: {}".format(val, e))
    # Also try editor property Class on K2Node_CreateWidget
    for prop in ("class_pin", "ClassToSpawn", "widget_class", "Class"):
        try:
            wbp = unreal.load_asset(WBP)
            gc = wbp.generated_class()
            create_node.set_editor_property(prop, gc)
            log("set prop {} ok".format(prop))
        except Exception as e:
            log("prop {}: {}".format(prop, e))

    # Fix FarmHUDWidget set: may need cast
    if set_hud:
        rv = find_pin(create_node, "ReturnValue", "Output")
        dest = find_pin(set_hud, "FarmHUDWidget", "Input")
        log("set_hud dest links before=" + str(len(conn(dest))))
        # Cast to WBP
        try:
            wbp = unreal.load_asset(WBP)
            gc = wbp.generated_class()
            cast_n = ge.add_cast_node(gc) if hasattr(ge, "add_cast_node") else None
            if not cast_n:
                # Dynamic cast via create_node
                cast_n = ge.create_node_from_name("Utilities|Casting|Cast To WBP_FarmHUD_C", unreal.Vector2D(0,0), [])
            log("cast_n=" + str(cast_n))
        except Exception as e:
            log("cast " + str(e))
            cast_n = None
        if cast_n is None:
            # Try connect again after class set
            connect(rv, dest, "retry set hud")
        else:
            bel.set_node_pos(cast_n, unreal.IntPoint(2900, -500))
            # rewire: create.then -> cast -> set
            # Actually cast is pure usually - connect object
            connect(rv, find_pin(cast_n, "Object", "Input") or find_pin(cast_n, "execute", "Input"), "rv->cast")
            as_pin = find_pin(cast_n, "As", "Output") or find_pin(cast_n, "ReturnValue", "Output")
            connect(as_pin, dest, "cast->set")

# Verify plant/harvest
log("=== Plant ===")
for n in nodes:
    p = find_pin(n, "InputAction")
    if p:
        try:
            if "IA_Plant" in (p.get_pin_value() or ""):
                started = find_pin(n, "Started", "Output")
                queue = [(c.get_owning_node(), 0, "Started") for c in conn(started)]
                seen=set()
                while queue:
                    cur,d,via=queue.pop(0)
                    if id(cur) in seen or d>12: continue
                    seen.add(id(cur))
                    log("  "*d + "[{}] {}".format(via, label(cur)))
                    for cp in bel.list_all_pins(cur):
                        if str(cp.get_pin_name()) in ("then","else"):
                            for c in conn(cp):
                                queue.append((c.get_owning_node(), d+1, str(cp.get_pin_name())))
        except Exception:
            pass

log("=== Harvest ===")
for n in nodes:
    p = find_pin(n, "InputAction")
    if p:
        try:
            if "IA_Harvest" in (p.get_pin_value() or ""):
                started = find_pin(n, "Started", "Output")
                queue = [(c.get_owning_node(), 0, "Started") for c in conn(started)]
                seen=set()
                while queue:
                    cur,d,via=queue.pop(0)
                    if id(cur) in seen or d>12: continue
                    seen.add(id(cur))
                    log("  "*d + "[{}] {}".format(via, label(cur)))
                    for cp in bel.list_all_pins(cur):
                        if str(cp.get_pin_name()) in ("then","else"):
                            for c in conn(cp):
                                queue.append((c.get_owning_node(), d+1, str(cp.get_pin_name())))
        except Exception:
            pass

# Compile status / errors on EventGraph
try:
    errs = ge.list_nodes_with_errors()
    log("EG errors=" + str(len(errs)))
    for n in errs[:15]:
        log("  ERR " + label(n) + " / " + n.get_name())
except Exception as e:
    log("list err " + str(e))

try:
    bel.compile_blueprint(bp)
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(CHAR)
log("DONE verify")
