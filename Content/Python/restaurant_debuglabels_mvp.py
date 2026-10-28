# -*- coding: utf-8 -*-
"""Bulletproof restaurant labels: destroy empty-mat RestName_*, DrawDebug on Manager Tick + Chinese near Print."""
import unreal
import json

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
PATH = "/Game/Farm/Restaurant/BP_RestaurantManager"
R = {"steps": [], "errors": [], "destroyed": [], "wired": {}}

PROPS = [
    # key, cn, eng, x, y, z_base, color RGBA
    ("OpenSign", "\u5f00\u4e1a\u724c", "OPEN", 1680.0, 500.0, 81.0, (0.0, 1.0, 1.0, 1.0)),      # cyan
    ("Stove", "\u7076\u53f0", "STOVE", 2080.0, 700.0, 53.0, (1.0, 0.55, 0.1, 1.0)),          # orange
    ("Table1", "\u9910\u684c1", "T1", 1820.0, 300.0, 28.0, (1.0, 1.0, 0.2, 1.0)),              # yellow
    ("Table2", "\u9910\u684c2", "T2", 2080.0, 300.0, 28.0, (0.4, 1.0, 0.2, 1.0)),              # lime
    ("Trash", "\u5783\u573e\u6876", "TRASH", 1780.0, 700.0, 40.0, (1.0, 0.2, 1.0, 1.0)),      # magenta
]
Z_OFF = 120.0

def log(m):
    unreal.log("[REST_DBGLBL] " + str(m))
    R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    substr = substr.lower()
    cands = []
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                cands.append(p)
    return cands[0] if cands else None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip conn " + label)
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
            log("setdef fail " + str(e)[:80])
            return False

def out_data(node):
    if not node:
        return None
    for name in ("ReturnValue", "Return Value"):
        p = find_pin(node, name, "Output")
        if p:
            return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate", "then", "completed", "loopbody"):
                return p
    return None

def make_vector(ge, x, y, z, nx, ny):
    n = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(n, pos(nx, ny))
    setdef(find_pin(n, "X", "Input"), "{:.1f}".format(x))
    setdef(find_pin(n, "Y", "Input"), "{:.1f}".format(y))
    setdef(find_pin(n, "Z", "Input"), "{:.1f}".format(z))
    return n

def color_str(rgba):
    # UE pin default for LinearColor often: (R=..,G=..,B=..,A=..)
    r, g, b, a = rgba
    return "(R={:.3f},G={:.3f},B={:.3f},A={:.3f})".format(r, g, b, a)

# ---------- 1) Destroy RestName_* / leftover RestLabel_* ----------
destroyed = 0
for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if lab.startswith("RestName_") or lab.startswith("RestLabel_"):
        R["destroyed"].append(lab)
        eas.destroy_actor(a)
        destroyed += 1
log("destroyed_labels={}".format(destroyed))
R["restname_failure"] = (
    "RestName_* StaticMeshActors existed (visible flags true) but M_RestLabel_* materials "
    "had EMPTY material graphs (expr_count=0) with Blend Masked — opacity mask unconnected "
    "so planes clipped fully invisible. Destroyed; replaced by DrawDebug."
)

# ---------- 2) Wire Manager ----------
bp = unreal.EditorAssetLibrary.load_asset(PATH)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Remove prior DrawRestDebugLabels custom + orphan calls if re-run
kill = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if (c == "K2Node_CustomEvent" and t == "DrawRestDebugLabels") or (c == "K2Node_CallFunction" and t == "DrawRestDebugLabels"):
        kill.append(n)
# Also kill nodes tagged by comment? skip — only remove our event and its call sites; body nodes may orphan
if kill:
    for n in kill:
        for p in bel.list_all_pins(n):
            try:
                p.break_pin_links()
            except Exception:
                pass
    ge.remove_nodes(kill)
    log("removed old DrawRestDebugLabels nodes={}".format(len(kill)))

# Purge orphan DrawDebug nodes from previous failed runs at high Y? Look for nodes with comment RestDbg
# Safer: only add fresh at Y=5200 area; if re-run multiple times graph grows — remove DrawDebugString/Sphere at y>~5000
high_dbg = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if t in ("DrawDebugString", "DrawDebugSphere", "MakeVector", "GetPlayerPawn", "Vector_Distance", "Branch", "PrintString"):
        try:
            np = bel.get_node_pos(n)
            if np and np.y >= 5000:
                # only remove if not clearly part of other systems — use y band 5000-9000
                if np.y < 9500:
                    high_dbg.append(n)
        except Exception:
            pass
if high_dbg:
    for n in high_dbg:
        for p in bel.list_all_pins(n):
            try:
                p.break_pin_links()
            except Exception:
                pass
    ge.remove_nodes(high_dbg)
    log("purged prior dbg band nodes={}".format(len(high_dbg)))

BASE_Y = 5200
ev = ge.add_custom_event_node("DrawRestDebugLabels")
bel.set_node_pos(ev, pos(0, BASE_Y))
log("added DrawRestDebugLabels")

prev_then = find_pin(ev, "then", "Output")
cursor_x = 300

# Get player once for near hints
pawn = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(pawn, pos(50, BASE_Y + 700))
setdef(find_pin(pawn, "PlayerIndex", "Input"), "0")
# GetActorLocation on pawn
get_loc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
if get_loc is None:
    get_loc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
bel.set_node_pos(get_loc, pos(50, BASE_Y + 820))
# GetPlayerPawn is pure usually; connect ReturnValue -> self of GetActorLocation
connect(out_data(pawn), find_pin(get_loc, "self", "Input"), "pawn->getloc")

for i, (key, cn, eng, x, y, z, rgba) in enumerate(PROPS):
    row = BASE_Y + i * 180
    lx, ly, lz = x, y, z + Z_OFF
    label_text = "{} {}".format(eng, cn)  # both English code + Chinese

    mv = make_vector(ge, lx, ly, lz, cursor_x, row)

    # Sphere
    sph = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
    bel.set_node_pos(sph, pos(cursor_x + 350, row))
    connect(prev_then, find_pin(sph, "execute", "Input"), "exec->sph"+key)
    connect(out_data(mv), find_pin(sph, "Center", "Input"), "ctr->sph"+key)
    setdef(find_pin(sph, "Radius", "Input"), "28.0")
    setdef(find_pin(sph, "Segments", "Input"), "10")
    setdef(find_pin(sph, "Duration", "Input"), "0.0")  # one frame
    setdef(find_pin(sph, "Thickness", "Input"), "3.0")
    # LineColor / Color pin
    for cname in ("LineColor", "Color", "TextColor"):
        cp = find_pin(sph, cname, "Input")
        if cp:
            setdef(cp, color_str(rgba))
            break

    # String
    ds = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
    bel.set_node_pos(ds, pos(cursor_x + 700, row))
    connect(find_pin(sph, "then", "Output"), find_pin(ds, "execute", "Input"), "sph->str"+key)
    # text location slightly above sphere
    mv2 = make_vector(ge, lx, ly, lz + 40.0, cursor_x, row + 70)
    connect(out_data(mv2), find_pin(ds, "TextLocation", "Input") or find_pin(ds, "text_location", "Input"), "loc->str"+key)
    setdef(find_pin(ds, "Text", "Input") or find_pin(ds, "InString", "Input"), label_text)
    setdef(find_pin(ds, "Duration", "Input"), "0.0")
    for cname in ("TextColor", "Color"):
        cp = find_pin(ds, cname, "Input")
        if cp:
            setdef(cp, color_str(rgba))
            break

    prev_then = find_pin(ds, "then", "Output")

# Near-hint Chinese Print (Key=RestHint) — chain after last draw
# For each prop: distance check; use Sequence-like serial branches
hint_y = BASE_Y + 5 * 180 + 40
near_prev = prev_then
player_loc = out_data(get_loc)

for i, (key, cn, eng, x, y, z, rgba) in enumerate(PROPS):
    row = hint_y + i * 160
    lx, ly, lz = x, y, z + Z_OFF
    mv = make_vector(ge, lx, ly, lz, 50, row)
    dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance")
    if dist is None:
        dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Distance")
    bel.set_node_pos(dist, pos(350, row))
    # V1=player V2=prop (pin names vary)
    p1 = find_pin(dist, "V1", "Input") or find_pin(dist, "A", "Input")
    p2 = find_pin(dist, "V2", "Input") or find_pin(dist, "B", "Input")
    connect(player_loc, p1, "ploc->d"+key)
    connect(out_data(mv), p2, "prop->d"+key)

    # Less Equal float
    le = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble")
    if le is None:
        le = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    bel.set_node_pos(le, pos(600, row))
    connect(out_data(dist), find_pin(le, "A", "Input"), "dist->le"+key)
    setdef(find_pin(le, "B", "Input"), "250.0")

    br = ge.add_branch_node() if hasattr(ge, "add_branch_node") else None
    if br is None:
        # K2Node_IfThenElse via add_node
        try:
            br = ge.add_node(unreal.K2Node_IfThenElse.static_class(), unreal.Vector2D(800, row))
        except Exception:
            br = None
    if br is None:
        # fallback: skip near print for this one
        log("no branch for " + key)
        continue
    bel.set_node_pos(br, pos(850, row))
    connect(near_prev, find_pin(br, "execute", "Input"), "exec->br"+key)
    connect(out_data(le), find_pin(br, "Condition", "Input"), "cond"+key)

    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(1150, row))
    setdef(find_pin(pr, "InString", "Input"), "\u3010{}\u3011{}  ({})".format(cn, eng, key))
    setdef(find_pin(pr, "Key", "Input"), "RestHint")
    setdef(find_pin(pr, "Duration", "Input"), "0.15")
    # TextColor
    for cname in ("TextColor",):
        cp = find_pin(pr, cname, "Input")
        if cp:
            setdef(cp, color_str(rgba))
    connect(find_pin(br, "then", "Output"), find_pin(pr, "execute", "Input"), "then->pr"+key)
    # false and print then both continue
    # Use Sequence manually: near_prev = br else OR print then — connect both to a Reroute? 
    # Simpler: chain through else always (continue even if near), and fire print on true without blocking
    # Actually: near_prev = else of branch; print is side fire on true with no further chain needed
    near_prev = find_pin(br, "else", "Output")

R["wired"]["draw_event"] = True

# ---------- 3) Append to Tick: RestaurantTick call then -> DrawRestDebugLabels ----------
tick_call_rt = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "RestaurantTick" and n.get_class().get_name() == "K2Node_CallFunction":
        # the call from Event Tick
        tick_call_rt = n
        break

call_draw = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:DrawRestDebugLabels")
if call_draw is None:
    # try without _C
    call_draw = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager:DrawRestDebugLabels")
bel.set_node_pos(call_draw, pos(600, 1400))
if tick_call_rt and call_draw:
    then_rt = find_pin(tick_call_rt, "then", "Output")
    # break any existing then links on call_rt then? should be empty
    connect(then_rt, find_pin(call_draw, "execute", "Input"), "TickRT->DrawLabels")
    R["wired"]["tick_chain"] = True
else:
    # Fallback: Sequence from Event Tick
    log("WARN no tick_call_rt or call_draw; trying Event Tick Sequence")
    tick_n = None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "Event Tick":
            tick_n = n
            break
    if tick_n and call_draw:
        # insert sequence
        try:
            seq = ge.add_sequence_node(2) if hasattr(ge, "add_sequence_node") else None
        except Exception:
            seq = None
        if seq is None:
            try:
                seq = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:Sequence")
            except Exception:
                seq = None
        if seq:
            bel.set_node_pos(seq, pos(200, 1350))
            then_tick = find_pin(tick_n, "then", "Output")
            # reconnect: break tick->rt, tick->seq, then0->rt, then1->draw
            old = list(then_tick.list_connected_pins()) if then_tick else []
            if then_tick:
                then_tick.break_pin_links()
            connect(then_tick, find_pin(seq, "execute", "Input"), "tick->seq")
            t0 = find_pin(seq, "then_0", "Output") or find_pin(seq, "Then 0", "Output")
            t1 = find_pin(seq, "then_1", "Output") or find_pin(seq, "Then 1", "Output")
            if old:
                connect(t0, old[0], "seq0->old")
            connect(t1, find_pin(call_draw, "execute", "Input"), "seq1->draw")
            R["wired"]["tick_sequence"] = True
        else:
            R["errors"].append("could not wire tick to draw")

# ---------- 4) BeginPlay once Print ----------
bp_node = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "Event BeginPlay":
        bp_node = n
        break
if bp_node:
    then_bp = find_pin(bp_node, "then", "Output")
    existing = list(then_bp.list_connected_pins()) if then_bp else []
    msg = (
        "Rest labels: OpenSign/Stove/Table1/Table2/Trash | "
        "\u5f00\u4e1a\u724c/\u7076\u53f0/\u9910\u684c1/\u9910\u684c2/\u5783\u573e\u6876 | "
        "locs (1680,500)(2080,700)(1820,300)(2080,300)(1780,700)"
    )
    pr0 = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr0, pos(300, 40))
    setdef(find_pin(pr0, "InString", "Input"), msg)
    setdef(find_pin(pr0, "Duration", "Input"), "8.0")
    setdef(find_pin(pr0, "Key", "Input"), "RestLabelsBoot")
    if not existing:
        connect(then_bp, find_pin(pr0, "execute", "Input"), "BP->print")
    else:
        # append after last? or sequence — append via connecting print after first target's then if free
        # put Sequence at start
        try:
            seq = ge.add_macro_node("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:Sequence")
        except Exception:
            seq = None
        if seq:
            bel.set_node_pos(seq, pos(150, 20))
            then_bp.break_pin_links()
            connect(then_bp, find_pin(seq, "execute", "Input"), "BP->seq")
            t0 = find_pin(seq, "then_0", "Output") or find_pin(seq, "Then 0", "Output")
            t1 = find_pin(seq, "then_1", "Output") or find_pin(seq, "Then 1", "Output")
            connect(t0, existing[0], "seq0->oldbp")
            connect(t1, find_pin(pr0, "execute", "Input"), "seq1->print")
        else:
            connect(then_bp, find_pin(pr0, "execute", "Input"), "BP->print_extra")
    R["wired"]["beginplay_print"] = True

# ---------- 5) Bump interact PrintStrings with Chinese ----------
REPLACEMENTS = [
    ("Restaurant STOVE:", "\u3010\u7076\u53f0\u3011Restaurant STOVE:"),
    ("Restaurant TABLE", "\u3010\u9910\u684c\u3011Restaurant TABLE"),
    ("Restaurant TRASH:", "\u3010\u5783\u573e\u6876\u3011Restaurant TRASH:"),
    ("Restaurant: OPEN", "\u3010\u5f00\u4e1a\u724c\u3011Restaurant: OPEN"),
    ("Restaurant: too early", "\u3010\u5f00\u4e1a\u724c\u3011Restaurant: too early"),
    ("Restaurant: too late", "\u3010\u5f00\u4e1a\u724c\u3011Restaurant: too late"),
    ("Restaurant: CLOSED", "\u3010\u5f00\u4e1a\u724c\u3011Restaurant: CLOSED"),
    ("Restaurant HOLD", "\u3010\u7076\u53f0\u3011Restaurant HOLD"),
    ("Restaurant SERVE", "\u3010\u9910\u684c\u3011Restaurant SERVE"),
    ("Restaurant WRONG", "\u3010\u9910\u684c\u3011Restaurant WRONG"),
    ("Restaurant E (other)", "\u3010?\u3011Restaurant E (other)"),
]
changed = 0
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "PrintString":
        continue
    pin = find_pin(n, "InString", "Input")
    if not pin:
        continue
    try:
        cur = pin.get_pin_value() or ""
    except Exception:
        cur = ""
    # skip if already has Chinese bracket
    if "\u3010" in cur:
        continue
    for old, new in REPLACEMENTS:
        if old in cur:
            setdef(pin, cur.replace(old, new, 1))
            changed += 1
            break
log("interact_prints_zh={}".format(changed))
R["wired"]["interact_zh"] = changed

# Compile + save
try:
    bel.compile_blueprint(bp)
    R["compiled"] = True
    log("compiled")
except Exception as e:
    R["errors"].append("compile " + str(e))
    R["compiled"] = False

unreal.EditorAssetLibrary.save_asset(PATH)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"] = True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        R["level_saved"] = True
    except Exception as e:
        R["errors"].append("save level " + str(e))
        R["level_saved"] = False

# Verify tick chain
verify = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "Event Tick":
        then = find_pin(n, "then", "Output")
        verify.append({"tick_to": [bel.get_node_title(p.get_owning_node()) for p in then.list_connected_pins()]})
    if bel.get_node_title(n) == "RestaurantTick" and n.get_class().get_name() == "K2Node_CallFunction":
        then = find_pin(n, "then", "Output")
        verify.append({"rt_call_to": [bel.get_node_title(p.get_owning_node()) for p in then.list_connected_pins()]})
    if bel.get_node_title(n) == "DrawRestDebugLabels" and n.get_class().get_name() == "K2Node_CustomEvent":
        then = find_pin(n, "then", "Output")
        verify.append({"draw_to": [bel.get_node_title(p.get_owning_node()) for p in then.list_connected_pins()]})
R["verify"] = verify

# One-shot editor preview spheres+strings so user may see in viewport even before PIE
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for key, cn, eng, x, y, z, rgba in PROPS:
        loc = unreal.Vector(x, y, z + Z_OFF)
        col = unreal.LinearColor(rgba[0], rgba[1], rgba[2], rgba[3])
        unreal.SystemLibrary.draw_debug_sphere(world, loc, 30.0, 12, col, 45.0, 4.0)
        unreal.SystemLibrary.draw_debug_string(world, unreal.Vector(x, y, z + Z_OFF + 40), "{} {}".format(eng, cn), None, col, 45.0)
    R["editor_preview_drawn"] = True
except Exception as e:
    R["editor_preview_drawn"] = False
    R["errors"].append("preview " + str(e)[:120])

out = r"E:\UE\FarmSim25D\Saved\restaurant_debuglabels_mvp.json"
open(out, "w", encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps(R, ensure_ascii=False, indent=2))
