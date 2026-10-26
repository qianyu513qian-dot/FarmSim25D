# -*- coding: utf-8 -*-
"""Probe VisualizeCell exec chain from entry in detail."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[PROBE2] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))

# Dump every exec connection
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    for p in bel.list_all_pins(n):
        if "exec" not in str(p.get_pin_type()).lower() and "execute" not in str(p.get_pin_name()).lower() and str(p.get_pin_name()).lower() not in ("then", "else", "completed", "loopbody", "then_0", "then_1", "then0", "then1"):
            # also catch Sequence then_0
            pn = str(p.get_pin_name()).lower()
            if pn not in ("then", "else", "execute", "completed", "loop body", "then_0", "then_1", "then0", "then1") and not pn.startswith("then"):
                continue
        conns = []
        for cp in p.list_connected_pins():
            conns.append("{}:{}@{}".format(cp.get_pin_name(), cp.get_owning_node().get_class().get_name(), bel.get_node_title(cp.get_owning_node())))
        if conns or str(p.get_pin_name()).lower() in ("then", "else", "execute") or str(p.get_pin_name()).lower().startswith("then"):
            if conns:
                log("{} [{}] {} -> {}".format(t, n.get_class().get_name(), p.get_pin_name(), conns))

# Dump Equal Byte pin values
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Equal" in t.lower() or "Sequence" in t or "HideGrass" in t:
        for p in bel.list_all_pins(n):
            try:
                v = p.get_pin_value()
            except Exception:
                v = ""
            conns = [bel.get_node_title(cp.get_owning_node()) + "." + str(cp.get_pin_name()) for cp in p.list_connected_pins()]
            log("DETAIL {} | {} dir={} val={!r} conns={}".format(t, p.get_pin_name(), p.get_pin_direction(), v, conns))

log("DONE")
