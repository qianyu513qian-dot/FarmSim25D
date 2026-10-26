# -*- coding: utf-8 -*-
"""SAFE: Reconfigure BP_PlotVisual for VMF soil+crop meshes. Rebuild ApplyState only.
No open_editor, no GridManager edits, no rename thrashing.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Grid/BP_PlotVisual"

MESH = {
    "dry": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "wet": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
    "seed": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling",
    "grow": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing",
    "mature": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature",
}


def log(m):
    unreal.log("[VMF_PV] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
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


def make_byte_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="byte")')
    return p


def ensure_crop_mesh(bp):
    """Ensure CropMesh StaticMeshComponent exists beside PlotMesh."""
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    root_h = None
    plot_h = None
    crop_h = None
    plot_obj = None
    crop_obj = None
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            if lib.is_root_component(data):
                root_h = h
            vname = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            if vname == "PlotMesh":
                plot_h = h
                plot_obj = obj
            if vname == "CropMesh":
                crop_h = h
                crop_obj = obj
        except Exception:
            pass

    if crop_h is None:
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", root_h if root_h else handles[0])
        params.set_editor_property("new_class", unreal.StaticMeshComponent)
        try:
            params.set_editor_property("blueprint_context", bp)
        except Exception:
            pass
        result = sub.add_new_subobject(params)
        log("add CropMesh result=" + str(result))
        # rename newest SMC that isn't PlotMesh
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        for h in handles:
            data = sub.k2_find_subobject_data_from_handle(h)
            try:
                vname = str(lib.get_variable_name(data) or "")
                obj = lib.get_object(data)
                if obj and "StaticMesh" in obj.get_class().get_name() and vname not in ("PlotMesh",):
                    if vname != "CropMesh":
                        try:
                            ok = sub.rename_subobject(h, unreal.Text("CropMesh"))
                            log("rename -> CropMesh: " + str(ok))
                        except Exception as e:
                            log("rename fail: " + str(e))
                    crop_h = h
                    crop_obj = lib.get_object(sub.k2_find_subobject_data_from_handle(h))
            except Exception:
                pass
        if root_h and crop_h:
            try:
                sub.attach_subobject(root_h, crop_h)
            except Exception as e:
                log("attach crop: " + str(e))

    def configure_smc(obj, label, mesh_path, rel_z=0.0):
        if not obj:
            log("no obj " + label)
            return
        try:
            obj.set_editor_property("static_mesh", unreal.load_asset(mesh_path) if mesh_path else None)
            log(label + " mesh set")
        except Exception as e:
            log(label + " mesh: " + str(e))
        try:
            obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        except Exception:
            try:
                bi = obj.get_editor_property("body_instance")
                bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
                obj.set_editor_property("body_instance", bi)
            except Exception as e2:
                log(label + " coll: " + str(e2))
        try:
            obj.set_editor_property("cast_shadow", False)
        except Exception:
            pass
        try:
            obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, float(rel_z)))
        except Exception as e:
            log(label + " rel: " + str(e))
        try:
            # Component scale 1; actor spawn scale 0.01
            obj.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
        except Exception:
            pass

    # refresh objs
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            vname = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            if vname == "PlotMesh":
                plot_obj = obj
            if vname == "CropMesh":
                crop_obj = obj
        except Exception:
            pass

    configure_smc(plot_obj, "PlotMesh", MESH["dry"], 0.0)
    configure_smc(crop_obj, "CropMesh", MESH["seed"], 5.0)
    # hide crop by default via empty mesh? keep seedling but ApplyState will manage
    try:
        if crop_obj:
            crop_obj.set_editor_property("static_mesh", None)
    except Exception:
        pass

    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile after comps: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)
    return True


def rebuild_apply_state(bp):
    """Force rebuild ApplyState: soil+crop meshes by E_PlotState byte."""
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    if "ApplyState" not in graphs:
        bel.add_function_graph(bp, "ApplyState")
        log("created ApplyState graph")

    graph = bel.find_graph(bp, "ApplyState")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    if not ge:
        unreal.log_error("no ApplyState GE")
        return False

    entry = None
    to_del = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            to_del.append(n)
    if to_del:
        ge.remove_nodes(to_del)
        log("cleared ApplyState nodes " + str(len(to_del)))

    # refresh entry after clear
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    if find_pin(entry, "State", "Output") is None:
        ge.add_graph_input_parameter("State", make_byte_pin())
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n

    get_soil = ge.add_get_member_variable_node("PlotMesh")
    bel.set_node_pos(get_soil, pos(200, 40))
    get_crop = ge.add_get_member_variable_node("CropMesh")
    bel.set_node_pos(get_crop, pos(200, 160))

    # Chain: State 0 / 1 / 2 / 3 / 4
    # Helper to make SetStaticMesh + optional hide
    def make_set_mesh(ge, x, y, mesh_path, self_get_node, self_pin_name):
        ssm = ge.add_call_function_node("/Script/Engine.StaticMeshComponent:SetStaticMesh")
        bel.set_node_pos(ssm, pos(x, y))
        connect(find_pin(self_get_node, self_pin_name, "Output") or find_pin(self_get_node, "PlotMesh", "Output") or find_pin(self_get_node, "CropMesh", "Output"),
                find_pin(ssm, "self", "Input"), "self")
        if mesh_path:
            set_val(find_pin(ssm, "NewMesh", "Input"), mesh_path, "mesh")
        else:
            # leave empty / clear
            try:
                find_pin(ssm, "NewMesh", "Input").set_pin_value("")
            except Exception:
                pass
        return ssm

    def make_hide(ge, x, y, self_get_node, pname, hidden):
        hid = ge.add_call_function_node("/Script/Engine.SceneComponent:SetHiddenInGame")
        bel.set_node_pos(hid, pos(x, y))
        connect(find_pin(self_get_node, pname, "Output"), find_pin(hid, "self", "Input"), "hide-self")
        set_val(find_pin(hid, "NewHidden", "Input") or find_pin(hid, "bNewHidden", "Input"), "true" if hidden else "false", "hidden")
        return hid

    prev_else = find_pin(entry, "then", "Output")
    # states: (val, soil_mesh, crop_mesh, crop_hidden)
    states = [
        (0, None, None, True),          # Empty: clear/hide both
        (1, MESH["dry"], None, True),   # Tilled
        (2, MESH["dry"], MESH["seed"], False),   # Planted
        (3, MESH["wet"], MESH["grow"], False),   # Watered
        (4, MESH["wet"], MESH["mature"], False), # Ready
    ]
    y = 0
    for state_val, soil_m, crop_m, crop_hidden in states:
        eq = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
        bel.set_node_pos(eq, pos(450, y))
        connect(find_pin(entry, "State", "Output"), find_pin(eq, "A", "Input"), "eqA{}".format(state_val))
        set_val(find_pin(eq, "B", "Input"), str(state_val), "eqB{}".format(state_val))

        br = ge.add_branch_node()
        bel.set_node_pos(br, pos(700, y))
        connect(prev_else, find_pin(br, "execute", "Input"), "->br{}".format(state_val))
        connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond{}".format(state_val))

        # Soil mesh
        ssm_soil = make_set_mesh(ge, 1000, y, soil_m if soil_m else MESH["dry"], get_soil, "PlotMesh")
        connect(find_pin(br, "then", "Output"), find_pin(ssm_soil, "execute", "Input"), "then->soil{}".format(state_val))
        # For Empty: hide soil; else show soil
        hid_soil = make_hide(ge, 1300, y, get_soil, "PlotMesh", state_val == 0)
        connect(find_pin(ssm_soil, "then", "Output"), find_pin(hid_soil, "execute", "Input"), "soil->hidS{}".format(state_val))

        # Crop mesh
        ssm_crop = make_set_mesh(ge, 1600, y, crop_m if crop_m else MESH["seed"], get_crop, "CropMesh")
        connect(find_pin(hid_soil, "then", "Output"), find_pin(ssm_crop, "execute", "Input"), "hidS->crop{}".format(state_val))
        hid_crop = make_hide(ge, 1900, y, get_crop, "CropMesh", crop_hidden or (crop_m is None))
        connect(find_pin(ssm_crop, "then", "Output"), find_pin(hid_crop, "execute", "Input"), "crop->hidC{}".format(state_val))

        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(2200, y))
        connect(find_pin(hid_crop, "then", "Output"), find_pin(ret, "execute", "Input"), "hidC->ret{}".format(state_val))

        prev_else = find_pin(br, "else", "Output")
        y += 220

    ret_f = ge.add_return_node()
    bel.set_node_pos(ret_f, pos(1000, y))
    connect(prev_else, find_pin(ret_f, "execute", "Input"), "final else")

    try:
        bel.compile_blueprint(bp)
        log("ApplyState compile ok")
    except Exception as e:
        unreal.log_warning("ApplyState compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)
    return True


def main():
    log("=== START ===")
    bp = unreal.load_asset(PATH)
    if not bp:
        unreal.log_error("no BP_PlotVisual")
        return
    ensure_crop_mesh(bp)
    bp = unreal.load_asset(PATH)
    rebuild_apply_state(bp)
    log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    log("=== END ===")


if __name__ == "__main__":
    main()
