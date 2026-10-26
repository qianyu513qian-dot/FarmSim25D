# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label + " a={} b={}".format(a, b))
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name())
        if name_substr.lower() in pn.lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def dump(node, label):
    pins = bel.list_all_pins(node) if node else []
    unreal.log("{} pins={}".format(label, len(pins)))
    for p in pins:
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def main():
    unreal.log("=== phase2_hoe_fix4 start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)

    # Rename TillCell_0 -> TillCell
    g = bel.find_graph(bp, "TillCell_0")
    if g:
        try:
            bel.rename_graph(g, "TillCell")
            unreal.log("renamed to TillCell")
        except Exception as ex:
            unreal.log_warning("rename_graph: " + str(ex))
    unreal.log("graphs: " + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("funcs: " + str([str(f.name) for f in bel.list_functions(bp)]))

    # Ensure TillCell has GridX/GridY inputs and Success bool return
    # Inspect entry node pins
    g = bel.find_graph(bp, "TillCell") or bel.find_graph(bp, "TillCell_0")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "TillCell" in t or t in ("Till Cell", "Till Cell 0"):
            dump(n, "entry")
        if "Return" in t:
            dump(n, "ret")

    try:
        bel.compile_blueprint(bp)
        unreal.log("mgr compile ok")
    except Exception as ex:
        unreal.log_warning("mgr compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)

    # Character: clean hoe-related nodes carefully
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    ia_node = None
    hoe_remove = []
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_Interact" in t:
            ia_node = n
        # Remove prior hoe attempt nodes by title
        if t in ("Till Cell", "Till Cell 0", "Branch"):
            # only remove Branch if near hoe - check connections later; mark all Branch from previous runs is risky
            pass
        if t in ("Till Cell", "Till Cell 0"):
            hoe_remove.append(n)

    # Find nodes connected from IA_Interact Started
    if ia_node:
        dump(ia_node, "ia")
        start = find_pin(ia_node, "Started", "Output")
        if start:
            connected = list(start.list_connected_pins())
            unreal.log("Started connected to " + str(len(connected)))
            for cp in connected:
                owner = cp.get_owning_node()
                unreal.log("  -> " + bel.get_node_title(owner))
                hoe_remove.append(owner)

    # Collect WorldToGrid / Get GridManagerRef / GetActorLocation that are ONLY for hoe
    # Simpler: remove everything connected downstream of Started, then rebuild
    frontier = list(hoe_remove)
    seen = set()
    while frontier:
        n = frontier.pop()
        if id(n) in seen:
            continue
        seen.add(id(n))
        hoe_remove.append(n)
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    frontier.append(cp.get_owning_node())
            # also follow data inputs' source nodes that we created (GetActorLocation etc) - skip to avoid nuking Tick

    # Also remove orphan Print Tilled/Cannot and their Branch
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            val = ""
            if insp:
                try:
                    val = insp.get_default_as_string()
                except Exception:
                    try:
                        val = str(insp.get_pin_value())
                    except Exception:
                        val = ""
            if val in ("Tilled!", "Cannot till"):
                hoe_remove.append(n)
                # find branch feeding it
                exec_in = find_pin(n, "execute", "Input")
                if exec_in:
                    for cp in list(exec_in.list_connected_pins()):
                        hoe_remove.append(cp.get_owning_node())

    hoe_remove = list({id(n): n for n in hoe_remove}.values())
    if hoe_remove:
        cge.remove_nodes(hoe_remove)
        unreal.log("removed hoe nodes " + str(len(hoe_remove)))

    if not ia_node:
        # re-find after remove
        for n in cge.list_all_nodes():
            if "IA_Interact" in bel.get_node_title(n):
                ia_node = n
                break
    if not ia_node:
        ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
        bel.set_node_pos(ia_node, pos(-1800, 700))

    # Create call nodes AFTER mgr compile
    fname = "TillCell"
    funcs = [str(f.name) for f in bel.list_functions(bp)]
    if "TillCell" not in funcs and "TillCell_0" in funcs:
        fname = "TillCell_0"
    path = "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:" + fname
    unreal.log("calling " + path)

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
    dump(till, "till-before-compile")

    # If no pins, compile character and reconstruct
    if till and len(bel.list_all_pins(till)) == 0:
        unreal.log("till has 0 pins, compiling char then recreating")
        try:
            bel.compile_blueprint(cbp)
        except Exception as ex:
            unreal.log_warning(str(ex))
        cge.remove_nodes([till])
        till = cge.add_call_function_node(path)
        bel.set_node_pos(till, pos(-950, 780))
        dump(till, "till-retry")

    # Try reconstruct if method exists
    if till and len(bel.list_all_pins(till)) == 0:
        for meth in ("reallocate_pins_during_reconstruction", "reconstruct_node", "allocate_default_pins"):
            if hasattr(till, meth):
                try:
                    getattr(till, meth)()
                    unreal.log("called " + meth)
                except Exception as ex:
                    unreal.log_warning(meth + ": " + str(ex))
        dump(till, "till-after-recon")

    # Try create_node_from_name with menu path style
    if till is None or len(bel.list_all_pins(till)) == 0:
        unreal.log("trying alternate create")
        if till:
            cge.remove_nodes([till])
        for alt in [
            "Call Function|" + fname,
            "Farm|Grid|" + fname,
            "BP_GridManager|" + fname,
            fname,
        ]:
            try:
                n = cge.create_node_from_name(alt, unreal.Vector2D(-950, 780), [])
                if n and len(bel.list_all_pins(n)) > 0:
                    till = n
                    unreal.log("alt ok: " + alt)
                    dump(till, "till-alt")
                    break
                elif n:
                    unreal.log("alt empty pins: " + alt)
                    cge.remove_nodes([n])
            except Exception as ex:
                unreal.log_warning(alt + ": " + str(ex))

    dump(till, "till-final")
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")

    # Exec chain: Started -> WorldToGrid -> TillCell
    connect(find_pin(ia_node, "Started", "Output"), find_pin(w2g, "execute", "Input"), "ia->w2g")
    connect(find_pin(w2g, "then", "Output"), find_pin(till, "execute", "Input"), "w2g->till")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, 780))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    succ = (find_pin(till, "Success", "Output")
            or find_pin(till, "ReturnValue", "Output")
            or find_pin(till, "Return Value", "Output"))
    connect(succ, find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, 720))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    insp = find_pin(pr_ok, "InString", "Input")
    if insp:
        try:
            insp.set_default_value("Tilled!")
        except Exception:
            try:
                insp.set_pin_value("Tilled!")
            except Exception as ex:
                unreal.log_warning(str(ex))

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, 880))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    insp2 = find_pin(pr_no, "InString", "Input")
    if insp2:
        try:
            insp2.set_default_value("Cannot till")
        except Exception:
            try:
                insp2.set_pin_value("Cannot till")
            except Exception as ex:
                unreal.log_warning(str(ex))

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning("char compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)

    # Verify final graph
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_Interact" in t or "Till" in t or t == "World To Grid" or t == "Branch":
            dump(n, t)
    unreal.log("=== phase2_hoe_fix4 done ===")


if __name__ == "__main__":
    main()