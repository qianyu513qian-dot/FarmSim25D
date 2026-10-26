# -*- coding: utf-8 -*-
"""Dump all EventGraph node titles on character."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[EG] " + str(m))
    print("[EG] " + str(m))

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())
log("node_count=" + str(len(nodes)))
for i, n in enumerate(nodes):
    cn = n.get_class().get_name()
    title = cn
    try:
        title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
    except Exception:
        try:
            title = str(n.get_node_title(0))
        except Exception:
            pass
    # also try get_title
    try:
        t2 = str(n.node_comment) if hasattr(n, "node_comment") else ""
    except Exception:
        t2 = ""
    log("{:03d} {} | {} | comment={!r}".format(i, cn, title[:120], t2[:40] if t2 else ""))

# Also check EnhancedInputAction events via pin names
for i, n in enumerate(nodes):
    cn = n.get_class().get_name()
    if "Input" in cn or "Enhanced" in cn or "CallFunction" in cn or "Variable" in cn or "Branch" in cn or "Print" in cn or "Event" in cn:
        pins = []
        for p in bel.list_all_pins(n):
            pins.append("{}:{}".format(p.get_pin_name(), p.get_pin_direction()))
        title = cn
        try:
            title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except Exception:
            pass
        log("DETAIL {} {} pins={}".format(i, title[:80], pins[:12]))
