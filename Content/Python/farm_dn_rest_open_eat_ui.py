# -*- coding: utf-8 -*-
"""OpenEatUI_v1: 17:00 open hint once/day + eating UI (用餐中). No cast — GAO+ArrayGet."""
import unreal, json

REPORT = {"steps": [], "errors": [], "ok": []}
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
MARKER = "OpenEatUI_v1"
FARM_CLOCK_CLS = "/Script/FarmSim25D.FarmClock"

def log(m):
    unreal.log("[OpenEatUI] " + str(m)); print("[OpenEatUI] " + str(m)); REPORT["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "Item"):
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

def walk_then(start, max_d=60):
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

def linear_last(ev, limit=50):
    cur = ev; last = ev
    for _ in range(limit):
        tp = find_pin(cur, "then", "Output")
        if not tp: return last, None
        links = list(tp.list_connected_pins() or [])
        if not links: return cur, tp
        last = links[0].get_owning_node(); cur = last
    return last, find_pin(last, "then", "Output")

def ensure_bool_var(bp, name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    if name in names:
        log("var exists " + name); return False
    t = bel.get_basic_type_by_name("bool")
    bel.add_member_variable(bp, name, t)
    log("var+ " + name); return True

def make_print(ge, x, y, text, dur="3.0", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key: setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def pin_def(p):
    if not p: return ""
    try: return str(p.get_default_as_string())
    except Exception: return ""

def has_rest_open_hint(ge):
    for n in ge.list_all_nodes():
        if title(n) == "PrintString" and pin_def(find_pin(n, "Key", "Input")) == "RestOpenHint":
            return True
    return False

def has_eating_ui(ge):
    for n in ge.list_all_nodes():
        if title(n) == "PrintString" and "用餐中" in pin_def(find_pin(n, "InString", "Input")):
            return True
        if title(n) == "Append" or "Concat" in title(n):
            for p in bel.list_all_pins(n):
                if "用餐中" in pin_def(p):
                    return True
        if title(n) == "DrawDebugString" and "用餐中" in pin_def(find_pin(n, "Text", "Input")):
            return True
    return False

# ===================== MANAGER =====================
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ensure_bool_var(mbp, "bOpenHintShownToday")

if has_rest_open_hint(mge):
    log("RestOpenHint exists — skip manager wire")
    REPORT["ok"].append("mgr_skip_idempotent")
else:
    tick = find_custom(mge, "RestaurantTick")
    if not tick:
        REPORT["errors"].append("no RestaurantTick")
    else:
        last, last_then = linear_last(tick, 50)
        log("tick last=" + title(last))
        if last_then is None:
            last_then = find_pin(last, "then", "Output")

        # If tick last then already wired to something (partial fail), don't double
        if last_then and list(last_then.list_connected_pins() or []):
            log("tick last then already linked to " + title(list(last_then.list_connected_pins())[0].get_owning_node()))
            # still OK to not append if partial — check for bOpenHint in chain from tick
            if any("bOpenHintShownToday" in title(n) for n in walk_then(tick, 80)):
                log("hint logic already in tick chain")
                REPORT["ok"].append("mgr_partial_present")
            else:
                REPORT["errors"].append("tick last busy, cannot append hint")
        else:
            bx, by = 3400, -200

            # Marker stamp (unconnected custom print)
            if not find_custom(mge, MARKER):
                try:
                    mk = mge.add_custom_event_node(MARKER)
                    bel.set_node_pos(mk, pos(bx - 500, by - 250))
                    st = make_print(mge, bx - 250, by - 250, MARKER, dur="0.0", key="RestMarker")
                    connect(find_pin(mk, "then", "Output"), find_pin(st, "execute", "Input"), "marker")
                except Exception as e:
                    make_print(mge, bx - 250, by - 250, MARKER, dur="0.0", key="RestMarker")
                    log("marker print only " + str(e)[:40])

            gao = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
            bel.set_node_pos(gao, pos(bx, by))
            cls_pin = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
            setdef(cls_pin, FARM_CLOCK_CLS)
            try:
                if cls_pin: cls_pin.set_default_value(FARM_CLOCK_CLS)
            except Exception:
                pass

            get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
            bel.set_node_pos(get0, pos(bx + 350, by + 100))
            setdef(find_pin(get0, "Index", "Input"), "0")
            connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input") or find_pin(get0, "Target Array", "Input"), "arr")

            gdm = mge.add_call_function_node("/Script/FarmSim25D.FarmClock:GetDisplayMinutes")
            bel.set_node_pos(gdm, pos(bx + 650, by + 100))
            connect(out_data(get0) or find_pin(get0, "Item", "Output"), find_pin(gdm, "self", "Input"), "item->gdm")

            # Comparisons — try promotable operators like existing graph
            geq = None
            lt = None
            try:
                geq = mge.add_promotable_operator_node(">=")
                lt = mge.add_promotable_operator_node("<")
            except Exception:
                pass
            if geq is None:
                geq = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt")
            if lt is None:
                lt = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_IntInt")
            bel.set_node_pos(geq, pos(bx + 950, by + 40))
            bel.set_node_pos(lt, pos(bx + 950, by + 180))
            setdef(find_pin(geq, "B", "Input"), "1020")
            setdef(find_pin(lt, "B", "Input"), "1020")
            connect(out_data(gdm), find_pin(geq, "A", "Input"), "gdm->geq")
            connect(out_data(gdm), find_pin(lt, "A", "Input"), "gdm->lt")

            get_open = mge.add_get_member_variable_node("bIsOpenBusiness")
            bel.set_node_pos(get_open, pos(bx + 950, by + 320))
            not_open = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
            bel.set_node_pos(not_open, pos(bx + 1150, by + 320))
            connect(out_data(get_open) or find_pin(get_open, "bIsOpenBusiness", "Output"), find_pin(not_open, "A", "Input"), "open->not")

            get_hint = mge.add_get_member_variable_node("bOpenHintShownToday")
            bel.set_node_pos(get_hint, pos(bx + 950, by + 440))
            not_hint = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
            bel.set_node_pos(not_hint, pos(bx + 1150, by + 440))
            connect(out_data(get_hint) or find_pin(get_hint, "bOpenHintShownToday", "Output"), find_pin(not_hint, "A", "Input"), "hint->not")

            and2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
            bel.set_node_pos(and2, pos(bx + 1350, by + 280))
            and3 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
            bel.set_node_pos(and3, pos(bx + 1550, by + 220))
            connect(out_data(geq), find_pin(and2, "A", "Input"), "geq->and2")
            connect(out_data(not_open), find_pin(and2, "B", "Input"), "notOpen->and2")
            connect(out_data(and2), find_pin(and3, "A", "Input"), "and2->and3")
            connect(out_data(not_hint), find_pin(and3, "B", "Input"), "notHint->and3")

            br_reset = mge.add_branch_node()
            bel.set_node_pos(br_reset, pos(bx + 1750, by))
            set_false = mge.add_set_member_variable_node("bOpenHintShownToday")
            bel.set_node_pos(set_false, pos(bx + 2050, by - 100))
            setdef(find_pin(set_false, "bOpenHintShownToday", "Input"), "false")

            br_hint = mge.add_branch_node()
            bel.set_node_pos(br_hint, pos(bx + 2050, by + 100))
            pr = make_print(mge, bx + 2350, by + 60, "已到17:00，可去开业牌开业", dur="4.0", key="RestOpenHint")
            setdef(find_pin(pr, "TextColor", "Input") or find_pin(pr, "Color", "Input"),
                   "(R=1.000000,G=0.850000,B=0.200000,A=1.000000)")
            set_true = mge.add_set_member_variable_node("bOpenHintShownToday")
            bel.set_node_pos(set_true, pos(bx + 2650, by + 60))
            setdef(find_pin(set_true, "bOpenHintShownToday", "Input"), "true")

            connect(last_then, find_pin(gao, "execute", "Input"), "tick->gao")
            connect(find_pin(gao, "then", "Output"), find_pin(br_reset, "execute", "Input"), "gao->brReset")
            connect(out_data(lt), find_pin(br_reset, "Condition", "Input"), "lt->resetCond")
            connect(find_pin(br_reset, "then", "Output"), find_pin(set_false, "execute", "Input"), "reset->false")
            connect(find_pin(br_reset, "else", "Output"), find_pin(br_hint, "execute", "Input"), "resetElse->hint")
            connect(out_data(and3), find_pin(br_hint, "Condition", "Input"), "and3->hintCond")
            connect(find_pin(br_hint, "then", "Output"), find_pin(pr, "execute", "Input"), "hint->print")
            connect(find_pin(pr, "then", "Output"), find_pin(set_true, "execute", "Input"), "print->true")
            REPORT["ok"].append("mgr_open_hint")

# ApplySignOpen: set hint shown true
aos = find_custom(mge, "ApplySignOpen")
if aos:
    chain = walk_then(aos, 20)
    if any("bOpenHintShownToday" in title(n) for n in chain):
        log("ApplySignOpen already sets hint")
    else:
        thenp = find_pin(aos, "then", "Output")
        old = list(thenp.list_connected_pins() or []) if thenp else []
        set_t = mge.add_set_member_variable_node("bOpenHintShownToday")
        bel.set_node_pos(set_t, pos(-250, 4300))
        setdef(find_pin(set_t, "bOpenHintShownToday", "Input"), "true")
        if thenp:
            try: thenp.break_pin_links()
            except Exception: pass
        connect(thenp, find_pin(set_t, "execute", "Input"), "open->hintTrue")
        if old:
            connect(find_pin(set_t, "then", "Output"), old[0], "hintTrue->oldOpen")
        REPORT["ok"].append("open_sets_hint")
else:
    REPORT["errors"].append("no ApplySignOpen")

bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# ===================== TABLE =====================
tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

if has_eating_ui(tge):
    log("eating UI exists — skip table")
    REPORT["ok"].append("tbl_skip_idempotent")
else:
    rb = find_custom(tge, "RefreshTableBubble")
    if not rb:
        REPORT["errors"].append("no RefreshTableBubble")
    else:
        chain = walk_then(rb, 30)
        dds = None; dish_br = None
        for n in chain:
            if title(n) == "DrawDebugString" and dds is None:
                dds = n
            elif dds is not None and title(n) == "Branch" and dish_br is None:
                dish_br = n; break
        log("dds={} dish_br={}".format(dds and title(dds), dish_br and title(dish_br)))
        if not dds or not dish_br:
            REPORT["errors"].append("bubble structure unexpected")
        else:
            dds_then = find_pin(dds, "then", "Output")
            dish_exec = find_pin(dish_br, "execute", "Input")
            # verify currently linked
            cur = [title(c.get_owning_node()) for c in (dds_then.list_connected_pins() or [])] if dds_then else []
            log("dds.then -> " + str(cur))
            try: dds_then.break_pin_links()
            except Exception: pass

            bx, by = 1000, 180
            get_eat = tge.add_get_member_variable_node("bEating")
            bel.set_node_pos(get_eat, pos(bx - 180, by + 160))
            br_eat = tge.add_branch_node()
            bel.set_node_pos(br_eat, pos(bx, by))
            connect(dds_then, find_pin(br_eat, "execute", "Input"), "dds->brEat")
            connect(out_data(get_eat) or find_pin(get_eat, "bEating", "Output"), find_pin(br_eat, "Condition", "Input"), "eat->cond")
            connect(find_pin(br_eat, "else", "Output"), dish_exec, "brEat.else->dish")

            dds_eat = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
            bel.set_node_pos(dds_eat, pos(bx + 280, by - 40))
            setdef(find_pin(dds_eat, "Text", "Input"), "用餐中")
            setdef(find_pin(dds_eat, "Duration", "Input"), "0.0")
            setdef(find_pin(dds_eat, "TextColor", "Input") or find_pin(dds_eat, "Color", "Input"),
                   "(R=0.200000,G=0.950000,B=0.450000,A=1.000000)")
            loc_old = find_pin(dds, "TextLocation", "Input")
            if loc_old:
                for c in (loc_old.list_connected_pins() or []):
                    connect(c, find_pin(dds_eat, "TextLocation", "Input"), "loc->ddsEat")
                    break
            connect(find_pin(br_eat, "then", "Output"), find_pin(dds_eat, "execute", "Input"), "brEat->ddsEat")

            get_tid = tge.add_get_member_variable_node("TableId")
            bel.set_node_pos(get_tid, pos(bx + 200, by + 200))
            to_s = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
            bel.set_node_pos(to_s, pos(bx + 400, by + 200))
            connect(out_data(get_tid) or find_pin(get_tid, "TableId", "Output"),
                    find_pin(to_s, "InInt", "Input") or find_pin(to_s, "InInteger", "Input") or find_pin(to_s, "inInt", "Input"),
                    "tid->str")

            # Use Append (Concat_StrStr) — match existing graph style "Append"
            def concat(ge, x, y):
                n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
                if n is None:
                    n = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Append")
                bel.set_node_pos(n, pos(x, y)); return n

            ap_key = concat(tge, bx + 620, by + 160)
            setdef(find_pin(ap_key, "A", "Input"), "RestOrder")
            connect(out_data(to_s), find_pin(ap_key, "B", "Input"), "id->key")

            to_name = tge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_StringToName")
            bel.set_node_pos(to_name, pos(bx + 860, by + 160))
            connect(out_data(ap_key), find_pin(to_name, "InString", "Input"), "key->name")

            ap1 = concat(tge, bx + 620, by + 260)
            setdef(find_pin(ap1, "A", "Input"), "桌")
            connect(out_data(to_s), find_pin(ap1, "B", "Input"), "id->ap1")
            ap2 = concat(tge, bx + 860, by + 260)
            connect(out_data(ap1), find_pin(ap2, "A", "Input"), "ap1->ap2")
            setdef(find_pin(ap2, "B", "Input"), " 用餐中")

            pr = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
            bel.set_node_pos(pr, pos(bx + 1100, by + 40))
            setdef(find_pin(pr, "Duration", "Input"), "0.15")
            setdef(find_pin(pr, "TextColor", "Input") or find_pin(pr, "Color", "Input"),
                   "(R=0.200000,G=0.950000,B=0.450000,A=1.000000)")
            connect(out_data(ap2), find_pin(pr, "InString", "Input"), "text->pr")
            connect(out_data(to_name), find_pin(pr, "Key", "Input"), "name->pr")
            connect(find_pin(dds_eat, "then", "Output"), find_pin(pr, "execute", "Input"), "ddsEat->pr")
            REPORT["ok"].append("tbl_eating_ui")

bel.compile_blueprint(tbp)
eas.save_asset(TBL)

for path, key in ((MGR, "mgr"), (TBL, "tbl")):
    bp = eas.load_asset(path)
    bel.compile_blueprint(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    try:
        errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    except Exception:
        errs = []
    try:
        st = str(bp.status)
    except Exception:
        st = "?"
    REPORT[key + "_status"] = st
    REPORT[key + "_errs"] = errs
    log("{} status={} errs={}".format(key, st, errs))
    eas.save_asset(path)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level " + str(e)[:60])
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

open(r"E:\UE\FarmSim25D\Saved\rest_open_eat_ui.json", "w", encoding="utf-8").write(json.dumps(REPORT, indent=2, ensure_ascii=False))
print(json.dumps({"ok_flags": REPORT["ok"], "errors": REPORT["errors"], "mgr_errs": REPORT.get("mgr_errs"), "tbl_errs": REPORT.get("tbl_errs")}, ensure_ascii=False))
