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
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def main():
    unreal.log("=== phase2_hoe_align start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    names = [str(n) for n in bel.list_graph_names(bp)]
    unreal.log("graphs " + str(names))

    # Remove empty TillCell if TillCell_0 has the real graph
    # Check node counts
    for gname in ("TillCell", "TillCell_0"):
        g = bel.find_graph(bp, gname)
        if not g:
            unreal.log("missing " + gname)
            continue
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        if not ge:
            unreal.log("no ge " + gname)
            continue
        nodes = list(ge.list_all_nodes())
        unreal.log(gname + " nodes=" + str(len(nodes)))
        for n in nodes:
            unreal.log("  " + bel.get_node_title(n))

    # Prefer rename TillCell_0 -> TillCell after removing empty TillCell
    try:
        bel.remove_function_graph(bp, "TillCell")
        unreal.log("removed empty TillCell")
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        bel.rename_graph(bp, "TillCell_0", "TillCell")
        unreal.log("renamed TillCell_0 -> TillCell")
    except Exception as ex:
        unreal.log_warning("rename: " + str(ex))
        # try find TillCell_0 and rename via API alternate
        try:
            g = bel.find_graph(bp, "TillCell_0")
            if g:
                g.rename("TillCell")
                unreal.log("graph.rename ok")
        except Exception as ex2:
            unreal.log_warning(str(ex2))

    unreal.log("graphs after: " + str([str(n) for n in bel.list_graph_names(bp)]))
    try:
        bel.compile_blueprint(bp)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)

    # Fix character wiring: remove bad TillCell call chain and re-add
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # Find IA_Interact node
    ia_node = None
    for n in cge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            ia_node = n
            unreal.log("found IA_Interact")
            dump(n, "ia")
            break

    # Remove existing TillCell calls and their following branch/prints from hoe
    remove = []
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "TillCell":
            remove.append(n)
    # Also remove Branch that only connects from TillCell - harder; remove Print Tilled/Cannot
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "Print String":
            insp = find_pin(n, "InString", "Input")
            try:
                val = insp.get_pin_value() if insp else ""
            except Exception:
                val = ""
            if val in ("Tilled!", "Cannot till"):
                remove.append(n)
    # remove orphan branches with no incoming from IA
    if remove:
        # also get branches connected from those TillCells
        extra = []
        for n in remove:
            thenp = find_pin(n, "then", "Output")
            if thenp:
                for cp in list(thenp.list_connected_pins()):
                    extra.append(cp.get_owning_node())
        remove = list(set(remove + extra))
        # one more hop for prints from branch
        extra2 = []
        for n in remove:
            for pname in ("then", "else"):
                pp = find_pin(n, pname, "Output")
                if pp:
                    for cp in list(pp.list_connected_pins()):
                        extra2.append(cp.get_owning_node())
        remove = list(set(remove + extra2))
        cge.remove_nodes(remove)
        unreal.log("removed " + str(len(remove)))

    if not ia_node:
        ia_node = cge.create_node_from_name("Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), [])
        bel.set_node_pos(ia_node, pos(-1800, 700))

    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1500, 750))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1500, 850))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1200, 750))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")
    dump(w2g, "w2g")

    till = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell")
    if not till:
        # try TillCell_0 path
        till = cge.create_node_from_name("Till Cell", unreal.Vector2D(-850, 750), [])
    bel.set_node_pos(till, pos(-850, 750))
    dump(till, "till")
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    # pin names from WorldToGrid are GridX/GridY
    connect(find_pin(w2g, "GridX", "Output") or find_pin(w2g, "Grid X", "Output"),
            find_pin(till, "GridX", "Input") or find_pin(till, "Grid X", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output") or find_pin(w2g, "Grid Y", "Output"),
            find_pin(till, "GridY", "Input") or find_pin(till, "Grid Y", "Input"), "gy")

    start = find_pin(ia_node, "Started", "Output")
    connect(start, find_pin(till, "execute", "Input"), "ia->till")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-550, 750))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    connect(find_pin(till, "Success", "Output") or find_pin(till, "Return Value", "Output") or find_pin(till, "ReturnValue", "Output"),
            find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-250, 700))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_pin_value("Tilled!")
    except Exception:
        pass
    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-250, 850))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_pin_value("Cannot till")
    except Exception:
        pass

    # Ensure IMC mapping - dump mappings
    try:
        ia = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/Actions/IA_Interact")
        imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
        k = unreal.Key()
        k.set_editor_property("key_name", "E")
        m = imc.map_key(ia, k)
        unreal.log("map_key result " + str(m))
        unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Input/IMC_Default")
    except Exception as ex:
        unreal.log_warning(str(ex))

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)

    # verify TillCell pins after rename
    funcs = bel.list_functions(bp)
    unreal.log("mgr funcs: " + str([(f.name if hasattr(f,'name') else f) for f in funcs]))
    unreal.log("=== phase2_hoe_align done ===")


if __name__ == "__main__":
    main()