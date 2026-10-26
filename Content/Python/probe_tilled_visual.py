# -*- coding: utf-8 -*-
"""Probe highlight + enum + GridManager tick/event for tilled visuals."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
ENUM = "/Game/Farm/Grid/E_PlotState"


def dump_pins(node, label):
    for p in bel.list_all_pins(node):
        unreal.log("  [{}] {} | {}".format(label, p.get_pin_name(), p.get_pin_direction()))


def main():
    unreal.log("=== probe_tilled_visual start ===")
    # Enum
    e = unreal.EditorAssetLibrary.load_asset(ENUM)
    unreal.log("enum=" + str(e))
    try:
        entries = e.get_editor_property("names")
        unreal.log("names=" + str(entries))
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        for attr in ("enumerators", "names", "display_name_map"):
            if hasattr(e, "get_editor_property"):
                try:
                    unreal.log(attr + "=" + str(e.get_editor_property(attr)))
                except Exception:
                    pass
    except Exception:
        pass

    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    unreal.log("mgr vars:")
    for v in bel.list_member_variables(bp):
        unreal.log("  " + str(v))
    unreal.log("mgr graphs: " + str([str(n) for n in bel.list_graph_names(bp)]))

    # Event graph nodes
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    if ge:
        for n in ge.list_all_nodes():
            unreal.log("mgr EG: " + bel.get_node_title(n))

    # Character tick highlight
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    tick = None
    for n in cge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Tick" in t and ("Receive" in t or t == "Event Tick" or "Tick" == t):
            tick = n
            unreal.log("found tick: " + t)
            dump_pins(n, "tick")
    # Walk tick chain briefly
    if tick:
        then = None
        for p in bel.list_all_pins(tick):
            if "then" in str(p.get_pin_name()).lower() or str(p.get_pin_name()) == "then":
                then = p
        # also Output execute often named then
        start_pins = [p for p in bel.list_all_pins(tick) if "OUTPUT" in str(p.get_pin_direction())]
        frontier = []
        for p in start_pins:
            if "then" in str(p.get_pin_name()).lower() or str(p.get_pin_name()) == "OutputDelegate":
                continue
            if str(p.get_pin_name()) in ("then", "execute") or "OUTPUT" in str(p.get_pin_direction()):
                if "then" == str(p.get_pin_name()) or str(p.get_pin_name()) == "then":
                    for cp in list(p.list_connected_pins()):
                        frontier.append(cp.get_owning_node())
        # simpler: all then from tick
        for p in bel.list_all_pins(tick):
            if str(p.get_pin_name()) == "then":
                for cp in list(p.list_connected_pins()):
                    frontier.append(cp.get_owning_node())
        seen = set()
        steps = 0
        while frontier and steps < 40:
            n = frontier.pop(0)
            if id(n) in seen:
                continue
            seen.add(id(n))
            steps += 1
            t = bel.get_node_title(n)
            unreal.log("tick-chain: " + t)
            for p in bel.list_all_pins(n):
                if "OUTPUT" in str(p.get_pin_direction()) and str(p.get_pin_name()) in ("then", "else"):
                    for cp in list(p.list_connected_pins()):
                        frontier.append(cp.get_owning_node())

    # DrawDebugBox path availability
    for path in [
        "/Script/Engine.KismetSystemLibrary:DrawDebugBox",
        "/Script/Engine.KismetSystemLibrary:DrawDebugSolidBox",
    ]:
        n = cge.add_call_function_node(path)
        if n:
            unreal.log("ok " + path + " pins=" + str(len(bel.list_all_pins(n))))
            for p in bel.list_all_pins(n):
                unreal.log("  " + str(p.get_pin_name()))
            cge.remove_nodes([n])
        else:
            unreal.log_warning("fail " + path)

    # ForLoop / Array_Length for PlotStates refresh
    for name in [
        "Utilities|FlowControl|ForLoop",
        "/Script/Engine.KismetArrayLibrary:Array_Length",
        "/Script/Engine.KismetArrayLibrary:Array_Get",
    ]:
        try:
            if name.startswith("/"):
                n = cge.add_call_function_node(name)
            else:
                n = cge.create_node_from_name(name, unreal.Vector2D(0, 0), [])
            unreal.log("node " + name + " -> " + str(n) + (" " + bel.get_node_title(n) if n else ""))
            if n:
                cge.remove_nodes([n])
        except Exception as ex:
            unreal.log_warning(name + ": " + str(ex))

    unreal.log("=== probe_tilled_visual done ===")


if __name__ == "__main__":
    main()