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

# Fix center connection + enum via import_text
set_elem = g2w = dbg = equal = entry = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    unreal.log("T=[" + t + "]")
    if "Set Array" in t: set_elem = n
    if t == "GridToWorld": g2w = n
    if "DrawDebugBox" in t: dbg = n
    if "Equal" in t.lower() or "Equal" in t.lower(): equal = n
    if t == "TillCell": entry = n

unreal.log("equal="+str(equal)+" set="+str(set_elem)+" g2w="+str(g2w)+" dbg="+str(dbg))

# Connect World Location -> Center
if g2w and dbg:
    wp = find_pin(g2w, "World", "Output")
    cp = find_pin(dbg, "Center", "Input")
    unreal.log("world pin="+str(wp.get_pin_name() if wp else None))
    if wp and cp:
        # break existing center links
        try:
            cp.break_pin_links()
        except Exception:
            pass
        ok = wp.try_create_connection(cp)
        unreal.log("center conn " + str(ok))

# Enum pin type info + import_text attempts
item = find_pin(set_elem, "Item", "Input") if set_elem else None
if item:
    unreal.log("Item type=" + str(item.get_pin_type()))
    unreal.log("Item type display=" + str(item.get_pin_type_display_string()))
    unreal.log("Item export=" + str(item.export_text()))
    for txt in [
        "Tilled",
        "E_PlotState::Tilled",
        "NewEnumerator1",
        "E_PlotState::NewEnumerator1",
        "(E_PlotState)1",
        "1",
    ]:
        try:
            item.import_text(txt)
            unreal.log("import_text({}) -> export={} val={}".format(txt, item.export_text(), item.get_pin_value()))
        except Exception as ex:
            unreal.log_warning("import {}: {}".format(txt, ex))

# Equal node B pin
for n in ge.list_all_nodes():
    if "Equal" in bel.get_node_title(n).lower() or "Byte" in bel.get_node_title(n):
        unreal.log("eq title=" + bel.get_node_title(n))
        for p in bel.list_all_pins(n):
            unreal.log("  {} exp={} val={} conn={}".format(
                p.get_pin_name(), p.export_text(), 
                (p.get_pin_value() if hasattr(p,'get_pin_value') else ''),
                len(list(p.list_connected_pins()))))

# BeginPlay Array_Add Empty how stored
ege = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
for n in ege.list_all_nodes():
    if "Add" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if "Item" in str(p.get_pin_name()) or "NewItem" in str(p.get_pin_name()):
                unreal.log("ArrayAdd {} export={} val={}".format(p.get_pin_name(), p.export_text(), p.get_pin_value()))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.log("done")