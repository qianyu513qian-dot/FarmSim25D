# -*- coding: utf-8 -*-
"""Fix UMG order strip after partial farm_dn_rest_umg_orders run."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
WBP = "/Game/Farm/UI/WBP_RestOrderList"
FONT = "/Game/Farm/Restaurant/Font_SimHei_TR"
REPORT = {"steps": []}

def log(m):
    unreal.log("[UMGFIX] " + str(m)); print("[UMGFIX] " + str(m)); REPORT["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name() if n else "?"

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
    for name in ("ReturnValue", "Return Value", "OrderListWidget", "OrderLine1", "OrderLine2",
                 "bIsOpenBusiness", "TableId", "Line1", "Line2", "AsBP Restaurant Manager",
                 "AsWBP RestOrderList", "TxtTitle", "TxtLine1", "TxtLine2"):
        p = find_pin(node, name, "Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n = str(p.get_pin_name()).lower()
            if n not in ("outputdelegate", "then", "else", "completed", "loopbody", "castfailed"):
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok)); return ok

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

def status_of(bp):
    try: return str(bp.get_editor_property("status"))
    except Exception as e: return str(e)

def make_obj_pin(class_path):
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="object",PinSubCategory="",PinSubCategoryObject="{}")'.format(class_path))
    return p

def add_cast(ge, class_bp_name):
    """Create DynamicCast via create_node_from_name Utilities|Casting|CastToX."""
    # Try several name forms
    candidates = [
        "Utilities|Casting|CastTo" + class_bp_name,
        "Utilities|Casting|Cast To " + class_bp_name,
        "CastTo" + class_bp_name,
        "Cast To " + class_bp_name,
    ]
    for cname in candidates:
        try:
            n = ge.create_node_from_name(cname, unreal.Vector2D(0, 0), [])
            if n:
                log("cast created via " + cname)
                return n
        except Exception as e:
            log("cast try {} {}".format(cname, e)[:100])
    return None

# =============================================================================
# A) Fix WBP UpdateOrders
# =============================================================================
wbp = unreal.load_asset(WBP)
# Ensure Tick stays disconnected
wge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))
tick = find_event(wge, "Tick")
if tick:
    tp = find_pin(tick, "then", "Output")
    if tp and list(tp.list_connected_pins() or []):
        tp.break_pin_links(); log("re-broke Tick")

# Compile so renamed widgets become variables
bel.compile_blueprint(wbp)
log("WBP after rename compile=" + status_of(wbp))

# Apply font/text
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o
font_cjk = unreal.load_asset(FONT)
for name, text, size in (("TxtTitle", "\u8ba2\u5355", 22), ("TxtLine1", "", 18), ("TxtLine2", "", 18)):
    tb = widgets.get(name)
    if not tb:
        log("MISSING widget " + name); continue
    try: tb.set_text(text)
    except Exception:
        try: tb.set_editor_property("text", text)
        except Exception as e: log(str(e))
    try:
        fi = tb.get_editor_property("font")
        fi.set_editor_property("size", float(size))
        if font_cjk:
            fi.set_editor_property("font_object", font_cjk)
        tb.set_editor_property("font", fi)
        tb.set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
    except Exception as e:
        log("font " + str(e)[:80])
for name in ("TxtSeeds", "TxtHarvest", "TxtClock", "TxtStamina", "TxtControls", "BarStamina", "BarPatience1", "BarPatience2"):
    if name in widgets:
        try: widgets[name].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        except Exception: pass

# Rebuild UpdateOrders cleanly
try:
    if bel.find_graph(wbp, "UpdateOrders"):
        bel.remove_function_graph(wbp, "UpdateOrders")
        log("removed UpdateOrders")
except Exception as e:
    log(str(e))
bel.compile_blueprint(wbp)
bel.add_function_graph(wbp, "UpdateOrders")
ugraph = bel.find_graph(wbp, "UpdateOrders")
uge = unreal.BlueprintGraphEditor.get_graph_editor(ugraph)
entry = None
to_del = []
for n in uge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
    else:
        to_del.append(n)
if to_del: uge.remove_nodes(to_del)
str_pin = bel.get_basic_type_by_name("string")
if find_pin(entry, "Line1", "Output") is None:
    uge.add_graph_input_parameter("Line1", str_pin)
if find_pin(entry, "Line2", "Output") is None:
    uge.add_graph_input_parameter("Line2", str_pin)
for n in uge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n
bel.set_node_pos(entry, pos(0, 0))

get_title = uge.add_get_member_variable_node("TxtTitle")
get_l1 = uge.add_get_member_variable_node("TxtLine1")
get_l2 = uge.add_get_member_variable_node("TxtLine2")
bel.set_node_pos(get_title, pos(250, -60))
bel.set_node_pos(get_l1, pos(250, 80))
bel.set_node_pos(get_l2, pos(250, 220))
log("get_title pins=" + str([(str(p.get_pin_name()), str(p.get_pin_type_display_string())) for p in bel.list_all_pins(get_title)]))
log("get_l1 pins=" + str([(str(p.get_pin_name()), str(p.get_pin_type_display_string())) for p in bel.list_all_pins(get_l1)]))

conv_t = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv_t, pos(520, -40))
setdef(find_pin(conv_t, "InString", "Input"), "\u8ba2\u5355")
conv1 = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv1, pos(520, 80))
connect(find_pin(entry, "Line1", "Output"), find_pin(conv1, "InString", "Input"), "L1")
conv2 = uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText")
bel.set_node_pos(conv2, pos(520, 220))
connect(find_pin(entry, "Line2", "Output"), find_pin(conv2, "InString", "Input"), "L2")

set_t = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
set_1 = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
set_2 = uge.add_call_function_node("/Script/UMG.TextBlock:SetText")
bel.set_node_pos(set_t, pos(820, -60))
bel.set_node_pos(set_1, pos(820, 80))
bel.set_node_pos(set_2, pos(820, 220))

connect(find_pin(entry, "then", "Output"), find_pin(set_t, "execute", "Input"), "e->t")
connect(out_data(get_title), find_pin(set_t, "self", "Input"), "t self")
connect(out_data(conv_t), find_pin(set_t, "InText", "Input"), "t txt")
connect(find_pin(set_t, "then", "Output"), find_pin(set_1, "execute", "Input"), "t->1")
connect(out_data(get_l1), find_pin(set_1, "self", "Input"), "1 self")
connect(out_data(conv1), find_pin(set_1, "InText", "Input"), "1 txt")
connect(find_pin(set_1, "then", "Output"), find_pin(set_2, "execute", "Input"), "1->2")
connect(out_data(get_l2), find_pin(set_2, "self", "Input"), "2 self")
connect(out_data(conv2), find_pin(set_2, "InText", "Input"), "2 txt")

# visibility Line1/2
def wire_line_vis(uge, prev_then, get_node, line_pin_name, entry, y):
    eq = uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr")
    bel.set_node_pos(eq, pos(1100, y))
    connect(find_pin(entry, line_pin_name, "Output"), find_pin(eq, "A", "Input"), line_pin_name + "eqA")
    setdef(find_pin(eq, "B", "Input"), "")
    br = uge.add_branch_node(); bel.set_node_pos(br, pos(1350, y))
    connect(prev_then, find_pin(br, "execute", "Input"), "prev->br")
    connect(out_data(eq), find_pin(br, "Condition", "Input"), "eq")
    hide = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
    show = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
    bel.set_node_pos(hide, pos(1600, y - 60)); bel.set_node_pos(show, pos(1600, y + 60))
    connect(out_data(get_node), find_pin(hide, "self", "Input"), "hself")
    connect(out_data(get_node), find_pin(show, "self", "Input"), "sself")
    setdef(find_pin(hide, "InVisibility", "Input"), "Collapsed")
    setdef(find_pin(show, "InVisibility", "Input"), "Visible")
    connect(find_pin(br, "then", "Output"), find_pin(hide, "execute", "Input"), "hide")
    connect(find_pin(br, "else", "Output"), find_pin(show, "execute", "Input"), "show")
    return find_pin(hide, "then", "Output"), find_pin(show, "then", "Output")

h1, s1 = wire_line_vis(uge, find_pin(set_2, "then", "Output"), get_l1, "Line1", entry, 80)
# merge h1/s1 into line2 vis
eq2 = uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr")
bel.set_node_pos(eq2, pos(1850, 200))
connect(find_pin(entry, "Line2", "Output"), find_pin(eq2, "A", "Input"), "L2eq")
setdef(find_pin(eq2, "B", "Input"), "")
br2 = uge.add_branch_node(); bel.set_node_pos(br2, pos(2100, 200))
connect(h1, find_pin(br2, "execute", "Input"), "h1->br2")
connect(s1, find_pin(br2, "execute", "Input"), "s1->br2")
connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "eq2")
hide2 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
show2 = uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(hide2, pos(2350, 140)); bel.set_node_pos(show2, pos(2350, 260))
connect(out_data(get_l2), find_pin(hide2, "self", "Input"), "h2")
connect(out_data(get_l2), find_pin(show2, "self", "Input"), "s2")
setdef(find_pin(hide2, "InVisibility", "Input"), "Collapsed")
setdef(find_pin(show2, "InVisibility", "Input"), "Visible")
connect(find_pin(br2, "then", "Output"), find_pin(hide2, "execute", "Input"), "hide2")
connect(find_pin(br2, "else", "Output"), find_pin(show2, "execute", "Input"), "show2")

bel.compile_blueprint(wbp)
werrs = []
for n in (uge.list_nodes_with_errors() or []):
    werrs.append(title(n))
for n in (wge.list_nodes_with_errors() or []):
    werrs.append(title(n))
REPORT["wbp_errs"] = werrs
log("WBP status={} errs={}".format(status_of(wbp), werrs))
eas.save_asset(WBP)

# =============================================================================
# B) Manager: retype OrderListWidget, rebuild RefreshOrderUI -> Ensure -> ApplyOrderUMG
# =============================================================================
mbp = unreal.load_asset(MGR)
# ensure vars
for name, t in (("OrderLine1", "string"), ("OrderLine2", "string"), ("bOrderDebugPrint", "bool")):
    names = [str(x) for x in bel.list_member_variable_names(mbp, False)]
    if name not in names:
        bel.add_member_variable(mbp, name, bel.get_basic_type_by_name(t))
        log("add " + name)

# Retype OrderListWidget to WBP_RestOrderList_C
try:
    bel.change_member_variable_type(mbp, "OrderListWidget", make_obj_pin("/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C"))
    log("retyped OrderListWidget -> WBP_RestOrderList_C")
except Exception as e:
    log("retype " + str(e))

# Ensure SetOrderLine exists (from partial run)
if not bel.find_graph(mbp, "SetOrderLine"):
    bel.add_function_graph(mbp, "SetOrderLine")
    sge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "SetOrderLine"))
    sentry = None
    for n in sge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            sentry = n
    if find_pin(sentry, "TableId", "Output") is None:
        sge.add_graph_input_parameter("TableId", bel.get_basic_type_by_name("int"))
    if find_pin(sentry, "Line", "Output") is None:
        sge.add_graph_input_parameter("Line", bel.get_basic_type_by_name("string"))
    for n in sge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            sentry = n
    eq1 = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    connect(find_pin(sentry, "TableId", "Output"), find_pin(eq1, "A", "Input"), "tid")
    setdef(find_pin(eq1, "B", "Input"), "1")
    br = sge.add_branch_node()
    connect(find_pin(sentry, "then", "Output"), find_pin(br, "execute", "Input"), "e")
    connect(out_data(eq1), find_pin(br, "Condition", "Input"), "c")
    set1 = sge.add_set_member_variable_node("OrderLine1")
    set2 = sge.add_set_member_variable_node("OrderLine2")
    connect(find_pin(br, "then", "Output"), find_pin(set1, "execute", "Input"), "t1")
    connect(find_pin(br, "else", "Output"), find_pin(set2, "execute", "Input"), "t2")
    connect(find_pin(sentry, "Line", "Output"), find_pin(set1, "OrderLine1", "Input"), "L1")
    connect(find_pin(sentry, "Line", "Output"), find_pin(set2, "OrderLine2", "Input"), "L2")
    log("created SetOrderLine")

bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Purge disconnected orphans from failed GetAllActors attempt (no exec in)
def purge_orphans(ge, keep_titles):
    kill = []
    for n in list(ge.list_all_nodes()):
        cls = n.get_class().get_name()
        if cls in ("K2Node_CustomEvent", "K2Node_Event", "K2Node_FunctionEntry", "K2Node_Knot"):
            continue
        t = title(n)
        if t in keep_titles:
            continue
        # has exec input?
        exe = find_pin(n, "execute", "Input")
        if exe is not None:
            if not list(exe.list_connected_pins() or []):
                # also skip if it's a pure node wrongly detected
                kill.append(n)
    # only kill clearly our leftovers
    real_kill = []
    for n in kill:
        t = title(n)
        if any(k in t for k in ("GetAllActors", "Array_Get", "Set OrderLine", "Concat", "Conv_", "Branch",
                                 "Equal", "EqualEqual", "SetOrderLine", "ApplyOrderUMG", "EnsureOrderUI",
                                 "PrintString", "IsValid", "SetVisibility", "UpdateOrders", "GetActorOfClass",
                                 "CastTo", "Cast To", "BooleanOR", "NotEqual", "NotEqual_StrStr")):
            # Don't kill EnsureOrderUI call if it's in BeginPlay chain
            real_kill.append(n)
    # safer: only kill GetAllActors / Array_Get / orphan Set OrderLine from refresh X range
    safer = []
    for n in kill:
        t = title(n)
        if "GetAllActors" in t or "Array_Get" in t or t.startswith("CastTo"):
            safer.append(n)
    if safer:
        ge.remove_nodes(safer)
        log("purged orphans " + str([title(n) for n in safer]))

purge_orphans(mge, set())

# Rebuild ApplyOrderUMG
apply = find_custom(mge, "ApplyOrderUMG")
if apply is None:
    apply = mge.add_custom_event_node("ApplyOrderUMG")
    bel.set_node_pos(apply, pos(-3000, 6600))
    log("created ApplyOrderUMG")
else:
    # break then
    tp = find_pin(apply, "then", "Output")
    if tp: tp.break_pin_links()

# Remove nodes that were only in old apply chain - skip aggressive

get_w = mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_w, pos(-2700, 6600))
isv = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
bel.set_node_pos(isv, pos(-2450, 6700))
connect(out_data(get_w), find_pin(isv, "Object", "Input"), "isv")
br = mge.add_branch_node(); bel.set_node_pos(br, pos(-2200, 6600))
connect(find_pin(apply, "then", "Output"), find_pin(br, "execute", "Input"), "a->br")
connect(out_data(isv), find_pin(br, "Condition", "Input"), "isc")

get_l1 = mge.add_get_member_variable_node("OrderLine1")
get_l2 = mge.add_get_member_variable_node("OrderLine2")
bel.set_node_pos(get_l1, pos(-2200, 6780)); bel.set_node_pos(get_l2, pos(-2200, 6880))

bel.compile_blueprint(wbp)
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
apply = find_custom(mge, "ApplyOrderUMG")

# Re-find the branch we just added by walking apply
chain = walk_then(apply, 15)
log("apply mid chain=" + str([title(n) for n in chain]))
# If broken mid-compile, rebuild from scratch more carefully in one go without mid compile

# Find Branch in chain
br = None
for n in chain:
    if n.get_class().get_name() == "K2Node_IfThenElse":
        br = n; break

if br is None:
    # full rebuild
    tp = find_pin(apply, "then", "Output")
    if tp: tp.break_pin_links()
    get_w = mge.add_get_member_variable_node("OrderListWidget")
    bel.set_node_pos(get_w, pos(-2700, 6600))
    isv = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid")
    bel.set_node_pos(isv, pos(-2450, 6700))
    connect(out_data(get_w), find_pin(isv, "Object", "Input"), "isv2")
    br = mge.add_branch_node(); bel.set_node_pos(br, pos(-2200, 6600))
    connect(find_pin(apply, "then", "Output"), find_pin(br, "execute", "Input"), "a->br2")
    connect(out_data(isv), find_pin(br, "Condition", "Input"), "isc2")
    get_l1 = mge.add_get_member_variable_node("OrderLine1")
    get_l2 = mge.add_get_member_variable_node("OrderLine2")
    bel.set_node_pos(get_l1, pos(-2200, 6780)); bel.set_node_pos(get_l2, pos(-2200, 6880))

call_upd = mge.add_call_function_node("/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C:UpdateOrders")
bel.set_node_pos(call_upd, pos(-1800, 6600))
connect(find_pin(br, "then", "Output"), find_pin(call_upd, "execute", "Input"), "br->upd")
# self = OrderListWidget (now typed as WBP)
# find get_w in chain or recreate link from IsValid's object source
# Get OrderListWidget again for self
get_w2 = mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_w2, pos(-2000, 6500))
connect(out_data(get_w2), find_pin(call_upd, "self", "Input"), "upd self")
connect(out_data(get_l1) if get_l1 else out_data(mge.add_get_member_variable_node("OrderLine1")),
        find_pin(call_upd, "Line1", "Input"), "upd L1")
connect(out_data(get_l2) if get_l2 else out_data(mge.add_get_member_variable_node("OrderLine2")),
        find_pin(call_upd, "Line2", "Input"), "upd L2")

# visibility
get_open = mge.add_get_member_variable_node("bIsOpenBusiness")
bel.set_node_pos(get_open, pos(-1800, 7000))
ne1 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
ne2 = mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
bel.set_node_pos(ne1, pos(-1500, 7100)); bel.set_node_pos(ne2, pos(-1500, 7200))
get_l1b = mge.add_get_member_variable_node("OrderLine1")
get_l2b = mge.add_get_member_variable_node("OrderLine2")
bel.set_node_pos(get_l1b, pos(-1800, 7100)); bel.set_node_pos(get_l2b, pos(-1800, 7200))
connect(out_data(get_l1b), find_pin(ne1, "A", "Input"), "ne1")
setdef(find_pin(ne1, "B", "Input"), "")
connect(out_data(get_l2b), find_pin(ne2, "A", "Input"), "ne2")
setdef(find_pin(ne2, "B", "Input"), "")
or1 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
or2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
bel.set_node_pos(or1, pos(-1200, 7050)); bel.set_node_pos(or2, pos(-950, 7050))
connect(out_data(get_open), find_pin(or1, "A", "Input"), "or1a")
connect(out_data(ne1), find_pin(or1, "B", "Input"), "or1b")
connect(out_data(or1), find_pin(or2, "A", "Input"), "or2a")
connect(out_data(ne2), find_pin(or2, "B", "Input"), "or2b")
br_vis = mge.add_branch_node(); bel.set_node_pos(br_vis, pos(-700, 6600))
connect(find_pin(call_upd, "then", "Output"), find_pin(br_vis, "execute", "Input"), "upd->vis")
connect(out_data(or2), find_pin(br_vis, "Condition", "Input"), "visc")
vis_show = mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
vis_hide = mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vis_show, pos(-400, 6500)); bel.set_node_pos(vis_hide, pos(-400, 6750))
get_w3 = mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_w3, pos(-700, 6500))
connect(out_data(get_w3), find_pin(vis_show, "self", "Input"), "show self")
connect(out_data(get_w3), find_pin(vis_hide, "self", "Input"), "hide self")
setdef(find_pin(vis_show, "InVisibility", "Input"), "Visible")
setdef(find_pin(vis_hide, "InVisibility", "Input"), "Collapsed")
connect(find_pin(br_vis, "then", "Output"), find_pin(vis_show, "execute", "Input"), "show")
connect(find_pin(br_vis, "else", "Output"), find_pin(vis_hide, "execute", "Input"), "hide")

# debug print optional
get_dbg = mge.add_get_member_variable_node("bOrderDebugPrint")
bel.set_node_pos(get_dbg, pos(-400, 7000))
br_dbg = mge.add_branch_node(); bel.set_node_pos(br_dbg, pos(-100, 6500))
connect(find_pin(vis_show, "then", "Output"), find_pin(br_dbg, "execute", "Input"), "s->d")
connect(find_pin(vis_hide, "then", "Output"), find_pin(br_dbg, "execute", "Input"), "h->d")
connect(out_data(get_dbg), find_pin(br_dbg, "Condition", "Input"), "dbg")
pr = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
bel.set_node_pos(pr, pos(200, 6450))
setdef(find_pin(pr, "InString", "Input"), "ORDER_DBG")
setdef(find_pin(pr, "Duration", "Input"), "0.0")
setdef(find_pin(pr, "Key", "Input"), "RestOrderHeader")
connect(find_pin(br_dbg, "then", "Output"), find_pin(pr, "execute", "Input"), "dbgprint")

# RefreshOrderUI: Ensure -> ApplyOrderUMG
ref = find_custom(mge, "RefreshOrderUI")
if ref is None:
    ref = mge.add_custom_event_node("RefreshOrderUI")
    bel.set_node_pos(ref, pos(-3200, 5700))
tp = find_pin(ref, "then", "Output")
if tp: tp.break_pin_links()
call_ens = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
bel.set_node_pos(call_ens, pos(-2900, 5700))
connect(find_pin(ref, "then", "Output"), find_pin(call_ens, "execute", "Input"), "r->e")
# compile so ApplyOrderUMG is callable
bel.compile_blueprint(mbp)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ref = find_custom(mge, "RefreshOrderUI")
# find Ensure call in chain
chain = walk_then(ref, 10)
log("refresh after ens wire=" + str([title(n) for n in chain]))
ens_call = None
for n in chain:
    if title(n) == "EnsureOrderUI":
        ens_call = n; break
if ens_call is None:
    ens_call = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(ens_call, pos(-2900, 5700))
    connect(find_pin(ref, "then", "Output"), find_pin(ens_call, "execute", "Input"), "r->e2")

call_app = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplyOrderUMG")
bel.set_node_pos(call_app, pos(-2500, 5700))
connect(find_pin(ens_call, "then", "Output"), find_pin(call_app, "execute", "Input"), "e->a")
log("RefreshOrderUI wired Ensure->Apply")

# Fix EnsureOrderUI Create Widget - OrderListWidget set should still work after retype
bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# =============================================================================
# C) Table: after RestOrder PrintString -> Cast Manager -> SetOrderLine
# =============================================================================
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
refb = find_custom(tge, "RefreshTableBubble")
prints = []
if refb:
    for n in walk_then(refb, 60):
        if title(n) != "PrintString":
            continue
        keyp = find_pin(n, "Key", "Input")
        if keyp and list(keyp.list_connected_pins() or []):
            prints.append(n)
            setdef(find_pin(n, "bPrintToScreen", "Input"), "false")
log("table RestOrder prints=" + str(len(prints)))

# Avoid double-wiring if already has GetActorOfClass after print
for i, prn in enumerate(prints):
    thenp = find_pin(prn, "then", "Output")
    already = False
    if thenp:
        for c in thenp.list_connected_pins() or []:
            if "GetActorOfClass" in title(c.get_owning_node()) or "SetOrderLine" in title(c.get_owning_node()):
                already = True
    if already:
        log("print {} already wired".format(i)); continue
    old_tgts = list(thenp.list_connected_pins() or []) if thenp else []
    if thenp:
        thenp.break_pin_links()
    get_act = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
    bel.set_node_pos(get_act, pos(2100, 5000 + i * 400))
    setdef(find_pin(get_act, "ActorClass", "Input"), "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
    connect(thenp, find_pin(get_act, "execute", "Input"), "pr->get")
    cast_m = add_cast(tge, "BP_RestaurantManager")
    if cast_m is None:
        log("NO CAST NODE - try list_available")
        # fallback: list_available from ReturnValue
        ret = find_pin(get_act, "ReturnValue", "Output")
        avail = tge.list_available_nodes([ret]) if ret else []
        name = None
        for a in avail:
            if a == "Utilities|Casting|CastToBP_RestaurantManager":
                name = a; break
        if name:
            cast_m = tge.create_node_from_name(name, unreal.Vector2D(2400, 5000 + i * 400), [])
            log("cast via avail " + str(cast_m is not None))
    if cast_m is None:
        log("FAILED cast; reconnect old"); 
        for tgt in old_tgts:
            connect(thenp, tgt, "restore")
        continue
    bel.set_node_pos(cast_m, pos(2400, 5000 + i * 400))
    connect(find_pin(get_act, "then", "Output"), find_pin(cast_m, "execute", "Input"), "g->c")
    connect(out_data(get_act), find_pin(cast_m, "Object", "Input"), "a->c")
    get_tid = tge.add_get_member_variable_node("TableId")
    bel.set_node_pos(get_tid, pos(2400, 5200 + i * 400))
    call_set = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
    bel.set_node_pos(call_set, pos(2800, 5000 + i * 400))
    connect(find_pin(cast_m, "then", "Output"), find_pin(call_set, "execute", "Input"), "c->s")
    connect(out_data(cast_m), find_pin(call_set, "self", "Input"), "s self")
    connect(out_data(get_tid), find_pin(call_set, "TableId", "Input"), "s tid")
    insp = find_pin(prn, "InString", "Input")
    if insp:
        links = list(insp.list_connected_pins() or [])
        if links:
            connect(links[0], find_pin(call_set, "Line", "Input"), "s line")
        else:
            setdef(find_pin(call_set, "Line", "Input"), "")
    for tgt in old_tgts:
        connect(find_pin(call_set, "then", "Output"), tgt, "restore")
    fail = find_pin(cast_m, "CastFailed", "Output")
    if fail:
        for tgt in old_tgts:
            connect(fail, tgt, "fail")
    log("wired SetOrderLine after print " + str(i))

# Clear on unoccupied else of first bOccupied branch
if refb:
    for n in walk_then(refb, 25):
        if n.get_class().get_name() != "K2Node_IfThenElse":
            continue
        cond = find_pin(n, "Condition", "Input")
        links = list(cond.list_connected_pins() or []) if cond else []
        if not any("bOccupied" in title(c.get_owning_node()) for c in links):
            continue
        elsep = find_pin(n, "else", "Output")
        # skip if already clears
        else_nodes = [c.get_owning_node() for c in (elsep.list_connected_pins() or [])] if elsep else []
        if any("SetOrderLine" in title(x) or "GetActorOfClass" in title(x) for x in else_nodes):
            log("clear already present"); break
        old_else = list(elsep.list_connected_pins() or []) if elsep else []
        if elsep: elsep.break_pin_links()
        get_act = tge.add_call_function_node("/Script/Engine.GameplayStatics:GetActorOfClass")
        bel.set_node_pos(get_act, pos(-500, 5900))
        setdef(find_pin(get_act, "ActorClass", "Input"), "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C")
        connect(elsep, find_pin(get_act, "execute", "Input"), "else->get")
        cast_m = add_cast(tge, "BP_RestaurantManager")
        if cast_m is None:
            ret = find_pin(get_act, "ReturnValue", "Output")
            avail = tge.list_available_nodes([ret]) if ret else []
            for a in avail:
                if a == "Utilities|Casting|CastToBP_RestaurantManager":
                    cast_m = tge.create_node_from_name(a, unreal.Vector2D(-200, 5900), []); break
        if cast_m is None:
            for tgt in old_else: connect(elsep, tgt, "restore else")
            log("clear cast failed"); break
        bel.set_node_pos(cast_m, pos(-200, 5900))
        connect(find_pin(get_act, "then", "Output"), find_pin(cast_m, "execute", "Input"), "g->c")
        connect(out_data(get_act), find_pin(cast_m, "Object", "Input"), "a->c")
        get_tid = tge.add_get_member_variable_node("TableId")
        bel.set_node_pos(get_tid, pos(-200, 6100))
        call_set = tge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:SetOrderLine")
        bel.set_node_pos(call_set, pos(200, 5900))
        connect(find_pin(cast_m, "then", "Output"), find_pin(call_set, "execute", "Input"), "c->s")
        connect(out_data(cast_m), find_pin(call_set, "self", "Input"), "ss")
        connect(out_data(get_tid), find_pin(call_set, "TableId", "Input"), "st")
        setdef(find_pin(call_set, "Line", "Input"), "")
        for tgt in old_else:
            connect(find_pin(call_set, "then", "Output"), tgt, "else restore")
        log("wired clear on unoccupied")
        break

# Final compile/save
final = {}
for path, key in ((WBP, "wbp"), (MGR, "mgr"), (TBL, "tbl")):
    bp = unreal.load_asset(path)
    bel.compile_blueprint(bp)
    errs = []
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    for n in (ge.list_nodes_with_errors() or []):
        msg = ""
        try: msg = str(n.get_editor_property("error_msg"))[:160]
        except Exception: pass
        errs.append({"t": title(n), "m": msg})
    for fname in ("UpdateOrders", "SetOrderLine"):
        g = bel.find_graph(bp, fname)
        if g:
            fge = unreal.BlueprintGraphEditor.get_graph_editor(g)
            for n in (fge.list_nodes_with_errors() or []):
                errs.append({"t": fname + ":" + title(n), "m": ""})
    final[key] = {"status": status_of(bp), "errs": errs}
    log("FINAL {} {} {}".format(key, final[key]["status"], errs))
    eas.save_asset(path)

mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(unreal.load_asset(MGR)))
for name, key in (("RefreshOrderUI", "refresh"), ("ApplyOrderUMG", "apply"), ("EnsureOrderUI", "ensure")):
    ev = find_custom(mge, name)
    REPORT[key] = [title(n) for n in walk_then(ev, 35)] if ev else []
    log(key + ": " + " -> ".join(REPORT[key][:30]))

widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o.get_class().get_name()
REPORT["widgets"] = widgets
REPORT["final"] = final
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
out = unreal.Paths.project_saved_dir() + "rest_umg_orders_fix.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
log("WROTE " + out)
print("DONE_FIX")
