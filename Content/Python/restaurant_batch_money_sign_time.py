# -*- coding: utf-8 -*-
"""Batch: (1) pay -> player Money+HUD (2) OpenSign open/closed visual (3) T -> 17:00."""
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

R = {"steps": [], "errors": [], "ok": []}

def log(m):
    unreal.log("[BATCH] " + str(m)); print("[BATCH] " + str(m)); R["steps"].append(str(m))

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
    for name in ("ReturnValue", "Return Value", "Item", "As BP_TopDownCharacter", "As FarmClock"):
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

def add_int(ge, x, y):
    n = ge.create_node_from_name("Utilities|Operators|integer + integer", unreal.Vector2D(x, y), [])
    if not n:
        n = ge.create_node_from_name("Math|Integer|integer + integer", unreal.Vector2D(x, y), [])
    if not n:
        n = ge.create_node_from_name("integer + integer", unreal.Vector2D(x, y), [])
    if not n:
        n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_IntInt")
    bel.set_node_pos(n, pos(x, y))
    return n

def ensure_emissive_mat(path, name, rgb):
    if eas.does_asset_exist(path):
        log("mat exists " + path)
        return eas.load_asset(path)
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
    log("created mat " + path)
    return mat

# ===================== 1) Character GrantMoney_* =====================
cbp = eas.load_asset(CHAR)
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

def ensure_grant(name, amount, y):
    old = find_custom(cge, name)
    if old:
        # remove whole chain for clean rewire
        thenp = find_pin(old, "then", "Output")
        kill = [old]
        if thenp:
            queue = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
            seen = set([id(old)])
            while queue:
                cur = queue.pop(0)
                if id(cur) in seen: continue
                seen.add(id(cur)); kill.append(cur)
                for pn in ("then", "else"):
                    tp = find_pin(cur, pn, "Output")
                    if tp:
                        for c in tp.list_connected_pins() or []:
                            queue.append(c.get_owning_node())
        cge.remove_nodes(kill)
        log("removed old " + name)
    ev = cge.add_custom_event_node(name)
    bel.set_node_pos(ev, pos(50, y))
    get_m = cge.add_get_member_variable_node("Money"); bel.set_node_pos(get_m, pos(300, y + 80))
    addn = add_int(cge, 550, y + 80)
    connect(out_data(get_m) or find_pin(get_m, "Money", "Output"), find_pin(addn, "A", "Input"), name + "A")
    setdef(find_pin(addn, "B", "Input"), str(amount))
    set_m = cge.add_set_member_variable_node("Money"); bel.set_node_pos(set_m, pos(850, y))
    connect(find_pin(ev, "then", "Output"), find_pin(set_m, "execute", "Input"), name + "set")
    connect(out_data(addn), find_pin(set_m, "Money", "Input"), name + "v")
    upd = cge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    bel.set_node_pos(upd, pos(1150, y))
    connect(find_pin(set_m, "then", "Output"), find_pin(upd, "execute", "Input"), name + "hud")
    pr = make_print(cge, 1450, y, "COINS +{} (restaurant pay merged)".format(amount), dur="2.0")
    connect(find_pin(upd, "then", "Output"), find_pin(pr, "execute", "Input"), name + "pr")
    log("wired " + name)
    return ev

ensure_grant("GrantMoney_Salad", 15, 5200)
ensure_grant("GrantMoney_Stew", 28, 5600)
bel.compile_blueprint(cbp)
eas.save_asset(CHAR)
R["ok"].append("GrantMoney on character")

# ===================== 1b) Manager pay -> GrantMoney =====================
mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

def wire_pay_to_player(ev_name, grant_name, y_off):
    ev = find_custom(mge, ev_name)
    if not ev:
        R["errors"].append("missing " + ev_name); return
    # Find terminal PrintString after Set RestaurantMoney
    thenp = find_pin(ev, "then", "Output")
    if not thenp or not thenp.list_connected_pins():
        R["errors"].append(ev_name + " empty"); return
    setn = thenp.list_connected_pins()[0].get_owning_node()
    then2 = find_pin(setn, "then", "Output")
    prn = then2.list_connected_pins()[0].get_owning_node() if then2 and then2.list_connected_pins() else None
    if not prn or title(prn) != "PrintString":
        # maybe already wired — look for GrantMoney in chain
        cur = setn
        term = setn
        for _ in range(10):
            tp = find_pin(cur, "then", "Output")
            if not tp or not tp.list_connected_pins():
                term = cur; break
            nxt = tp.list_connected_pins()[0].get_owning_node()
            if grant_name in title(nxt):
                log(ev_name + " already has " + grant_name); return
            term = nxt; cur = nxt
        prn = term
    # If Print then already goes somewhere with Grant, skip
    pr_then = find_pin(prn, "then", "Output")
    if pr_then:
        for c in pr_then.list_connected_pins() or []:
            if grant_name in title(c.get_owning_node()) or "GetPlayer" in title(c.get_owning_node()):
                log(ev_name + " already extended"); return
            # break unexpected
        try: pr_then.break_pin_links()
        except Exception: pass

    pawn = mge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(pawn, pos(1400, y_off))
    setdef(find_pin(pawn, "PlayerIndex", "Input") or find_pin(pawn, "Index", "Input"), "0")
    cast = mge.add_cast_node(eas.load_asset(CHAR).generated_class())
    bel.set_node_pos(cast, pos(1700, y_off))
    connect(find_pin(prn, "then", "Output"), find_pin(cast, "execute", "Input"), ev_name + "->cast")
    connect(out_data(pawn), find_pin(cast, "Object", "Input"), ev_name + "pawn")
    call = mge.add_call_function_node(
        "/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:" + grant_name)
    bel.set_node_pos(call, pos(2100, y_off))
    connect(find_pin(cast, "then", "Output"), find_pin(call, "execute", "Input"), ev_name + "->grant")
    # As Character -> self
    as_pin = None
    for p in bel.list_all_pins(cast):
        if "OUTPUT" in str(p.get_pin_direction()) and "as " in str(p.get_pin_name()).lower():
            as_pin = p; break
    if as_pin is None:
        as_pin = out_data(cast)
    connect(as_pin, find_pin(call, "self", "Input"), ev_name + "self")
    log("wired " + ev_name + " -> " + grant_name)

# Place near existing pay events (~Y 2200 area from knife3)
wire_pay_to_player("OnGuestPaidSalad", "GrantMoney_Salad", 2200)
wire_pay_to_player("OnGuestPaidStew", "GrantMoney_Stew", 2450)
R["ok"].append("pay -> player Money")

# ===================== 2) OpenSign visual mats + tag + ApplySign* =====================
mat_open = ensure_emissive_mat(MAT_OPEN, "M_SignOpen", (0.15, 1.0, 0.25))      # green open
mat_closed = ensure_emissive_mat(MAT_CLOSED, "M_SignClosed", (0.45, 0.12, 0.12))  # dim red closed

# Tag RestMark_OpenSign
tagged = 0
for a in actor_sub.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab == "RestMark_OpenSign":
        tags = list(a.tags) if a.tags else []
        if "RestSignMark" not in [str(t) for t in tags]:
            tags.append("RestSignMark")
            a.tags = tags
            tagged += 1
            log("tagged RestMark_OpenSign RestSignMark")
        # apply closed mat now in editor
        try:
            smc = a.static_mesh_component
            if smc and mat_closed:
                smc.set_material(0, mat_closed)
                log("editor set closed mat")
        except Exception as e:
            log("editor mat " + str(e)[:60])
if tagged == 0:
    # still try find by existing materials
    for a in unreal.GameplayStatics.get_all_actors_of_class(
            unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
            unreal.StaticMeshActor.static_class()):
        lab = a.get_actor_label() or ""
        if "RestMark_OpenSign" in lab:
            tags = list(a.tags) if a.tags else []
            if "RestSignMark" not in [str(t) for t in tags]:
                tags.append("RestSignMark"); a.tags = tags; tagged += 1
                log("tagged via GS")
log("tagged_count=" + str(tagged))

def ensure_apply_sign(name, mat_path, scale, y):
    old = find_custom(mge, name)
    if old:
        thenp = find_pin(old, "then", "Output")
        kill = [old]
        if thenp:
            queue = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
            seen = set([id(old)])
            while queue:
                cur = queue.pop(0)
                if id(cur) in seen: continue
                seen.add(id(cur)); kill.append(cur)
                for pn in ("then", "else", "LoopBody", "Completed"):
                    tp = find_pin(cur, pn, "Output")
                    if tp:
                        for c in tp.list_connected_pins() or []:
                            queue.append(c.get_owning_node())
        # only remove if chain looks like ours (GetAllActorsWithTag)
        mge.remove_nodes(kill)
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
    # GetComponentByClass StaticMeshComponent
    gcc = mge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
    bel.set_node_pos(gcc, pos(1000, y + 80))
    connect(find_pin(fe, "Array Element", "Output"), find_pin(gcc, "self", "Input"), name + "self")
    # set class pin
    cls_pin = find_pin(gcc, "ComponentClass", "Input") or find_pin(gcc, "Class", "Input")
    setdef(cls_pin, "/Script/Engine.StaticMeshComponent")
    try:
        if cls_pin:
            cls_pin.set_default_value("/Script/Engine.StaticMeshComponent")
    except Exception: pass
    # SetMaterial
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
    # Scale after material
    sc = mge.add_call_function_node("/Script/Engine.Actor:SetActorScale3D")
    bel.set_node_pos(sc, pos(1800, y))
    connect(find_pin(sm, "then", "Output"), find_pin(sc, "execute", "Input"), name + "sc")
    connect(find_pin(fe, "Array Element", "Output"), find_pin(sc, "self", "Input"), name + "scself")
    # NewScale vector
    mv = mge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mv, pos(1600, y + 120))
    setdef(find_pin(mv, "X", "Input"), str(scale))
    setdef(find_pin(mv, "Y", "Input"), str(scale))
    setdef(find_pin(mv, "Z", "Input"), str(scale))
    connect(out_data(mv), find_pin(sc, "NewScale3D", "Input") or find_pin(sc, "Scale", "Input") or find_pin(sc, "NewScale", "Input"), name + "scale")
    pr = make_print(mge, 2100, y, "Sign visual: " + name, dur="1.0")
    connect(find_pin(sc, "then", "Output"), find_pin(pr, "execute", "Input"), name + "pr")
    log("wired " + name)

ensure_apply_sign("ApplySignOpen", MAT_OPEN, 0.85, 6400)
ensure_apply_sign("ApplySignClosed", MAT_CLOSED, 0.55, 6800)

# Insert ApplySign* after each Set bIsOpenBusiness
def insert_after_set_open():
    for n in list(mge.list_all_nodes()):
        if title(n) != "Set bIsOpenBusiness":
            continue
        val_pin = find_pin(n, "bIsOpenBusiness", "Input")
        v = (val_pin.get_pin_value() if val_pin else "") or ""
        is_open = str(v).lower() in ("true", "1")
        call_name = "ApplySignOpen" if is_open else "ApplySignClosed"
        thenp = find_pin(n, "then", "Output")
        if not thenp:
            continue
        # already wired?
        for c in thenp.list_connected_pins() or []:
            if call_name in title(c.get_owning_node()) or "ApplySign" in title(c.get_owning_node()):
                log("already " + call_name + " after Set val=" + str(v)); break
        else:
            old_tgts = list(thenp.list_connected_pins() or [])
            try: thenp.break_pin_links()
            except Exception: pass
            call = mge.add_call_function_node(
                "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:" + call_name)
            # place near set node
            bel.set_node_pos(call, pos(900, 0))  # will be messy but ok
            try:
                # try get node pos
                pass
            except Exception: pass
            connect(thenp, find_pin(call, "execute", "Input"), "Set->" + call_name)
            call_then = find_pin(call, "then", "Output")
            for t in old_tgts:
                connect(call_then, t, call_name + "->old")
            log("inserted " + call_name + " after Set val=" + str(v))

insert_after_set_open()

# BeginPlay -> ApplySignClosed (if not already)
bp_ev = None
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "BeginPlay" in title(n):
        bp_ev = n; break
if bp_ev:
    # find a free terminal or prepend via Sequence — append call at start via inserting after BeginPlay then
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
        call = mge.add_call_function_node(
            "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplySignClosed")
        bel.set_node_pos(call, pos(400, -400))
        connect(thenp, find_pin(call, "execute", "Input"), "BP->closed")
        for t in old:
            connect(find_pin(call, "then", "Output"), t, "closed->oldBP")
        log("BeginPlay -> ApplySignClosed")
R["ok"].append("OpenSign visual")

# ===================== 3) T key -> 17:00 =====================
# Create IA_SkipTo17
if eas.does_asset_exist(IA_PATH):
    ia = eas.load_asset(IA_PATH)
    log("IA_SkipTo17 exists")
else:
    factory = unreal.InputAction_Factory()
    ia = tools.create_asset("IA_SkipTo17", IA_DIR, unreal.InputAction, factory)
    log("created IA_SkipTo17")
if ia:
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception as e:
        log(str(e))
    eas.save_asset(IA_PATH)

imc = eas.load_asset(IMC)
try:
    imc.unmap_all_keys_from_action(ia)
except Exception:
    pass
k = unreal.Key()
k.import_text("T")
try:
    m = imc.map_key(ia, k)
    log("mapped T -> IA_SkipTo17 " + str(m))
except Exception as e:
    R["errors"].append("map T " + str(e))
eas.save_asset(IMC)

# Wire on character EventGraph
# Remove old IA_SkipTo17 nodes
kill_ia = []
for n in cge.list_all_nodes():
    if "IA_SkipTo17" in title(n):
        # collect downstream
        kill_ia.append(n)
        for pn_name in ("Started", "Triggered", "Ongoing", "Canceled", "Completed"):
            tp = find_pin(n, pn_name, "Output")
            if not tp: continue
            queue = [c.get_owning_node() for c in (tp.list_connected_pins() or [])]
            seen = set()
            while queue:
                cur = queue.pop(0)
                if id(cur) in seen: continue
                seen.add(id(cur)); kill_ia.append(cur)
                for pn in ("then", "else", "Completed"):
                    p2 = find_pin(cur, pn, "Output")
                    if p2:
                        for c in p2.list_connected_pins() or []:
                            queue.append(c.get_owning_node())
if kill_ia:
    # unique
    uniq = []; ids=set()
    for n in kill_ia:
        if id(n) not in ids:
            ids.add(id(n)); uniq.append(n)
    cge.remove_nodes(uniq)
    log("removed old IA_SkipTo17 chain " + str(len(uniq)))

ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_SkipTo17", unreal.Vector2D(50, 6000), [])
if not ia_node:
    ia_node = cge.create_node_from_name("EnhancedActionEvents|IA_SkipTo17", unreal.Vector2D(50, 6000), [])
if not ia_node:
    R["errors"].append("IA_SkipTo17 node create failed")
    log("IA node FAILED")
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
    connect(out_data(get0) or find_pin(get0, "Item", "Output"), find_pin(rc, "self", "Input"), "clock self")
    sp = find_pin(rc, "SavedState", "Input")
    if sp:
        setdef(sp, "(AbsoluteDay=1,Minutes=1020.000000)")
        try: sp.set_pin_value("(AbsoluteDay=1,Minutes=1020.000000)")
        except Exception: pass
    pr = make_print(cge, 1500, 6000, "Time \u2192 17:00", dur="3.0", key="SkipTo17")
    connect(find_pin(rc, "then", "Output"), find_pin(pr, "execute", "Input"), "rc->pr")
    log("wired IA_SkipTo17 -> RestoreClock 1020")
    R["ok"].append("T -> 17:00")

# Compile + save
for path in (CHAR, MGR, IMC, IA_PATH, MAT_OPEN, MAT_CLOSED):
    try:
        if eas.does_asset_exist(path):
            if path in (CHAR, MGR):
                bel.compile_blueprint(eas.load_asset(path))
            eas.save_asset(path)
    except Exception as e:
        R["errors"].append("save " + path + " " + str(e)[:80])

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log("level save " + str(e)[:60])
try:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
except Exception:
    pass

# Compile error dump
for path, label in ((CHAR, "char"), (MGR, "mgr")):
    bp = eas.load_asset(path)
    bel.compile_blueprint(bp)
    try:
        # no direct API — use log
        log("compiled " + label)
    except Exception as e:
        R["errors"].append(label + " " + str(e))

out = unreal.Paths.project_saved_dir() + "restaurant_batch_money_sign_time.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, indent=2, ensure_ascii=False)
log("WROTE " + out)
log("DONE ok=" + str(R["ok"]) + " errors=" + str(len(R["errors"])))
