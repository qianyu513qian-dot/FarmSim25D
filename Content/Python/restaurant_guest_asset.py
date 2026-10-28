# -*- coding: utf-8 -*-
"""Probe Manny mat params; create BP_RestGuest; fix Widget draw_size; create tint MIs."""
import unreal

def log(m):
    unreal.log("[GUEST] " + str(m))
    print("[GUEST] " + str(m))

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# Material params
for path in (
    "/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New",
    "/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New",
    "/Game/Characters/Mannequins/Materials/M_Mannequin",
):
    mat = unreal.load_asset(path)
    if not mat:
        log("missing " + path); continue
    log("=== " + path + " class=" + mat.get_class().get_name())
    try:
        # scalar
        for i in range(mel.get_scalar_parameter_names(mat).__len__() if False else 0):
            pass
        scalars = list(mel.get_scalar_parameter_names(mat) or [])
        vectors = list(mel.get_vector_parameter_names(mat) or [])
        texs = list(mel.get_texture_parameter_names(mat) or [])
        log("  scalars=" + str(scalars))
        log("  vectors=" + str(vectors))
        log("  textures=" + str([str(t) for t in texs]))
    except Exception as e:
        log("  params " + str(e))
        # parent
        try:
            parent = mat.get_editor_property("parent")
            log("  parent=" + str(parent))
            if parent:
                log("  p scalars=" + str(list(mel.get_scalar_parameter_names(parent) or [])))
                log("  p vectors=" + str(list(mel.get_vector_parameter_names(parent) or [])))
        except Exception as e2:
            log("  parent " + str(e2))

# Fix draw_size on OrderBubble
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
wc = None
for o in unreal.ObjectIterator(unreal.WidgetComponent):
    if "BP_RestaurantTable" in o.get_path_name() and ("OrderBubble" in o.get_path_name() or "Widget_GEN" in o.get_path_name()):
        wc = o
        log("WC " + o.get_path_name())
if wc:
    try:
        wc.set_editor_property("draw_size", unreal.IntPoint(200, 100))
        log("draw_size IntPoint ok")
    except Exception as e:
        log("draw_size " + str(e))
    # Prefer SCREEN for iso readability
    try:
        wc.set_editor_property("space", unreal.WidgetSpace.SCREEN)
        log("space SCREEN")
    except Exception as e:
        log(str(e))
    # start hidden
    try:
        wc.set_editor_property("hidden_in_game", True)
        log("hidden default True (show when occupied)")
    except Exception as e:
        log(str(e))

# Create tinted torso MIs: red, blue, green
parent_mi = unreal.load_asset("/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New")
parent_mat = unreal.load_asset("/Game/Characters/Mannequins/Materials/M_Mannequin")
base = parent_mi
DIR = "/Game/Farm/Restaurant/Guests"
if not eas.does_directory_exist(DIR):
    eas.make_directory(DIR)

# Find a Color-like vector param name
vec_names = []
try:
    vec_names = [str(x) for x in list(mel.get_vector_parameter_names(base) or [])]
except Exception:
    pass
if not vec_names and parent_mat:
    try:
        vec_names = [str(x) for x in list(mel.get_vector_parameter_names(parent_mat) or [])]
    except Exception:
        pass
log("vec_names=" + str(vec_names))

# Color overrides - common UE5 mannequin uses "Tint" or Color_Tint or similar
# We'll create MIC children and set whatever vector we find; also try Color
COLORS = {
    "GuestRed": unreal.LinearColor(0.85, 0.15, 0.12, 1.0),
    "GuestBlue": unreal.LinearColor(0.15, 0.35, 0.9, 1.0),
    "GuestGreen": unreal.LinearColor(0.12, 0.7, 0.25, 1.0),
}
created_mis = {}
factory = unreal.MaterialInstanceConstantFactoryNew()
for name, col in COLORS.items():
    path = DIR + "/MI_" + name
    if eas.does_asset_exist(path):
        eas.delete_asset(path)
    factory.set_editor_property("initial_parent", base)
    mi = tools.create_asset("MI_" + name, DIR, unreal.MaterialInstanceConstant, factory)
    # set parent explicitly
    try:
        mel.set_material_instance_parent(mi, base)
    except Exception as e:
        log("set parent " + str(e))
    # try common param names
    tried = list(vec_names) + ["Tint", "Color", "BaseColor", "Paint Color", "AccentColor", "ClothColor", "ColorTint", "TintColor"]
    set_ok = False
    for pn in tried:
        try:
            ok = mel.set_material_instance_vector_parameter_value(mi, pn, col)
            if ok:
                log("set {} on {} = ok".format(pn, name))
                set_ok = True
                break
        except Exception as e:
            pass
    if not set_ok:
        log("NO vector param worked for " + name + " — will use runtime multiply via CreateDMI + custom")
    eas.save_asset(path)
    created_mis[name] = path
    log("created " + path)

# Create BP_RestGuest Actor
guest_path = "/Game/Farm/Restaurant/BP_RestGuest"
if eas.does_asset_exist(guest_path):
    eas.delete_asset(guest_path)

# ActorBlueprintFactory
abf = unreal.BlueprintFactory()
abf.set_editor_property("parent_class", unreal.Actor)
gbp = tools.create_asset("BP_RestGuest", "/Game/Farm/Restaurant", unreal.Blueprint, abf)
log("guest bp=" + str(gbp))

# Add SkeletalMeshComponent
handles = list(sub.k2_gather_subobject_data_for_blueprint(gbp) or [])
log("guest handles before=" + str(len(handles)))
parent = handles[0] if handles else None
# Prefer scene root if present
for h in handles:
    ex = sub.k2_find_subobject_data_from_handle(h).export_text()
    if "SceneComponent" in ex or "DefaultSceneRoot" in ex:
        parent = h
        log("parent root found")
        break

params = unreal.AddNewSubobjectParams()
params.blueprint_context = gbp
params.new_class = unreal.SkeletalMeshComponent
params.parent_handle = parent
params.conform_transform_to_parent = True
res = sub.add_new_subobject(params)
log("add SKC=" + str(res))
# rename
handles2 = list(sub.k2_gather_subobject_data_for_blueprint(gbp) or [])
for h in handles2:
    ex = sub.k2_find_subobject_data_from_handle(h).export_text()
    if "SkeletalMeshComponent" in ex and "GEN_VARIABLE" in ex:
        sub.rename_subobject(h, "GuestMesh")
        log("renamed GuestMesh")

# Configure mesh template
skel = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
gm = None
for o in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    if "BP_RestGuest" in o.get_path_name() and "GEN_VARIABLE" in o.get_path_name():
        gm = o
        log("GuestMesh tmpl " + o.get_path_name())
        break
if gm and skel:
    for prop in ("skeletal_mesh_asset", "SkeletalMeshAsset"):
        try:
            gm.set_editor_property(prop, skel)
            log("set mesh via " + prop)
        except Exception as e:
            log(prop + " " + str(e))
    # collision off
    try:
        gm.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception as e:
        log("col " + str(e))
    # anim
    abp = unreal.load_asset("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed")
    if abp:
        try:
            gm.set_editor_property("anim_class", abp.generated_class())
            log("anim_class set")
        except Exception as e:
            try:
                gm.set_editor_property("animation_blueprint", abp)
                log("animation_blueprint set")
            except Exception as e2:
                log("anim " + str(e) + " / " + str(e2))

# Add vars: TintIndex (int), TableId (int)
for vname, vtype in (("TintIndex", unreal.IntProperty), ("TableOwnerId", unreal.IntProperty)):
    try:
        # add_member_variable(bp, name) then change type
        bel.add_member_variable(gbp, vname)
        log("added var " + vname)
    except Exception as e:
        log("var " + vname + " " + str(e))
try:
    gbp.change_member_variable_type("TintIndex", "int")
except Exception as e:
    log("type TintIndex " + str(e))
try:
    gbp.change_member_variable_type("TableOwnerId", "int")
except Exception as e:
    log("type TableOwnerId " + str(e))

# BeginPlay: apply tint via CreateDynamicMaterialInstance on element 1
# We'll wire a simple graph: BeginPlay -> CreateDMI(element 1) -> SetVectorParameterValue
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))

def pos(x,y): return unreal.IntPoint(int(x),int(y))
def find_pin(node, substr, direction=None):
    if not node: return None
    for p in bel.list_all_pins(node):
        if substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok
def setdef(pin,val):
    if not pin: return False
    try: pin.set_pin_value(str(val)); return True
    except Exception:
        try: pin.set_default_value(str(val)); return True
        except Exception as e: log("setdef "+str(e)); return False

# Find BeginPlay
bp_node = None
for n in ge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in str(bel.get_node_title(n)):
        bp_node = n
        break
if not bp_node:
    # add
    try:
        bp_node = ge.add_event_node("ReceiveBeginPlay")
    except Exception:
        bp_node = None
        for n in ge.list_all_nodes():
            log("node " + str(bel.get_node_title(n)) + " " + n.get_class().get_name())

log("BeginPlay node=" + str(bp_node))

# Simpler tint approach: set override materials on the component to our MIs based on TintIndex
# Graph: BeginPlay -> Switch on TintIndex -> Set Material (element 1)
# For v1 even simpler: just set material 1 to GuestRed by default on CDO, and provide ApplyTint custom event

# Set default override material element 1 to red MI on template
mi_red = unreal.load_asset(DIR + "/MI_GuestRed")
if gm and mi_red:
    try:
        # override_materials array
        mats = [None, mi_red]
        # slot 0 keep default, slot 1 torso
        gm.set_editor_property("override_materials", [mi_red])  # may apply to all
        log("override_materials set")
    except Exception as e:
        log("override " + str(e))

# Custom event ApplyTint(TintIndex)
# For reliability, spawn script will set material after spawn via Python in editor test;
# In game BP: ApplyTint sets material from index.

apply_ev = ge.add_custom_event_node("ApplyTint")
bel.set_node_pos(apply_ev, pos(0, 300))
# add int input?
try:
    # Custom event inputs via bel
    pass
except Exception:
    pass

# ApplyTint body: Get GuestMesh -> CreateDynamicMaterialInstance(1) -> SetVectorParameter("Color"/Tint)
get_mesh = ge.add_get_member_variable_node("GuestMesh")
bel.set_node_pos(get_mesh, pos(300, 350))
# CreateDynamicMaterialInstance
cdmi = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:CreateDynamicMaterialInstance")
bel.set_node_pos(cdmi, pos(600, 300))
setdef(find_pin(cdmi, "ElementIndex", "Input"), "1")
# SetVectorParameterValue on MID
svp = ge.add_call_function_node("/Script/Engine.MaterialInstanceDynamic:SetVectorParameterValue")
bel.set_node_pos(svp, pos(1000, 300))
setdef(find_pin(svp, "ParameterName", "Input"), "Tint")
# Color from TintIndex - use Select or Branch chain. For simplicity set fixed magenta first then improve.
# Make LinearColor for cyan as test
make_col = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeColor")
bel.set_node_pos(make_col, pos(700, 500))
setdef(find_pin(make_col, "R", "Input") or find_pin(make_col, "X", "Input"), "0.2")
setdef(find_pin(make_col, "G", "Input") or find_pin(make_col, "Y", "Input"), "0.8")
setdef(find_pin(make_col, "B", "Input") or find_pin(make_col, "Z", "Input"), "0.9")
setdef(find_pin(make_col, "A", "Input") or find_pin(make_col, "W", "Input"), "1.0")

connect(find_pin(apply_ev, "then", "Output"), find_pin(cdmi, "execute", "Input"), "apply->cdmi")
connect(find_pin(get_mesh, "GuestMesh", "Output") or list(bel.list_all_pins(get_mesh))[0], find_pin(cdmi, "self", "Input"), "mesh->self")
connect(find_pin(cdmi, "then", "Output"), find_pin(svp, "execute", "Input"), "cdmi->svp")
connect(find_pin(cdmi, "ReturnValue", "Output"), find_pin(svp, "self", "Input"), "mid->self")
# Value pin
val_pin = find_pin(svp, "Value", "Input")
col_out = find_pin(make_col, "ReturnValue", "Output")
connect(col_out, val_pin, "col->val")

# Also call ApplyTint from BeginPlay
if bp_node:
    call_apply = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
    # might fail before compile - use custom event call
    try:
        # K2Node_CallParentFunction / call custom
        call_apply = None
        for attempt in range(1):
            # add call to custom event via CallFunction after compile
            pass
    except Exception:
        pass
    # Wire BeginPlay -> ApplyTint via CallFunction on self - use add_call_function after compile

bel.compile_blueprint(gbp)
eas.save_asset(guest_path)

# After compile, wire BeginPlay -> ApplyTint
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
bp_node = None
apply_ev = None
for n in ge.list_all_nodes():
    t = str(bel.get_node_title(n))
    c = n.get_class().get_name()
    if c=="K2Node_Event" and "BeginPlay" in t:
        bp_node = n
    if c=="K2Node_CustomEvent" and t=="ApplyTint":
        apply_ev = n
# Call ApplyTint
call = ge.add_call_function_node("/Game/Farm/Restaurant/BP_RestGuest.BP_RestGuest_C:ApplyTint")
bel.set_node_pos(call, pos(400, 0))
if bp_node and call:
    # disconnect existing then if any? parent beginplay?
    thenp = find_pin(bp_node, "then", "Output")
    # If already connected, splice
    existing = list(thenp.list_connected_pins() or []) if thenp else []
    connect(thenp, find_pin(call, "execute", "Input"), "bp->apply")
    if existing:
        connect(find_pin(call, "then", "Output"), existing[0], "apply->old")

bel.compile_blueprint(gbp)
eas.save_asset(guest_path)
bel.compile_blueprint(tbp)
eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
log("DONE_GUEST_ASSET")
