# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA = "/Game/TopDown/Input/Actions/IA_Interact"


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


def dump(node, label):
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def main():
    unreal.log("=== phase2_hoe_fix3 start ===")
    # Probe IMC DefaultKeyMappings
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    for prop in ("default_key_mappings", "DefaultKeyMappings", "mappings"):
        try:
            v = imc.get_editor_property(prop)
            unreal.log("imc." + prop + " = " + str(v) + " type=" + str(type(v)))
        except Exception as ex:
            unreal.log_warning(prop + ": " + str(ex))
    # dir map_key / map related
    for n in dir(imc):
        if "map" in n.lower() or "key" in n.lower():
            unreal.log("imc." + n)
    # Look at existing mappings via default_mapping_contexts on character or find how Move is mapped
    # Try unreal.InputCoreTypes or Keys
    try:
        keys = unreal.Keys
        unreal.log("Keys.E = " + str(keys.E))
    except Exception as ex:
        unreal.log_warning("Keys: " + str(ex))
    try:
        k = unreal.InputChord()
        unreal.log("InputChord " + str(k))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Try map_key with Keys.E if available
    ia = unreal.EditorAssetLibrary.load_asset(IA)
    try:
        from unreal import Keys
        m = imc.map_key(ia, Keys.E)
        unreal.log("map_key Keys.E -> " + str(m))
    except Exception as ex:
        unreal.log_warning("map Keys.E: " + str(ex))
    try:
        # EnhancedInputKeyMapping
        mapping = unreal.EnhancedActionKeyMapping()
        mapping.set_editor_property("action", ia)
        # try set key via name on struct
        try:
            key = unreal.Key()
            # In UE5 python, sometimes: unreal.Name("E")
            key.set_editor_property("key_name", unreal.Name("E"))
            mapping.set_editor_property("key", key)
            unreal.log("mapping key set: " + str(mapping.get_editor_property("key")))
        except Exception as ex:
            unreal.log_warning("set key: " + str(ex))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Read how existing Move mapping is stored - open asset as text? use get_editor_property default_key_mappings
    try:
        dkm = imc.get_editor_property("default_key_mappings")
        unreal.log("dkm len " + str(len(dkm)) if dkm is not None else "None")
        if dkm:
            for i, m in enumerate(dkm):
                unreal.log("dkm[{}] {}".format(i, m))
                try:
                    unreal.log("  action=" + str(m.get_editor_property("action")))
                    unreal.log("  key=" + str(m.get_editor_property("key")))
                except Exception as ex:
                    unreal.log_warning(str(ex))
    except Exception as ex:
        unreal.log_warning("dkm: " + str(ex))

    # Fix character graph with TillCell_0
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # Clean previous hoe nodes: IA_Interact kept; remove Till Cell / Till Cell 0 / WorldToGrid duplicates from hoe area / Branch+Prints for till
    remove = []
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if t in ("Till Cell", "Till Cell 0", "TillCell", "TillCell_0"):
            remove.append(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            val = ""
            try:
                val = insp.get_default_as_string() if insp else ""
            except Exception:
                try:
                    val = str(insp.get_pin_value()) if insp else ""
                except Exception:
                    val = ""
            if "Till" in str(val) or "Cannot till" in str(val) or val in ("Tilled!", "Cannot till"):
                remove.append(n)
    # also remove WorldToGrid that are only for hoe - keep Tick's WorldToGrid
    # safer: remove branches that have no IA connection after cleanup
    extra = set()
    for n in remove:
        for pname in ("then", "else", "execute"):
            # outgoing
            for p in bel.list_all_pins(n):
                if str(p.get_pin_direction()).endswith("OUTPUT: 1>") or "OUTPUT" in str(p.get_pin_direction()):
                    for cp in list(p.list_connected_pins()):
                        extra.add(cp.get_owning_node())
    remove = list(set(remove) | extra)
    # second hop for prints
    extra2 = set()
    for n in remove:
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    extra2.add(cp.get_owning_node())
    remove = list(set(remove) | extra2)
    if remove:
        cge.remove_nodes(remove)
        unreal.log("removed " + str(len(remove)))

    ia_node = None
    for n in cge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            ia_node = n
            break
    if not ia_node:
        ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
        bel.set_node_pos(ia_node, pos(-1800, 700))
        unreal.log("created IA_Interact")

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1500, 750))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1500, 900))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1200, 750))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")

    till = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell_0")
    bel.set_node_pos(till, pos(-850, 750))
    dump(till, "till")
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")
    connect(find_pin(ia_node, "Started", "Output"), find_pin(till, "execute", "Input"), "ia->till")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-550, 750))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    succ = find_pin(till, "Success", "Output") or find_pin(till, "ReturnValue", "Output") or find_pin(till, "Return Value", "Output")
    connect(succ, find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-250, 700))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_pin_value("Tilled!")
    except Exception as ex:
        unreal.log_warning("set Tilled: " + str(ex))
        try:
            find_pin(pr_ok, "InString", "Input").set_default_value("Tilled!")
        except Exception as ex2:
            unreal.log_warning(str(ex2))

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-250, 850))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_pin_value("Cannot till")
    except Exception:
        try:
            find_pin(pr_no, "InString", "Input").set_default_value("Cannot till")
        except Exception as ex:
            unreal.log_warning(str(ex))

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)

    # Rename TillCell_0 properly: remove and recreate as TillCell? Or use rename_graph correctly
    # rename_graph takes at most 2 args - maybe (graph, new_name) or (bp, new_name) wrong
    try:
        import inspect
        unreal.log("rename_graph sig: " + str(inspect.signature(bel.rename_graph)))
    except Exception as ex:
        unreal.log_warning(str(ex))
        try:
            unreal.log("rename_graph doc: " + str(bel.rename_graph.__doc__))
        except Exception:
            pass

    unreal.log("=== phase2_hoe_fix3 done ===")


if __name__ == "__main__":
    main()