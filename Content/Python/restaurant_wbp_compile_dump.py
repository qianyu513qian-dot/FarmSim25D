# -*- coding: utf-8 -*-
"""Dump compile status/errors for restaurant WBPs and related BPs."""
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

PATHS = [
    "/Game/Farm/UI/WBP_RestOrderList",
    "/Game/Farm/UI/WBP_RestOrderBubble",
    "/Game/Farm/Restaurant/BP_RestaurantManager",
    "/Game/Farm/Restaurant/BP_RestaurantTable",
    "/Game/Farm/Restaurant/BP_RestGuest",
]

R = {"assets": {}}

def log(m):
    unreal.log("[WBPFIX] " + str(m))
    print("[WBPFIX] " + str(m))

def status_of(bp):
    try:
        return str(bp.get_editor_property("status"))
    except Exception as e:
        return "status_err:" + str(e)[:120]

def dump_asset(path):
    out = {"path": path, "exists": eas.does_asset_exist(path)}
    if not out["exists"]:
        return out
    bp = eas.load_asset(path)
    out["type"] = bp.get_class().get_name() if bp else None
    out["status_before"] = status_of(bp) if bp else None
    # compile
    try:
        bel.compile_blueprint(bp)
        out["compile"] = "ok_call"
    except Exception as e:
        out["compile"] = "ex:" + str(e)[:300]
    out["status_after"] = status_of(bp)
    # generated class
    try:
        out["generated_class"] = str(bp.generated_class())
    except Exception as e:
        out["generated_class_err"] = str(e)[:200]
    # node errors via graphs
    err_nodes = []
    graphs = []
    try:
        if hasattr(bel, "get_all_graphs"):
            graphs = list(bel.get_all_graphs(bp) or [])
    except Exception as e:
        out["graphs_err"] = str(e)[:120]
    if not graphs:
        for gname in ("EventGraph", "WidgetGraph", "Designer", "ConstructionScript"):
            try:
                g = bel.find_graph(bp, gname)
                if g:
                    graphs.append(g)
            except Exception:
                pass
        try:
            eg = bel.find_event_graph(bp)
            if eg:
                graphs.append(eg)
        except Exception:
            pass
    out["graph_names"] = []
    for g in graphs:
        try:
            gname = g.get_name()
        except Exception:
            gname = str(g)
        out["graph_names"].append(gname)
        try:
            ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        except Exception as e:
            out.setdefault("ge_err", []).append(gname + ":" + str(e)[:80])
            continue
        try:
            for n in (ge.list_nodes_with_errors() or []):
                title = str(bel.get_node_title(n))
                cls = n.get_class().get_name()
                issues = []
                for prop in ("error_type", "bHasCompilerMessage", "error_msg", "ErrorMsg", "ErrorType"):
                    try:
                        v = n.get_editor_property(prop)
                        if v:
                            issues.append(prop + "=" + str(v)[:300])
                    except Exception:
                        pass
                pins = []
                for p in bel.list_all_pins(n):
                    pins.append({
                        "name": str(p.get_pin_name()),
                        "dir": str(p.get_pin_direction()),
                        "type": str(p.get_pin_type_display_string()),
                        "linked": len(p.list_connected_pins() or []),
                    })
                err_nodes.append({"graph": gname, "title": title, "cls": cls, "issues": issues, "pins": pins})
        except Exception as e:
            out.setdefault("list_err", []).append(gname + ":" + str(e)[:120])
        # also scan all nodes for error props
        try:
            for n in ge.list_all_nodes():
                for prop in ("error_msg", "ErrorMsg"):
                    try:
                        v = n.get_editor_property(prop)
                        if v and str(v).strip():
                            err_nodes.append({
                                "graph": gname,
                                "title": str(bel.get_node_title(n)),
                                "cls": n.get_class().get_name(),
                                "msg": str(v)[:400],
                            })
                    except Exception:
                        pass
        except Exception:
            pass
    out["err_nodes"] = err_nodes

    # WidgetTree info for WBPs
    if "WidgetBlueprint" in (out["type"] or ""):
        try:
            tree = unreal.load_object(bp, "WidgetTree")
            out["widget_tree"] = str(tree)
            # try root
            for prop in ("RootWidget", "root_widget"):
                try:
                    rw = tree.get_editor_property(prop)
                    out["root_widget"] = str(rw)
                    out["root_name"] = rw.get_name() if rw else None
                except Exception as e:
                    out.setdefault("root_err", []).append(prop + ":" + str(e)[:80])
            # list named widgets via dir / get_all_widgets?
            widgets = []
            try:
                # WidgetTree has get_all_widgets in some versions
                if hasattr(tree, "get_all_widgets"):
                    for w in tree.get_all_widgets() or []:
                        widgets.append(w.get_name() + ":" + w.get_class().get_name())
                else:
                    # fall back: iterate outer objects? 
                    pass
            except Exception as e:
                out["widgets_err"] = str(e)[:120]
            out["widgets"] = widgets
        except Exception as e:
            out["tree_err"] = str(e)[:200]

        # Parent class
        try:
            out["parent_class"] = str(bp.get_editor_property("parent_class"))
        except Exception as e:
            try:
                out["parent_class"] = str(bp.parent_class)
            except Exception as e2:
                out["parent_class_err"] = str(e)[:80] + "/" + str(e2)[:80]

    return out

for p in PATHS:
    log("dump " + p)
    try:
        R["assets"][p] = dump_asset(p)
    except Exception as e:
        R["assets"][p] = {"path": p, "fatal": str(e), "tb": traceback.format_exc()[-500:]}
        log("fatal " + str(e))

# Also scrape recent log lines for WBP_RestOrderList
log_path = unreal.Paths.project_saved_dir() + "Logs/FarmSim25D.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-12000:]
    hits = []
    for i, line in enumerate(lines):
        if "WBP_RestOrder" in line or "RestOrderList" in line or "RestOrderBubble" in line:
            # take nearby context
            ctx = "".join(lines[max(0, i-1):min(len(lines), i+3)]).strip()
            if ctx not in hits:
                hits.append(ctx[:500])
    R["log_hits"] = hits[-40:]
    log("log_hits=" + str(len(hits)))
except Exception as e:
    R["log_err"] = str(e)

outp = unreal.Paths.project_saved_dir() + "WBP_RestOrder_compile_dump.json"
with open(outp, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("WROTE " + outp)
