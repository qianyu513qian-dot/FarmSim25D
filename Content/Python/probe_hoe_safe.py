# -*- coding: utf-8 -*-
"""Conservative probe only — no open_editor, no rename, no remove."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA = "/Game/TopDown/Input/Actions/IA_Interact"


def dump_pins(node, label):
    if not node:
        unreal.log(label + ": None")
        return
    pins = bel.list_all_pins(node)
    unreal.log("{} title={} pins={}".format(label, bel.get_node_title(node), len(pins)))
    for p in pins:
        unreal.log("  {} | {}".format(p.get_pin_name(), p.get_pin_direction()))


def main():
    unreal.log("=== probe_hoe_safe start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("mgr graphs: " + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("mgr funcs: " + str([str(f.name) for f in bel.list_functions(bp)]))

    till_name = None
    for f in bel.list_functions(bp):
        if "Till" in str(f.name):
            till_name = str(f.name)
            break
    unreal.log("till_name=" + str(till_name))

    if till_name:
        g = bel.find_graph(bp, till_name)
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g) if g else None
        unreal.log("till graph={} ge={}".format(g, ge))
        if ge:
            for n in ge.list_all_nodes():
                t = bel.get_node_title(n)
                unreal.log("  till-node: " + t)
                if "Till" in t or "Return" in t or "IsValid" in t or "Branch" in t or "Set Array" in t or t == "Get":
                    dump_pins(n, t)

    # Try add_call without keeping it — check pin count
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    eg = bel.find_event_graph(cbp)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    unreal.log("char event ge=" + str(cge))
    if cge and till_name:
        path = "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:" + till_name
        n = cge.add_call_function_node(path)
        dump_pins(n, "trial-call")
        if n:
            cge.remove_nodes([n])
            unreal.log("trial call removed")

    # Character: list IA_Interact and nearby
    if cge:
        for n in cge.list_all_nodes():
            t = bel.get_node_title(n)
            if "IA_Interact" in t or "Till" in t:
                dump_pins(n, t)
                # list Started connections
                for p in bel.list_all_pins(n):
                    if "Started" in str(p.get_pin_name()):
                        cps = list(p.list_connected_pins())
                        unreal.log("  Started -> " + str(len(cps)))
                        for cp in cps:
                            unreal.log("    " + bel.get_node_title(cp.get_owning_node()))

    # IMC IA_Interact keys
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    dkm = imc.get_editor_property("default_key_mappings")
    unreal.log("IMC: " + str(dkm))
    ia_ok = unreal.EditorAssetLibrary.does_asset_exist(IA)
    unreal.log("IA_Interact exists=" + str(ia_ok))

    # WorldToGrid call pin check
    if cge:
        n = cge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:WorldToGrid")
        dump_pins(n, "trial-w2g")
        if n:
            cge.remove_nodes([n])

    unreal.log("=== probe_hoe_safe done ===")


if __name__ == "__main__":
    main()