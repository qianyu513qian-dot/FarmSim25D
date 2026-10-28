# -*- coding: utf-8 -*-
"""Insert RefreshTableBubble at start of Table Tick; clean Manager orphan errors; literal pins for timer."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"

R = {"steps": []}

def log(m):
    unreal.log("[UI_W7] " + str(m)); print("[UI_W7] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

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
    for name in ("ReturnValue", "Return Value"):
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
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def find_event(ge, name_substr):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and name_substr in title(n):
            return n
    return None

def walk_then(start, max_d=40):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

# ===== Table: prepend RefreshTableBubble on Tick =====
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
tick = find_event(tge, "Tick")
if tick:
    thenp = find_pin(tick, "then", "Output")
    old = list(thenp.list_connected_pins() or []) if thenp else []
    # Check if already first is RefreshTableBubble
    first = title(old[0].get_owning_node()) if old else ""
    log("Tick first=" + first)
    if "RefreshTableBubble" not in first:
        call_rb = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C:RefreshTableBubble")
        bel.set_node_pos(call_rb, pos(-200, 200))
        if thenp:
            try: thenp.break_pin_links()
            except Exception: pass
        connect(thenp, find_pin(call_rb, "execute", "Input"), "Tick->RB")
        if old:
            connect(find_pin(call_rb, "then", "Output"), old[0], "RB->oldTick")
        log("prepended RefreshTableBubble on Tick")
    else:
        log("already first")

# Remove broken SetTimer if FunctionName empty — optional, leave it (harmless if name empty may warn)
# Disconnect RefreshTableBubble from PayAndClear/TimeoutLeave to avoid double-call confusion — keep OK

# ===== Manager: clean orphan GetAllActors / Get with errors =====
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))

# List all error nodes with connection status
try:
    errs = list(mge.list_nodes_with_errors() or [])
except Exception:
    errs = []
log("mgr errors before=" + str([title(n) for n in errs]))

ref = find_custom(mge, "RefreshOrderUI")
ref_nodes = set(id(n) for n in walk_then(ref, 40)) if ref else set()
ens = find_custom(mge, "EnsureOrderUI")
ens_nodes = set(id(n) for n in walk_then(ens, 40)) if ens else set()
keep = ref_nodes | ens_nodes

for n in errs:
    # If not in Ensure/Refresh chains and disconnected exec, break all pins
    exe = find_pin(n, "execute", "Input")
    has_exec_in = bool(exe and list(exe.list_connected_pins() or []))
    in_chain = id(n) in keep
    log("err {} in_chain={} has_exec_in={}".format(title(n), in_chain, has_exec_in))
    if not in_chain:
        for p in bel.list_all_pins(n):
            try: p.break_pin_links()
            except Exception: pass
        log("  broke orphan " + title(n))

# Ensure the Refresh chain GetAllActors is healthy — check ActorClass via making a ClassLiteral
# Connect a MakeClass / ClassReference if needed
for n in walk_then(ref, 40) if ref else []:
    if "GetAllActorsOfClass" in title(n):
        cp = find_pin(n, "ActorClass", "Input")
        linked = list(cp.list_connected_pins() or []) if cp else []
        log("Refresh GetAllActors class linked={} type OutActors check".format(len(linked)))
        for p in bel.list_all_pins(n):
            log("  {} {} {}".format(p.get_pin_name(), p.get_pin_direction(), p.get_pin_type_display_string())[:100])
        # If ActorClass has no default that sticks, create GetClassDefaults or use SelectClass
        # Try add_call Get Soft Class? Use "Class Is Child Of" — simpler: retarget
        # Use bel / ge retarget? 
        # Create a Variable SoftClassPath? 
        # Best: add member var TableClass as class BP_RestaurantTable, get and connect
        names = [str(x) for x in bel.list_member_variable_names(mbp, False)]
        if "TableActorClass" not in names:
            p = unreal.EdGraphPinType()
            # class reference pin
            p.import_text('(PinCategory="class",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")')
            bel.add_member_variable(mbp, "TableActorClass", p)
            log("added TableActorClass var")
        # Set default on CDO
        try:
            cdo = unreal.get_default_object(mbp.generated_class())
            tcls = unreal.load_asset(TBL).generated_class()
            if hasattr(cdo, "set_editor_property"):
                cdo.set_editor_property("TableActorClass", tcls)
                log("CDO TableActorClass set")
        except Exception as e:
            log("CDO set " + str(e)[:80])
        get_cls = mge.add_get_member_variable_node("TableActorClass")
        bel.set_node_pos(get_cls, pos(-2300, 6000))
        if cp:
            try: cp.break_pin_links()
            except Exception: pass
            connect(out_data(get_cls) or find_pin(get_cls, "TableActorClass", "Output"), cp, "TableActorClass->ActorClass")

bel.compile_blueprint(mbp)

# Re-set CDO after compile
try:
    mbp = unreal.load_asset(MGR)
    cdo = unreal.get_default_object(mbp.generated_class())
    tcls = unreal.load_asset(TBL).generated_class()
    cdo.set_editor_property("TableActorClass", tcls)
    log("CDO TableActorClass re-set OK value=" + str(cdo.get_editor_property("TableActorClass")))
except Exception as e:
    log("CDO reset " + str(e))

# Fix timer with MakeLiteralName / Conv
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
for n in tge.list_all_nodes():
    if "Timer" in title(n):
        fn_pin = find_pin(n, "FunctionName", "Input")
        time_pin = find_pin(n, "Time", "Input")
        loop_pin = find_pin(n, "bLooping", "Input") or find_pin(n, "Looping", "Input")
        # MakeLiteralName
        lit = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralName")
        if lit is None:
            lit = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_StringToName")
        bel.set_node_pos(lit, pos(500, -400))
        if lit:
            for p in bel.list_all_pins(lit):
                log("lit pin " + str(p.get_pin_name()) + " " + str(p.get_pin_type_display_string())[:40])
            # set Value / InString
            vp = find_pin(lit, "Value", "Input") or find_pin(lit, "InString", "Input") or find_pin(lit, "InName", "Input")
            # try set_pin_value
            if vp:
                try:
                    vp.set_pin_value("RefreshTableBubble")
                except Exception:
                    try: vp.set_default_value("RefreshTableBubble")
                    except Exception: pass
            connect(out_data(lit), fn_pin, "lit->FunctionName")
        # Time via MakeLiteralFloat
        litf = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralFloat")
        if litf is None:
            litf = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralDouble")
        bel.set_node_pos(litf, pos(500, -250))
        if litf:
            vp = find_pin(litf, "Value", "Input")
            if vp:
                try: vp.set_pin_value("0.2")
                except Exception:
                    try: vp.set_default_value("0.2")
                    except Exception: pass
            connect(out_data(litf), time_pin, "litf->Time")
        # Looping via MakeLiteralBool
        litb = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
        bel.set_node_pos(litb, pos(500, -100))
        if litb:
            vp = find_pin(litb, "Value", "Input")
            if vp:
                try: vp.set_pin_value("true")
                except Exception:
                    try: vp.set_default_value("true")
                    except Exception: pass
            connect(out_data(litb), loop_pin, "litb->Loop")
        log("timer literals wired")

bel.compile_blueprint(tbp); eas.save_asset(TBL)
bel.compile_blueprint(mbp); eas.save_asset(MGR)
bel.compile_blueprint(unreal.load_asset(GUEST)); eas.save_asset(GUEST)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# Final status
for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    R[key + "_err"] = errs
    log("{} err={}".format(key, errs))

tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(MGR), "EventGraph"))
tick = find_event(tge, "Tick")
R["tick"] = [title(n) for n in walk_then(tick, 15)] if tick else []
log("tick: " + " -> ".join(R["tick"][:15]))
ref = find_custom(mge, "RefreshOrderUI")
R["refresh"] = [title(n) for n in walk_then(ref, 20)] if ref else []
log("refresh: " + " -> ".join(R["refresh"][:20]))
sp = find_custom(tge, "SpawnGuestVisual")
R["spawn"] = [title(n) for n in walk_then(sp, 20)] if sp else []
log("spawn: " + " -> ".join(R["spawn"][:20]))

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire7_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("ALL_DONE")
