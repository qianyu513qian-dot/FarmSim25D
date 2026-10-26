# -*- coding: utf-8 -*-
"""Force GrowCell Equal.B=Watered(3), Set Item=4, VisualizeCell State=4."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_GC] " + str(m))
    print("[FIX_GC] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = str(bel.get_node_title(n))
    if "equal" in t.lower():
        b = find_pin(n, "B", "Input")
        before = b.get_pin_value() if b else None
        if b:
            b.set_pin_value("3")
            log("GrowCell Equal.B {} -> {}".format(before, b.get_pin_value()))
    if "Set Array" in t:
        item = find_pin(n, "Item", "Input")
        if item:
            log("Set.Item before={!r}".format(item.get_pin_value()))
            item.set_pin_value("4")
            log("Set.Item after={!r}".format(item.get_pin_value()))
    if t == "VisualizeCell":
        st = find_pin(n, "State", "Input")
        if st:
            log("Viz.State before={!r}".format(st.get_pin_value()))
            st.set_pin_value("4")
            log("Viz.State after={!r}".format(st.get_pin_value()))

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE")
