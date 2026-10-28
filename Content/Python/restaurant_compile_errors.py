# -*- coding: utf-8 -*-
import unreal, json, traceback

bel = unreal.BlueprintEditorLibrary
paths = [
    "/Game/Farm/Restaurant/BP_RestaurantTable",
    "/Game/Farm/Restaurant/BP_RestaurantManager",
]
REPORT = {"assets": {}}

def pin_info(p):
    return {
        "name": str(p.get_pin_name()),
        "dir": str(p.get_pin_direction()),
        "type": str(p.get_pin_type_display_string()),
        "val": p.get_pin_value(),
        "linked": [bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()) for c in p.list_connected_pins()],
    }

def dump_bp(path):
    out = {"path": path, "compile": None, "status": None, "compiler_msgs": [], "nodes": [], "errors_guess": []}
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        out["error"] = "load failed"
        return out
    # compile and capture
    try:
        # clear log? just compile
        bel.compile_blueprint(bp)
        out["compile"] = "called"
    except Exception as e:
        out["compile_ex"] = str(e)
    # status
    try:
        st = bel.get_blueprint_compile_status(bp) if hasattr(bel, "get_blueprint_compile_status") else None
        out["status"] = str(st)
    except Exception as e:
        out["status_err"] = str(e)
    try:
        out["generated_class"] = str(bp.generated_class()) if hasattr(bp, "generated_class") else None
    except Exception as e:
        out["gc_err"] = str(e)
    # BlueprintEditorLibrary get status via property
    for attr in ("status", "blueprint_status", "compile_status"):
        if hasattr(bp, attr):
            try:
                out[attr] = str(getattr(bp, attr))
            except Exception:
                pass
    try:
        out["status_prop"] = str(bp.get_editor_property("status"))
    except Exception as e:
        out["status_prop_err"] = str(e)[:120]

    # walk graphs
    try:
        graphs = list(bel.get_all_graphs(bp)) if hasattr(bel, "get_all_graphs") else []
    except Exception:
        graphs = []
    if not graphs:
        # fallback find known
        for gname in ("EventGraph", "RestaurantInteract", "TrySeat", "ClearSeat"):
            g = bel.find_graph(bp, gname)
            if g:
                graphs.append(g)
        eg = bel.find_event_graph(bp)
        if eg and eg not in graphs:
            graphs.append(eg)

    out["graph_names"] = []
    for g in graphs:
        try:
            gname = g.get_name() if hasattr(g, "get_name") else str(g)
        except Exception:
            gname = str(g)
        out["graph_names"].append(gname)
        try:
            ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        except Exception as e:
            out["errors_guess"].append("no ge for " + gname + ": " + str(e)[:80])
            continue
        for n in ge.list_all_nodes():
            title = bel.get_node_title(n)
            cls = n.get_class().get_name()
            pins = []
            issues = []
            for p in bel.list_all_pins(n):
                info = pin_info(p)
                pins.append(info)
                # orphan exec inputs that look required?
            # check error state on node
            err = None
            for meth in ("get_error_msg", "get_node_error", "error_msg"):
                if hasattr(n, meth):
                    try:
                        err = getattr(n, meth)() if callable(getattr(n, meth)) else getattr(n, meth)
                    except Exception:
                        pass
            for prop in ("error_type", "bHasCompilerMessage", "error_msg"):
                if hasattr(n, "get_editor_property"):
                    try:
                        v = n.get_editor_property(prop)
                        if v:
                            issues.append(prop + "=" + str(v)[:200])
                    except Exception:
                        pass
            node_rec = {"graph": gname, "title": title, "cls": cls, "err": str(err) if err else None, "issues": issues}
            # flag disconnected self on call functions
            if cls in ("K2Node_CallFunction", "K2Node_MacroInstance"):
                selfp = None
                ex = None
                for p in bel.list_all_pins(n):
                    if str(p.get_pin_name()).lower() == "self":
                        selfp = p
                    if str(p.get_pin_name()).lower() == "execute":
                        ex = p
                if selfp is not None:
                    linked = selfp.list_connected_pins()
                    # self can be implicit
                    node_rec["self_linked"] = len(linked)
                    node_rec["self_type"] = str(selfp.get_pin_type_display_string())
                if ex is not None:
                    node_rec["exec_in"] = len(ex.list_connected_pins())
            # Variable set/get type issues - include all pins summary short
            bad_pins = []
            for p in bel.list_all_pins(n):
                # unconnected non-exec inputs that might be required - hard to know
                pass
            node_rec["pins"] = pins
            out["nodes"].append(node_rec)

    return out

# Also try MessageLog
def read_message_log():
    msgs = []
    try:
        # unreal.EditorUtilityLibrary?
        pass
    except Exception:
        pass
    # Kismet compiler results via AssetEditor
    try:
        import re
        log_path = r"E:\UE\FarmSim25D\Saved\Logs\FarmSim25D.log"
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-8000:]
        # find recent Blueprint compile errors for our assets
        interesting = []
        for i, line in enumerate(lines):
            if "BP_RestaurantTable" in line or "BP_RestaurantManager" in line or "RestaurantTable" in line or "RestaurantManager" in line:
                if any(k in line for k in ("Error", "Warning", "Compile", "Failed", "pin", "Pin", "Cannot", "could not", "incompatible")):
                    interesting.append(line.strip()[:400])
        # also grab blocks after "Compile of"
        for i, line in enumerate(lines):
            if "Compile of" in line and ("Restaurant" in line):
                block = [line.strip()[:300]]
                for j in range(1, 30):
                    if i + j < len(lines):
                        block.append(lines[i + j].strip()[:300])
                interesting.append("BLOCK:" + " | ".join(block[:15]))
        msgs = interesting[-80:]
    except Exception as e:
        msgs = ["log_err " + str(e)]
    return msgs

for p in paths:
    try:
        REPORT["assets"][p] = dump_bp(p)
    except Exception as e:
        REPORT["assets"][p] = {"fatal": str(e), "tb": traceback.format_exc()[:1000]}

REPORT["log_msgs"] = read_message_log()

# compact node dump: only nodes with issues or Call/Set/Get/Branch that look broken
compact = {}
for p, data in REPORT["assets"].items():
    nodes = data.get("nodes", [])
    keep = []
    for n in nodes:
        title = n.get("title", "")
        # keep customs and anything with empty exec when it needs it, or self issues
        flag = False
        reasons = []
        if n.get("issues"):
            flag = True
            reasons += n["issues"]
        if n.get("err"):
            flag = True
            reasons.append(str(n["err"]))
        # Call with exec_in 0 and is not pure - might be orphan OK
        # Variable set with data pin type mismatch - check linked types later
        # Print InString linked vs default
        if "TrySeat" in title or "ClearSeat" in title or "HandlePlayerE" in title or "RestaurantTick" in title or "SeatGuest" in title or "ClearGuests" in title:
            flag = True
        if n.get("cls") == "K2Node_CallFunction" and n.get("self_linked") == 0:
            # check if self is "Self Object Reference" OK unbound
            st = n.get("self_type", "")
            if "Self" not in st and st and "wildcard" not in st.lower():
                # Actor ref unbound may be error if required from other class
                if "Restaurant" in st or "Table" in st or "FarmClock" in st or "Manager" in st:
                    flag = True
                    reasons.append("unbound typed self: " + st)
        if flag:
            keep.append({
                "graph": n.get("graph"),
                "title": title,
                "cls": n.get("cls"),
                "reasons": reasons,
                "self_linked": n.get("self_linked"),
                "self_type": n.get("self_type"),
                "exec_in": n.get("exec_in"),
                "pins": [{k: pin[k] for k in ("name", "dir", "type", "val", "linked")} for pin in n.get("pins", [])],
            })
    compact[p] = {
        "status_prop": data.get("status_prop"),
        "status": data.get("status"),
        "compile_ex": data.get("compile_ex"),
        "graph_names": data.get("graph_names"),
        "flagged": keep,
        "node_count": len(nodes),
    }

REPORT["compact"] = compact
open(r"E:\UE\FarmSim25D\Saved\restaurant_compile_errors.json", "w", encoding="utf-8").write(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str))
print(json.dumps({"log_n": len(REPORT["log_msgs"]), "log": REPORT["log_msgs"][-40:], "compact_keys": {k: {"status": v.get("status_prop"), "flagged": len(v.get("flagged", [])), "graphs": v.get("graph_names"), "n": v.get("node_count")} for k, v in compact.items()}}, indent=2, ensure_ascii=False)[:12000])