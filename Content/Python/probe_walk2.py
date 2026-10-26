# -*- coding: utf-8 -*-
"""Walk ALL exec outs from Plant/Harvest IA nodes."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[W] " + str(m))
    print("[W] " + str(m))

def linked(p):
    try:
        return list(p.get_linked_to() or [])
    except Exception:
        return []

def node_label(n):
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        try:
            pv = p.get_pin_value()
        except Exception:
            pv = ""
        if pn == "InString" and pv:
            return "Print({!r})".format(pv)
        if pn == "InputAction" and pv:
            return "IA(" + pv.split("/")[-1].split(".")[0] + ")"
    pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
    cn = n.get_class().get_name()
    if "GridX" in pins and "WorldLocation" in pins and "execute" in pins:
        return "WorldToGrid"
    if "GridX" in pins and "Success" in pins:
        return "CellOp(*Success*)"
    if "GridManagerRef" in pins:
        return "Get.GridManagerRef"
    if cn == "K2Node_IfThenElse":
        return "Branch"
    if set(pins) >= {"self", "ReturnValue"} and "execute" not in pins and len(pins) <= 3:
        return "PureGet(ActorLoc?)"
    if "Visualize" in str(n):
        return "Visualize?"
    return cn + str(pins[:6])

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

for i, n in enumerate(nodes):
    if n.get_class().get_name() != "K2Node_EnhancedInputAction":
        continue
    ia = ""
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "InputAction":
            try:
                ia = p.get_pin_value() or ""
            except Exception:
                pass
    short = ia.split("/")[-1].split(".")[0] if ia else "?"
    if short not in ("IA_Plant", "IA_Harvest", "IA_Interact"):
        continue
    log("==== node[{}] {}".format(i, short))
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        links = linked(p)
        if links:
            log("  OUT {} -> {}".format(pn, [node_label(lp.get_owning_node()) for lp in links]))

# Also reverse: find who feeds Print Planted/Harvested
for i, n in enumerate(nodes):
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) != "InString":
            continue
        try:
            pv = p.get_pin_value() or ""
        except Exception:
            continue
        if pv.strip() not in ("Planted!", "Harvested!", "Cannot plant", "Cannot harvest", "Tilled!"):
            continue
        log("PRINT[{}] {!r}".format(i, pv))
        # find execute pin inbound
        for ep in bel.list_all_pins(n):
            if str(ep.get_pin_name()) != "execute":
                continue
            for lp in linked(ep):
                own = lp.get_owning_node()
                log("  fed by pin={} node={}".format(lp.get_pin_name(), node_label(own)))
                # if branch, note which
                if own.get_class().get_name() == "K2Node_IfThenElse":
                    for bp_pin in bel.list_all_pins(own):
                        bpn = str(bp_pin.get_pin_name())
                        for lp2 in linked(bp_pin):
                            if lp2.get_owning_node() == n:
                                log("  via Branch.{}".format(bpn))

# BeginPlay chain
for i, n in enumerate(nodes):
    if n.get_class().get_name() != "K2Node_Event":
        continue
    has_delta = any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n))
    if has_delta:
        continue
    log("BEGINPLAY node[{}]".format(i))
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) != "then":
            continue
        queue = [(lp.get_owning_node(), 0) for lp in linked(p)]
        seen = set()
        while queue:
            cur, d = queue.pop(0)
            if id(cur) in seen or d > 8:
                continue
            seen.add(id(cur))
            log("  " + ("  "*d) + node_label(cur))
            for cp in bel.list_all_pins(cur):
                if str(cp.get_pin_name()) in ("then",):
                    for lp in linked(cp):
                        queue.append((lp.get_owning_node(), d+1))
