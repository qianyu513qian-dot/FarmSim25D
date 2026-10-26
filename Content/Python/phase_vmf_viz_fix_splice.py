# -*- coding: utf-8 -*-
"""Verify/fix VisualizeCell splice: dbg.then should only go to VisualizeCell."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[VMF_FIX] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok))
    return ok

bp = unreal.load_asset(MGR)
# Compile errors?
try:
    errs = bel.get_blueprint_compile_status(bp) if hasattr(bel, "get_blueprint_compile_status") else None
    log("compile status="+str(errs))
except Exception as e:
    log("status err "+str(e))

for fname in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    dbg = None
    viz = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "DrawDebugBox":
            dbg = n
        if "VisualizeCell" in t:
            viz = n
    if not dbg:
        log(fname+" no dbg")
        continue
    thenp = find_pin(dbg, "then", "Output")
    cps = list(thenp.list_connected_pins()) if thenp else []
    log(fname+" dbg.then conn="+str([(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps]))
    if viz:
        for p in bel.list_all_pins(viz):
            if "INPUT" in str(p.get_pin_direction()).upper() or "input" in str(p.get_pin_direction()).lower():
                vcps = list(p.list_connected_pins())
                val=""
                try: val=str(p.get_pin_value())
                except: pass
                if vcps or val:
                    log("  viz.{} val=[{}] <- {}".format(p.get_pin_name(), val,
                        [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in vcps]))
        # viz.then
        vt = find_pin(viz, "then", "Output")
        if vt:
            log("  viz.then -> "+str([(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in vt.list_connected_pins()]))

    # Fix: if dbg.then connects to both Return and VisualizeCell, break return link
    if thenp and len(cps) > 1:
        for cp in list(cps):
            own = cp.get_owning_node()
            if bel.get_node_title(own) == "Return Node":
                try:
                    thenp.break_single_pin_link(cp)
                    log(fname+" broke dbg->Return")
                except Exception as e:
                    log(fname+" break_single fail "+str(e))
                    try:
                        thenp.break_pin_links()
                        log(fname+" broke all dbg.then")
                        # re-connect to viz
                        if viz:
                            connect(thenp, find_pin(viz, "execute", "Input"), fname+" re-viz")
                            # ensure viz->ret
                            ret_exec = find_pin(own, "execute", "Input")
                            # find success return
                            connect(find_pin(viz, "then", "Output"), ret_exec, fname+" re-ret")
                    except Exception as e2:
                        log(fname+" break_all fail "+str(e2))
    elif thenp and len(cps) == 1 and bel.get_node_title(cps[0].get_owning_node()) == "Return Node":
        # only return - viz not connected on exec from dbg
        log(fname+" ONLY return — need rewire")
        if viz:
            try:
                thenp.break_pin_links()
            except Exception as e:
                log(str(e))
            connect(thenp, find_pin(viz, "execute", "Input"), fname+" fix-viz")
            connect(find_pin(viz, "then", "Output"), cps[0], fname+" fix-ret")

# Check VisualizeCell compile issues / nodes with errors
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
try:
    errs = vge.list_nodes_with_errors()
    log("VisualizeCell error nodes="+str(len(errs)))
    for n in errs:
        log("  ERR "+bel.get_node_title(n))
except Exception as e:
    log("list errors: "+str(e))
try:
    warns = vge.list_nodes_with_warnings()
    log("VisualizeCell warn nodes="+str(len(warns)))
    for n in warns[:10]:
        log("  WARN "+bel.get_node_title(n))
except Exception as e:
    log("list warns: "+str(e))

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile "+str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("done")
