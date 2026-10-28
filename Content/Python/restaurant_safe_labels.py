# -*- coding: utf-8 -*-
"""Safe MVP labels: opaque color cubes + new BP_RestDebugLabels DrawDebug Tick. No Manager graph wipe."""
import unreal
import json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
R = {"steps": [], "errors": [], "destroyed": [], "marks": [], "bp": {}}

DIR = "/Game/Farm/Restaurant"
LABEL_DIR = DIR + "/Labels"
BP_PATH = DIR + "/BP_RestDebugLabels"
MGR = DIR + "/BP_RestaurantManager"

PROPS = [
    ("OpenSign", "\u5f00\u4e1a\u724c", "OPEN", 1680.0, 500.0, 81.0, (0.0, 1.0, 1.0)),
    ("Stove", "\u7076\u53f0", "STOVE", 2080.0, 700.0, 53.0, (1.0, 0.55, 0.1)),
    ("Table1", "\u9910\u684c1", "T1", 1820.0, 300.0, 28.0, (1.0, 1.0, 0.15)),
    ("Table2", "\u9910\u684c2", "T2", 2080.0, 300.0, 28.0, (0.35, 1.0, 0.2)),
    ("Trash", "\u5783\u573e\u6876", "TRASH", 1780.0, 700.0, 40.0, (1.0, 0.2, 1.0)),
]
Z_OFF = 120.0
CUBE = "/Engine/BasicShapes/Cube"

def log(m):
    unreal.log("[REST_SAFE_LBL] " + str(m))
    R["steps"].append(str(m))

def ensure_dir(p):
    if not unreal.EditorAssetLibrary.does_directory_exist(p):
        unreal.EditorAssetLibrary.make_directory(p)

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

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
            log("setdef " + str(e)[:60])
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

def color_str(rgb):
    r, g, b = rgb
    return "(R={:.3f},G={:.3f},B={:.3f},A=1.000)".format(r, g, b)

R["restname_failure"] = (
    "RestName_* existed with visible=true, Unlit Masked TwoSided, but M_RestLabel_* had "
    "EMPTY material graphs (expr_count=0). Masked with no OpacityMask => fully clipped/invisible."
)
for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if lab.startswith("RestName_") or lab.startswith("RestLabel_") or lab.startswith("RestMark_") or lab == "RestDebugLabels":
        R["destroyed"].append(lab)
        eas.destroy_actor(a)
log("destroyed={}".format(len(R["destroyed"])))

ensure_dir(LABEL_DIR)
mats = {}
for key, cn, eng, x, y, z, rgb in PROPS:
    mat_name = "M_RestMark_" + key
    mat_path = LABEL_DIR + "/" + mat_name
    if unreal.EditorAssetLibrary.does_asset_exist(mat_path):
        try:
            unreal.EditorAssetLibrary.delete_asset(mat_path)
        except Exception as e:
            log("del mat " + str(e)[:60])
    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(mat_name, LABEL_DIR, unreal.Material, factory)
    if not mat:
        R["errors"].append("mat fail " + key)
        continue
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception:
        pass
    try:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    except Exception:
        pass
    try:
        mat.set_editor_property("two_sided", True)
    except Exception:
        pass
    const = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -350, 0)
    const.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.connect_material_property(const, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(mat_path)
    mats[key] = mat
    log("mat " + mat_path)

cube_mesh = unreal.EditorAssetLibrary.load_asset(CUBE)
for key, cn, eng, x, y, z, rgb in PROPS:
    loc = unreal.Vector(x, y, z + Z_OFF)
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
    if not actor:
        R["errors"].append("spawn mark " + key)
        continue
    lab = "RestMark_" + key
    actor.set_actor_label(lab)
    try:
        actor.set_folder_path("Restaurant/Labels")
    except Exception:
        pass
    actor.set_actor_scale3d(unreal.Vector(0.35, 0.35, 0.35))
    smc = actor.static_mesh_component
    smc.set_editor_property("static_mesh", cube_mesh)
    if key in mats:
        smc.set_material(0, mats[key])
    try:
        smc.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    try:
        smc.set_editor_property("cast_shadow", False)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        smc.set_visibility(True, True)
        smc.set_hidden_in_game(False)
    except Exception:
        pass
    R["marks"].append({"label": lab, "cn": cn, "eng": eng, "loc": [x, y, z + Z_OFF]})
    log("mark " + lab)

if unreal.EditorAssetLibrary.does_asset_exist(BP_PATH):
    try:
        unreal.EditorAssetLibrary.delete_asset(BP_PATH)
        log("deleted old BP_RestDebugLabels")
    except Exception as e:
        log("del bp " + str(e)[:80])

factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.Actor)
bp = tools.create_asset("BP_RestDebugLabels", DIR, unreal.Blueprint, factory)
if not bp:
    R["errors"].append("bp create fail")
else:
    try:
        bel.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, 0))
    except Exception as e:
        log("beginplay ov " + str(e)[:80])
    try:
        bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 400))
    except Exception as e:
        log("tick ov " + str(e)[:80])

    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    bp_ev = None
    tick_ev = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        if c == "K2Node_Event" and "BeginPlay" in t:
            bp_ev = n
        if c == "K2Node_Event" and "Tick" in t:
            tick_ev = n

    msg = "Rest labels ON: OPEN/\u5f00\u4e1a\u724c STOVE/\u7076\u53f0 T1/\u9910\u684c1 T2/\u9910\u684c2 TRASH/\u5783\u573e\u6876"
    if bp_ev:
        pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(300, 0))
        setdef(find_pin(pr, "InString", "Input"), msg)
        setdef(find_pin(pr, "Duration", "Input"), "8.0")
        setdef(find_pin(pr, "Key", "Input"), "RestLabelsBoot")
        connect(find_pin(bp_ev, "then", "Output"), find_pin(pr, "execute", "Input"), "BP->print")
        R["bp"]["beginplay"] = True

    if tick_ev:
        prev = find_pin(tick_ev, "then", "Output")
        for i, (key, cn, eng, x, y, z, rgb) in enumerate(PROPS):
            row = 400 + i * 140
            lx, ly, lz = x, y, z + Z_OFF
            mv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
            bel.set_node_pos(mv, pos(200, row))
            setdef(find_pin(mv, "X", "Input"), "{:.1f}".format(lx))
            setdef(find_pin(mv, "Y", "Input"), "{:.1f}".format(ly))
            setdef(find_pin(mv, "Z", "Input"), "{:.1f}".format(lz))

            sph = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugSphere")
            bel.set_node_pos(sph, pos(500, row))
            connect(prev, find_pin(sph, "execute", "Input"), "->sph" + key)
            connect(out_data(mv), find_pin(sph, "Center", "Input"), "c" + key)
            setdef(find_pin(sph, "Radius", "Input"), "32.0")
            setdef(find_pin(sph, "Segments", "Input"), "10")
            setdef(find_pin(sph, "Duration", "Input"), "0.0")
            setdef(find_pin(sph, "Thickness", "Input"), "3.5")
            cp = find_pin(sph, "LineColor", "Input") or find_pin(sph, "Color", "Input")
            setdef(cp, color_str(rgb))

            mv2 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
            bel.set_node_pos(mv2, pos(200, row + 60))
            setdef(find_pin(mv2, "X", "Input"), "{:.1f}".format(lx))
            setdef(find_pin(mv2, "Y", "Input"), "{:.1f}".format(ly))
            setdef(find_pin(mv2, "Z", "Input"), "{:.1f}".format(lz + 45.0))

            ds = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugString")
            bel.set_node_pos(ds, pos(850, row))
            connect(find_pin(sph, "then", "Output"), find_pin(ds, "execute", "Input"), "sph->ds" + key)
            connect(out_data(mv2), find_pin(ds, "TextLocation", "Input"), "tl" + key)
            setdef(find_pin(ds, "Text", "Input"), "{} {}".format(eng, cn))
            setdef(find_pin(ds, "Duration", "Input"), "0.0")
            tcp = find_pin(ds, "TextColor", "Input") or find_pin(ds, "Color", "Input")
            setdef(tcp, color_str(rgb))
            prev = find_pin(ds, "then", "Output")
        R["bp"]["tick_draws"] = 5
    else:
        R["errors"].append("no tick event")

    try:
        bel.compile_blueprint(bp)
        R["bp"]["compiled"] = True
    except Exception as e:
        R["errors"].append("compile " + str(e)[:100])
        R["bp"]["compiled"] = False
    unreal.EditorAssetLibrary.save_asset(BP_PATH)

    cls = unreal.EditorAssetLibrary.load_blueprint_class(BP_PATH)
    if cls:
        inst = eas.spawn_actor_from_class(cls, unreal.Vector(1900, 500, 200), unreal.Rotator())
        if inst:
            inst.set_actor_label("RestDebugLabels")
            try:
                inst.set_folder_path("Restaurant")
            except Exception:
                pass
            R["bp"]["spawned"] = True
            log("spawned RestDebugLabels")
        else:
            R["errors"].append("spawn instance fail")
    else:
        R["errors"].append("load_blueprint_class fail")

changed = 0
try:
    mbp = unreal.EditorAssetLibrary.load_asset(MGR)
    mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
    REPL = [
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
    ]
    for n in mge.list_all_nodes():
        if bel.get_node_title(n) != "PrintString":
            continue
        pin = find_pin(n, "InString", "Input")
        if not pin:
            continue
        try:
            cur = pin.get_pin_value() or ""
        except Exception:
            cur = ""
        if "\u3010" in cur:
            continue
        for old, new in REPL:
            if old in cur:
                setdef(pin, cur.replace(old, new, 1))
                changed += 1
                break
    if changed:
        bel.compile_blueprint(mbp)
        unreal.EditorAssetLibrary.save_asset(MGR)
    log("mgr_prints_zh={}".format(changed))
    R["mgr_prints_zh"] = changed
except Exception as e:
    R["errors"].append("mgr prints " + str(e)[:120])

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"] = True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        R["level_saved"] = True
    except Exception as e:
        R["errors"].append("level " + str(e)[:80])
        R["level_saved"] = False

verify = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("RestMark_") or lab.startswith("RestName_") or lab == "RestDebugLabels" or lab.startswith("Restaurant_"):
        loc = a.get_actor_location()
        verify.append({"lab": lab, "cls": a.get_class().get_name(), "loc": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)]})
R["verify"] = verify

out = r"E:\UE\FarmSim25D\Saved\restaurant_safe_labels.json"
open(out, "w", encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps({k: R[k] for k in ("destroyed", "marks", "bp", "mgr_prints_zh", "level_saved", "errors", "restname_failure", "verify") if k in R}, ensure_ascii=False, indent=2))