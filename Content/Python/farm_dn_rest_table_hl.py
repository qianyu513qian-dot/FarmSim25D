# -*- coding: utf-8 -*-
"""Batch: hold-dish highlight matching table (DrawDebugBox + RestMark scale). Surgical."""
import unreal, json
REPORT = {"ok": [], "errors": [], "steps": []}
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
MARKER = "TableHL_v1"

def log(m):
    unreal.log("[TABLEHL] " + str(m)); print("[TABLEHL] " + str(m)); REPORT["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "Item", "Array Element"):
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
            log("setdef fail " + str(e)[:80]); return False

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def walk_kill_from(ge, start):
    kill = []; seen = set(); q = [start]
    while q:
        cur = q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); kill.append(cur)
        for pn in ("then", "else", "LoopBody", "Completed"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return kill

def make_print(ge, x, y, text, dur="0.2", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key:
        setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def add_foreach(ge, x, y):
    fe = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(fe, pos(x, y))
    return fe

def walk(start, limit=30):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

# ---------- tags ----------
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TAG_MAP = {
    "Restaurant_Table1": "RestTableHL1",
    "Restaurant_Table2": "RestTableHL2",
    "RestMark_Table1": "RestMarkHL1",
    "RestMark_Table2": "RestMarkHL2",
}
tagged = 0
for a in actor_sub.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab not in TAG_MAP:
        continue
    want = TAG_MAP[lab]
    tags = list(a.tags) if a.tags else []
    if want not in [str(t) for t in tags]:
        tags.append(want)
        a.tags = tags
        tagged += 1
        log("tagged {} -> {}".format(lab, want))
REPORT["tagged"] = tagged
REPORT["ok"].append("tags")

# ---------- manager ----------
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

for nm in ("SyncHeldTableHL", MARKER):
    old = find_custom(mge, nm)
    if old:
        mge.remove_nodes(walk_kill_from(mge, old))
        log("removed " + nm)

Y = -5200

def wire_hl(ge, exec_pin, table_tag, mark_tag, x0, y0, rgba, label):
    r, gcol, b, a = rgba
    gaw = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gaw, pos(x0, y0))
    connect(exec_pin, find_pin(gaw, "execute", "Input"), label + "gaw")
    setdef(find_pin(gaw, "Tag", "Input"), table_tag)
    fe = add_foreach(ge, x0 + 320, y0)
    connect(find_pin(gaw, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), label + "fe")
    connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe, "Array", "Input"), label + "arr")

    gal = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(gal, pos(x0 + 650, y0 + 70))
    connect(find_pin(fe, "Array Element", "Output"), find_pin(gal, "self", "Input"), label + "self")

    lift = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(lift, pos(x0 + 650, y0 + 220))
    setdef(find_pin(lift, "X", "Input"), "0.0")
    setdef(find_pin(lift, "Y", "Input"), "0.0")
    setdef(find_pin(lift, "Z", "Input"), "45.0")
    addv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    bel.set_node_pos(addv, pos(x0 + 900, y0 + 120))
    connect(out_data(gal), find_pin(addv, "A", "Input"), label + "A")
    connect(out_data(lift), find_pin(addv, "B", "Input"), label + "B")

    ext = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(ext, pos(x0 + 900, y0 + 280))
    setdef(find_pin(ext, "X", "Input"), "95.0")
    setdef(find_pin(ext, "Y", "Input"), "95.0")
    setdef(find_pin(ext, "Z", "Input"), "60.0")

    ddb = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    bel.set_node_pos(ddb, pos(x0 + 1200, y0))
    connect(find_pin(fe, "LoopBody", "Output"), find_pin(ddb, "execute", "Input"), label + "box")
    connect(out_data(addv), find_pin(ddb, "Center", "Input"), label + "c")
    connect(out_data(ext), find_pin(ddb, "Extent", "Input"), label + "e")
    setdef(find_pin(ddb, "Duration", "Input"), "0.0")
    setdef(find_pin(ddb, "Thickness", "Input"), "6.0")
    lc = find_pin(ddb, "LineColor", "Input") or find_pin(ddb, "Color", "Input")
    if lc:
        setdef(lc, "(R={:.6f},G={:.6f},B={:.6f},A={:.6f})".format(r, gcol, b, a))

    dsp = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
    bel.set_node_pos(dsp, pos(x0 + 1550, y0))
    connect(find_pin(ddb, "then", "Output"), find_pin(dsp, "execute", "Input"), label + "sph")
    connect(out_data(addv), find_pin(dsp, "Center", "Input"), label + "sc")
    setdef(find_pin(dsp, "Radius", "Input"), "75.0")
    setdef(find_pin(dsp, "Duration", "Input"), "0.0")
    setdef(find_pin(dsp, "Thickness", "Input"), "3.5")
    sc = find_pin(dsp, "LineColor", "Input") or find_pin(dsp, "Color", "Input")
    if sc:
        setdef(sc, "(R={:.6f},G={:.6f},B={:.6f},A={:.6f})".format(r, gcol, b, a))

    # RestMark scale up (fixed pulse stand-in; Duration0 box already pulses visually via redraw)
    gaw2 = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gaw2, pos(x0 + 320, y0 + 480))
    connect(find_pin(fe, "Completed", "Output"), find_pin(gaw2, "execute", "Input"), label + "mgaw")
    setdef(find_pin(gaw2, "Tag", "Input"), mark_tag)
    fe2 = add_foreach(ge, x0 + 650, y0 + 480)
    connect(find_pin(gaw2, "then", "Output"), find_pin(fe2, "Exec", "Input") or find_pin(fe2, "execute", "Input"), label + "mfe")
    connect(find_pin(gaw2, "OutActors", "Output"), find_pin(fe2, "Array", "Input"), label + "marr")
    mk = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mk, pos(x0 + 950, y0 + 560))
    setdef(find_pin(mk, "X", "Input"), "1.35")
    setdef(find_pin(mk, "Y", "Input"), "1.35")
    setdef(find_pin(mk, "Z", "Input"), "1.35")
    sas = ge.add_call_function_node("/Script/Engine.Actor:SetActorScale3D")
    bel.set_node_pos(sas, pos(x0 + 1250, y0 + 480))
    connect(find_pin(fe2, "LoopBody", "Output"), find_pin(sas, "execute", "Input"), label + "scale")
    connect(find_pin(fe2, "Array Element", "Output"), find_pin(sas, "self", "Input"), label + "mself")
    connect(out_data(mk), find_pin(sas, "NewScale3D", "Input") or find_pin(sas, "Scale", "Input"), label + "sv")
    return find_pin(fe2, "Completed", "Output")

def wire_reset(ge, exec_pin, x0, y0):
    prev = exec_pin
    for i, tag in enumerate(("RestMarkHL1", "RestMarkHL2")):
        yy = y0 + i * 260
        gaw = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
        bel.set_node_pos(gaw, pos(x0, yy))
        connect(prev, find_pin(gaw, "execute", "Input"), "rst" + tag)
        setdef(find_pin(gaw, "Tag", "Input"), tag)
        fe = add_foreach(ge, x0 + 320, yy)
        connect(find_pin(gaw, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), "rstfe" + tag)
        connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe, "Array", "Input"), "rstarr" + tag)
        mk = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(mk, pos(x0 + 650, yy + 70))
        setdef(find_pin(mk, "X", "Input"), "1.0")
        setdef(find_pin(mk, "Y", "Input"), "1.0")
        setdef(find_pin(mk, "Z", "Input"), "1.0")
        sas = ge.add_call_function_node("/Script/Engine.Actor:SetActorScale3D")
        bel.set_node_pos(sas, pos(x0 + 950, yy))
        connect(find_pin(fe, "LoopBody", "Output"), find_pin(sas, "execute", "Input"), "rsts" + tag)
        connect(find_pin(fe, "Array Element", "Output"), find_pin(sas, "self", "Input"), "rstself" + tag)
        connect(out_data(mk), find_pin(sas, "NewScale3D", "Input") or find_pin(sas, "Scale", "Input"), "rstv" + tag)
        prev = find_pin(fe, "Completed", "Output")
    return prev

ev = mge.add_custom_event_node("SyncHeldTableHL")
bel.set_node_pos(ev, pos(-200, Y))

get_h = mge.add_get_member_variable_node("HeldDishId")
bel.set_node_pos(get_h, pos(80, Y + 90))
ne = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:NotEqual_IntInt")
bel.set_node_pos(ne, pos(320, Y + 90))
connect(out_data(get_h), find_pin(ne, "A", "Input"), "hA")
setdef(find_pin(ne, "B", "Input"), "0")
br = mge.add_branch_node(); bel.set_node_pos(br, pos(560, Y))
connect(find_pin(ev, "then", "Output"), find_pin(br, "execute", "Input"), "hold?")
connect(out_data(ne), find_pin(br, "Condition", "Input"), "holding")

# HeldTableId == 1?
get_t = mge.add_get_member_variable_node("HeldTableId")
bel.set_node_pos(get_t, pos(800, Y + 70))
eq1 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq1, pos(1040, Y + 70))
connect(out_data(get_t), find_pin(eq1, "A", "Input"), "tA")
setdef(find_pin(eq1, "B", "Input"), "1")
br1 = mge.add_branch_node(); bel.set_node_pos(br1, pos(1280, Y))
connect(find_pin(br, "then", "Output"), find_pin(br1, "execute", "Input"), "which")
connect(out_data(eq1), find_pin(br1, "Condition", "Input"), "t1")

CYAN = (0.05, 1.0, 0.9, 1.0)
GREEN = (0.25, 1.0, 0.3, 1.0)
wire_hl(mge, find_pin(br1, "then", "Output"), "RestTableHL1", "RestMarkHL1", 1580, Y - 20, CYAN, "T1")

# else: only highlight table2 if HeldTableId == 2
get_t2 = mge.add_get_member_variable_node("HeldTableId")
bel.set_node_pos(get_t2, pos(1580, Y + 900))
eq2 = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq2, pos(1820, Y + 900))
connect(out_data(get_t2), find_pin(eq2, "A", "Input"), "t2A")
setdef(find_pin(eq2, "B", "Input"), "2")
br2 = mge.add_branch_node(); bel.set_node_pos(br2, pos(2060, Y + 820))
connect(find_pin(br1, "else", "Output"), find_pin(br2, "execute", "Input"), "t2?")
connect(out_data(eq2), find_pin(br2, "Condition", "Input"), "t2c")
wire_hl(mge, find_pin(br2, "then", "Output"), "RestTableHL2", "RestMarkHL2", 2360, Y + 820, GREEN, "T2")

# not holding -> reset marks (also covers ClearHeld / serve / trash next tick)
wire_reset(mge, find_pin(br, "else", "Output"), 860, Y + 1700)

mk = mge.add_custom_event_node(MARKER)
bel.set_node_pos(mk, pos(-200, Y - 250))
prmk = make_print(mge, 150, Y - 250, "TableHL_v1", dur="0.01", key="RestMarker")
connect(find_pin(mk, "then", "Output"), find_pin(prmk, "execute", "Input"), "mk")
REPORT["ok"].append("SyncHeldTableHL_built")

# Compile once so callable exists
bel.compile_blueprint(mbp)
st = str(mbp.get_editor_property("status"))
REPORT["mgr_mid"] = st
log("mid " + st)
if "ERROR" in st:
    for n in mge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                REPORT["errors"].append(title(n) + ":" + str(em)[:160])
        except Exception:
            pass
    open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_table_hl.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
    print(json.dumps(REPORT, indent=2, ensure_ascii=False)[:5000])
    raise SystemExit(0)

# Wire RestaurantTick: after SyncHeldMesh
rt = find_custom(mge, "RestaurantTick")
thenp = find_pin(rt, "then", "Output") if rt else None
sync_mesh = None
already = False
if thenp:
    q = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
    seen = set()
    while q:
        cur = q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        tn = title(cur)
        if "SyncHeldMesh" in tn and sync_mesh is None:
            sync_mesh = cur
        if tn == "SyncHeldTableHL" or "SyncHeldTableHL" in tn:
            already = True
        for pn in ("then", "else"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())

if already:
    log("already wired")
    REPORT["ok"].append("tick_exists")
else:
    call_hl = mge.add_call_function_node(MGR + ".BP_RestaurantManager_C:SyncHeldTableHL")
    bel.set_node_pos(call_hl, pos(450, -380))
    if sync_mesh is not None:
        mesh_then = find_pin(sync_mesh, "then", "Output")
        old = list(mesh_then.list_connected_pins() or []) if mesh_then else []
        if mesh_then:
            mesh_then.break_pin_links()
        connect(mesh_then, find_pin(call_hl, "execute", "Input"), "Mesh->HL")
        for ot in old:
            connect(find_pin(call_hl, "then", "Output"), ot, "HL->next")
        REPORT["ok"].append("tick_after_mesh")
        log("wired SyncHeldMesh -> SyncHeldTableHL")
    elif thenp is not None:
        old = list(thenp.list_connected_pins() or [])
        thenp.break_pin_links()
        connect(thenp, find_pin(call_hl, "execute", "Input"), "RT->HL")
        for ot in old:
            connect(find_pin(call_hl, "then", "Output"), ot, "HL->old")
        REPORT["ok"].append("tick_fallback")
        log("wired RestaurantTick -> SyncHeldTableHL fallback")
    else:
        REPORT["errors"].append("no RestaurantTick")

bel.compile_blueprint(mbp)
st2 = str(mbp.get_editor_property("status"))
REPORT["mgr_status"] = st2
log("final " + st2)
if "ERROR" not in st2:
    eas.save_asset(MGR)
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_save_current_level()
        REPORT["ok"].append("saved_level")
    except Exception as e:
        REPORT["errors"].append("levelsave " + str(e)[:80])
    REPORT["ok"].append("saved_mgr")
else:
    for n in mge.list_all_nodes():
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                REPORT["errors"].append(title(n) + ":" + str(em)[:160])
        except Exception:
            pass

rt = find_custom(mge, "RestaurantTick")
hl = find_custom(mge, "SyncHeldTableHL")
REPORT["RestaurantTick"] = walk(rt, 18) if rt else []
REPORT["SyncHeldTableHL"] = walk(hl, 20) if hl else []

open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_table_hl.json","w",encoding="utf-8").write(
    json.dumps(REPORT, indent=2, ensure_ascii=False))
print(json.dumps(REPORT, indent=2, ensure_ascii=False)[:7000])