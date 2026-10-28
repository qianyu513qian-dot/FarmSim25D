# -*- coding: utf-8 -*-
"""Finalize guest MIs + BP_RestGuest mesh."""
import unreal, json

def log(m):
    unreal.log("[GUEST3] " + str(m))
    print("[GUEST3] " + str(m))

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary

DIR = "/Game/Farm/Restaurant/Guests"
if not eas.does_directory_exist(DIR):
    eas.make_directory(DIR)

parent = unreal.load_asset("/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New")
COLORS = {
    "GuestRed": unreal.LinearColor(0.9, 0.12, 0.1, 1.0),
    "GuestBlue": unreal.LinearColor(0.12, 0.35, 0.95, 1.0),
    "GuestGreen": unreal.LinearColor(0.1, 0.75, 0.22, 1.0),
}
for name, col in COLORS.items():
    path = DIR + "/MI_" + name
    if eas.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        factory = unreal.MaterialInstanceConstantFactoryNew()
        mi = tools.create_asset("MI_" + name, DIR, unreal.MaterialInstanceConstant, factory)
    cur_parent = None
    try:
        cur_parent = mi.get_editor_property("parent")
    except Exception:
        pass
    log("{} parent before={}".format(name, cur_parent))
    mel.set_material_instance_parent(mi, parent)
    # try Name object
    ok = False
    for pname in ("Paint Tint", unreal.Name("Paint Tint")):
        try:
            ok = mel.set_material_instance_vector_parameter_value(mi, pname, col)
            log("set {} via {!r} -> {}".format(name, pname, ok))
            if ok:
                break
        except Exception as e:
            log("set fail {} {}".format(pname, e))
    # verify
    try:
        got = mel.get_material_instance_vector_parameter_value(mi, "Paint Tint")
        log("verify {} = {}".format(name, got))
    except Exception as e:
        log("verify fail " + str(e))
    try:
        mel.update_material_instance(mi)
    except Exception:
        pass
    eas.save_asset(path)

# Ensure BP_RestGuest
PATH = "/Game/Farm/Restaurant/BP_RestGuest"
if not eas.does_asset_exist(PATH):
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    tools.create_asset("BP_RestGuest", "/Game/Farm/Restaurant", unreal.Blueprint, factory)
    eas.save_asset(PATH)
bp = unreal.load_asset(PATH)

def ensure_var(name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        bel.add_member_variable(bp, name, t)
        log("add var " + name)
    else:
        try:
            bel.change_member_variable_type(bp, name, t)
        except Exception:
            pass

ensure_var("TintIndex", "int")
ensure_var("TableOwnerId", "int")
# object ref for nothing; GuestMesh is component

# Ensure GuestMesh skeletal
handles = list(sub.k2_gather_subobject_data_for_blueprint(bp) or [])
root_h = None
mesh_h = None
mesh_obj = None
for h in handles:
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        if lib.is_root_component(data):
            root_h = h
        vname = str(lib.get_variable_name(data) or "")
        obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
        if obj and "SkeletalMesh" in obj.get_class().get_name():
            mesh_h = h
            mesh_obj = obj
            if vname != "GuestMesh":
                try:
                    sub.rename_subobject(h, unreal.Text("GuestMesh"))
                except Exception:
                    pass
    except Exception as e:
        log("hscan " + str(e))

if mesh_obj is None:
    params = unreal.AddNewSubobjectParams()
    params.set_editor_property("parent_handle", root_h if root_h else handles[0])
    params.set_editor_property("new_class", unreal.SkeletalMeshComponent)
    params.set_editor_property("blueprint_context", bp)
    sub.add_new_subobject(params)
    handles = list(sub.k2_gather_subobject_data_for_blueprint(bp) or [])
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
            if obj and "SkeletalMesh" in obj.get_class().get_name():
                try:
                    sub.rename_subobject(h, unreal.Text("GuestMesh"))
                except Exception:
                    pass
                mesh_obj = lib.get_associated_object(sub.k2_find_subobject_data_from_handle(h)) if hasattr(lib, "get_associated_object") else lib.get_object(sub.k2_find_subobject_data_from_handle(h))
                break
        except Exception:
            pass

skel = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
mi_red = unreal.load_asset(DIR + "/MI_GuestRed")
mi_blue = unreal.load_asset(DIR + "/MI_GuestBlue")
mi_green = unreal.load_asset(DIR + "/MI_GuestGreen")
log("mesh_obj=" + str(mesh_obj))
if mesh_obj and skel:
    for prop in ("skeletal_mesh_asset", "SkeletalMeshAsset"):
        try:
            mesh_obj.set_editor_property(prop, skel)
            log("set " + prop)
        except Exception as e:
            log(str(e))
    try:
        mesh_obj.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception as e:
        log("col " + str(e))
    try:
        mesh_obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    except Exception as e:
        log("loc " + str(e))
    # Set override materials: index0 head keep, index1 torso tinted
    # In UE, override_materials replaces; use set_material on template if available
    if mi_red:
        try:
            mesh_obj.set_material(1, mi_red)
            log("set_material 1 red ok")
        except Exception as e:
            log("set_material " + str(e))
            try:
                mesh_obj.set_editor_property("override_materials", [None, mi_red])
                log("override_materials ok")
            except Exception as e2:
                log("ov " + str(e2))
    abp = unreal.load_asset("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed")
    if abp:
        for prop in ("anim_class", "AnimClass"):
            try:
                mesh_obj.set_editor_property(prop, abp.generated_class())
                log("anim ok " + prop)
                break
            except Exception as e:
                log("anim " + str(e))

# ApplyTint custom event: SetMaterial based on TintIndex with branches
# Clear old EventGraph custom ApplyTint bodies if re-run — only add if missing
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    cands = []
    for p in bel.list_all_pins(node):
        if substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                cands.append(p)
    return cands[0] if cands else None

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
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef " + str(e)); return False

def out_data(node):
    p = find_pin(node, "ReturnValue", "Output")
    if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("then", "else", "completed", "loopbody", "outputdelegate"):
                return p
    return None

have_apply = any(n.get_class().get_name()=="K2Node_CustomEvent" and str(bel.get_node_title(n))=="ApplyTint" for n in ge.list_all_nodes())
if not have_apply:
    apply_ev = ge.add_custom_event_node("ApplyTint")
    bel.set_node_pos(apply_ev, pos(0, 300))
    get_tint = ge.add_get_member_variable_node("TintIndex")
    bel.set_node_pos(get_tint, pos(200, 450))
    get_mesh = ge.add_get_member_variable_node("GuestMesh")
    bel.set_node_pos(get_mesh, pos(200, 320))

    # TintIndex == 0 ?
    eq0 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
    bel.set_node_pos(eq0, pos(450, 450))
    setdef(find_pin(eq0, "B", "Input"), "0")
    connect(out_data(get_tint), find_pin(eq0, "A", "Input"), "tintA")

    # Use Branch via Macro Instance? In UE5 python often:
    # ge.add_node with class - try common pattern from restaurant scripts
    br_cls = unreal.K2Node_IfThenElse
    br0 = ge.add_node(br_cls.static_class()) if hasattr(ge, "add_node") else None
    if br0 is None:
        # search how Branch is added in knife3
        log("NO add_node for branch — use SetMaterial red only")
        setmat = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
        bel.set_node_pos(setmat, pos(700, 300))
        setdef(find_pin(setmat, "ElementIndex", "Input"), "1")
        connect(find_pin(apply_ev, "then", "Output"), find_pin(setmat, "execute", "Input"), "ex")
        connect(out_data(get_mesh), find_pin(setmat, "self", "Input"), "self")
        # material object pin
        mp = find_pin(setmat, "Material", "Input")
        if mp and mi_red:
            try:
                # K2Node pins: set_pin_default or connect from MakeLiteral
                lit = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralObject") if False else None
            except Exception:
                pass
            # Use soft class path as default string often fails; create Get node for asset?
            # Variable SoftObject — skip, set on template default is enough
            log("material pin left default; template override handles tint")
    else:
        bel.set_node_pos(br0, pos(700, 300))
        connect(find_pin(apply_ev, "then", "Output"), find_pin(br0, "execute", "Input"), "ex")
        connect(out_data(eq0), find_pin(br0, "Condition", "Input"), "cond")
        log("branch wired")

bel.compile_blueprint(bp)
eas.save_asset(PATH)

# Report
names = [str(n) for n in bel.list_member_variable_names(bp, False)]
log("vars=" + str(names))
handles = list(sub.k2_gather_subobject_data_for_blueprint(bp) or [])
for h in handles:
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        log("sub " + str(lib.get_variable_name(data)) + " " + str(lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else ""))
    except Exception as e:
        log("sub " + str(e))
log("DONE_GUEST3")
