# -*- coding: utf-8 -*-
"""Create guest tint MIs + BP_RestGuest with Manny mesh and Paint Tint."""
import unreal

def log(m):
    unreal.log("[GUEST2] " + str(m))
    print("[GUEST2] " + str(m))

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
        mel.set_material_instance_parent(mi, parent)
    ok = mel.set_material_instance_vector_parameter_value(mi, "Paint Tint", col)
    log("MI_{} Paint Tint={} ok={}".format(name, col, ok))
    try:
        mel.update_material_instance(mi)
    except Exception:
        pass
    eas.save_asset(path)

# BP_RestGuest
PATH = "/Game/Farm/Restaurant/BP_RestGuest"
if eas.does_asset_exist(PATH):
    # recreate clean
    eas.delete_asset(PATH)
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.Actor)
bp = tools.create_asset("BP_RestGuest", "/Game/Farm/Restaurant", unreal.Blueprint, factory)
eas.save_asset(PATH)
bp = unreal.load_asset(PATH)
log("bp=" + str(bp))

# vars
for name, ptype in (("TintIndex", "int"), ("TableOwnerId", "int")):
    names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
    if name not in names:
        try:
            bel.add_member_variable(bp, name, ptype)
        except Exception:
            bel.add_member_variable(bp, name)
            try:
                bp.change_member_variable_type(name, ptype)
            except Exception as e:
                log("type {} {}".format(name, e))
    log("var " + name)

# Add SkeletalMeshComponent GuestMesh
handles = list(sub.k2_gather_subobject_data_for_blueprint(bp) or [])
root_h = None
for h in handles:
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        if lib.is_root_component(data):
            root_h = h
    except Exception:
        pass
if root_h is None and handles:
    root_h = handles[0]

params = unreal.AddNewSubobjectParams()
params.set_editor_property("parent_handle", root_h)
params.set_editor_property("new_class", unreal.SkeletalMeshComponent)
params.set_editor_property("blueprint_context", bp)
res = sub.add_new_subobject(params)
log("add SKC " + str(res))

handles = list(sub.k2_gather_subobject_data_for_blueprint(bp) or [])
target_h = None
target_obj = None
for h in handles:
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        obj = lib.get_associated_object(data) if hasattr(lib, "get_associated_object") else lib.get_object(data)
        vname = str(lib.get_variable_name(data) or "")
        if obj and "SkeletalMesh" in obj.get_class().get_name():
            try:
                sub.rename_subobject(h, unreal.Text("GuestMesh"))
            except Exception:
                try:
                    sub.rename_subobject(h, "GuestMesh")
                except Exception as e:
                    log("rename " + str(e))
            target_h = h
            data2 = sub.k2_find_subobject_data_from_handle(h)
            target_obj = lib.get_associated_object(data2) if hasattr(lib, "get_associated_object") else lib.get_object(data2)
            break
    except Exception as e:
        log("scan " + str(e))

skel = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
mi_red = unreal.load_asset(DIR + "/MI_GuestRed")
if target_obj and skel:
    for prop in ("skeletal_mesh_asset", "SkeletalMeshAsset"):
        try:
            target_obj.set_editor_property(prop, skel)
            log("mesh set " + prop)
        except Exception as e:
            log(prop + " " + str(e))
    try:
        target_obj.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception as e:
        log("col " + str(e))
    # scale ~1 (same as player)
    try:
        target_obj.set_editor_property("relative_location", unreal.Vector(0, 0, -90))  # feet at actor origin-ish
    except Exception:
        pass
    # override torso material (element 1)
    try:
        # Keep head/legs default; override index 1
        overrides = [None, mi_red]
        # UE may need full array matching slot count
        target_obj.set_editor_property("override_materials", [None, mi_red])
        log("override mats set")
    except Exception as e:
        log("override " + str(e))
        try:
            target_obj.set_material(1, mi_red)
            log("set_material(1) ok")
        except Exception as e2:
            log("set_material " + str(e2))
    abp = unreal.load_asset("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed")
    if abp:
        for prop in ("anim_class", "AnimClass"):
            try:
                target_obj.set_editor_property(prop, abp.generated_class())
                log("anim " + prop)
            except Exception as e:
                log("anim " + prop + " " + str(e))

# Wire ApplyTint(TintIndex uses Get) -> SetMaterial element 1 from select of 3 MIs
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if substr.lower() in str(p.get_pin_name()).lower():
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
            log("setdef " + str(e))
            return False

# Custom event ApplyTint
apply_ev = ge.add_custom_event_node("ApplyTint")
bel.set_node_pos(apply_ev, pos(0, 400))

# Get TintIndex, GuestMesh
get_tint = ge.add_get_member_variable_node("TintIndex")
bel.set_node_pos(get_tint, pos(200, 550))
get_mesh = ge.add_get_member_variable_node("GuestMesh")
bel.set_node_pos(get_mesh, pos(200, 450))

# Branch TintIndex==0 -> red, ==1 blue, else green. Use two branches.
eq0 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_IntInt")
bel.set_node_pos(eq0, pos(450, 520))
setdef(find_pin(eq0, "B", "Input"), "0")
connect(find_pin(get_tint, "TintIndex", "Output"), find_pin(eq0, "A", "Input"), "tint->eq0")

br0 = ge.add_branch_node() if hasattr(ge, "add_branch_node") else ge.add_node(unreal.K2Node_IfThenElse) if False else None
# add_if_then_else?
br0 = None
try:
    br0 = ge.add_node_by_class(unreal.K2Node_IfThenElse)
except Exception:
    pass
if br0 is None:
    # use CallFunction? Macro?
    try:
        br0 = ge.add_knot_node()  # wrong
    except Exception:
        pass
# Standard in this project: ge doesn't have add_branch - they use add_call? Look at helpers
# From knife scripts: Branch via unreal.BlueprintGraphEditor - check methods
log("ge methods branchish=" + str([x for x in dir(ge) if "branch" in x.lower() or "if" in x.lower() or "add_" in x.lower()][:40]))

# Simpler: always SetMaterial to red on BeginPlay; Manager/Table sets material after spawn via SetMaterial call
# For ApplyTint: SetMaterial(1, soft ref) - use three SetMaterial with branches from Select node

# Use Select node for material
# K2Node_Select
sel = None
try:
    sel = ge.add_select_node()
except Exception as e:
    log("add_select " + str(e))
try:
    sel = ge.add_node(unreal.load_object(None, "/Script/BlueprintGraph.K2Node_Select"))
except Exception as e:
    log("add_node select " + str(e))

# Fallback reliable path: BeginPlay SetMaterial(1) to MI_GuestRed; Table after spawn calls SetMaterial based on TableId
setmat = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
bel.set_node_pos(setmat, pos(700, 400))
setdef(find_pin(setmat, "ElementIndex", "Input"), "1")
# Material pin - set soft path default hard: load MI as default on pin
mat_pin = find_pin(setmat, "Material", "Input")
if mat_pin and mi_red:
    try:
        # set object pin
        mat_pin.set_default_object(mi_red) if hasattr(mat_pin, "set_default_object") else None
        setdef(mat_pin, mi_red.get_path_name())
        log("mat default set")
    except Exception as e:
        log("mat pin " + str(e))

connect(find_pin(apply_ev, "then", "Output"), find_pin(setmat, "execute", "Input"), "apply->setmat")
mesh_out = find_pin(get_mesh, "GuestMesh", "Output")
if mesh_out is None:
    for p in bel.list_all_pins(get_mesh):
        if "OUTPUT" in str(p.get_pin_direction()):
            mesh_out = p
            break
connect(mesh_out, find_pin(setmat, "self", "Input"), "mesh->self")

# BeginPlay -> ApplyTint
bp_node = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "BeginPlay" in str(bel.get_node_title(n)):
        bp_node = n
        break
bel.compile_blueprint(bp)

# recall ApplyTint call
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
bp_node = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "BeginPlay" in str(bel.get_node_title(n)):
        bp_node = n
call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
bel.set_node_pos(call, pos(400, 0))
if bp_node:
    connect(find_pin(bp_node, "then", "Output"), find_pin(call, "execute", "Input"), "bp->applycall")

bel.compile_blueprint(bp)
eas.save_asset(PATH)
log("DONE_GUEST2 errors check")
# list compile errors if API exists
try:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = ge.list_nodes_with_errors()
    log("errors=" + str(len(errs)))
    for n in errs:
        log("  ERR " + str(bel.get_node_title(n)))
except Exception as e:
    log("errlist " + str(e))
log("DONE")
