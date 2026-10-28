# -*- coding: utf-8 -*-
"""Batch: held-dish feedback + stove cook progress. Surgical; keep TryClaimCook rules."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

STOVE = "/Game/Farm/Restaurant/BP_RestaurantStove"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
R = {"steps": [], "errors": [], "ok": []}

def log(m):
    unreal.log("[HELDCOOK] " + str(m)); print("[HELDCOOK] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

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
    for name in ("ReturnValue", "Return Value", "Item", "HeldDishId", "CookTimeLeft", "bCooking", "bCookReady", "CookingDishId"):
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
        log("skip " + label); R["errors"].append("skip " + label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}".format(label, ok))
    if not ok: R["errors"].append("fail " + label)
    return ok

def setdef(pin, val):
    if not pin: return False
    try:
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef fail " + str(e)[:80]); return False

def make_print(ge, x, y, text, dur="0.2", key="", color=None):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key:
        setdef(find_pin(pr, "Key", "Input"), key)
    # TextColor is LinearColor struct — leave default if hard
    return pr

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

def already_has_key(ge, key):
    for n in ge.list_all_nodes():
        if title(n) != "PrintString":
            continue
        kp = find_pin(n, "Key", "Input")
        if not kp:
            continue
        try:
            v = kp.get_default_as_string() if hasattr(kp, "get_default_as_string") else None
        except Exception:
            v = None
        try:
            if v is None:
                v = kp.get_default_value()
        except Exception:
            pass
        if v and key in str(v):
            return True
        # also check pin value API
        try:
            pv = kp.get_pin_value() if hasattr(kp, "get_pin_value") else None
            if pv and key in str(pv):
                return True
        except Exception:
            pass
    # fallback: scan for marker comment / custom
    if find_custom(ge, "HeldCookFx_v1"):
        return True
    return False

def get_print_key(n):
    kp = find_pin(n, "Key", "Input")
    if not kp:
        return ""
    for getter in ("get_default_as_string", "get_default_value", "get_pin_value"):
        if hasattr(kp, getter):
            try:
                return str(getattr(kp, getter)() or "")
            except Exception:
                pass
    return ""

# =====================================================================
# STOVE: cook progress on Tick
# =====================================================================
sbp = eas.load_asset(STOVE)
sge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))

# marker to allow idempotent-ish re-run: remove previous HeldCookFx nodes if custom marker exists
# Prefer: if any PrintString has Key RestCook, skip stove tick insert but still fix READY text
has_restcook = False
for n in sge.list_all_nodes():
    if title(n) == "PrintString" and "RestCook" in get_print_key(n):
        has_restcook = True
        break

tick = find_event(sge, "Tick")
# Find cooking Set CookTimeLeft: exec_from Branch, then -> Branch
tick_set = None
tick_done_br = None
cook_br = None  # first branch after tick
if tick:
    thenp = find_pin(tick, "then", "Output")
    firsts = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    for n in firsts:
        if title(n) == "Branch":
            cook_br = n
            break

for n in sge.list_all_nodes():
    if title(n) != "Set CookTimeLeft":
        continue
    ex = find_pin(n, "execute", "Input")
    th = find_pin(n, "then", "Output")
    froms = [title(c.get_owning_node()) for c in (ex.list_connected_pins() or [])] if ex else []
    tos = [c.get_owning_node() for c in (th.list_connected_pins() or [])] if th else []
    if "Branch" in froms and any(title(t) == "Branch" for t in tos):
        tick_set = n
        for t in tos:
            if title(t) == "Branch":
                tick_done_br = t
        break

log("stove tick_set={} done_br={} cook_br={} has_restcook={}".format(
    tick_set is not None, tick_done_br is not None, cook_br is not None, has_restcook))

if tick_set and tick_done_br and not has_restcook:
    # Break SetCTL -> done Branch; insert progress FX then reconnect
    th = find_pin(tick_set, "then", "Output")
    th.break_pin_links()

    Y = -400  # park FX above tick lane
    X = 1300

    # GetActorLocation
    gal = sge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(gal, pos(X, Y + 200))
    # self is implicit for member? need self pin
    # DrawDebugBox
    ddb = sge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    bel.set_node_pos(ddb, pos(X + 350, Y))
    connect(th, find_pin(ddb, "execute", "Input"), "ctl->box")
    connect(out_data(gal), find_pin(ddb, "Center", "Input"), "boxCenter")
    # raise center: MakeVector + Add
    mk = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mk, pos(X, Y + 320))
    setdef(find_pin(mk, "X", "Input"), "0.0")
    setdef(find_pin(mk, "Y", "Input"), "0.0")
    setdef(find_pin(mk, "Z", "Input"), "140.0")
    addv = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    bel.set_node_pos(addv, pos(X + 200, Y + 280))
    connect(out_data(gal), find_pin(addv, "A", "Input"), "addA")
    connect(out_data(mk), find_pin(addv, "B", "Input"), "addB")
    # reconnect center from add
    cp = find_pin(ddb, "Center", "Input")
    if cp:
        cp.break_pin_links()
    connect(out_data(addv), find_pin(ddb, "Center", "Input"), "boxCenter2")
    # Extent: MakeVector (50, 12, 12) — fixed orange bar while cooking
    mk2 = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mk2, pos(X + 50, Y + 420))
    setdef(find_pin(mk2, "X", "Input"), "55.0")
    setdef(find_pin(mk2, "Y", "Input"), "14.0")
    setdef(find_pin(mk2, "Z", "Input"), "14.0")
    connect(out_data(mk2), find_pin(ddb, "Extent", "Input"), "extent")
    setdef(find_pin(ddb, "Duration", "Input"), "0.0")  # one frame
    setdef(find_pin(ddb, "Thickness", "Input"), "2.0")

    # remaining time string: Get CookTimeLeft -> Conv -> Append
    get_tl = sge.add_get_member_variable_node("CookTimeLeft")
    bel.set_node_pos(get_tl, pos(X + 700, Y + 200))
    conv = sge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
    if conv is None:
        conv = sge.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
    bel.set_node_pos(conv, pos(X + 950, Y + 200))
    connect(out_data(get_tl), find_pin(conv, "InDouble", "Input") or find_pin(conv, "InFloat", "Input") or find_pin(conv, "double", "Input") or find_pin(conv, "In", "Input"), "convIn")
    # left trim: use Append "做菜中 " + time + "s"
    ap1 = sge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap1, pos(X + 1200, Y + 160))
    setdef(find_pin(ap1, "A", "Input"), "做菜中 ")
    connect(out_data(conv), find_pin(ap1, "B", "Input"), "ap1B")
    ap2 = sge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(ap2, pos(X + 1450, Y + 160))
    connect(out_data(ap1), find_pin(ap2, "A", "Input"), "ap2A")
    setdef(find_pin(ap2, "B", "Input"), "s")

    pr = make_print(sge, X + 1700, Y, "做菜中", dur="0.15", key="RestCook")
    # wire InString from ap2
    isp = find_pin(pr, "InString", "Input")
    if isp:
        isp.break_pin_links()
        # clear default so connected value used
    connect(out_data(ap2), isp, "prStr")
    connect(find_pin(ddb, "then", "Output"), find_pin(pr, "execute", "Input"), "box->pr")

    # DrawDebugString above stove too
    dds = sge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
    bel.set_node_pos(dds, pos(X + 1700, Y + 120))
    connect(find_pin(pr, "then", "Output"), find_pin(dds, "execute", "Input"), "pr->dds")
    connect(out_data(addv), find_pin(dds, "TextLocation", "Input"), "ddsLoc")
    connect(out_data(ap2), find_pin(dds, "Text", "Input"), "ddsTxt")
    setdef(find_pin(dds, "Duration", "Input"), "0.0")

    # reconnect to done branch
    connect(find_pin(dds, "then", "Output"), find_pin(tick_done_br, "execute", "Input"), "fx->doneBr")
    R["ok"].append("stove_cook_progress")
    log("inserted stove cook progress FX")
elif has_restcook:
    log("stove RestCook already present — skip insert")
    R["ok"].append("stove_cook_progress_exists")
else:
    R["errors"].append("could not find tick Set CookTimeLeft chain")

# Update READY PrintString text/key (the one after Set bCookReady in tick chain)
# Walk tick: ... Set bCookReady -> PrintString
ready_pr = None
if tick_done_br:
    # then of done branch -> Set bCooking -> Set bCookReady -> Print
    thenp = find_pin(tick_done_br, "then", "Output")
    q = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    seen = set()
    while q:
        cur = q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        if title(cur) == "PrintString":
            ready_pr = cur
            break
        tp = find_pin(cur, "then", "Output")
        if tp:
            for c in tp.list_connected_pins() or []:
                q.append(c.get_owning_node())

if ready_pr:
    setdef(find_pin(ready_pr, "InString", "Input"), "【灶台】菜好了！按 E 端起")
    setdef(find_pin(ready_pr, "Key", "Input"), "RestCook")
    setdef(find_pin(ready_pr, "Duration", "Input"), "2.5")
    R["ok"].append("ready_print_zh")
    log("updated READY print")
else:
    R["errors"].append("READY print not found")

# Wire cook_br ELSE: if ready show highlight, else clear RestCook
# Only if else not already linked to our FX
if cook_br and not has_restcook:
    elsep = find_pin(cook_br, "else", "Output")
    else_links = [c.get_owning_node() for c in (elsep.list_connected_pins() or [])] if elsep else []
    if else_links:
        log("cook_br else already linked to " + ",".join(title(n) for n in else_links))
    else:
        Y2 = 1100
        get_r = sge.add_get_member_variable_node("bCookReady")
        bel.set_node_pos(get_r, pos(400, Y2 + 80))
        br_r = sge.add_branch_node(); bel.set_node_pos(br_r, pos(650, Y2))
        connect(elsep, find_pin(br_r, "execute", "Input"), "cookElse->ready?")
        connect(out_data(get_r), find_pin(br_r, "Condition", "Input"), "readyCond")

        # READY highlight: DrawDebugSphere + Print
        gal2 = sge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
        bel.set_node_pos(gal2, pos(900, Y2 + 100))
        mk3 = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(mk3, pos(900, Y2 + 220))
        setdef(find_pin(mk3, "X", "Input"), "0.0")
        setdef(find_pin(mk3, "Y", "Input"), "0.0")
        setdef(find_pin(mk3, "Z", "Input"), "160.0")
        add3 = sge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
        bel.set_node_pos(add3, pos(1150, Y2 + 160))
        connect(out_data(gal2), find_pin(add3, "A", "Input"), "rA")
        connect(out_data(mk3), find_pin(add3, "B", "Input"), "rB")
        dsp = sge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
        bel.set_node_pos(dsp, pos(1400, Y2))
        connect(find_pin(br_r, "then", "Output"), find_pin(dsp, "execute", "Input"), "ready->sphere")
        connect(out_data(add3), find_pin(dsp, "Center", "Input"), "sphC")
        setdef(find_pin(dsp, "Radius", "Input"), "28.0")
        setdef(find_pin(dsp, "Duration", "Input"), "0.0")
        setdef(find_pin(dsp, "Thickness", "Input"), "3.0")
        pr_ready = make_print(sge, 1750, Y2, "【灶台】菜好了！按 E 端起", dur="0.2", key="RestCook")
        connect(find_pin(dsp, "then", "Output"), find_pin(pr_ready, "execute", "Input"), "sph->pr")
        dds2 = sge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
        bel.set_node_pos(dds2, pos(2050, Y2))
        connect(find_pin(pr_ready, "then", "Output"), find_pin(dds2, "execute", "Input"), "pr->dds2")
        connect(out_data(add3), find_pin(dds2, "TextLocation", "Input"), "dds2loc")
        setdef(find_pin(dds2, "Text", "Input"), "菜好了")
        setdef(find_pin(dds2, "Duration", "Input"), "0.0")

        # not ready: clear RestCook key
        pr_clr = make_print(sge, 1400, Y2 + 200, " ", dur="0.05", key="RestCook")
        connect(find_pin(br_r, "else", "Output"), find_pin(pr_clr, "execute", "Input"), "idle->clr")
        R["ok"].append("stove_ready_highlight")
        log("wired ready highlight on cook else")

bel.compile_blueprint(sbp)
sst = str(sbp.get_editor_property("status"))
R["stove_status"] = sst
log("stove status " + sst)
if "ERROR" not in sst:
    eas.save_asset(STOVE)
else:
    for n in sge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append("stove:" + title(n) + ":" + str(em)[:180])
        except Exception:
            pass

# =====================================================================
# MANAGER: held dish feedback + RefreshOrderUI on RestaurantTick
# =====================================================================
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

has_restheld = False
for n in mge.list_all_nodes():
    if title(n) == "PrintString" and "RestHeld" in get_print_key(n):
        has_restheld = True
        break

rt = find_custom(mge, "RestaurantTick")
if rt is None:
    R["errors"].append("RestaurantTick missing")
else:
    thenp = find_pin(rt, "then", "Output")
    existing = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    log("RestaurantTick then -> " + str([title(n) for n in existing]))

    if has_restheld:
        log("RestHeld already present — skip manager fx")
        R["ok"].append("held_fx_exists")
    else:
        # If already has links, append after last; else start fresh
        start_exec = thenp
        chain_x = 300
        if existing:
            # don't break existing — find terminal then and append
            # For empty RestaurantTick, existing=[] — good
            # If something is there, walk to end
            cur = existing[0]
            seen = set()
            while cur and id(cur) not in seen:
                seen.add(id(cur))
                tp = find_pin(cur, "then", "Output")
                nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])] if tp else []
                if not nxts:
                    start_exec = tp
                    chain_x = 300
                    break
                cur = nxts[0]
            else:
                start_exec = thenp

        Y = -600
        # Call RefreshOrderUI first (cheap quality)
        call_ref = mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:RefreshOrderUI")
        bel.set_node_pos(call_ref, pos(chain_x, Y))
        if existing and start_exec is thenp:
            # empty — connect from then
            connect(thenp, find_pin(call_ref, "execute", "Input"), "RT->Refresh")
        elif existing and start_exec is not thenp:
            connect(start_exec, find_pin(call_ref, "execute", "Input"), "term->Refresh")
        else:
            connect(thenp, find_pin(call_ref, "execute", "Input"), "RT->Refresh")

        # HeldDishId != 0?
        get_h = mge.add_get_member_variable_node("HeldDishId")
        bel.set_node_pos(get_h, pos(chain_x + 250, Y + 120))
        ne = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
        bel.set_node_pos(ne, pos(chain_x + 500, Y + 120))
        connect(out_data(get_h), find_pin(ne, "A", "Input"), "hA")
        setdef(find_pin(ne, "B", "Input"), "0")
        br = mge.add_branch_node(); bel.set_node_pos(br, pos(chain_x + 750, Y))
        connect(find_pin(call_ref, "then", "Output"), find_pin(br, "execute", "Input"), "ref->hold?")
        connect(out_data(ne), find_pin(br, "Condition", "Input"), "holding?")

        # Player location for sphere
        gpp = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
        bel.set_node_pos(gpp, pos(chain_x + 1000, Y + 80))
        setdef(find_pin(gpp, "PlayerIndex", "Input"), "0")
        gal = mge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
        bel.set_node_pos(gal, pos(chain_x + 1300, Y + 80))
        # wire self from pawn
        connect(out_data(gpp), find_pin(gal, "self", "Input"), "pawn->gal")

        mk = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(mk, pos(chain_x + 1300, Y + 220))
        setdef(find_pin(mk, "X", "Input"), "0.0")
        setdef(find_pin(mk, "Y", "Input"), "0.0")
        setdef(find_pin(mk, "Z", "Input"), "120.0")
        addv = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
        bel.set_node_pos(addv, pos(chain_x + 1550, Y + 140))
        connect(out_data(gal), find_pin(addv, "A", "Input"), "pA")
        connect(out_data(mk), find_pin(addv, "B", "Input"), "pB")

        dsp = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
        bel.set_node_pos(dsp, pos(chain_x + 1800, Y))
        connect(find_pin(br, "then", "Output"), find_pin(dsp, "execute", "Input"), "hold->sph")
        connect(out_data(addv), find_pin(dsp, "Center", "Input"), "hsphC")
        setdef(find_pin(dsp, "Radius", "Input"), "22.0")
        setdef(find_pin(dsp, "Duration", "Input"), "0.0")
        setdef(find_pin(dsp, "Thickness", "Input"), "2.5")

        # dish == 1 salad else stew
        get_h2 = mge.add_get_member_variable_node("HeldDishId")
        bel.set_node_pos(get_h2, pos(chain_x + 1800, Y + 200))
        eq1 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
        bel.set_node_pos(eq1, pos(chain_x + 2050, Y + 200))
        connect(out_data(get_h2), find_pin(eq1, "A", "Input"), "eqA")
        setdef(find_pin(eq1, "B", "Input"), "1")
        br_d = mge.add_branch_node(); bel.set_node_pos(br_d, pos(chain_x + 2300, Y))
        connect(find_pin(dsp, "then", "Output"), find_pin(br_d, "execute", "Input"), "sph->dish?")
        connect(out_data(eq1), find_pin(br_d, "Condition", "Input"), "salad?")

        pr_s = make_print(mge, chain_x + 2600, Y - 40, "手上：番茄沙拉", dur="0.2", key="RestHeld")
        connect(find_pin(br_d, "then", "Output"), find_pin(pr_s, "execute", "Input"), "salad")
        pr_w = make_print(mge, chain_x + 2600, Y + 80, "手上：炖菜", dur="0.2", key="RestHeld")
        connect(find_pin(br_d, "else", "Output"), find_pin(pr_w, "execute", "Input"), "stew")

        # DrawDebugString for held
        dds_s = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
        bel.set_node_pos(dds_s, pos(chain_x + 2900, Y - 40))
        connect(find_pin(pr_s, "then", "Output"), find_pin(dds_s, "execute", "Input"), "ps->dds")
        connect(out_data(addv), find_pin(dds_s, "TextLocation", "Input"), "ddsSloc")
        setdef(find_pin(dds_s, "Text", "Input"), "手上：番茄沙拉")
        setdef(find_pin(dds_s, "Duration", "Input"), "0.0")

        dds_w = mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
        bel.set_node_pos(dds_w, pos(chain_x + 2900, Y + 80))
        connect(find_pin(pr_w, "then", "Output"), find_pin(dds_w, "execute", "Input"), "pw->dds")
        connect(out_data(addv), find_pin(dds_w, "TextLocation", "Input"), "ddsWloc")
        setdef(find_pin(dds_w, "Text", "Input"), "手上：炖菜")
        setdef(find_pin(dds_w, "Duration", "Input"), "0.0")

        # empty hands: clear RestHeld
        pr_e = make_print(mge, chain_x + 1800, Y + 320, " ", dur="0.05", key="RestHeld")
        connect(find_pin(br, "else", "Output"), find_pin(pr_e, "execute", "Input"), "empty->clr")
        R["ok"].append("held_fx")
        R["ok"].append("RestaurantTick->RefreshOrderUI")
        log("wired held FX + RefreshOrderUI on RestaurantTick")

# ClearHeld: append clear print Key=RestHeld
ch = find_custom(mge, "ClearHeld")
if ch:
    # walk to end
    cur = ch
    seen = set()
    last_then = find_pin(ch, "then", "Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp = find_pin(cur, "then", "Output")
        if not tp:
            break
        nxts = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            last_then = tp
            break
        cur = nxts[0]
    # check if already clears
    already = False
    for n in mge.list_all_nodes():
        if title(n) == "PrintString" and "RestHeld" in get_print_key(n):
            # if linked from ClearHeld chain
            pass
    pr_c = make_print(mge, 1200, -200, " ", dur="0.1", key="RestHeld")
    # also clear RestCook when dumping? not always — only when trash. Skip RestCook here.
    if last_then and not (last_then.list_connected_pins() or []):
        connect(last_then, find_pin(pr_c, "execute", "Input"), "ClearHeld->clrPrint")
        R["ok"].append("ClearHeld_clear_print")
    else:
        # still try
        connect(last_then, find_pin(pr_c, "execute", "Input"), "ClearHeld->clrPrint2")
        log("ClearHeld append attempted")

# Update Receive* one-shot prints to Chinese with Key (nice pickup moment)
for ev_name, zh in [
    ("ReceiveSalad1", "手上：番茄沙拉（桌1）"),
    ("ReceiveSalad2", "手上：番茄沙拉（桌2）"),
    ("ReceiveStew1", "手上：炖菜（桌1）"),
    ("ReceiveStew2", "手上：炖菜（桌2）"),
]:
    ev = find_custom(mge, ev_name)
    if not ev:
        continue
    thenp = find_pin(ev, "then", "Output")
    q = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])] if thenp else []
    seen = set()
    while q:
        cur = q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        if title(cur) == "PrintString":
            setdef(find_pin(cur, "InString", "Input"), zh)
            setdef(find_pin(cur, "Key", "Input"), "RestHeld")
            setdef(find_pin(cur, "Duration", "Input"), "2.0")
            R["ok"].append(ev_name + "_zh")
            log("updated " + ev_name)
            break
        tp = find_pin(cur, "then", "Output")
        if tp:
            for c in tp.list_connected_pins() or []:
                q.append(c.get_owning_node())

bel.compile_blueprint(mbp)
mst = str(mbp.get_editor_property("status"))
R["mgr_status"] = mst
log("mgr status " + mst)
if "ERROR" not in mst:
    eas.save_asset(MGR)
else:
    for n in mge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append("mgr:" + title(n) + ":" + str(em)[:180])
        except Exception:
            pass

# marker custom (no body) for future idempotency detection
if not find_custom(mge, "HeldCookFx_v1") and "ERROR" not in mst:
    try:
        mk = mge.add_custom_event_node("HeldCookFx_v1")
        bel.set_node_pos(mk, pos(-400, -800))
        bel.compile_blueprint(mbp)
        eas.save_asset(MGR)
        R["ok"].append("marker")
    except Exception as e:
        log("marker " + str(e)[:80])

open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_held_cook.json", "w", encoding="utf-8").write(
    json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:8000])
