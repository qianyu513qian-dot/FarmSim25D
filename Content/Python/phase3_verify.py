# -*- coding: utf-8 -*-
"""Verify planting wiring + TillCell still healthy."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def main():
    unreal.log("=== phase3_verify start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))

    for fname in ("TillCell", "PlantCell"):
        g = bel.find_graph(bp, fname)
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        unreal.log("--- " + fname + " ---")
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if "Equal" in t.lower():
                b = find_pin(n, "B", "Input")
                unreal.log("  Equal.B=" + str(b.get_pin_value() if b else None))
            if "Set Array" in t:
                item = find_pin(n, "Item", "Input")
                cps = list(item.list_connected_pins()) if item else []
                unreal.log("  Set.Item val={} conn={}".format(
                    item.get_pin_value() if item else None, len(cps)))
            if "DrawDebug" in t:
                color = find_pin(n, "LineColor", "Input")
                dur = find_pin(n, "Duration", "Input")
                unreal.log("  Debug color={} dur={}".format(
                    color.get_pin_value() if color else None,
                    dur.get_pin_value() if dur else None))
            if t == "MakeVector":
                unreal.log("  Extent XYZ={} {} {}".format(
                    find_pin(n, "X", "Input").get_pin_value(),
                    find_pin(n, "Y", "Input").get_pin_value(),
                    find_pin(n, "Z", "Input").get_pin_value()))

    # BeginPlay NewItem
    eg = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    for n in eg.list_all_nodes():
        if bel.get_node_title(n) == "Add":
            item = find_pin(n, "NewItem", "Input") or find_pin(n, "New Item", "Input")
            if item:
                unreal.log("BeginPlay Add NewItem=" + str(item.get_pin_value()))

    # Character chains
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    for want in ("IA_Interact", "IA_Plant"):
        node = None
        for n in cge.list_all_nodes():
            if want in bel.get_node_title(n):
                node = n
                break
        unreal.log("CHAR " + want + " present=" + str(bool(node)))
        if not node:
            continue
        start = find_pin(node, "Started", "Output")
        frontier = [cp.get_owning_node() for cp in list(start.list_connected_pins())] if start else []
        seen = set()
        while frontier:
            n = frontier.pop(0)
            if id(n) in seen:
                continue
            seen.add(id(n))
            t = bel.get_node_title(n)
            extra = ""
            if t == "Print String":
                insp = find_pin(n, "InString", "Input")
                try:
                    extra = " [" + str(insp.get_pin_value()) + "]"
                except Exception:
                    try:
                        extra = " [" + str(insp.get_default_as_string()) + "]"
                    except Exception:
                        extra = ""
            unreal.log("  chain: " + t + extra)
            for p in bel.list_all_pins(n):
                if "OUTPUT" in str(p.get_pin_direction()):
                    for cp in list(p.list_connected_pins()):
                        frontier.append(cp.get_owning_node())

    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("E mapped=" + str("IA_Interact" in txt and "Key=E" in txt))
    unreal.log("F mapped=" + str("IA_Plant" in txt and "Key=F" in txt))

    try:
        bel.compile_blueprint(bp)
        bel.compile_blueprint(cbp)
        unreal.log("compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.log("=== phase3_verify done ===")


if __name__ == "__main__":
    main()
