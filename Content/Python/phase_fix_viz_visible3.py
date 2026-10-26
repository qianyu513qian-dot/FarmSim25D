# -*- coding: utf-8 -*-
"""Find GridManager in level; inspect character Till/Plant call; fix ApplyState visibility; hide grass Z-fight."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def log(m):
    unreal.log("[FIX_VIZ3] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}]: {}".format(label, ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


# Level GridManager
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

gm = None
for a in actors:
    try:
        cn = a.get_class().get_name()
        lab = a.get_actor_label()
    except Exception:
        continue
    if "GridManager" in cn or "GridManager" in str(lab):
        gm = a
        log("FOUND GM {} class={} loc={}".format(lab, cn, a.get_actor_location()))
        try:
            w = a.get_editor_property("GridWidth")
            h = a.get_editor_property("GridHeight")
            cs = a.get_editor_property("CellSize")
            log("  instance W={} H={} CellSize={}".format(w, h, cs))
        except Exception as e:
            log("  props " + str(e))
        try:
            pv = a.get_editor_property("PlotVisuals")
            log("  PlotVisuals len={}".format(len(pv) if pv is not None else None))
        except Exception as e:
            log("  PlotVisuals " + str(e))

if not gm:
    log("NO GridManager in level — searching character for spawn/ref")

# Character graphs: TillCell / Visualize
char_paths = [
    "/Game/TopDown/Blueprints/BP_TopDownCharacter",
    "/Game/Farm/BP_TopDownCharacter",
    "/Game/Blueprints/BP_TopDownCharacter",
]
char_bp = None
for p in char_paths:
    char_bp = unreal.load_asset(p)
    if char_bp:
        log("char bp=" + p)
        break
if not char_bp:
    # search
    for a in unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False):
        if "TopDownCharacter" in a or "BP_Player" in a:
            if a.endswith("." + a.split("/")[-1]):
                log("candidate " + a)
                if "Character" in a:
                    char_bp = unreal.load_asset(a.split(".")[0])
                    if char_bp:
                        log("loaded " + a)
                        break

if char_bp:
    for gname in bel.list_graph_names(char_bp):
        ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(char_bp, str(gname)))
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if any(k in t for k in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell", "GridManager", "Visualize")):
                log("CHAR[{}] node={}".format(gname, t))
                for p in bel.list_all_pins(n):
                    d = str(p.get_pin_direction())
                    if "INPUT" in d.upper() or "input" in d.lower():
                        cps = list(p.list_connected_pins())
                        v = pin_val(p)
                        if cps or (v and v not in ("", "0", "False")):
                            log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), v,
                                [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:3]))

# Fix: Rebuild ApplyState more carefully - use SetVisibility + SetHiddenInGame
# AND set mesh via loaded soft refs stored as BP variables

def ensure_mesh_vars(bp):
    names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(bp)]
    mesh_vars = {
        "Mesh_SoilDry": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
        "Mesh_SoilWet": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
        "Mesh_Seed": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling",
        "Mesh_Grow": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing",
        "Mesh_Mature": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature",
    }
    for vn, path in mesh_vars.items():
        if vn not in names:
            pin = unreal.EdGraphPinType()
            pin.import_text(
                '(PinCategory="object",PinSubCategory="",'
                'PinSubCategoryObject="/Script/Engine.StaticMesh")'
            )
            try:
                ok = bel.add_member_variable(bp, vn, pin)
                log("add var {} -> {}".format(vn, ok))
            except Exception as e:
                log("add var {} fail {}".format(vn, e))
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile after vars " + str(e))

    # Set CDO defaults
    try:
        gen = unreal.load_object(None, PV + ".BP_PlotVisual_C")
        cdo = unreal.get_default_object(gen) if gen else None
        if cdo:
            for vn, path in mesh_vars.items():
                asset = unreal.load_asset(path)
                try:
                    cdo.set_editor_property(vn, asset)
                    log("CDO.{} set {}".format(vn, asset.get_name() if asset else None))
                except Exception as e:
                    log("CDO.{} fail {}".format(vn, e))
    except Exception as e:
        log("CDO " + str(e))

    unreal.EditorAssetLibrary.save_asset(PV)
    return mesh_vars


def rebuild_apply_state_with_vars(bp, mesh_vars):
    graph = bel.find_graph(bp, "ApplyState")
    if not graph:
        bel.add_function_graph(bp, "ApplyState")
        graph = bel.find_graph(bp, "ApplyState")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)

    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
        log("cleared ApplyState " + str(len(to_del)))

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    if find_pin(entry, "State", "Output") is None:
        p = unreal.EdGraphPinType()
        p.import_text('(PinCategory="byte")')
        ge.add_graph_input_parameter("State", p)
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n

    get_soil = ge.add_get_member_variable_node("PlotMesh")
    bel.set_node_pos(get_soil, pos(200, 40))
    get_crop = ge.add_get_member_variable_node("CropMesh")
    bel.set_node_pos(get_crop, pos(200, 160))

    # Pre-get mesh vars
    get_meshes = {}
    yi = 0
    for vn in ("Mesh_SoilDry", "Mesh_SoilWet", "Mesh_Seed", "Mesh_Grow", "Mesh_Mature"):
        gn = ge.add_get_member_variable_node(vn)
        bel.set_node_pos(gn, pos(200, 300 + yi))
        get_meshes[vn] = gn
        yi += 80

    def make_set_mesh(x, y, mesh_get_node, mesh_var_name, self_get, self_name):
        ssm = ge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(ssm, pos(x, y))
        connect(find_pin(self_get, self_name, "Output"), find_pin(ssm, "self", "Input"), "self-" + self_name)
        if mesh_get_node and mesh_var_name:
            connect(find_pin(mesh_get_node, mesh_var_name, "Output"), find_pin(ssm, "NewMesh", "Input"), "mesh-" + mesh_var_name)
        else:
            # clear mesh - leave NewMesh none
            pass
        return ssm

    def make_hide(x, y, self_get, pname, hidden):
        hid = ge.add_call_function_node("/Script/Engine.SceneComponent:SetHiddenInGame")
        bel.set_node_pos(hid, pos(x, y))
        connect(find_pin(self_get, pname, "Output"), find_pin(hid, "self", "Input"), "hid-self")
        set_val(find_pin(hid, "NewHidden", "Input") or find_pin(hid, "bNewHidden", "Input"),
                "true" if hidden else "false", "hid")
        return hid

    def make_vis(x, y, self_get, pname, visible):
        # SetVisibility(NewVisibility, bPropagateToChildren)
        vis = ge.add_call_function_node("/Script/Engine.SceneComponent:SetVisibility")
        bel.set_node_pos(vis, pos(x, y))
        connect(find_pin(self_get, pname, "Output"), find_pin(vis, "self", "Input"), "vis-self")
        set_val(find_pin(vis, "NewVisibility", "Input") or find_pin(vis, "bNewVisibility", "Input"),
                "true" if visible else "false", "vis")
        return vis

    # states: (val, soil_var, crop_var_or_None, crop_hidden)
    states = [
        (0, None, None, True),
        (1, "Mesh_SoilDry", None, True),
        (2, "Mesh_SoilDry", "Mesh_Seed", False),
        (3, "Mesh_SoilWet", "Mesh_Grow", False),
        (4, "Mesh_SoilWet", "Mesh_Mature", False),
    ]
    prev_else = find_pin(entry, "then", "Output")
    y = 0
    for state_val, soil_v, crop_v, crop_hidden in states:
        eq = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
        bel.set_node_pos(eq, pos(450, y))
        connect(find_pin(entry, "State", "Output"), find_pin(eq, "A", "Input"), "eqA")
        set_val(find_pin(eq, "B", "Input"), str(state_val), "eqB")

        br = ge.add_branch_node()
        bel.set_node_pos(br, pos(700, y))
        connect(prev_else, find_pin(br, "execute", "Input"), "->br")
        connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond")

        soil_get = get_meshes.get(soil_v) if soil_v else get_meshes["Mesh_SoilDry"]
        ssm_soil = make_set_mesh(1000, y, soil_get if soil_v else None, soil_v, get_soil, "PlotMesh")
        connect(find_pin(br, "then", "Output"), find_pin(ssm_soil, "execute", "Input"), "then->soil")

        hid_soil = make_hide(1250, y, get_soil, "PlotMesh", state_val == 0)
        connect(find_pin(ssm_soil, "then", "Output"), find_pin(hid_soil, "execute", "Input"), "soil->hid")

        vis_soil = make_vis(1450, y, get_soil, "PlotMesh", state_val != 0)
        connect(find_pin(hid_soil, "then", "Output"), find_pin(vis_soil, "execute", "Input"), "hid->visS")

        crop_get = get_meshes.get(crop_v) if crop_v else get_meshes["Mesh_Seed"]
        ssm_crop = make_set_mesh(1700, y, crop_get if crop_v else None, crop_v, get_crop, "CropMesh")
        connect(find_pin(vis_soil, "then", "Output"), find_pin(ssm_crop, "execute", "Input"), "visS->crop")

        hid_crop = make_hide(1950, y, get_crop, "CropMesh", crop_hidden or (crop_v is None))
        connect(find_pin(ssm_crop, "then", "Output"), find_pin(hid_crop, "execute", "Input"), "crop->hidC")

        vis_crop = make_vis(2150, y, get_crop, "CropMesh", not (crop_hidden or (crop_v is None)))
        connect(find_pin(hid_crop, "then", "Output"), find_pin(vis_crop, "execute", "Input"), "hidC->visC")

        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(2400, y))
        connect(find_pin(vis_crop, "then", "Output"), find_pin(ret, "execute", "Input"), "visC->ret")

        prev_else = find_pin(br, "else", "Output")
        y += 260

    ret_f = ge.add_return_node()
    bel.set_node_pos(ret_f, pos(1000, y))
    connect(prev_else, find_pin(ret_f, "execute", "Input"), "final")

    try:
        bel.compile_blueprint(bp)
        log("ApplyState rebuilt compile ok")
    except Exception as e:
        log("ApplyState compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(PV)


# Attach check + ensure PlotMesh attached to root
def ensure_attach(bp):
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    root_h = plot_h = crop_h = None
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            if lib.is_root_component(data):
                root_h = h
            vname = str(lib.get_variable_name(data) or "")
            if vname == "PlotMesh":
                plot_h = h
            if vname == "CropMesh":
                crop_h = h
        except Exception:
            pass
    if root_h and plot_h:
        try:
            ok = sub.attach_subobject(root_h, plot_h)
            log("attach PlotMesh: " + str(ok))
        except Exception as e:
            log("attach PlotMesh " + str(e))
    if root_h and crop_h:
        try:
            ok = sub.attach_subobject(root_h, crop_h)
            log("attach CropMesh: " + str(ok))
        except Exception as e:
            log("attach CropMesh " + str(e))
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(PV)


log("=== START ===")
pv = unreal.load_asset(PV)
mesh_vars = ensure_mesh_vars(pv)
pv = unreal.load_asset(PV)
ensure_attach(pv)
pv = unreal.load_asset(PV)
rebuild_apply_state_with_vars(pv, mesh_vars)

# Expand grid to 40 to match scene (safe)
gbp = unreal.load_asset(MGR)
try:
    gen = unreal.load_object(None, MGR + ".BP_GridManager_C")
    cdo = unreal.get_default_object(gen) if gen else None
    if cdo:
        # Don't change width if Plots array logic depends on BeginPlay init with old size
        # Just log current
        log("CDO GridWidth still {}".format(cdo.get_editor_property("GridWidth")))
except Exception as e:
    log(str(e))

unreal.EditorAssetLibrary.save_asset(PV)
unreal.EditorAssetLibrary.save_asset(MGR)
try:
    unreal.EditorAssetLibrary.save_directory("/Game/Farm/Grid")
except Exception:
    pass
log("=== END ===")
