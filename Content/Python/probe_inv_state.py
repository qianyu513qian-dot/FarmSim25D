# -*- coding: utf-8 -*-
"""Probe character vars + plant/harvest EventGraph nodes for inventory wiring."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[INV_PROBE] " + str(m))
    print("[INV_PROBE] " + str(m))

def dump_pins(node, label):
    for p in bel.list_all_pins(node):
        log("  [{}] {} | {} | links={}".format(
            label, p.get_pin_name(), p.get_pin_direction(),
            len(p.get_linked_to()) if hasattr(p, "get_linked_to") else "?"))

bp = unreal.load_asset(CHAR)
log("CHAR loaded=" + str(bool(bp)))
try:
    vars_ = bel.list_member_variable_names(bp) if hasattr(bel, "list_member_variable_names") else []
    log("vars=" + str([str(v) for v in vars_]))
except Exception as e:
    log("vars err " + str(e))
    # fallback
    try:
        for v in bp.get_editor_property("new_variables"):
            log("var " + str(v.var_name) + " type=" + str(v.var_type))
    except Exception as e2:
        log("vars2 " + str(e2))

funcs = []
try:
    for f in bel.list_functions(bp):
        funcs.append(str(f.name) if hasattr(f, "name") else str(f))
except Exception:
    pass
log("funcs=" + str(funcs))
log("graphs=" + str([str(g) for g in bel.list_graph_names(bp)]))

# EventGraph dump titles containing Plant/Harvest/Till/Print/IA_
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
hits = []
for n in ge.list_all_nodes():
    title = ""
    try:
        title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
    except Exception:
        title = n.get_class().get_name()
    cn = n.get_class().get_name()
    keys = ("Plant", "Harvest", "Till", "IA_", "Print", "Seed", "Money", "Crop", "WorldToGrid", "Visualize")
    if any(k.lower() in title.lower() or k.lower() in cn.lower() for k in keys):
        hits.append((title, cn, n))
log("hit_count=" + str(len(hits)))
for title, cn, n in hits:
    log("--- " + title + " | " + cn)
    dump_pins(n, title[:40])

# GridManager funcs
gm = unreal.load_asset(MGR)
log("GM graphs=" + str([str(g) for g in bel.list_graph_names(gm)]))
log("GM funcs=" + str([str(f.name) if hasattr(f,"name") else str(f) for f in bel.list_functions(gm)]))

# UMG create capability
log("has WidgetBlueprintFactory=" + str(hasattr(unreal, "WidgetBlueprintFactory")))
log("has create_asset=" + str(hasattr(unreal.AssetToolsHelpers.get_asset_tools(), "create_asset")))
