# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
MGR = "/Game/Farm/Grid/BP_GridManager"


def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def main():
    unreal.log("=== phase2_verify start ===")
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

    # Find hoe chain prints: walk from IA_Interact Started
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
        unreal.log("chain: " + bel.get_node_title(n))
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                for cp in list(p.list_connected_pins()):
                    frontier.append(cp.get_owning_node())

    for n in chain:
        if bel.get_node_title(n) != "Print String":
            continue
        insp = find_pin(n, "InString", "Input")
        unreal.log("Print pin methods related:")
        for m in dir(insp):
            if not m.startswith("_"):
                unreal.log("  " + m)
        cur = ""
        try:
            cur = insp.get_default_as_string()
        except Exception as ex:
            unreal.log_warning("get_default_as_string: " + str(ex))
        try:
            cur2 = insp.get_pin_value()
            unreal.log("get_pin_value=" + str(cur2))
        except Exception as ex:
            unreal.log_warning("get_pin_value: " + str(ex))
        unreal.log("current default=[" + str(cur) + "]")
        # Determine then vs else
        ein = find_pin(n, "execute", "Input")
        src = list(ein.list_connected_pins())[0]
        src_name = str(src.get_pin_name())
        msg = "Tilled!" if src_name == "then" else "Cannot till"
        ok = False
        for meth, args in [
            ("set_pin_value", (msg,)),
            ("set_default_as_string", (msg,)),
            ("set_default_value", (msg,)),
        ]:
            if hasattr(insp, meth):
                try:
                    getattr(insp, meth)(*args)
                    unreal.log(meth + " -> " + msg)
                    ok = True
                    break
                except Exception as ex:
                    unreal.log_warning(meth + ": " + str(ex))
        if not ok:
            # try import_text on pin
            try:
                insp.import_text('"' + msg + '"')
                unreal.log("import_text ok " + msg)
            except Exception as ex:
                unreal.log_warning("import_text: " + str(ex))

    # Verify TillCell internals: entry GridX connected?
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "TillCell":
            for p in bel.list_all_pins(n):
                cps = list(p.list_connected_pins())
                unreal.log("entry {} -> {} pins".format(p.get_pin_name(), len(cps)))
                for cp in cps:
                    unreal.log("  -> {} .{}".format(bel.get_node_title(cp.get_owning_node()), cp.get_pin_name()))
        if t == "Return Node":
            succ = find_pin(n, "Success", "Input")
            if succ:
                try:
                    unreal.log("Return Success default=" + str(succ.get_default_as_string()))
                except Exception:
                    try:
                        unreal.log("Return Success val=" + str(succ.get_pin_value()))
                    except Exception as ex:
                        unreal.log_warning(str(ex))
                cps = list(succ.list_connected_pins())
                unreal.log("Return Success connected=" + str(len(cps)))

    try:
        bel.compile_blueprint(cbp)
        bel.compile_blueprint(bp)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("=== phase2_verify done ===")


if __name__ == "__main__":
    main()