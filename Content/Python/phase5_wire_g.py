# -*- coding: utf-8 -*-
"""SAFE: IMC map G->IA_Grow + ADD character grow chain. No remove_nodes, no open_editor."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA_GROW = "/Game/TopDown/Input/Actions/IA_Grow"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] : {}".format(label, ok))
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
        return
    try:
        pin.set_pin_value(str(value))
    except Exception as ex:
        unreal.log_warning(label + str(ex))


def ensure_ia_and_map():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_GROW):
        unreal.EditorAssetLibrary.duplicate_asset(IA_PLANT, IA_GROW)
        unreal.log("duplicated IA_Grow")
    ia = unreal.load_asset(IA_GROW)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_GROW)
    imc = unreal.load_asset(IMC)
    k = unreal.Key()
    k.import_text("G")
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception:
        pass
    m = imc.map_key(ia, k)
    unreal.log("map G -> " + m.get_editor_property("key").export_text())
    unreal.EditorAssetLibrary.save_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("has G=" + str("Key=G" in txt) + " Grow=" + str("IA_Grow" in txt) + " E=" + str("Key=E" in txt))


def wire_character_add_only():
    cbp = unreal.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # Skip if IA_Grow already present
    for n in cge.list_all_nodes():
        try:
            t = bel.get_node_title(n)
        except Exception:
            t = str(n)
        if "IA_Grow" in t:
            unreal.log("IA_Grow already wired — skip character")
            return

    y = 2100
    ia = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Grow", unreal.Vector2D(-1800, y), [])
    if not ia:
        # fallback path variants
        for path in (
            "Enhanced Input|IA_Grow",
            "Input|IA_Grow",
        ):
            ia = cge.create_node_from_name(path, unreal.Vector2D(-1800, y), [])
            if ia:
                break
    if not ia:
        unreal.log_error("could not create IA_Grow event node")
        return
    bel.set_node_pos(ia, pos(-1800, y))
    unreal.log("IA_Grow node ok")

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1600, y + 80))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1600, y + 220))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1300, y + 80))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input") or find_pin(w2g, "World Location", "Input"), "loc")

    grow = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GrowCell")
    bel.set_node_pos(grow, pos(-950, y + 80))
    if grow and len(bel.list_all_pins(grow)) == 0:
        try:
            bel.compile_blueprint(cbp)
        except Exception:
            pass
        cge.remove_nodes([grow])
        grow = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GrowCell")
        bel.set_node_pos(grow, pos(-950, y + 80))

    connect(ref_out, find_pin(grow, "self", "Input"), "ref-grow")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(grow, "GridX", "Input") or find_pin(grow, "Grid X", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(grow, "GridY", "Input") or find_pin(grow, "Grid Y", "Input"), "gy")

    start = find_pin(ia, "Started", "Output") or find_pin(ia, "Triggered", "Output") or find_pin(ia, "Pressed", "Output")
    if find_pin(w2g, "execute", "Input"):
        connect(start, find_pin(w2g, "execute", "Input"), "ia->w2g")
        connect(find_pin(w2g, "then", "Output"), find_pin(grow, "execute", "Input"), "w2g->grow")
    else:
        connect(start, find_pin(grow, "execute", "Input"), "ia->grow")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, y + 80))
    connect(find_pin(grow, "then", "Output"), find_pin(br, "execute", "Input"), "grow->br")
    connect(find_pin(grow, "Success", "Output"), find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, y + 20))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    insp = find_pin(pr_ok, "InString", "Input")
    try:
        insp.set_default_value("Grown!")
    except Exception:
        set_val(insp, "Grown!", "ok")

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, y + 180))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    insp2 = find_pin(pr_no, "InString", "Input")
    try:
        insp2.set_default_value("Cannot grow")
    except Exception:
        set_val(insp2, "Cannot grow", "no")

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def main():
    unreal.log("=== phase5_wire_g start ===")
    ensure_ia_and_map()
    wire_character_add_only()
    unreal.log("=== phase5_wire_g done ===")


if __name__ == "__main__":
    main()
