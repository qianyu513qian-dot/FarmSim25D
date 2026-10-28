# -*- coding: utf-8 -*-
"""Fix BP_RestaurantTable/Manager compile: replace GetActorLabel; remove broken ClearGuests calls."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
R = {"steps": [], "errors": [], "before": {}, "after": {}}

def log(m):
    unreal.log("[FIXC] " + str(m))
    R["steps"].append(str(m))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    return ok

def status_of(bp):
    try:
        return str(bp.get_editor_property("status"))
    except Exception as e:
        return str(e)

def replace_getactorlabel(ge, bp_name):
    """Replace each GetActorLabel with GetDisplayName (runtime-safe), rewiring consumers."""
    victims = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        # title may be GetActorLabel or Get Actor Label
        if "GetActorLabel" in t.replace(" ", "") or t == "GetActorLabel":
            victims.append(n)
        # also check function name via pins / class
        if n.get_class().get_name() == "K2Node_CallFunction":
            # inspect if any hint
            pass
    # broader search: pin owning - look at all call nodes
    for n in list(ge.list_all_nodes()):
        if n in victims:
            continue
        if n.get_class().get_name() != "K2Node_CallFunction":
            continue
        t = bel.get_node_title(n)
        if "ActorLabel" in t or "Get Actor Label" in t:
            victims.append(n)

    log("{} GetActorLabel count={}".format(bp_name, len(victims)))
    for old in victims:
        # collect outgoing string links from ReturnValue
        ret = find_pin(old, "ReturnValue", "Output") or find_pin(old, "Return", "Output")
        self_pin = find_pin(old, "self", "Input")
        self_src = None
        if self_pin:
            linked = self_pin.list_connected_pins()
            self_src = linked[0] if linked else None
        consumers = []
        if ret:
            for c in list(ret.list_connected_pins()):
                consumers.append(c)

        # create GetDisplayName
        neu = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
        if neu is None:
            neu = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetObjectName")
        bel.set_node_pos(neu, bel.get_node_pos(old) if hasattr(bel, "get_node_pos") else unreal.IntPoint(0, 0))
        try:
            # copy position
            pass
        except Exception:
            pass

        # wire object/self
        obj_pin = find_pin(neu, "Object", "Input") or find_pin(neu, "self", "Input")
        if self_src and obj_pin:
            connect(self_src, obj_pin, bp_name + " self->display")
        # if no self_src, leave unbound (self context) for table; for manager foreach need source

        new_ret = find_pin(neu, "ReturnValue", "Output")
        # break old ret links then reconnect consumers to new_ret
        if ret:
            ret.break_pin_links()
        for c in consumers:
            connect(new_ret, c, bp_name + " display->consumer")

        # remove old
        ge.remove_nodes([old])
        log("{} replaced GetActorLabel -> {}".format(bp_name, bel.get_node_title(neu)))

def remove_broken_clearguests_calls(ge):
    """Remove ClearGuests CallFunction nodes that have no exec pins (corrupt)."""
    kill = []
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "ClearGuests":
            continue
        if n.get_class().get_name() != "K2Node_CallFunction":
            continue
        pins = list(bel.list_all_pins(n))
        has_exec = any(str(p.get_pin_name()).lower() in ("execute", "then") for p in pins)
        if not pins or not has_exec:
            kill.append(n)
            log("kill broken ClearGuests call pins=" + str(len(pins)))
    if kill:
        ge.remove_nodes(kill)
    return len(kill)

def fix_table():
    path = "/Game/Farm/Restaurant/BP_RestaurantTable"
    bp = unreal.EditorAssetLibrary.load_asset(path)
    R["before"]["table"] = status_of(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    # list all call titles for debug
    calls = [bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() == "K2Node_CallFunction"]
    log("table calls: " + str(calls))
    replace_getactorlabel(ge, "table")
    # Also simplify TrySeat print if still broken: ensure no editor fns remain
    leftover = [bel.get_node_title(n) for n in ge.list_all_nodes() if "ActorLabel" in bel.get_node_title(n) or "Get Actor Label" in bel.get_node_title(n)]
    log("table leftover label nodes: " + str(leftover))
    bel.compile_blueprint(bp)
    R["after"]["table"] = status_of(bp)
    if "ERROR" in R["after"]["table"]:
        # nuclear simplify TrySeat print path: remove Append/GetDisplayName chain, use fixed Print
        simplify_tryseat_print(ge, bp)
        bel.compile_blueprint(bp)
        R["after"]["table"] = status_of(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    log("table status " + R["after"]["table"])

def simplify_tryseat_print(ge, bp):
    """If still erroring, replace fancy append print with fixed string PrintString."""
    # find TrySeat custom event
    try_ev = None
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and bel.get_node_title(n) == "TrySeat":
            try_ev = n
    if not try_ev:
        return
    # remove GetDisplayName / Append / Concat nodes that feed Print near TrySeat
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t in ("GetDisplayName", "GetObjectName", "Append", "Concat_StrStr") or "Concat" in t or t.startswith("Append"):
            kill.append(n)
        if "ActorLabel" in t:
            kill.append(n)
    # Also fix PrintString InString that may be disconnected - set default
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "PrintString":
            # check if in TrySeat chain by seeing exec from Set bHasOrder
            insp = find_pin(n, "InString", "Input")
            if insp:
                # if linked from removed nodes, break and set default
                linked = insp.list_connected_pins()
                # after kill we'll set
                pass
    if kill:
        # before remove, break InString links on prints and set fixed text
        for n in ge.list_all_nodes():
            if bel.get_node_title(n) != "PrintString":
                continue
            insp = find_pin(n, "InString", "Input")
            if not insp:
                continue
            # if connected to append/display
            srcs = [bel.get_node_title(c.get_owning_node()) for c in insp.list_connected_pins()]
            if any(("Append" in s or "Concat" in s or "Display" in s or "ObjectName" in s or "ActorLabel" in s) for s in srcs):
                insp.break_pin_links()
                try:
                    insp.set_pin_value("Restaurant GUEST seated (order set)")
                except Exception:
                    pass
                log("print simplified")
        ge.remove_nodes(kill)
        log("simplified tryseat killed " + str(len(kill)))

def fix_manager():
    path = "/Game/Farm/Restaurant/BP_RestaurantManager"
    bp = unreal.EditorAssetLibrary.load_asset(path)
    R["before"]["manager"] = status_of(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    calls = [bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() == "K2Node_CallFunction"]
    log("mgr call sample: " + str([c for c in calls if "Label" in c or "Clear" in c or "Display" in c or "GetActor" in c]))
    # all titles containing Label
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Label" in t or "label" in t:
            log("mgr label-ish node: " + t + " " + n.get_class().get_name())

    remove_broken_clearguests_calls(ge)
    replace_getactorlabel(ge, "manager")

    # If Contains/Append still feed from removed label, ensure GetDisplayName wired from ForEach Array Element
    # Find Contains SearchIn source
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "Contains":
            sin = find_pin(n, "SearchIn", "Input")
            if sin and not sin.list_connected_pins():
                # need a display name from foreach element
                # find ForEach whose LoopBody leads to this Contains branch
                # simpler: add GetDisplayName, wire Array Element from the RestInteract ForEach
                fe = None
                for m in ge.list_all_nodes():
                    if bel.get_node_title(m) == "For Each Loop":
                        # RestInteract one: Array from GetAllActorsWithTag
                        ap = find_pin(m, "Array", "Input")
                        if ap and any("WithTag" in bel.get_node_title(c.get_owning_node()) for c in ap.list_connected_pins()):
                            fe = m
                            break
                if fe:
                    gdn = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
                    bel.set_node_pos(gdn, unreal.IntPoint(2100, 120))
                    connect(find_pin(fe, "Array Element", "Output"), find_pin(gdn, "Object", "Input"), "el->gdn")
                    connect(find_pin(gdn, "ReturnValue", "Output"), sin, "gdn->contains")
                    # also Append B for print
                    for app in ge.list_all_nodes():
                        if bel.get_node_title(app) in ("Append",) or "Concat" in bel.get_node_title(app):
                            bp_ = find_pin(app, "B", "Input")
                            if bp_ and not bp_.list_connected_pins():
                                connect(find_pin(gdn, "ReturnValue", "Output"), bp_, "gdn->appendB")
                    log("rewired Contains SearchIn via GetDisplayName")

    # Remove ANY remaining GetActorLabel
    kill = []
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n).replace(" ", "")
        if "GetActorLabel" in t or "ActorLabel" in bel.get_node_title(n):
            kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("mgr killed leftover label " + str(len(kill)))

    bel.compile_blueprint(bp)
    R["after"]["manager"] = status_of(bp)

    if "ERROR" in R["after"]["manager"]:
        # more aggressive: for HandlePlayerE OpenSign detection, if Contains broken, use Print only path
        log("manager still error, dumping node errors...")
        for n in ge.list_all_nodes():
            try:
                et = n.get_editor_property("error_type")
                em = n.get_editor_property("error_msg")
                if et and str(et) not in ("0", "ET_None", "None", "<ERedirectionType."):
                    log("ERR node {} type={} msg={}".format(bel.get_node_title(n), et, str(em)[:200]))
                if em and str(em).strip():
                    log("MSG {} :: {}".format(bel.get_node_title(n), str(em)[:250]))
            except Exception:
                pass
        # try read log again after compile
    unreal.EditorAssetLibrary.save_asset(path)
    log("manager status " + R["after"]["manager"])

def read_fresh_log():
    msgs = []
    try:
        with open(r"E:\UE\FarmSim25D\Saved\Logs\FarmSim25D.log", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-2000:]
        for line in lines:
            if "BP_Restaurant" in line and ("Error" in line or "Warning" in line or "failed to compile" in line):
                msgs.append(line.strip()[:350])
    except Exception as e:
        msgs.append(str(e))
    return msgs[-30:]

fix_table()
fix_manager()
R["log_after"] = read_fresh_log()

# final status re-load
for key, path in (("table", "/Game/Farm/Restaurant/BP_RestaurantTable"), ("manager", "/Game/Farm/Restaurant/BP_RestaurantManager")):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    bel.compile_blueprint(bp)
    R["after"][key + "_final"] = status_of(bp)
    unreal.EditorAssetLibrary.save_asset(path)

# character IA untouched check
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = {}
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        p = find_pin(n, "Started", "Output")
        ia["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
    if bel.get_node_title(n) == "TillSoil":
        p = find_pin(n, "execute", "Input")
        ia["TillSoil"] = [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()]
R["ia"] = ia

open(r"E:\UE\FarmSim25D\Saved\restaurant_fix_compile.json", "w", encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str)[:8000])