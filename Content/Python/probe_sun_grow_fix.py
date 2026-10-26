# -*- coding: utf-8 -*-
"""Probe GrowCell + AdvanceDayGrowth + ApplyDayNightVisuals yaw wiring."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[PROBE] " + str(m))
    print("[PROBE] " + str(m))


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


def dump_graph(fname):
    bp = unreal.load_asset(MGR)
    graphs = [str(g) for g in bel.list_graph_names(bp)]
    log("graphs has {}: {}".format(fname, fname in graphs))
    if fname not in graphs:
        return
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    nodes = list(ge.list_all_nodes())
    log("=== {} nodes={} ===".format(fname, len(nodes)))
    for n in nodes:
        t = title(n)
        cls = n.get_class().get_name()
        log("NODE [{}] {}".format(cls, t))
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            pd = str(p.get_pin_direction())
            try:
                v = p.get_pin_value()
            except Exception:
                v = "?"
            cps = []
            try:
                for c in p.list_connected_pins():
                    cps.append((title(c.get_owning_node()), str(c.get_pin_name())))
            except Exception:
                pass
            # Only dump interesting pins (exec, equal, enum, state, connected)
            interesting = (
                cps
                or "equal" in t.lower()
                or "branch" in t.lower()
                or pn.lower() in ("execute", "then", "else", "condition", "returnvalue", "a", "b", "index", "self", "success")
                or "plot" in pn.lower()
                or "state" in pn.lower()
                or "water" in pn.lower()
                or "plant" in t.lower()
                or "grow" in t.lower()
                or "visual" in t.lower()
                or "yaw" in t.lower()
                or "maprange" in t.lower()
                or "timeofday" in pn.lower()
            )
            if interesting:
                log("  {}.{} [{}] val={!r} -> {}".format(t, pn, pd, v, cps))
    errs = ge.list_nodes_with_errors()
    log("{} errors={}".format(fname, len(errs)))


log("START probe")
dump_graph("GrowCell")
dump_graph("AdvanceDayGrowth")
dump_graph("ApplyDayNightVisuals")
log("END probe")
