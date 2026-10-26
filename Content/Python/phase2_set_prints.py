# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def main():
    unreal.log("=== set print msgs ===")
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    ia_node = None
    for n in cge.list_all_nodes():
        if "IA_Interact" in bel.get_node_title(n):
            ia_node = n
            break
    start = find_pin(ia_node, "Started", "Output")
    frontier = [cp.get_owning_node() for cp in list(start.list_connected_pins())]
    seen = set()
    chain = []
    while frontier:
        n = frontier.pop(0)
        if id(n) in seen:
            continue
        seen.add(id(n))
        chain.append(n)
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    frontier.append(cp.get_owning_node())

    for n in chain:
        title = bel.get_node_title(n)
        if "Print" not in title:
            continue
        insp = find_pin(n, "InString", "Input")
        ein = find_pin(n, "execute", "Input")
        src = list(ein.list_connected_pins())[0]
        src_name = str(src.get_pin_name())
        msg = "Tilled!" if src_name == "then" else "Cannot till"
        unreal.log("Print from Branch.{} -> set '{}'".format(src_name, msg))
        for m in dir(insp):
            if "pin" in m.lower() or "default" in m.lower() or "value" in m.lower() or "text" in m.lower():
                if not m.startswith("_"):
                    unreal.log("  meth " + m)
        try:
            insp.set_pin_value(msg)
            unreal.log("set_pin_value ok")
        except Exception as ex:
            unreal.log_warning("set_pin_value: " + str(ex))
        try:
            unreal.log("after get_pin_value=" + str(insp.get_pin_value()))
        except Exception as ex:
            unreal.log_warning(str(ex))
        try:
            unreal.log("after get_default_as_string=" + str(insp.get_default_as_string()))
        except Exception as ex:
            unreal.log_warning(str(ex))

    bel.compile_blueprint(cbp)
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.log("done")


if __name__ == "__main__":
    main()