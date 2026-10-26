# -*- coding: utf-8 -*-
"""Conservative hoe wire: no open_editor, no rename."""
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


def main():
    unreal.log("=== phase2_hoe_safe start ===")

    # 1) IMC: map E to IA_Interact (same pattern as WASD script)
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    ia = unreal.EditorAssetLibrary.load_asset(IA)
    # Unmap duplicate empties first
    try:
        imc.unmap_all_keys_from_action(ia)
        unreal.log("unmapped old IA_Interact keys")
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        m = imc.map_key(ia, unreal.Key.E)
        unreal.log("map_key E -> " + str(m))
    except Exception as ex:
        unreal.log_warning("Key.E failed: " + str(ex))
        # fallback try Key with name
        try:
            m = imc.map_key(ia, unreal.Key("E"))
            unreal.log("map_key Key(E) -> " + str(m))
        except Exception as ex2:
            unreal.log_warning(str(ex2))
    unreal.EditorAssetLibrary.save_asset(IMC)
    unreal.log("IMC after: " + str(imc.get_editor_property("default_key_mappings")))

    # 2) Character EventGraph — remove only orphan TillCell calls + till prints
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    ia_node = None
    remove = []
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "IA_Interact" in t:
            ia_node = n
        if t == "TillCell" or t.startswith("Till Cell"):
            remove.append(n)

    # Also remove nodes only reachable from those TillCells / from Started if any
    if ia_node:
        start = find_pin(ia_node, "Started", "Output")
        if start:
            for cp in list(start.list_connected_pins()):
                remove.append(cp.get_owning_node())

    for n in list(remove):
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    remove.append(cp.get_owning_node())

    # Print strings for till
    for n in cge.list_all_nodes():
        if bel.get_node_title(n) == "Print String":
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

    # Don't remove Get GridManagerRef used by Tick — only remove ones we create in hoe chain.
    # Safer: only remove TillCell + downstream + till prints + Started downstream.
    # Filter out nodes titled Get GridManagerRef / WorldToGrid if they have OTHER connections from Tick.
    # Simpler approach: only remove Till* and till prints and whatever Started currently connects to.
    final_remove = []
    for n in remove:
        t = bel.get_node_title(n)
        # Keep shared Tick helpers: never remove if title is ReceiveTick related
        if t in ("Get GridManagerRef", "WorldToGrid", "GridToWorld"):
            # only remove if exclusively in Started chain — skip keeping for safety if ambiguous
            # We'll create fresh Get/WorldToGrid for hoe; leave Tick ones alone.
            # If this node is in remove because it's downstream of Started, remove it.
            pass
        final_remove.append(n)

    final_remove = list({id(n): n for n in final_remove}.values())
    if final_remove:
        # Extra safety: don't remove ReceiveTick / ReceiveBeginPlay / Set GridManagerRef
        safe = []
        for n in final_remove:
            t = bel.get_node_title(n)
            if t in ("ReceiveTick", "ReceiveBeginPlay", "Event Tick", "Event BeginPlay"):
                continue
            if t.startswith("Set GridManagerRef"):
                continue
            safe.append(n)
        cge.remove_nodes(safe)
        unreal.log("removed " + str(len(safe)))

    # re-find ia
    if not ia_node:
        for n in cge.list_all_nodes():
            if "IA_Interact" in bel.get_node_title(n):
                ia_node = n
                break
    if not ia_node:
        ia_node = cge.create_node_from_name(
            "Input|EnhancedActionEvents|IA_Interact", unreal.Vector2D(-1800, 700), []
        )
        bel.set_node_pos(ia_node, pos(-1800, 700))
        unreal.log("created IA_Interact node")

    # Fresh hoe chain (separate Get nodes so Tick untouched)
    get_ref = cge.add_get_member_variable_node("GridManagerRef")
    bel.set_node_pos(get_ref, pos(-1600, 780))
    ref_out = find_pin(get_ref, "GridManagerRef", "Output")

    get_loc = cge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    bel.set_node_pos(get_loc, pos(-1600, 920))

    w2g = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
    bel.set_node_pos(w2g, pos(-1300, 780))
    connect(ref_out, find_pin(w2g, "self", "Input"), "ref-w2g")
    connect(find_pin(get_loc, "ReturnValue", "Output"), find_pin(w2g, "WorldLocation", "Input"), "loc")

    till = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:TillCell")
    bel.set_node_pos(till, pos(-950, 780))
    unreal.log("till pins=" + str(len(bel.list_all_pins(till)) if till else 0))
    connect(ref_out, find_pin(till, "self", "Input"), "ref-till")
    connect(find_pin(w2g, "GridX", "Output"), find_pin(till, "GridX", "Input"), "gx")
    connect(find_pin(w2g, "GridY", "Output"), find_pin(till, "GridY", "Input"), "gy")
    connect(find_pin(ia_node, "Started", "Output"), find_pin(w2g, "execute", "Input"), "ia->w2g")
    connect(find_pin(w2g, "then", "Output"), find_pin(till, "execute", "Input"), "w2g->till")

    br = cge.add_branch_node()
    bel.set_node_pos(br, pos(-650, 780))
    connect(find_pin(till, "then", "Output"), find_pin(br, "execute", "Input"), "till->br")
    connect(find_pin(till, "Success", "Output"), find_pin(br, "Condition", "Input"), "succ")

    pr_ok = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_ok, pos(-350, 720))
    connect(find_pin(br, "then", "Output"), find_pin(pr_ok, "execute", "Input"), "ok")
    try:
        find_pin(pr_ok, "InString", "Input").set_default_value("Tilled!")
    except Exception as ex:
        unreal.log_warning("set Tilled: " + str(ex))

    pr_no = cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr_no, pos(-350, 880))
    connect(find_pin(br, "else", "Output"), find_pin(pr_no, "execute", "Input"), "no")
    try:
        find_pin(pr_no, "InString", "Input").set_default_value("Cannot till")
    except Exception as ex:
        unreal.log_warning("set Cannot: " + str(ex))

    try:
        bel.compile_blueprint(cbp)
        unreal.log("char compile ok")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)

    # Verify Started chain
    start = find_pin(ia_node, "Started", "Output")
    cps = list(start.list_connected_pins()) if start else []
    unreal.log("Started connections=" + str(len(cps)))
    for cp in cps:
        unreal.log("  -> " + bel.get_node_title(cp.get_owning_node()))

    unreal.log("=== phase2_hoe_safe done ===")


if __name__ == "__main__":
    main()