# -*- coding: utf-8 -*-
"""Inspect WBP_RestOrderList EventGraph + widget names; fix missing TxtMoney."""
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
PATH = "/Game/Farm/UI/WBP_RestOrderList"
BUB = "/Game/Farm/UI/WBP_RestOrderBubble"
R = {"steps": []}

def log(m):
    unreal.log("[WBPFIX2] " + str(m)); print("[WBPFIX2] " + str(m)); R["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

wbp = unreal.load_asset(PATH)
# widgets
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    pn = o.get_path_name()
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in pn:
        widgets[o.get_name()] = o.get_class().get_name()
R["widgets"] = widgets
log("widgets=" + str(widgets))

# EventGraph nodes
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))
nodes = []
for n in ge.list_all_nodes():
    pins = []
    for p in bel.list_all_pins(n):
        pins.append({
            "name": str(p.get_pin_name()),
            "dir": str(p.get_pin_direction()),
            "type": str(p.get_pin_type_display_string()),
            "linked": [title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in (p.list_connected_pins() or [])],
        })
    err = None
    try:
        err = n.get_editor_property("error_msg")
    except Exception:
        pass
    nodes.append({"title": title(n), "cls": n.get_class().get_name(), "err": str(err)[:200] if err else None, "pins": pins})
R["nodes"] = nodes
log("node_count=" + str(len(nodes)))
for n in nodes:
    log("  {} | {} err={}".format(n["title"], n["cls"], n["err"]))

# Also bubble widgets + nodes
bub = unreal.load_asset(BUB)
bwidgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderBubble.WBP_RestOrderBubble:WidgetTree." in o.get_path_name():
        bwidgets[o.get_name()] = o.get_class().get_name()
R["bubble_widgets"] = bwidgets
bge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bub))
berrs = []
for n in (bge.list_nodes_with_errors() or []):
    berrs.append(title(n))
R["bubble_err_nodes"] = berrs
try:
    R["bubble_status"] = str(bub.get_editor_property("status"))
except Exception as e:
    R["bubble_status"] = str(e)

out = unreal.Paths.project_saved_dir() + "WBP_RestOrder_inspect.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("WROTE " + out)
