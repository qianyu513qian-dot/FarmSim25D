# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def find_pin(node, sub, direction=None):
    for p in bel.list_all_pins(node):
        if sub.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))

ge.set_local_variable_default_value("LitTilled", "1")
ge.set_local_variable_default_value("LitEmpty", "0")
unreal.log("LitTilled def=" + str(ge.get_local_variable_default_value("LitTilled")))
unreal.log("LitEmpty def=" + str(ge.get_local_variable_default_value("LitEmpty")))

# Prefer Get LitTilled -> Item
set_elem = None
for n in ge.list_all_nodes():
    if "Set Array" in bel.get_node_title(n):
        set_elem = n

# Remove extra Get StateTilled if present; use local
remove = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "StateTilled" in t or "StateEmpty" in t:
        remove.append(n)
if remove:
    ge.remove_nodes(remove)
    unreal.log("removed member gets " + str(len(remove)))

get_t = ge.add_get_local_variable_node("LitTilled")
item = find_pin(set_elem, "Item", "Input")
try:
    item.break_pin_links()
except Exception:
    pass
out = find_pin(get_t, "LitTilled", "Output")
ok = out.try_create_connection(item)
unreal.log("LitTilled->Item " + str(ok) + " out=" + str(out.get_pin_name() if out else None))

# Verify visual chain still intact
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "DrawDebug" in t:
        c = find_pin(n, "Center", "Input")
        d = find_pin(n, "Duration", "Input")
        col = find_pin(n, "LineColor", "Input")
        unreal.log("dbg center_conn={} dur={} color={}".format(
            len(list(c.list_connected_pins())),
            d.get_pin_value(), col.get_pin_value()))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.log("ready for playtest")