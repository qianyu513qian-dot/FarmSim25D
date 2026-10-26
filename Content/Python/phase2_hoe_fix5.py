# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


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
    pins = bel.list_all_pins(node) if node else []
    unreal.log("{} pins={}".format(label, len(pins)))
    for p in pins:
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def open_ge(bp, graph_name):
    g = bel.find_graph(bp, graph_name)
    if not g:
        unreal.log_warning("no graph " + graph_name)
        return None, None
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    if not ge:
        # open blueprint editor
        try:
            unreal.AssetEditorSubsystem().open_editor_for_assets([bp])
        except Exception as ex:
            unreal.log_warning(str(ex))
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    return g, ge


def main():
    unreal.log("=== phase2_hoe_fix5 start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("graphs: " + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("funcs: " + str([str(f.name) for f in bel.list_functions(bp)]))

    # Rename whatever TillCell_* to TillCell
    for name in list(bel.list_graph_names(bp)):
        sn = str(name)
        if sn.startswith("TillCell") and sn != "TillCell":
            g = bel.find_graph(bp, sn)
            try:
                bel.rename_graph(g, "TillCell")
                unreal.log("renamed {} -> TillCell".format(sn))
            except Exception as ex:
                unreal.log_warning("rename {}: {}".format(sn, ex))
    # If both TillCell and TillCell_1 exist somehow, keep the one with more nodes
    unreal.log("graphs after rename: " + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("funcs after: " + str([str(f.name) for f in bel.list_functions(bp)]))

    fname = None
    for f in bel.list_functions(bp):
        if str(f.name).startswith("TillCell"):
            fname = str(f.name)
            break
    unreal.log("using function " + str(fname))

    g, ge = open_ge(bp, fname)
    if ge:
        for n in ge.list_all_nodes():
            unreal.log("node: " + bel.get_node_title(n))
            if "TillCell" in bel.get_node_title(n) or "Return" in bel.get_node_title(n):
                dump(n, bel.get_node_title(n))

    try:
        bel.compile_blueprint(bp)
        unreal.log("mgr compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)

    # --- Character ---
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    try:
        unreal.AssetEditorSubsystem().open_editor_for_assets([cbp])
    except Exception:
        pass
    eg = bel.find_event_graph(cbp)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(eg)

    # Remove nodes downstream of IA_Interact Started + till prints
    ia_node = None
    for n in cge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            ia_node = n
            break

    remove = []
    if ia_node:
        start = find_pin(ia_node, "Started", "Output")
        frontier = []
        if start:
            for cp in list(start.list_connected_pins()):
                frontier.append(cp.get_owning_node())
        seen = set()
        while frontier:
            n = frontier.pop()
            if id(n) in seen:
                continue
            seen.add(id(n))
            remove.append(n)
            for p in bel.list_all_pins(n):
                if "OUTPUT" in str(p.get_pin_direction()):
                    for cp in list(p.list_connected_pins()):
                        frontier.append(cp.get_owning_node())

    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if t in ("Till Cell", "Till Cell 0", "Till Cell 1"):
            remove.append(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            val = ""
            if insp:
                try:
                    val = insp.get_default_as_string()
                except Exception:
                    val = ""
            if val in ("Tilled!", "Cannot till"):
                remove.append(n)
                ein = find_pin(n, "execute", "Input")
                if ein:
                    for cp in list(ein.list_connected_pins()):
                        remove.append(cp.get_owning_node())

    remove = list({id(n): n for n in remove}.values())
    if remove:
        cge.remove_nodes(remove)
        unreal.log("removed " + str(len(remove)))

    if not ia_node:
        for n in cge.list_all_nodes():
            if "IA_Interact" in bel.get_node_title(n):
                ia_node = n
                break
    if not ia_node:
        ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
        bel.set_node_pos(ia_node, pos(-1800, 700))

    path = "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:" + fname
    unreal.log("add_call " + path)

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1600, 780))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1600, 920))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1300, 780))
    dump(w2g, "w2g")
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")

    till = cge.add_call_function_node(path)
    bel.set_node_pos(till, pos(-950, 780))
    dump(till, "till")

    if till and len(bel.list_all_pins(till)) == 0:
        unreal.log("0 pins - compile + recreate")
        try:
            bel.compile_blueprint(cbp)
        except Exception as ex:
            unreal.log_warning(str(ex))
        cge.remove_nodes([till])
        # refresh path from compiled mgr
        till = cge.add_call_function_node(path)
        bel.set_node_pos(till, pos(-950, 780))
        dump(till, "till2")

    # Inspect CallFunction node properties for function reference
    if till:
        for prop in dir(till):
            if "func" in prop.lower() or "member" in prop.lower() or "pin" in prop.lower():
                if not prop.startswith("_"):
                    unreal.log("till." + prop)
        try:
            # K2Node_CallFunction has FunctionReference
            fr = till.get_editor_property("function_reference") if hasattr(till, "get_editor_property") else None
            unreal.log("function_reference " + str(fr))
        except Exception as ex:
            unreal.log_warning(str(ex))

    connect(ref_out, find_pin(till, "self", "Input") or find_pin(till, "Target", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")
    connect(find_pin(ia_node, "Started", "Output"), find_pin(w2g, "execute", "Input"), "ia->w2g")
    connect(find_pin(w2g, "then", "Output"), find_pin(till, "execute", "Input"), "w2g->till")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, 780))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    connect(
        find_pin(till, "Success", "Output") or find_pin(till, "ReturnValue", "Output") or find_pin(till, "Return Value", "Output"),
        find_pin(br, "Condition", "Input"),
        "succ",
    )

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, 720))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_default_value("Tilled!")
    except Exception as ex:
        unreal.log_warning(str(ex))

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, 880))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
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
    unreal.log("=== phase2_hoe_fix5 done ===")


if __name__ == "__main__":
    main()