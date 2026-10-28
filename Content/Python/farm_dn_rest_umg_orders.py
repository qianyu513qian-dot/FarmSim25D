# -*- coding: utf-8 -*-
"""Replace RestOrder PrintString strip with live UMG TextBlocks on WBP_RestOrderList.

- WBP: disconnect FarmHUD Tick; rename TxtTitle/TxtLine1/TxtLine2; CJK font; UpdateOrders(Line1,Line2)
- Manager: OrderLine1/2 + RefreshOrderUI gathers 2 tables -> UpdateOrders; visibility; debug print off
Surgical: do not wipe Manager cook/serve graphs.
"""
import unreal
import json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
WBP = "/Game/Farm/UI/WBP_RestOrderList"
FONT = "/Game/Farm/Restaurant/Font_SimHei_TR"

REPORT = {"steps": [], "ok": [], "warn": [], "err": []}


def log(m):
    s = str(m)
    unreal.log("[UMGORD] " + s)
    print("[UMGORD] " + s)
    REPORT["steps"].append(s)


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name() if n else "?"


def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def out_data(node):
    if not node:
        return None
    for name in (
        "ReturnValue", "Return Value", "Item", "OrderListWidget", "bOccupied", "CurrentOrder",
        "CurrentDishId", "bEating", "PatienceLeft", "TableId", "bIsOpenBusiness", "Line1", "Line2",
        "OrderLine1", "OrderLine2", "AsBP Restaurant Table", "AsWBP RestOrderList",
    ):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "else", "completed", "loopbody"):
                return p
    return None


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    return ok


def setdef(pin, val):
    if not pin:
        return False
    try:
        pin.set_pin_value(str(val))
        return True
    except Exception:
        try:
            pin.set_default_value(str(val))
            return True
        except Exception as e:
            log("setdef fail " + str(e)[:100])
            return False


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
    seen = []
    ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d:
            continue
        ids.add(id(cur))
        seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen


def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    if name in names:
        return False
    t = bel.get_basic_type_by_name(type_name)
    bel.add_member_variable(bp, name, t)
    log("add var {}.{}".format(bp.get_name(), name))
    return True


def status_of(bp):
    try:
        return str(bp.get_editor_property("status"))
    except Exception as e:
        return str(e)


def set_tb_font_text(tb, text, size=20):
    try:
        tb.set_text(text)
    except Exception:
        try:
            tb.set_editor_property("text", text)
        except Exception as e:
            log("set_text " + str(e)[:80])
    font_cjk = unreal.load_asset(FONT)
    try:
        fi = tb.get_editor_property("font")
        fi.set_editor_property("size", float(size))
        if font_cjk:
            try:
                fi.set_editor_property("font_object", font_cjk)
            except Exception:
                pass
        tb.set_editor_property("font", fi)
    except Exception as e:
        log("font " + str(e)[:80])


# =============================================================================
# 1) WBP_RestOrderList
# =============================================================================
wbp = unreal.load_asset(WBP)
wge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))

# Disconnect FarmHUD Event Tick so it cannot overwrite order texts / reference missing vars
tick = find_event(wge, "Tick")
if tick:
    thenp = find_pin(tick, "then", "Output")
    if thenp:
        try:
            thenp.break_pin_links()
            log("broke Event Tick then links")
        except Exception as e:
            log("tick break " + str(e))

# Also disconnect PreConstruct/Construct if they feed farm logic (they were empty in inspect)
# Purge Get TxtMoney / SetText chains that are orphaned? Leave orphans; compile after rename.

# Collect widgets
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o
log("widgets before=" + str(sorted(widgets.keys())))

# Rename map
rename_map = {
    "TxtMoney": "TxtTitle",
    "TxtOrder1": "TxtLine1",
    "TxtOrder2": "TxtLine2",
}
for old, new in rename_map.items():
    if old in widgets and new not in widgets:
        try:
            widgets[old].rename(new)
            log("renamed {} -> {}".format(old, new))
        except Exception as e:
            try:
                widgets[old].rename(new, widgets[old].get_outer())
                log("renamed2 {} -> {}".format(old, new))
            except Exception as e2:
                log("rename fail {} {}".format(old, e2))

# Refresh widget map
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o
log("widgets after=" + str(sorted(widgets.keys())))

# Ensure TxtTitle / TxtLine1 / TxtLine2 exist
tree = unreal.load_object(wbp, "WidgetTree")
layout = widgets.get("HUDLayout")
for need, default, sz in (
    ("TxtTitle", "\u8ba2\u5355", 22),
    ("TxtLine1", "", 18),
    ("TxtLine2", "", 18),
):
    if need not in widgets:
        tb = unreal.new_object(unreal.TextBlock, tree, need)
        set_tb_font_text(tb, default, sz)
        if layout:
            try:
                layout.add_child_to_vertical_box(tb)
                log("created+added " + need)
            except Exception as e:
                log("add " + need + " " + str(e))
        widgets[need] = tb
    else:
        set_tb_font_text(widgets[need], default if need == "TxtTitle" else (widgets[need].get_text() if hasattr(widgets[need], "get_text") else default), 22 if need == "TxtTitle" else 18)
        if need == "TxtTitle":
            set_tb_font_text(widgets[need], "\u8ba2\u5355", 22)
        else:
            set_tb_font_text(widgets[need], "", 18)
        try:
            widgets[need].set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
        except Exception:
            pass

# Collapse farm leftovers
for name in ("TxtSeeds", "TxtHarvest", "TxtClock", "TxtStamina", "TxtControls", "BarStamina", "BarPatience1", "BarPatience2"):
    if name in widgets:
        try:
            widgets[name].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        except Exception:
            pass

# Remove broken Get TxtMoney nodes (FarmHUD leftovers)
kill = []
for n in list(wge.list_all_nodes()):
    if n.get_class().get_name() == "K2Node_VariableGet" and "TxtMoney" in title(n):
        for p in bel.list_all_pins(n):
            try:
                p.break_pin_links()
            except Exception:
                pass
        kill.append(n)
        log("purge Get TxtMoney")
if kill:
    wge.remove_nodes(kill)

# Create / rebuild UpdateOrders(Line1, Line2)
try:
    if bel.find_graph(wbp, "UpdateOrders"):
        bel.remove_function_graph(wbp, "UpdateOrders")
        log("removed old UpdateOrders")
except Exception as e:
    log("no old UpdateOrders " + str(e)[:60])

bel.add_function_graph(wbp, "UpdateOrders")
ugraph = bel.find_graph(wbp, "UpdateOrders")
uge = unreal.BlueprintGraphEditor.get_graph_editor(ugraph)
# clear non-entry
entry = None
to_del = []
for n in uge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
    else:
        to_del.append(n)
if to_del:
    uge.remove_nodes(to_del)

str_pin = bel.get_basic_type_by_name("string")
# refresh entry
for n in uge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
if find_pin(entry, "Line1", "Output") is None:
    uge.add_graph_input_parameter("Line1", str_pin)
if find_pin(entry, "Line2", "Output") is None:
    uge.add_graph_input_parameter("Line2", str_pin)
for n in uge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
bel.set_node_pos(entry, pos(0, 0))

# Get text widgets + SetText
get_title = uge.add_get_member_variable_node("TxtTitle")
bel.set_node_pos(get_title, pos(250, -80))
get_l1 = uge.add_get_member_variable_node("TxtLine1")
bel.set_node_pos(get_l1, pos(250, 80))
get_l2 = uge.add_get_member_variable_node("TxtLine2")
bel.set_node_pos(get_l2, pos(250, 240))

conv_t = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv_t, pos(500, -40))
setdef(find_pin(conv_t, "InString", "Input"), "\u8ba2\u5355")

conv1 = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv1, pos(500, 80))
connect(find_pin(entry, "Line1", "Output"), find_pin(conv1, "InString", "Input"), "L1->conv")

conv2 = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv2, pos(500, 240))
connect(find_pin(entry, "Line2", "Output"), find_pin(conv2, "InString", "Input"), "L2->conv")

set_t = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
bel.set_node_pos(set_t, pos(800, -80))
set_1 = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
bel.set_node_pos(set_1, pos(800, 80))
set_2 = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
bel.set_node_pos(set_2, pos(800, 240))

connect(find_pin(entry, "then", "Output"), find_pin(set_t, "execute", "Input"), "entry->setT")
connect(out_data(get_title), find_pin(set_t, "self", "Input"), "title self")
connect(out_data(conv_t), find_pin(set_t, "InText", "Input") or find_pin(set_t, "Text", "Input") or find_pin(set_t, "In Text", "Input"), "title text")

connect(find_pin(set_t, "then", "Output"), find_pin(set_1, "execute", "Input"), "t->1")
connect(out_data(get_l1), find_pin(set_1, "self", "Input"), "l1 self")
connect(out_data(conv1), find_pin(set_1, "InText", "Input") or find_pin(set_1, "Text", "Input") or find_pin(set_1, "In Text", "Input"), "l1 text")

connect(find_pin(set_1, "then", "Output"), find_pin(set_2, "execute", "Input"), "1->2")
connect(out_data(get_l2), find_pin(set_2, "self", "Input"), "l2 self")
connect(out_data(conv2), find_pin(set_2, "InText", "Input") or find_pin(set_2, "Text", "Input") or find_pin(set_2, "In Text", "Input"), "l2 text")

# Show/hide line visibility: empty -> Collapsed
# Line1 visibility
is_empty1 = uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr")
bel.set_node_pos(is_empty1, pos(1100, 40))
connect(find_pin(entry, "Line1", "Output"), find_pin(is_empty1, "A", "Input"), "e1A")
setdef(find_pin(is_empty1, "B", "Input"), "")
br1 = uge.add_branch_node()
bel.set_node_pos(br1, pos(1350, 40))
connect(find_pin(set_2, "then", "Output"), find_pin(br1, "execute", "Input"), "set2->br1")
connect(out_data(is_empty1), find_pin(br1, "Condition", "Input"), "empty1")

vis_hide1 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vis_hide1, pos(1600, -40))
vis_show1 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vis_show1, pos(1600, 120))
connect(out_data(get_l1), find_pin(vis_hide1, "self", "Input"), "vh1 self")
connect(out_data(get_l1), find_pin(vis_show1, "self", "Input"), "vs1 self")
setdef(find_pin(vis_hide1, "InVisibility", "Input") or find_pin(vis_hide1, "Visibility", "Input"), "Collapsed")
setdef(find_pin(vis_show1, "InVisibility", "Input") or find_pin(vis_show1, "Visibility", "Input"), "Visible")
connect(find_pin(br1, "then", "Output"), find_pin(vis_hide1, "execute", "Input"), "empty->hide1")
connect(find_pin(br1, "else", "Output"), find_pin(vis_show1, "execute", "Input"), "ne->show1")

# Merge then continue to line2 vis: use Sequence-like by wiring both hide/show then to next branch
is_empty2 = uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr")
bel.set_node_pos(is_empty2, pos(1850, 40))
connect(find_pin(entry, "Line2", "Output"), find_pin(is_empty2, "A", "Input"), "e2A")
setdef(find_pin(is_empty2, "B", "Input"), "")
br2 = uge.add_branch_node()
bel.set_node_pos(br2, pos(2100, 40))
connect(find_pin(vis_hide1, "then", "Output"), find_pin(br2, "execute", "Input"), "h1->br2")
connect(find_pin(vis_show1, "then", "Output"), find_pin(br2, "execute", "Input"), "s1->br2")
connect(out_data(is_empty2), find_pin(br2, "Condition", "Input"), "empty2")

vis_hide2 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vis_hide2, pos(2350, -40))
vis_show2 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vis_show2, pos(2350, 120))
connect(out_data(get_l2), find_pin(vis_hide2, "self", "Input"), "vh2")
connect(out_data(get_l2), find_pin(vis_show2, "self", "Input"), "vs2")
setdef(find_pin(vis_hide2, "InVisibility", "Input") or find_pin(vis_hide2, "Visibility", "Input"), "Collapsed")
setdef(find_pin(vis_show2, "InVisibility", "Input") or find_pin(vis_show2, "Visibility", "Input"), "Visible")
connect(find_pin(br2, "then", "Output"), find_pin(vis_hide2, "execute", "Input"), "e2hide")
connect(find_pin(br2, "else", "Output"), find_pin(vis_show2, "execute", "Input"), "e2show")

bel.compile_blueprint(wbp)
log("WBP compile status=" + status_of(wbp))
werrs = [title(n) for n in (wge.list_nodes_with_errors() or [])]
# also check UpdateOrders graph errors
try:
    uerrs = [title(n) for n in (uge.list_nodes_with_errors() or [])]
except Exception:
    uerrs = []
REPORT["wbp_errs"] = werrs + uerrs
log("wbp errs=" + str(REPORT["wbp_errs"]))
eas.save_asset(WBP)

# =============================================================================
# 2) Manager vars + SetOrderLine + rebuild RefreshOrderUI UMG push
# =============================================================================
mbp = unreal.load_asset(MGR)
ensure_var(mbp, "OrderLine1", "string")
ensure_var(mbp, "OrderLine2", "string")
ensure_var(mbp, "bOrderDebugPrint", "bool")
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Set default bOrderDebugPrint = false on CDO if possible
try:
    cdo = mbp.generated_class().get_default_object()
    cdo.set_editor_property("b_order_debug_print", False)
except Exception:
    try:
        cdo = mbp.generated_class().get_default_object()
        cdo.set_editor_property("bOrderDebugPrint", False)
    except Exception as e:
        log("cdo debug " + str(e)[:80])

# --- SetOrderLine(TableId, Line) function ---
try:
    if bel.find_graph(mbp, "SetOrderLine"):
        bel.remove_function_graph(mbp, "SetOrderLine")
except Exception:
    pass
bel.add_function_graph(mbp, "SetOrderLine")
sgraph = bel.find_graph(mbp, "SetOrderLine")
sge = unreal.BlueprintGraphEditor.get_graph_editor(sgraph)
sentry = None
to_del = []
for n in sge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        sentry = n
    else:
        to_del.append(n)
if to_del:
    sge.remove_nodes(to_del)
int_pin = bel.get_basic_type_by_name("int")
str_pin = bel.get_basic_type_by_name("string")
if find_pin(sentry, "TableId", "Output") is None:
    sge.add_graph_input_parameter("TableId", int_pin)
if find_pin(sentry, "Line", "Output") is None:
    sge.add_graph_input_parameter("Line", str_pin)
for n in sge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        sentry = n
bel.set_node_pos(sentry, pos(0, 0))

eq1 = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq1, pos(300, 40))
connect(find_pin(sentry, "TableId", "Output"), find_pin(eq1, "A", "Input"), "tid")
setdef(find_pin(eq1, "B", "Input"), "1")
br = sge.add_branch_node()
bel.set_node_pos(br, pos(550, 0))
connect(find_pin(sentry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
connect(out_data(eq1), find_pin(br, "Condition", "Input"), "eq1")
set1 = sge.add_set_member_variable_node("OrderLine1")
bel.set_node_pos(set1, pos(850, -80))
set2 = sge.add_set_member_variable_node("OrderLine2")
bel.set_node_pos(set2, pos(850, 120))
connect(find_pin(br, "then", "Output"), find_pin(set1, "execute", "Input"), "t1")
connect(find_pin(br, "else", "Output"), find_pin(set2, "execute", "Input"), "t2")
connect(find_pin(sentry, "Line", "Output"), find_pin(set1, "OrderLine1", "Input"), "L->1")
connect(find_pin(sentry, "Line", "Output"), find_pin(set2, "OrderLine2", "Input"), "L->2")
bel.compile_blueprint(mbp)
log("SetOrderLine status=" + status_of(mbp))

# --- Rebuild RefreshOrderUI body (keep event node; replace then chain) ---
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ref = find_custom(mge, "RefreshOrderUI")
if ref is None:
    ref = mge.add_custom_event_node("RefreshOrderUI")
    bel.set_node_pos(ref, pos(-3200, 5700))
    log("created RefreshOrderUI")

# Break old then chain from RefreshOrderUI but DO NOT delete EnsureOrderUI custom event itself
old_chain = walk_then(ref, 30)
log("old refresh: " + " -> ".join(title(n) for n in old_chain))
then_ref = find_pin(ref, "then", "Output")
if then_ref:
    try:
        then_ref.break_pin_links()
        log("broke RefreshOrderUI.then")
    except Exception as e:
        log(str(e))

# Remove orphaned PrintString / EnsureOrderUI CALL nodes that were only in refresh chain
# (Keep EnsureOrderUI custom event definition)
orphans = []
for n in old_chain:
    t = title(n)
    cls = n.get_class().get_name()
    # Only remove call nodes / prints that are disconnected now
    if cls == "K2Node_CallFunction" and (t in ("PrintString", "EnsureOrderUI") or "PrintString" in t):
        # check if still has exec inputs
        exe = find_pin(n, "execute", "Input")
        linked = list(exe.list_connected_pins() or []) if exe else []
        if not linked:
            orphans.append(n)
if orphans:
    mge.remove_nodes(orphans)
    log("removed {} orphan refresh nodes".format(len(orphans)))

Y = 5700
X = -3000

# EnsureOrderUI call
call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
bel.set_node_pos(call_ens, pos(X, Y))
connect(find_pin(ref, "then", "Output"), find_pin(call_ens, "execute", "Input"), "ref->ens")

# Clear lines
set_c1 = mge.add_set_member_variable_node("OrderLine1")
bel.set_node_pos(set_c1, pos(X + 350, Y))
setdef(find_pin(set_c1, "OrderLine1", "Input"), "")
set_c2 = mge.add_set_member_variable_node("OrderLine2")
bel.set_node_pos(set_c2, pos(X + 700, Y))
setdef(find_pin(set_c2, "OrderLine2", "Input"), "")
connect(find_pin(call_ens, "then", "Output"), find_pin(set_c1, "execute", "Input"), "ens->c1")
connect(find_pin(set_c1, "then", "Output"), find_pin(set_c2, "execute", "Input"), "c1->c2")

# GetAllActorsOfClass tables
get_all = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
bel.set_node_pos(get_all, pos(X + 1050, Y))
setdef(find_pin(get_all, "ActorClass", "Input"), "/Game/Farm/Restaurant/BP_RestaurantTable.BP_RestaurantTable_C")
connect(find_pin(set_c2, "then", "Output"), find_pin(get_all, "execute", "Input"), "c2->all")

tbl_cls = unreal.load_asset(TBL).generated_class()
wbp_cls = unreal.load_asset(WBP).generated_class()


def wire_table_slot(ge, prev_then_node, array_node, index, base_x, base_y, label):
    """From GetAllActors OutActors, Array_Get index, cast, if occupied build CN line and SetOrderLine."""
    arr_get = ge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(arr_get, pos(base_x, base_y))
    connect(find_pin(array_node, "OutActors", "Output"), find_pin(arr_get, "TargetArray", "Input"), label + "arr")
    setdef(find_pin(arr_get, "Index", "Input"), str(index))

    # Array_Get is pure in some versions — still chain exec via Sequence using Branch IsValid after cast
    cast = ge.add_cast_node(tbl_cls)
    bel.set_node_pos(cast, pos(base_x + 280, base_y))
    connect(out_data(arr_get), find_pin(cast, "Object", "Input") or find_pin(cast, "execute", "Input") and find_pin(cast, "Object", "Input"), label + "castobj")
    # Cast usually has execute
    has_exec = find_pin(cast, "execute", "Input") is not None
    if has_exec:
        connect(find_pin(prev_then_node, "then", "Output"), find_pin(cast, "execute", "Input"), label + "prev->cast")
    else:
        # need Branch after dummy
        pass

    # cast success pin often "then" / "CastSucceeded"
    cast_then = find_pin(cast, "then", "Output")
    cast_failed = find_pin(cast, "CastFailed", "Output") or find_pin(cast, "else", "Output")
    cast_out = None
    for p in bel.list_all_pins(cast):
        if "OUTPUT" in str(p.get_pin_direction()) and "Object" in str(p.get_pin_type_display_string()):
            cast_out = p
            break
    if cast_out is None:
        cast_out = out_data(cast)

    get_occ = ge.add_get_member_variable_node("bOccupied")
    bel.set_node_pos(get_occ, pos(base_x + 550, base_y + 120))
    # Target of get member when not self: need to set "self" pin from cast
    connect(cast_out, find_pin(get_occ, "self", "Input"), label + "occ self")

    br_occ = ge.add_branch_node()
    bel.set_node_pos(br_occ, pos(base_x + 800, base_y))
    if has_exec and cast_then:
        connect(cast_then, find_pin(br_occ, "execute", "Input"), label + "cast->brocc")
    elif not has_exec:
        connect(find_pin(prev_then_node, "then", "Output"), find_pin(br_occ, "execute", "Input"), label + "prev->brocc")
    connect(out_data(get_occ), find_pin(br_occ, "Condition", "Input"), label + "occ")

    # When NOT occupied: clear via SetOrderLine with "" — need TableId first
    get_tid_empty = ge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid_empty, pos(base_x + 800, base_y + 220))
    connect(cast_out, find_pin(get_tid_empty, "self", "Input"), label + "tidE self")
    call_clear = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_clear, pos(base_x + 1100, base_y + 200))
    connect(find_pin(br_occ, "else", "Output"), find_pin(call_clear, "execute", "Input"), label + "empty")
    connect(out_data(get_tid_empty), find_pin(call_clear, "TableId", "Input"), label + "clear tid")
    setdef(find_pin(call_clear, "Line", "Input"), "")

    # Occupied path: gather fields
    get_tid = ge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid, pos(base_x + 1050, base_y - 200))
    connect(cast_out, find_pin(get_tid, "self", "Input"), label + "tid self")
    get_dish = ge.add_get_member_variable_node("CurrentDishId")
    bel.set_node_pos(get_dish, pos(base_x + 1050, base_y - 100))
    connect(cast_out, find_pin(get_dish, "self", "Input"), label + "dish self")
    get_eat = ge.add_get_member_variable_node("bEating")
    bel.set_node_pos(get_eat, pos(base_x + 1050, base_y + 0))
    connect(cast_out, find_pin(get_eat, "self", "Input"), label + "eat self")
    get_pl = ge.add_get_member_variable_node("PatienceLeft")
    bel.set_node_pos(get_pl, pos(base_x + 1050, base_y + 80))
    connect(cast_out, find_pin(get_pl, "self", "Input"), label + "pl self")

    # Dish name branch
    eq_dish = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq_dish, pos(base_x + 1300, base_y - 100))
    connect(out_data(get_dish), find_pin(eq_dish, "A", "Input"), label + "dishA")
    setdef(find_pin(eq_dish, "B", "Input"), "1")
    br_dish = ge.add_branch_node()
    bel.set_node_pos(br_dish, pos(base_x + 1550, base_y - 160))
    connect(find_pin(br_occ, "then", "Output"), find_pin(br_dish, "execute", "Input"), label + "occ->dish")
    connect(out_data(eq_dish), find_pin(br_dish, "Condition", "Input"), label + "eqdish")

    # Build: "桌" + id + " " + dishCN + " " + status
    # We build two parallel SetOrderLine calls for salad vs stew, each with status branch — heavy.
    # Simpler: use temp locals via Set OrderLine after constructing with selects.
    # Practical: two full concat chains (salad/stew), each with nested eating branch.

    def build_and_set(ge, exec_pin, dish_cn, y_off, tag):
        to_id = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
        bel.set_node_pos(to_id, pos(base_x + 1800, base_y + y_off))
        connect(out_data(get_tid), find_pin(to_id, "InInt", "Input"), tag + "id")

        ap1 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(ap1, pos(base_x + 2050, base_y + y_off))
        setdef(find_pin(ap1, "A", "Input"), "\u684c")  # 桌
        connect(out_data(to_id), find_pin(ap1, "B", "Input"), tag + "ap1")

        ap2 = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(ap2, pos(base_x + 2300, base_y + y_off))
        connect(out_data(ap1), find_pin(ap2, "A", "Input"), tag + "ap2a")
        setdef(find_pin(ap2, "B", "Input"), " " + dish_cn + " ")

        # status: eating?
        br_eat = ge.add_branch_node()
        bel.set_node_pos(br_eat, pos(base_x + 2550, base_y + y_off))
        connect(exec_pin, find_pin(br_eat, "execute", "Input"), tag + "->eat")
        connect(out_data(get_eat), find_pin(br_eat, "Condition", "Input"), tag + "eating")

        # eating line
        ap_eat = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(ap_eat, pos(base_x + 2800, base_y + y_off - 60))
        connect(out_data(ap2), find_pin(ap_eat, "A", "Input"), tag + "apea")
        setdef(find_pin(ap_eat, "B", "Input"), "\u7528\u9910\u4e2d")  # 用餐中
        call_e = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
        bel.set_node_pos(call_e, pos(base_x + 3100, base_y + y_off - 60))
        connect(find_pin(br_eat, "then", "Output"), find_pin(call_e, "execute", "Input"), tag + "sete")
        connect(out_data(get_tid), find_pin(call_e, "TableId", "Input"), tag + "tidE")
        connect(out_data(ap_eat), find_pin(call_e, "Line", "Input"), tag + "lineE")

        # patience line
        to_pl = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
        if to_pl is None:
            to_pl = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
        bel.set_node_pos(to_pl, pos(base_x + 2800, base_y + y_off + 80))
        connect(out_data(get_pl), find_pin(to_pl, "InDouble", "Input") or find_pin(to_pl, "InFloat", "Input") or find_pin(to_pl, "In", "Input"), tag + "pl")
        ap_pl = ge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        bel.set_node_pos(ap_pl, pos(base_x + 3050, base_y + y_off + 80))
        connect(out_data(ap2), find_pin(ap_pl, "A", "Input"), tag + "appa")
        connect(out_data(to_pl), find_pin(ap_pl, "B", "Input"), tag + "appb")
        call_p = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
        bel.set_node_pos(call_p, pos(base_x + 3350, base_y + y_off + 80))
        connect(find_pin(br_eat, "else", "Output"), find_pin(call_p, "execute", "Input"), tag + "setp")
        connect(out_data(get_tid), find_pin(call_p, "TableId", "Input"), tag + "tidP")
        connect(out_data(ap_pl), find_pin(call_p, "Line", "Input"), tag + "lineP")

        # return a node whose then we can continue from — use a dummy Branch false merge is hard;
        # return both terminals; caller will Sequence from cast_failed / clear / call_e / call_p via later IsValid widget push from a NEW custom continuation.
        return call_clear, call_e, call_p, cast_failed

    # Salad (dish==1) and Stew (else)
    # Note: build_and_set wires exec from br_dish then/else
    # For salad:
    to_id_s = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(to_id_s, pos(base_x + 1800, base_y - 200))
    connect(out_data(get_tid), find_pin(to_id_s, "InInt", "Input"), label + "sid")
    ap1s = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap1s, pos(base_x + 2050, base_y - 200))
    setdef(find_pin(ap1s, "A", "Input"), "\u684c")
    connect(out_data(to_id_s), find_pin(ap1s, "B", "Input"), label + "sap1")
    ap2s = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap2s, pos(base_x + 2300, base_y - 200))
    connect(out_data(ap1s), find_pin(ap2s, "A", "Input"), label + "sap2a")
    setdef(find_pin(ap2s, "B", "Input"), " \u756a\u8304\u6c99\u62c9 ")  # 番茄沙拉

    br_eats = mge.add_branch_node()
    bel.set_node_pos(br_eats, pos(base_x + 2550, base_y - 200))
    connect(find_pin(br_dish, "then", "Output"), find_pin(br_eats, "execute", "Input"), label + "salad")
    connect(out_data(get_eat), find_pin(br_eats, "Condition", "Input"), label + "se")

    ap_es = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap_es, pos(base_x + 2800, base_y - 280))
    connect(out_data(ap2s), find_pin(ap_es, "A", "Input"), label + "ases")
    setdef(find_pin(ap_es, "B", "Input"), "\u7528\u9910\u4e2d")
    call_es = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_es, pos(base_x + 3100, base_y - 280))
    connect(find_pin(br_eats, "then", "Output"), find_pin(call_es, "execute", "Input"), label + "calles")
    connect(out_data(get_tid), find_pin(call_es, "TableId", "Input"), label + "tides")
    connect(out_data(ap_es), find_pin(call_es, "Line", "Input"), label + "lines")

    to_pls = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
    if to_pls is None:
        to_pls = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
    bel.set_node_pos(to_pls, pos(base_x + 2800, base_y - 120))
    connect(out_data(get_pl), find_pin(to_pls, "InDouble", "Input") or find_pin(to_pls, "InFloat", "Input"), label + "pls")
    ap_ps = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap_ps, pos(base_x + 3050, base_y - 120))
    connect(out_data(ap2s), find_pin(ap_ps, "A", "Input"), label + "apps")
    connect(out_data(to_pls), find_pin(ap_ps, "B", "Input"), label + "appsb")
    call_ps = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_ps, pos(base_x + 3350, base_y - 120))
    connect(find_pin(br_eats, "else", "Output"), find_pin(call_ps, "execute", "Input"), label + "callps")
    connect(out_data(get_tid), find_pin(call_ps, "TableId", "Input"), label + "tidps")
    connect(out_data(ap_ps), find_pin(call_ps, "Line", "Input"), label + "lineps")

    # Stew
    to_id_w = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_IntToString")
    bel.set_node_pos(to_id_w, pos(base_x + 1800, base_y + 40))
    connect(out_data(get_tid), find_pin(to_id_w, "InInt", "Input"), label + "wid")
    ap1w = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap1w, pos(base_x + 2050, base_y + 40))
    setdef(find_pin(ap1w, "A", "Input"), "\u684c")
    connect(out_data(to_id_w), find_pin(ap1w, "B", "Input"), label + "wap1")
    ap2w = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap2w, pos(base_x + 2300, base_y + 40))
    connect(out_data(ap1w), find_pin(ap2w, "A", "Input"), label + "wap2")
    setdef(find_pin(ap2w, "B", "Input"), " \u7096\u83dc ")  # 炖菜

    br_eatw = mge.add_branch_node()
    bel.set_node_pos(br_eatw, pos(base_x + 2550, base_y + 40))
    connect(find_pin(br_dish, "else", "Output"), find_pin(br_eatw, "execute", "Input"), label + "stew")
    connect(out_data(get_eat), find_pin(br_eatw, "Condition", "Input"), label + "we")

    ap_ew = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap_ew, pos(base_x + 2800, base_y - 20))
    connect(out_data(ap2w), find_pin(ap_ew, "A", "Input"), label + "aew")
    setdef(find_pin(ap_ew, "B", "Input"), "\u7528\u9910\u4e2d")
    call_ew = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_ew, pos(base_x + 3100, base_y - 20))
    connect(find_pin(br_eatw, "then", "Output"), find_pin(call_ew, "execute", "Input"), label + "calle")
    connect(out_data(get_tid), find_pin(call_ew, "TableId", "Input"), label + "tidew")
    connect(out_data(ap_ew), find_pin(call_ew, "Line", "Input"), label + "lineew")

    to_plw = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
    if to_plw is None:
        to_plw = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
    bel.set_node_pos(to_plw, pos(base_x + 2800, base_y + 120))
    connect(out_data(get_pl), find_pin(to_plw, "InDouble", "Input") or find_pin(to_plw, "InFloat", "Input"), label + "plw")
    ap_pw = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap_pw, pos(base_x + 3050, base_y + 120))
    connect(out_data(ap2w), find_pin(ap_pw, "A", "Input"), label + "apw")
    connect(out_data(to_plw), find_pin(ap_pw, "B", "Input"), label + "apwb")
    call_pw = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_pw, pos(base_x + 3350, base_y + 120))
    connect(find_pin(br_eatw, "else", "Output"), find_pin(call_pw, "execute", "Input"), label + "callpw")
    connect(out_data(get_tid), find_pin(call_pw, "TableId", "Input"), label + "tidpw")
    connect(out_data(ap_pw), find_pin(call_pw, "Line", "Input"), label + "linepw")

    # Return nodes that finish this slot (for chaining next slot / push UI)
    finish_nodes = [call_clear, call_es, call_ps, call_ew, call_pw]
    if cast_failed:
        # cast fail: just continue — use a Print no-op? Better: empty Reroute via Branch false
        pass
    return finish_nodes, cast, has_exec


# Slot 0
fin0, cast0, has_exec0 = wire_table_slot(mge, get_all, get_all, 0, X + 1400, Y - 50, "T0")
# For slot 1 we need a Sequence after all fin0 then pins — use a custom event PushOrderUI called from each terminal
# Simpler approach: add custom event ApplyOrderUMG and call it from each finish then + from cast fail.

apply = find_custom(mge, "ApplyOrderUMG")
if apply:
    # remove old body
    for n in walk_then(apply, 40):
        pass
else:
    apply = mge.add_custom_event_node("ApplyOrderUMG")
    bel.set_node_pos(apply, pos(X, Y + 900))

# Break apply then and rebuild
athen = find_pin(apply, "then", "Output")
if athen:
    try:
        athen.break_pin_links()
    except Exception:
        pass

# Wire all finish nodes -> ApplyOrderUMG call
call_apply_nodes = []
for fn in fin0:
    ca = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplyOrderUMG")
    # ApplyOrderUMG is custom event — need compile first to call it. Use call after compile.
    call_apply_nodes.append((fn, ca))

# Actually Custom Events become callable after compile. Mid-compile now:
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
# Re-find nodes by walking refresh again — fragile. Better: don't use ApplyOrderUMG custom;
# inline UMG push AFTER both table slots using Sequence macro.

log("mid compile after slot0 scaffold status=" + status_of(mbp))

# Because chaining two table slots + many terminals is fragile, switch strategy:
# Tables push lines via SetOrderLine from their existing RefreshTableBubble Print path,
# Manager RefreshOrderUI only: Ensure -> ApplyOrderUMG (read OrderLine1/2 -> UpdateOrders).

# DETOUR: remove the heavy GetAllActors chain we just added and do the simpler path.
# Break ref->ens chain we started and rebuild clean simple RefreshOrderUI.

ref = find_custom(mge, "RefreshOrderUI")
apply = find_custom(mge, "ApplyOrderUMG")
ens_ev = find_custom(mge, "EnsureOrderUI")

# Purge nodes we added in this RefreshOrderUI attempt that are only reachable from ref
# Safest: break ref.then, build: Ensure -> ApplyOrderUMG call only.
# Table-side will fill OrderLine1/2.

if ref:
    tp = find_pin(ref, "then", "Output")
    if tp:
        # disconnect everything
        try:
            tp.break_pin_links()
        except Exception:
            pass

call_ens2 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
bel.set_node_pos(call_ens2, pos(-3000, 5700))
connect(find_pin(ref, "then", "Output"), find_pin(call_ens2, "execute", "Input"), "ref->ens2")

# Build ApplyOrderUMG body first, compile, then call it
if apply is None:
    apply = mge.add_custom_event_node("ApplyOrderUMG")
    bel.set_node_pos(apply, pos(-3000, 6600))

# Clear apply chain
for n in walk_then(apply, 50):
    for p in bel.list_all_pins(n):
        try:
            p.break_pin_links()
        except Exception:
            pass
# remove disconnected call nodes near apply — skip mass delete to avoid collateral

athen = find_pin(apply, "then", "Output")
if athen:
    try:
        athen.break_pin_links()
    except Exception:
        pass

# ApplyOrderUMG:
# Get OrderListWidget -> IsValid -> Cast WBP -> UpdateOrders(OrderLine1, OrderLine2)
# Visibility: (bIsOpenBusiness || OrderLine1!="" || OrderLine2!="")

get_w = mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_w, pos(-2700, 6600))
isv = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
bel.set_node_pos(isv, pos(-2500, 6680))
connect(out_data(get_w), find_pin(isv, "Object", "Input") or find_pin(isv, "Object", "Input"), "w->isv")
br_w = mge.add_branch_node()
bel.set_node_pos(br_w, pos(-2300, 6600))
connect(find_pin(apply, "then", "Output"), find_pin(br_w, "execute", "Input"), "apply->br")
connect(out_data(isv), find_pin(br_w, "Condition", "Input"), "isv")

cast_w = mge.add_cast_node(wbp_cls)
bel.set_node_pos(cast_w, pos(-2000, 6600))
connect(find_pin(br_w, "then", "Output"), find_pin(cast_w, "execute", "Input"), "br->castw")
connect(out_data(get_w), find_pin(cast_w, "Object", "Input"), "w->cast")

get_l1 = mge.add_get_member_variable_node("OrderLine1")
bel.set_node_pos(get_l1, pos(-2000, 6800))
get_l2 = mge.add_get_member_variable_node("OrderLine2")
bel.set_node_pos(get_l2, pos(-2000, 6900))

# Need compile before UpdateOrders is callable — compile WBP already done
bel.compile_blueprint(wbp)
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
# re-acquire key nodes by title near positions is hard; find apply again and rebuild if lost

apply = find_custom(mge, "ApplyOrderUMG")
ref = find_custom(mge, "RefreshOrderUI")
log("reacquire apply=" + str(apply is not None) + " ref=" + str(ref is not None))

# Find cast_w in apply chain if exists
chain = walk_then(apply, 30) if apply else []
log("apply chain now: " + " -> ".join(title(n) for n in chain))

# If ApplyOrderUMG body incomplete, rebuild completely
need_rebuild_apply = not any("UpdateOrders" in title(n) for n in chain)
if need_rebuild_apply and apply:
    # Break and rebuild cleanly
    athen = find_pin(apply, "then", "Output")
    if athen:
        athen.break_pin_links()
    get_w = mge.add_get_member_variable_node("OrderListWidget")
    bel.set_node_pos(get_w, pos(-2700, 6600))
    isv = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(isv, pos(-2450, 6700))
    connect(out_data(get_w), find_pin(isv, "Object", "Input"), "w isv")
    br_w = mge.add_branch_node()
    bel.set_node_pos(br_w, pos(-2200, 6600))
    connect(find_pin(apply, "then", "Output"), find_pin(br_w, "execute", "Input"), "a->br")
    connect(out_data(isv), find_pin(br_w, "Condition", "Input"), "isvc")

    cast_w = mge.add_cast_node(unreal.load_asset(WBP).generated_class())
    bel.set_node_pos(cast_w, pos(-1900, 6600))
    connect(find_pin(br_w, "then", "Output"), find_pin(cast_w, "execute", "Input"), "br->cw")
    connect(out_data(get_w), find_pin(cast_w, "Object", "Input"), "wobj")

    get_l1 = mge.add_get_member_variable_node("OrderLine1")
    bel.set_node_pos(get_l1, pos(-1900, 6780))
    get_l2 = mge.add_get_member_variable_node("OrderLine2")
    bel.set_node_pos(get_l2, pos(-1900, 6880))

    call_upd = mge.add_call_function_node("/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C:UpdateOrders")
    bel.set_node_pos(call_upd, pos(-1500, 6600))
    cast_then = find_pin(cast_w, "then", "Output")
    connect(cast_then, find_pin(call_upd, "execute", "Input"), "cw->upd")
    # self = cast output
    cast_out = None
    for p in bel.list_all_pins(cast_w):
        if "OUTPUT" in str(p.get_pin_direction()) and "Object" in str(p.get_pin_type_display_string()):
            cast_out = p
            break
    connect(cast_out or out_data(cast_w), find_pin(call_upd, "self", "Input"), "upd self")
    connect(out_data(get_l1), find_pin(call_upd, "Line1", "Input") or find_pin(call_upd, "Line 1", "Input"), "upd L1")
    connect(out_data(get_l2), find_pin(call_upd, "Line2", "Input") or find_pin(call_upd, "Line 2", "Input"), "upd L2")

    # Visibility after UpdateOrders
    get_open = mge.add_get_member_variable_node("bIsOpenBusiness")
    bel.set_node_pos(get_open, pos(-1500, 7000))
    ne1 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
    bel.set_node_pos(ne1, pos(-1200, 7100))
    connect(out_data(get_l1), find_pin(ne1, "A", "Input"), "ne1A")
    setdef(find_pin(ne1, "B", "Input"), "")
    ne2 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
    bel.set_node_pos(ne2, pos(-1200, 7200))
    connect(out_data(get_l2), find_pin(ne2, "A", "Input"), "ne2A")
    setdef(find_pin(ne2, "B", "Input"), "")
    or1 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    bel.set_node_pos(or1, pos(-900, 7050))
    connect(out_data(get_open), find_pin(or1, "A", "Input"), "orA")
    connect(out_data(ne1), find_pin(or1, "B", "Input"), "orB")
    or2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    bel.set_node_pos(or2, pos(-650, 7050))
    connect(out_data(or1), find_pin(or2, "A", "Input"), "or2A")
    connect(out_data(ne2), find_pin(or2, "B", "Input"), "or2B")

    br_vis = mge.add_branch_node()
    bel.set_node_pos(br_vis, pos(-400, 6600))
    connect(find_pin(call_upd, "then", "Output"), find_pin(br_vis, "execute", "Input"), "upd->vis")
    connect(out_data(or2), find_pin(br_vis, "Condition", "Input"), "viscond")

    vis_show = mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
    bel.set_node_pos(vis_show, pos(-100, 6500))
    vis_hide = mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
    bel.set_node_pos(vis_hide, pos(-100, 6750))
    connect(cast_out or out_data(cast_w), find_pin(vis_show, "self", "Input"), "show self")
    connect(cast_out or out_data(cast_w), find_pin(vis_hide, "self", "Input"), "hide self")
    setdef(find_pin(vis_show, "InVisibility", "Input") or find_pin(vis_show, "Visibility", "Input"), "Visible")
    setdef(find_pin(vis_hide, "InVisibility", "Input") or find_pin(vis_hide, "Visibility", "Input"), "Collapsed")
    connect(find_pin(br_vis, "then", "Output"), find_pin(vis_show, "execute", "Input"), "show")
    connect(find_pin(br_vis, "else", "Output"), find_pin(vis_hide, "execute", "Input"), "hide")

    # Optional debug print gated
    get_dbg = mge.add_get_member_variable_node("bOrderDebugPrint")
    bel.set_node_pos(get_dbg, pos(-100, 7000))
    br_dbg = mge.add_branch_node()
    bel.set_node_pos(br_dbg, pos(200, 6500))
    connect(find_pin(vis_show, "then", "Output"), find_pin(br_dbg, "execute", "Input"), "show->dbg")
    connect(find_pin(vis_hide, "then", "Output"), find_pin(br_dbg, "execute", "Input"), "hide->dbg")
    connect(out_data(get_dbg), find_pin(br_dbg, "Condition", "Input"), "dbg")
    pr = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(500, 6450))
    setdef(find_pin(pr, "InString", "Input"), "\u8ba2\u5355")
    setdef(find_pin(pr, "Duration", "Input"), "0.0")
    setdef(find_pin(pr, "Key", "Input"), "RestOrderHeader")
    setdef(find_pin(pr, "bPrintToScreen", "Input"), "true")
    connect(find_pin(br_dbg, "then", "Output"), find_pin(pr, "execute", "Input"), "dbgprint")
    # Append lines into print for debug
    apd = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(apd, pos(350, 6580))
    setdef(find_pin(apd, "A", "Input"), "\u8ba2\u5355\n")
    connect(out_data(get_l1), find_pin(apd, "B", "Input"), "apd1")
    apd2 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(apd2, pos(350, 6680))
    connect(out_data(apd), find_pin(apd2, "A", "Input"), "apd2a")
    # newline + line2
    apd2b = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(apd2b, pos(350, 6780))
    connect(out_data(apd), find_pin(apd2b, "A", "Input"), "x")
    setdef(find_pin(apd2, "B", "Input"), "\n")
    # simplify: just connect get_l1 to print for now
    connect(out_data(get_l1), find_pin(pr, "InString", "Input"), "pr str")

    log("ApplyOrderUMG rebuilt")

bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ref = find_custom(mge, "RefreshOrderUI")
apply = find_custom(mge, "ApplyOrderUMG")

# RefreshOrderUI: EnsureOrderUI -> ApplyOrderUMG
if ref:
    tp = find_pin(ref, "then", "Output")
    if tp:
        tp.break_pin_links()
    call_ens3 = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens3, pos(-3000, 5700))
    connect(find_pin(ref, "then", "Output"), find_pin(call_ens3, "execute", "Input"), "r->e")
    call_app = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplyOrderUMG")
    bel.set_node_pos(call_app, pos(-2600, 5700))
    connect(find_pin(call_ens3, "then", "Output"), find_pin(call_app, "execute", "Input"), "e->a")
    log("RefreshOrderUI -> Ensure -> ApplyOrderUMG")

bel.compile_blueprint(mbp)

# =============================================================================
# 3) Table: after order PrintString, also SetOrderLine; disable screen print by default
# =============================================================================
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
refb = find_custom(tge, "RefreshTableBubble")

# Find PrintString nodes with RestOrder key in bubble chain and:
# - set bPrintToScreen false (UMG primary)
# - after them, GetActorOfClass Manager -> SetOrderLine(TableId, InString)

def find_print_restorder(ge):
    found = []
    for n in ge.list_all_nodes():
        if title(n) != "PrintString":
            continue
        keyp = find_pin(n, "Key", "Input")
        # Key may be linked to Concat RestOrder+id
        linked = False
        if keyp:
            for c in keyp.list_connected_pins() or []:
                own = c.get_owning_node()
                # check if related to RestOrder concat — inspect defaults on Concat A
                if "Concat" in title(own) or "Append" in title(own):
                    ap = find_pin(own, "A", "Input")
                    try:
                        val = ap.get_default_value() if ap else ""
                    except Exception:
                        val = ""
                    if "RestOrder" in str(val):
                        linked = True
            try:
                kv = keyp.get_default_value()
            except Exception:
                kv = ""
            if "RestOrder" in str(kv):
                linked = True
        # Also match by InString linked to Append with 桌
        insp = find_pin(n, "InString", "Input")
        if insp and list(insp.list_connected_pins() or []):
            # likely our strip print
            if linked or True:
                # Heuristic: Duration 0.0 and has Key link
                dur = find_pin(n, "Duration", "Input")
                try:
                    dval = dur.get_default_value() if dur else ""
                except Exception:
                    dval = ""
                if linked or str(dval) in ("0.0", "0", "0.00"):
                    if linked:
                        found.append(n)
    return found


prints = find_print_restorder(tge)
log("RestOrder prints found=" + str(len(prints)))

# Broader: in RefreshTableBubble walk, all PrintString
if refb:
    for n in walk_then(refb, 50):
        if title(n) == "PrintString":
            if n not in prints:
                # check key link
                keyp = find_pin(n, "Key", "Input")
                has_key_link = keyp and list(keyp.list_connected_pins() or [])
                if has_key_link:
                    prints.append(n)
log("prints total=" + str(len(prints)))

for prn in prints:
    setdef(find_pin(prn, "bPrintToScreen", "Input"), "false")
    log("disabled screen print on " + title(prn))

# Add helper custom PushOrderLineUMG on table: takes no params, builds line like bubble and SetOrderLine
# Simpler: for each RestOrder PrintString, splice after then: GetActorOfClass -> Cast Manager -> SetOrderLine(TableId, same InString)

bel.compile_blueprint(mbp)  # ensure SetOrderLine callable
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
mgr_cls = unreal.load_asset(MGR).generated_class()

# Re-find prints
prints = []
refb = find_custom(tge, "RefreshTableBubble")
if refb:
    for n in walk_then(refb, 60):
        if title(n) == "PrintString":
            keyp = find_pin(n, "Key", "Input")
            if keyp and list(keyp.list_connected_pins() or []):
                prints.append(n)
                setdef(find_pin(n, "bPrintToScreen", "Input"), "false")

log("wiring SetOrderLine after {} prints".format(len(prints)))

for i, prn in enumerate(prints):
    thenp = find_pin(prn, "then", "Output")
    # capture existing then targets
    old_tgts = []
    if thenp:
        old_tgts = list(thenp.list_connected_pins() or [])
        try:
            thenp.break_pin_links()
        except Exception:
            pass

    get_act = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
    bel.set_node_pos(get_act, pos(2000 + i * 50, 5200 + i * 350))
    setdef(find_pin(get_act, "ActorClass", "Input"), "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    connect(thenp, find_pin(get_act, "execute", "Input"), "pr->get")

    cast_m = tge.add_cast_node(mgr_cls)
    bel.set_node_pos(cast_m, pos(2300 + i * 50, 5200 + i * 350))
    connect(find_pin(get_act, "then", "Output"), find_pin(cast_m, "execute", "Input"), "get->cast")
    connect(out_data(get_act), find_pin(cast_m, "Object", "Input"), "act->cast")

    get_tid = tge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid, pos(2300 + i * 50, 5400 + i * 350))

    call_set = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_set, pos(2700 + i * 50, 5200 + i * 350))
    connect(find_pin(cast_m, "then", "Output"), find_pin(call_set, "execute", "Input"), "cast->set")
    cast_out = None
    for p in bel.list_all_pins(cast_m):
        if "OUTPUT" in str(p.get_pin_direction()) and "Object" in str(p.get_pin_type_display_string()):
            cast_out = p
            break
    connect(cast_out or out_data(cast_m), find_pin(call_set, "self", "Input"), "set self")
    connect(out_data(get_tid), find_pin(call_set, "TableId", "Input"), "set tid")
    # Line = same as Print InString input source
    insp = find_pin(prn, "InString", "Input")
    src = None
    if insp:
        links = list(insp.list_connected_pins() or [])
        if links:
            src = links[0]
    if src:
        connect(src, find_pin(call_set, "Line", "Input"), "set line")
    else:
        setdef(find_pin(call_set, "Line", "Input"), "")

    # restore old then targets after SetOrderLine
    set_then = find_pin(call_set, "then", "Output")
    for tgt in old_tgts:
        connect(set_then, tgt, "restore then")

    # Also on cast fail restore
    fail = find_pin(cast_m, "CastFailed", "Output")
    if fail and old_tgts:
        for tgt in old_tgts:
            connect(fail, tgt, "fail restore")

# Clear line when not occupied: find first Branch on bOccupied in RefreshTableBubble else path
if refb:
    # Find Branch whose condition is bOccupied
    for n in walk_then(refb, 20):
        if n.get_class().get_name() != "K2Node_IfThenElse":
            continue
        cond = find_pin(n, "Condition", "Input")
        links = list(cond.list_connected_pins() or []) if cond else []
        from_occ = False
        for c in links:
            if "bOccupied" in title(c.get_owning_node()):
                from_occ = True
        if not from_occ:
            continue
        elsep = find_pin(n, "else", "Output")
        # If else empty or only goes to non-clear, splice clear
        old_else = list(elsep.list_connected_pins() or []) if elsep else []
        get_act = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
        bel.set_node_pos(get_act, pos(-400, 5800))
        setdef(find_pin(get_act, "ActorClass", "Input"), "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
        if elsep:
            try:
                elsep.break_pin_links()
            except Exception:
                pass
            connect(elsep, find_pin(get_act, "execute", "Input"), "empty->get")
        cast_m = tge.add_cast_node(mgr_cls)
        bel.set_node_pos(cast_m, pos(-100, 5800))
        connect(find_pin(get_act, "then", "Output"), find_pin(cast_m, "execute", "Input"), "g->c")
        connect(out_data(get_act), find_pin(cast_m, "Object", "Input"), "a->c")
        get_tid = tge.add_get_member_variable_node("TableId")
        bel.set_node_pos(get_tid, pos(-100, 6000))
        call_set = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
        bel.set_node_pos(call_set, pos(300, 5800))
        connect(find_pin(cast_m, "then", "Output"), find_pin(call_set, "execute", "Input"), "c->s")
        cast_out = None
        for p in bel.list_all_pins(cast_m):
            if "OUTPUT" in str(p.get_pin_direction()) and "Object" in str(p.get_pin_type_display_string()):
                cast_out = p
                break
        connect(cast_out or out_data(cast_m), find_pin(call_set, "self", "Input"), "ss")
        connect(out_data(get_tid), find_pin(call_set, "TableId", "Input"), "st")
        setdef(find_pin(call_set, "Line", "Input"), "")
        # restore old else
        for tgt in old_else:
            connect(find_pin(call_set, "then", "Output"), tgt, "else restore")
        log("wired clear OrderLine on unoccupied else")
        break

# Also handle 用餐中: if bubble print doesn't include it, OrderLine from print may still show patience during eat.
# Optional enhancement: skip for this batch if prints already updated by open_eat_ui batch.
# Check farm_dn_rest_open_eat for 用餐中 in bubble — parent said 用餐中 was added to side strip Print.

bel.compile_blueprint(tbp)
bel.compile_blueprint(mbp)
bel.compile_blueprint(wbp)

# Final error sweep
final = {}
for path, ge_name in ((WBP, "wbp"), (MGR, "mgr"), (TBL, "tbl")):
    bp = unreal.load_asset(path)
    bel.compile_blueprint(bp)
    st = status_of(bp)
    errs = []
    try:
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
        for n in (ge.list_nodes_with_errors() or []):
            msg = ""
            try:
                msg = str(n.get_editor_property("error_msg"))[:160]
            except Exception:
                pass
            errs.append({"title": title(n), "msg": msg})
    except Exception as e:
        errs.append({"title": "ge", "msg": str(e)})
    # function graphs
    for fname in ("UpdateOrders", "SetOrderLine", "ApplyOrderUMG"):
        try:
            g = bel.find_graph(bp, fname)
            if g:
                fge = unreal.BlueprintGraphEditor.get_graph_editor(g)
                for n in (fge.list_nodes_with_errors() or []):
                    errs.append({"title": fname + ":" + title(n), "msg": ""})
        except Exception:
            pass
    final[ge_name] = {"status": st, "errs": errs}
    log("FINAL {} {} errs={}".format(ge_name, st, errs))
    eas.save_asset(path)

REPORT["final"] = final

# Dump chains
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(unreal.load_asset(MGR)))
for name, key in (("RefreshOrderUI", "refresh"), ("ApplyOrderUMG", "apply"), ("EnsureOrderUI", "ensure")):
    ev = find_custom(mge, name)
    REPORT[key] = [title(n) for n in walk_then(ev, 40)] if ev else []
    log(key + ": " + " -> ".join(REPORT[key][:25]))

widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o.get_class().get_name()
REPORT["widgets_final"] = widgets

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
out = unreal.Paths.project_saved_dir() + "rest_umg_orders_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
log("WROTE " + out)
print("DONE_UMG_ORDERS")