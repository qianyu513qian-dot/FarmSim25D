# -*- coding: utf-8 -*-
"""Dump WorldToGrid + character EventGraph PrintString for Grid."""
import unreal

def log(m):
    unreal.log("[GDUMP] " + str(m))

bel = unreal.BlueprintEditorLibrary

def dump_graph(bp_path, gname):
    bp = unreal.load_asset(bp_path)
    g = bel.find_graph(bp, gname)
    if not g:
        log("no graph %s in %s" % (gname, bp_path))
        return
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    # Discover node listing API
    nodes = []
    for attr in ("get_nodes_in_graph", "get_selected_nodes", "list_nodes"):
        if hasattr(ge, attr):
            log("ge has " + attr)
    if hasattr(bel, "get_graph_nodes"):
        nodes = list(bel.get_graph_nodes(g))
        log("bel.get_graph_nodes count=%d" % len(nodes))
    elif hasattr(bel, "list_all_nodes"):
        nodes = list(bel.list_all_nodes(g))
        log("bel.list_all_nodes count=%d" % len(nodes))
    else:
        # try select all / iterate via ed graph
        try:
            ug = g  # UEdGraph
            # unreal may expose nodes property
            if hasattr(ug, "nodes"):
                nodes = list(ug.nodes)
                log("ug.nodes count=%d" % len(nodes))
            elif hasattr(ug, "get_editor_property"):
                try:
                    nodes = list(ug.get_editor_property("nodes"))
                    log("prop nodes count=%d" % len(nodes))
                except Exception as e:
                    log("prop nodes e " + str(e))
        except Exception as e:
            log("ug e " + str(e))

    for n in nodes:
        try:
            cls = n.get_class().get_name()
        except Exception:
            cls = "?"
        title = ""
        try:
            title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except Exception:
            try:
                title = str(n.get_node_title(0))
            except Exception:
                title = n.get_name() if hasattr(n, "get_name") else str(n)
        pins_info = []
        try:
            for p in bel.list_all_pins(n):
                pn = str(p.get_pin_name())
                try:
                    dv = str(p.get_default_as_string())
                except Exception:
                    dv = ""
                if dv and dv not in ("", "0", "0.0", "None", "false", "True", "true"):
                    pins_info.append("%s=%s" % (pn, dv[:80]))
                elif pn.lower() in ("in string", "instring", "string", "format", "in text"):
                    pins_info.append("%s=%s" % (pn, dv[:80]))
        except Exception:
            pass
        # Always log Print / Format / WorldToGrid related
        interesting = any(k in (cls + " " + title) for k in (
            "Print", "Format", "WorldToGrid", "GridToWorld", "GetPlayer", "GetActorLocation",
            "Branch", "Variable", "Grid", "Origin", "Cell", "Floor", "Truncate", "Divide"))
        if interesting or "Print" in cls or "Format" in title:
            log("NODE %s | %s | %s" % (cls, title[:100], "; ".join(pins_info)[:200]))

dump_graph("/Game/Farm/Grid/BP_GridManager", "WorldToGrid")
dump_graph("/Game/Farm/Grid/BP_GridManager", "EventGraph")
dump_graph("/Game/TopDown/Blueprints/BP_TopDownCharacter", "EventGraph")
log("DONE")