# -*- coding: utf-8 -*-
"""BP_PlotVisual.ApplyState(State byte): set PlotMesh material by state. NEW function only."""
import unreal

bel = unreal.BlueprintEditorLibrary
PATH = "/Game/Farm/Grid/BP_PlotVisual"
MATS = {
    1: "/Game/Farm/Art/Mats/M_Tilled",
    2: "/Game/Farm/Art/Mats/M_Planted",
    3: "/Game/Farm/Art/Mats/M_Watered",
    4: "/Game/Farm/Art/Mats/M_Ready",
}


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
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
        unreal.log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def make_byte_pin():
    p = unreal.EdGraphPinType()
    p.import_text('(PinCategory="byte")')
    return p


def dump(node, label):
    if not node:
        return
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def fix_collision_and_attach():
    bp = unreal.load_asset(PATH)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    root_h = None
    mesh_h = None
    mesh_obj = None
    for h in handles:
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            if lib.is_root_component(data):
                root_h = h
            vname = str(lib.get_variable_name(data) or "")
            if vname == "PlotMesh":
                mesh_h = h
                mesh_obj = lib.get_object(data)
        except Exception:
            pass
    if mesh_obj:
        try:
            mesh_obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            unreal.log("set_collision_enabled ok")
        except Exception as e:
            unreal.log_warning("collision method: " + str(e))
            try:
                bi = mesh_obj.get_editor_property("body_instance")
                bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
                mesh_obj.set_editor_property("body_instance", bi)
                unreal.log("body_instance collision ok")
            except Exception as e2:
                unreal.log_warning("bi: " + str(e2))
        try:
            mesh_obj.set_editor_property("cast_shadow", False)
        except Exception:
            pass
        # Ensure material default
        try:
            mesh_obj.set_material(0, unreal.load_asset(MATS[1]))
        except Exception:
            pass
    if root_h and mesh_h:
        try:
            ok = sub.attach_subobject(root_h, mesh_h)
            unreal.log("attach_subobject -> " + str(ok))
        except Exception as e:
            unreal.log_warning("attach: " + str(e))
        try:
            # Prefer mesh as scene root for simpler transforms
            ok = sub.make_new_scene_root(mesh_h)
            unreal.log("make_new_scene_root -> " + str(ok))
        except Exception as e:
            unreal.log_warning("make root: " + str(e))
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        unreal.log_warning(str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)


def build_apply_state():
    bp = unreal.load_asset(PATH)
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    unreal.log("graphs=" + str(graphs))
    if "ApplyState" in graphs:
        unreal.log("ApplyState exists — leave it")
        return True

    bel.add_function_graph(bp, "ApplyState")
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

    if find_pin(entry, "State", "Output") is None:
        ge.add_graph_input_parameter("State", make_byte_pin())

    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
    dump(entry, "entry")

    # Get PlotMesh component
    get_mesh = ge.add_get_member_variable_node("PlotMesh")
    bel.set_node_pos(get_mesh, pos(200, 200))
    dump(get_mesh, "get_mesh")

    # Switch on Int (promote byte)
    # Try SwitchInteger / Switch on Int
    switch = None
    for path in (
        "Flow Control|Switch|Switch on Int",
        "Switch on Int",
        "Utilities|Switch|SwitchInteger",
    ):
        try:
            switch = ge.create_node_from_name(path, unreal.Vector2D(500, 0), [])
            if switch and len(bel.list_all_pins(switch)) > 0:
                unreal.log("switch via " + path)
                break
            if switch:
                ge.remove_nodes([switch])
                switch = None
        except Exception as e:
            unreal.log_warning("switch try {}: {}".format(path, e))

    if not switch:
        # Fallback: chain of Equal+Branch — still works
        unreal.log("no Switch node — using Branch chain")
        return build_apply_state_branches(ge, entry, get_mesh)

    bel.set_node_pos(switch, pos(500, 0))
    dump(switch, "switch")
    connect(find_pin(entry, "then", "Output"), find_pin(switch, "execute", "Input") or find_pin(switch, "Exec", "Input"), "e->sw")
    # Selection pin
    sel = find_pin(switch, "Selection", "Input") or find_pin(switch, "Index", "Input") or find_pin(switch, "Value", "Input")
    # May need byte->int cast; try direct
    connect(find_pin(entry, "State", "Output"), sel, "state->sel")

    # Add pins 1..4 if needed — Switch on Int often has Add pin
    # Set materials for each case
    for state_val, mat_path, y in ((1, MATS[1], 0), (2, MATS[2], 150), (3, MATS[3], 300), (4, MATS[4], 450)):
        case_pin = find_pin(switch, str(state_val), "Output")
        if not case_pin:
            # Try to add case
            try:
                if hasattr(switch, "add_pin_to_switch_node"):
                    switch.add_pin_to_switch_node()
                    unreal.log("add_pin_to_switch_node")
                case_pin = find_pin(switch, str(state_val), "Output")
            except Exception as e:
                unreal.log_warning("add case: " + str(e))
        dump(switch, "switch2")
        setm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
        bel.set_node_pos(setm, pos(900, y))
        if case_pin:
            connect(case_pin, find_pin(setm, "execute", "Input"), "case{}->set".format(state_val))
        connect(find_pin(get_mesh, "PlotMesh", "Output"), find_pin(setm, "self", "Input"), "mesh->set")
        set_val(find_pin(setm, "Element Index", "Input") or find_pin(setm, "ElementIndex", "Input"), "0", "elem")
        # Material pin — set default to asset path
        mat_pin = find_pin(setm, "Material", "Input")
        set_val(mat_pin, mat_path, "mat{}".format(state_val))
        # Also try soft object
        try:
            mat_pin.set_default_value(mat_path)
        except Exception:
            pass

    # Default / 0: do nothing (or hide) — just return
    ret = ge.add_return_node()
    bel.set_node_pos(ret, pos(1200, 600))
    # Wire Default to return if exists
    def_pin = find_pin(switch, "Default", "Output")
    if def_pin:
        connect(def_pin, find_pin(ret, "execute", "Input"), "def->ret")

    try:
        bel.compile_blueprint(bp)
        unreal.log("ApplyState compile ok")
    except Exception as e:
        unreal.log_warning("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)
    return True


def build_apply_state_branches(ge, entry, get_mesh):
    """Fallback: sequential Equal(State,N) + Branch + SetMaterial."""
    bp = unreal.load_asset(PATH)
    prev_else = find_pin(entry, "then", "Output")
    y = 0
    for state_val, mat_path in ((1, MATS[1]), (2, MATS[2]), (3, MATS[3]), (4, MATS[4])):
        eq = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
        bel.set_node_pos(eq, pos(400, y))
        connect(find_pin(entry, "State", "Output"), find_pin(eq, "A", "Input"), "eqA{}".format(state_val))
        set_val(find_pin(eq, "B", "Input"), str(state_val), "eqB{}".format(state_val))

        br = ge.add_branch_node()
        bel.set_node_pos(br, pos(650, y))
        connect(prev_else, find_pin(br, "execute", "Input"), "->br{}".format(state_val))
        connect(find_pin(eq, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond{}".format(state_val))

        setm = ge.add_call_function_node("/Script/Engine.PrimitiveComponent:SetMaterial")
        bel.set_node_pos(setm, pos(950, y))
        connect(find_pin(br, "then", "Output"), find_pin(setm, "execute", "Input"), "then->set{}".format(state_val))
        connect(find_pin(get_mesh, "PlotMesh", "Output"), find_pin(setm, "self", "Input"), "mesh{}".format(state_val))
        set_val(find_pin(setm, "Element Index", "Input") or find_pin(setm, "ElementIndex", "Input"), "0", "el")
        set_val(find_pin(setm, "Material", "Input"), mat_path, "mat{}".format(state_val))

        ret = ge.add_return_node()
        bel.set_node_pos(ret, pos(1250, y))
        connect(find_pin(setm, "then", "Output"), find_pin(ret, "execute", "Input"), "set->ret{}".format(state_val))

        prev_else = find_pin(br, "else", "Output")
        y += 200

    ret_f = ge.add_return_node()
    bel.set_node_pos(ret_f, pos(950, y))
    connect(prev_else, find_pin(ret_f, "execute", "Input"), "final else")

    try:
        bel.compile_blueprint(bp)
        unreal.log("ApplyState branches compile ok")
    except Exception as e:
        unreal.log_warning("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)
    return True


def main():
    unreal.log("=== phase_viz_apply start ===")
    fix_collision_and_attach()
    build_apply_state()
    bp = unreal.load_asset(PATH)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
    unreal.log("=== phase_viz_apply done ===")


if __name__ == "__main__":
    main()
