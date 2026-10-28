# -*- coding: utf-8 -*-
"""Continue batch: pay->Money via GetAllActorsOfClass Character; sign visual; T->17:00."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
IMC = "/Game/TopDown/Input/IMC_Default"
IA_DIR = "/Game/TopDown/Input/Actions"
IA_PATH = IA_DIR + "/IA_SkipTo17"
LABEL_DIR = "/Game/Farm/Restaurant/Labels"
MAT_OPEN = LABEL_DIR + "/M_SignOpen"
MAT_CLOSED = LABEL_DIR + "/M_SignClosed"
CHAR_CLS = "/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C"

R = {"steps": [], "errors": [], "ok": []}

def log(m):
    unreal.log("[BATCH2] " + str(m)); print("[BATCH2] " + str(m)); R["steps"].append(str(m))

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
            log("setdef " + str(e)[:80]); return False

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def make_print(ge, x, y, text, dur="2.0", key=""):
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(x, y))
    setdef(find_pin(pr, "InString", "Input"), text)
    setdef(find_pin(pr, "Duration", "Input"), dur)
    if key:
        setdef(find_pin(pr, "Key", "Input"), key)
    return pr

def walk_kill_from(ge, start):
    kill = [start]; seen = set([id(start)])
    thenp = find_pin(start, "then", "Output")
    queue = []
    if thenp:
        queue = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
    while queue:
        cur = queue.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); kill.append(cur)
        for pn in ("then", "else", "LoopBody", "Completed", "Started"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append(c.get_owning_node())
    return kill

# ---------- verify GrantMoney exists on character ----------
cbp = eas.load_asset(CHAR)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
for nm in ("GrantMoney_Salad", "GrantMoney_Stew"):
    if find_custom(cge, nm):
        log("have " + nm); R["ok"].append(nm)
    else:
        R["errors"].append("missing " + nm)

# ---------- wire Manager pay ----------
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

def find_pay_terminal(ev_name):
    ev = find_custom(mge, ev_name)
    if not ev: return None, None
    # walk to last node in then-chain; prefer PrintString after Set RestaurantMoney
    cur = ev
    last = ev
    for _ in range(20):
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins():
            break
        nxt = tp.list_connected_pins()[0].get_owning_node()
        # stop before GrantMoney / GetAllActors if already extended
        if "GrantMoney" in title(nxt) or ("GetAllActorsOfClass" in title(nxt) and cur != ev):
            return ev, cur  # cur is last before extension
        last = nxt; cur = nxt
    return ev, last

def wire_pay(ev_name, grant_name, y):
    ev, term = find_pay_terminal(ev_name)
    if not ev or not term:
        R["errors"].append("no " + ev_name); return
    # if term then already GrantMoney, skip
    tp = find_pin(term, "then", "Output")
    if tp:
        for c in tp.list_connected_pins() or []:
            if grant_name in title(c.get_owning_node()) or "GetAllActorsOfClass" in title(c.get_owning_node()):
                # check further for grant
                log(ev_name + " appears extended already"); return
        # clear then to rewire
        old = list(tp.list_connected_pins() or [])
        # if old exists and isn't our stuff, we'll chain after grant
        try: tp.break_pin_links()
        except Exception: pass
    else:
        old = []

    gao = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(1400, y))
    connect(find_pin(term, "then", "Output"), find_pin(gao, "execute", "Input"), ev_name + "->gao")
    cls = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
    setdef(cls, CHAR_CLS)
    try:
        if cls: cls.set_default_value(CHAR_CLS)
    except Exception: pass

    get0 = mge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(1750, y + 80))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), ev_name + "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")

    call = mge.add_call_function_node(CHAR_CLS + ":" + grant_name)
    bel.set_node_pos(call, pos(2100, y))
    connect(find_pin(gao, "then", "Output"), find_pin(call, "execute", "Input"), ev_name + "->grant")
    ok = connect(out_data(get0) or find_pin(get0, "Item", "Output"), find_pin(call, "self", "Input"), ev_name + "self")
    if not ok:
        R["errors"].append(ev_name + " self connect failed")
    # reattach old if any (unlikely)
    for t in old:
        connect(find_pin(call, "then", "Output"), t, ev_name + "old")
    log("wired " + ev_name + " -> " + grant_name)
    R["ok"].append(ev_name + "->" + grant_name)

wire_pay("OnGuestPaidSalad", "GrantMoney_Salad", 2200)
wire_pay("OnGuestPaidStew", "GrantMoney_Stew", 2500)

# ---------- materials ----------
def ensure_emissive_mat(path, name, rgb):
    if eas.does_asset_exist(path):
        log("mat exists " + path); return eas.load_asset(path)
    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(name, LABEL_DIR, unreal.Material, factory)
    if not mat:
        R["errors"].append("mat fail " + name); return None
    try: mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception: pass
    try: mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    except Exception: pass
    try: mat.set_editor_property("two_sided", True)
    except Exception: pass
    const = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -350, 0)
    const.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.connect_material_property(const, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eas.save_asset(path)
    log("created " + path)
    return mat

mat_open = ensure_emissive_mat(MAT_OPEN, "M_SignOpen", (0.15, 1.0, 0.25))
mat_closed = ensure_emissive_mat(MAT_CLOSED, "M_SignClosed", (0.45, 0.12, 0.12))

# Tag RestMark_OpenSign
for a in actor_sub.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab == "RestMark_OpenSign":
        tags = list(a.tags) if a.tags else []
        if "RestSignMark" not in [str(t) for t in tags]:
            tags.append("RestSignMark"); a.tags = tags
            log("tagged RestMark_OpenSign")
        try:
            if mat_closed and a.static_mesh_component:
                a.static_mesh_component.set_material(0, mat_closed)
        except Exception as e:
            log("mat set " + str(e)[:60])

def ensure_apply_sign(name, mat_path, scale, y):
    old = find_custom(mge, name)
    if old:
        mge.remove_nodes(walk_kill_from(mge, old))
        log("removed old " + name)
    ev = mge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(0, y))
    gaw = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsWithTag")
    bel.set_node_pos(gaw, pos(300, y))
    connect(find_pin(ev, "then", "Output"), find_pin(gaw, "execute", "Input"), name + "gaw")
    setdef(find_pin(gaw, "Tag", "Input"), "RestSignMark")
    fe = mge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForEachLoop")
    bel.set_node_pos(fe, pos(650, y))
    connect(find_pin(gaw, "then", "Output"), find_pin(fe, "Exec", "Input") or find_pin(fe, "execute", "Input"), name + "fe")
    connect(find_pin(gaw, "OutActors", "Output"), find_pin(fe, "Array", "Input"), name + "arr")
    gcc = mge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
    bel.set_node_pos(gcc, pos(1000, y + 80))
    connect(find_pin(fe, "Array Element", "Output"), find_pin(gcc, "self", "Input"), name + "self")
    cls_pin = find_pin(gcc, "ComponentClass", "Input") or find_pin(gcc, "Class", "Input")
    setdef(cls_pin, "/Script/Engine.StaticMeshComponent")
    try:
        if cls_pin: cls_pin.set_default_value("/Script/Engine.StaticMeshComponent")
    except Exception: pass
    sm = mge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
    bel.set_node_pos(sm, pos(1400, y))
    connect(find_pin(fe, "LoopBody", "Output"), find_pin(sm, "execute", "Input"), name + "sm")
    connect(out_data(gcc), find_pin(sm, "self", "Input"), name + "mesh")
    setdef(find_pin(sm, "ElementIndex", "Input") or find_pin(sm, "Index", "Input"), "0")
    mat_pin = find_pin(sm, "Material", "Input")
    if mat_pin:
        try:
            mat_pin.set_default_value(mat_path + "." + mat_path.split("/")[-1])
        except Exception:
            setdef(mat_pin, mat_path)
    sc = mge.add_call_function_node("/Script/Engine.Actor:SetActorScale3D")
    bel.set_node_pos(sc, pos(1800, y))
    connect(find_pin(sm, "then", "Output"), find_pin(sc, "execute", "Input"), name + "sc")
    connect(find_pin(fe, "Array Element", "Output"), find_pin(sc, "self", "Input"), name + "scself")
    mv = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mv, pos(1600, y + 120))
    setdef(find_pin(mv, "X", "Input"), str(scale))
    setdef(find_pin(mv, "Y", "Input"), str(scale))
    setdef(find_pin(mv, "Z", "Input"), str(scale))
    connect(out_data(mv), find_pin(sc, "NewScale3D", "Input") or find_pin(sc, "NewScale", "Input") or find_pin(sc, "Scale", "Input"), name + "scale")
    pr = make_print(mge, 2100, y, "Sign: " + name.replace("ApplySign", ""), dur="1.0")
    connect(find_pin(sc, "then", "Output"), find_pin(pr, "execute", "Input"), name + "pr")
    log("wired " + name)

ensure_apply_sign("ApplySignOpen", MAT_OPEN, 0.85, 6400)
ensure_apply_sign("ApplySignClosed", MAT_CLOSED, 0.55, 6800)

# Insert after Set bIsOpenBusiness
for n in list(mge.list_all_nodes()):
    if title(n) != "Set bIsOpenBusiness":
        continue
    val_pin = find_pin(n, "bIsOpenBusiness", "Input")
    v = (val_pin.get_pin_value() if val_pin else "") or ""
    is_open = str(v).lower() in ("true", "1")
    call_name = "ApplySignOpen" if is_open else "ApplySignClosed"
    thenp = find_pin(n, "then", "Output")
    if not thenp: continue
    already = False
    for c in thenp.list_connected_pins() or []:
        if "ApplySign" in title(c.get_owning_node()):
            already = True; break
    if already:
        log("already inserted " + call_name); continue
    old_tgts = list(thenp.list_connected_pins() or [])
    try: thenp.break_pin_links()
    except Exception: pass
    call = mge.add_call_function_node(MGR + ".BP_RestaurantManager_C:" + call_name)
    bel.set_node_pos(call, pos(1000, 0))
    connect(thenp, find_pin(call, "execute", "Input"), "Set->" + call_name)
    for t in old_tgts:
        connect(find_pin(call, "then", "Output"), t, call_name + "->old")
    log("inserted " + call_name + " val=" + str(v))

# BeginPlay -> ApplySignClosed
bp_ev = None
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "BeginPlay" in title(n):
        bp_ev = n; break
if bp_ev:
    thenp = find_pin(bp_ev, "then", "Output")
    already = False
    if thenp:
        for c in thenp.list_connected_pins() or []:
            if "ApplySignClosed" in title(c.get_owning_node()):
                already = True
    if not already and thenp:
        old = list(thenp.list_connected_pins() or [])
        try: thenp.break_pin_links()
        except Exception: pass
        call = mge.add_call_function_node(MGR + ".BP_RestaurantManager_C:ApplySignClosed")
        bel.set_node_pos(call, pos(350, -450))
        connect(thenp, find_pin(call, "execute", "Input"), "BP->closed")
        for t in old:
            connect(find_pin(call, "then", "Output"), t, "closed->oldBP")
        log("BeginPlay -> ApplySignClosed")
R["ok"].append("sign visual")

# ---------- T key SkipTo17 ----------
if eas.does_asset_exist(IA_PATH):
    ia = eas.load_asset(IA_PATH)
else:
    factory = unreal.InputAction_Factory()
    ia = tools.create_asset("IA_SkipTo17", IA_DIR, unreal.InputAction, factory)
    log("created IA")
if ia:
    try: ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception: pass
    eas.save_asset(IA_PATH)

imc = eas.load_asset(IMC)
try: imc.unmap_all_keys_from_action(ia)
except Exception: pass
k = unreal.Key(); k.import_text("T")
try:
    imc.map_key(ia, k); log("mapped T")
except Exception as e:
    R["errors"].append("map T " + str(e))
eas.save_asset(IMC)

# Remove old IA_SkipTo17 chains
kill_ia = []
for n in cge.list_all_nodes():
    if "IA_SkipTo17" in title(n):
        kill_ia.extend(walk_kill_from(cge, n))
        # also Started downstream
        for pn_name in ("Started", "Triggered"):
            tp = find_pin(n, pn_name, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    kill_ia.extend(walk_kill_from(cge, c.get_owning_node()))
if kill_ia:
    uniq=[]; ids=set()
    for n in kill_ia:
        if id(n) not in ids: ids.add(id(n)); uniq.append(n)
    cge.remove_nodes(uniq); log("removed IA chain " + str(len(uniq)))

ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_SkipTo17", unreal.Vector2D(50, 6000), [])
if not ia_node:
    ia_node = cge.create_node_from_name("EnhancedActionEvents|IA_SkipTo17", unreal.Vector2D(50, 6000), [])
if not ia_node:
    R["errors"].append("IA node create failed")
else:
    bel.set_node_pos(ia_node, pos(50, 6000))
    started = find_pin(ia_node, "Started", "Output")
    gao = cge.add_call_function_node("/Script/Engine.GameplayStatics:GetAllActorsOfClass")
    bel.set_node_pos(gao, pos(400, 6000))
    connect(started, find_pin(gao, "execute", "Input"), "T->gao")
    cls = find_pin(gao, "ActorClass", "Input") or find_pin(gao, "Class", "Input")
    setdef(cls, "/Script/FarmSim25D.FarmClock")
    try:
        if cls: cls.set_default_value("/Script/FarmSim25D.FarmClock")
    except Exception: pass
    get0 = cge.add_call_function_node("/Script/Engine.KismetArrayLibrary:Array_Get")
    bel.set_node_pos(get0, pos(750, 6080))
    connect(find_pin(gao, "OutActors", "Output"), find_pin(get0, "TargetArray", "Input") or find_pin(get0, "Array", "Input"), "arr")
    setdef(find_pin(get0, "Index", "Input"), "0")
    rc = cge.add_call_function_node("/Script/FarmSim25D.FarmClock:RestoreClock")
    bel.set_node_pos(rc, pos(1100, 6000))
    connect(find_pin(gao, "then", "Output"), find_pin(rc, "execute", "Input"), "gao->rc")
    connect(out_data(get0) or find_pin(get0, "Item", "Output"), find_pin(rc, "self", "Input"), "clock")
    sp = find_pin(rc, "SavedState", "Input")
    if sp:
        try: sp.set_pin_value("(AbsoluteDay=1,Minutes=1020.000000)")
        except Exception: setdef(sp, "(AbsoluteDay=1,Minutes=1020.000000)")
    pr = make_print(cge, 1500, 6000, "Time \u2192 17:00", dur="3.0", key="SkipTo17")
    connect(find_pin(rc, "then", "Output"), find_pin(pr, "execute", "Input"), "rc->pr")
    log("wired T -> 17:00")
    R["ok"].append("T->17:00")

# Compile save
for path in (CHAR, MGR):
    bp = eas.load_asset(path)
    bel.compile_blueprint(bp)
    eas.save_asset(path)
    log("compiled " + path.split("/")[-1])
for path in (IMC, IA_PATH, MAT_OPEN, MAT_CLOSED):
    if eas.does_asset_exist(path):
        eas.save_asset(path)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log(str(e)[:60])
try:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
except Exception:
    pass

# Verify chains
def chain_titles(ge, name):
    ev = find_custom(ge, name)
    if not ev: return []
    out = []
    cur = ev
    for _ in range(15):
        tp = find_pin(cur, "then", "Output")
        if not tp or not tp.list_connected_pins(): break
        cur = tp.list_connected_pins()[0].get_owning_node()
        out.append(title(cur))
    return out

R["salad_chain"] = chain_titles(mge, "OnGuestPaidSalad")
R["stew_chain"] = chain_titles(mge, "OnGuestPaidStew")
R["grant_salad"] = chain_titles(cge, "GrantMoney_Salad")
log("salad_chain " + str(R["salad_chain"]))
log("stew_chain " + str(R["stew_chain"]))

out = unreal.Paths.project_saved_dir() + "restaurant_batch2.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, indent=2, ensure_ascii=False)
log("DONE errors=" + str(len(R["errors"])) + " ok=" + str(R["ok"]))
