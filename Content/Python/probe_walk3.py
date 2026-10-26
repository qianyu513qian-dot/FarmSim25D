# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[W3] " + str(m))
    print("[W3] " + str(m))

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def label(n):
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        try:
            pv = p.get_pin_value() or ""
        except Exception:
            pv = ""
        if pn == "InString" and pv:
            return "Print({!r})".format(pv)
        if pn == "InputAction" and pv:
            return "IA(" + pv.split("/")[-1].split(".")[0] + ")"
    pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
    cn = n.get_class().get_name()
    if "GridX" in pins and "WorldLocation" in pins:
        return "WorldToGrid"
    if "GridX" in pins and "Success" in pins:
        return "CellOp"
    if "GridManagerRef" in pins:
        return "Get.GridManagerRef"
    if cn == "K2Node_IfThenElse":
        return "Branch"
    if "ReturnValue" in pins and "execute" not in pins and len(pins) <= 3:
        return "PureGet"
    return cn

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
    if short not in ("IA_Plant", "IA_Harvest"):
        continue
    log("==== {} node[{}]".format(short, i))
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        cs = conn(p)
        if cs:
            log("  {} -> {}".format(pn, [label(c.get_owning_node()) for c in cs]))
    # BFS from Started/Triggered
    start_pins = []
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) in ("Started", "Triggered"):
            start_pins.extend(conn(p))
    queue = [(c.get_owning_node(), 0, str(c.get_pin_name())) for c in start_pins]
    seen = set()
    while queue:
        cur, d, via = queue.pop(0)
        if id(cur) in seen or d > 15:
            continue
        seen.add(id(cur))
        log("  {ind}[{via}] {lab}".format(ind="  "*d, via=via, lab=label(cur)))
        for cp in bel.list_all_pins(cur):
            cpn = str(cp.get_pin_name())
            if cpn in ("then", "else"):
                for c in conn(cp):
                    queue.append((c.get_owning_node(), d+1, cpn))

# BeginPlay
for i, n in enumerate(nodes):
    if n.get_class().get_name() != "K2Node_Event":
        continue
    if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
        continue
    log("BEGINPLAY[{}]".format(i))
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) != "then":
            continue
        queue = [(c.get_owning_node(), 0) for c in conn(p)]
        seen = set()
        while queue:
            cur, d = queue.pop(0)
            if id(cur) in seen or d > 10:
                continue
            seen.add(id(cur))
            log("  " + ("  "*d) + label(cur))
            for cp in bel.list_all_pins(cur):
                if str(cp.get_pin_name()) == "then":
                    for c in conn(cp):
                        queue.append((c.get_owning_node(), d+1))

# Who feeds Planted! / Harvested!
for want in ("Planted!", "Harvested!"):
    for n in nodes:
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "InString":
                try:
                    if p.get_pin_value() == want:
                        log("FEEDERS of " + want)
                        for ep in bel.list_all_pins(n):
                            if str(ep.get_pin_name()) == "execute":
                                for c in conn(ep):
                                    log("  <- {} from {}".format(c.get_pin_name(), label(c.get_owning_node())))
                        for tp in bel.list_all_pins(n):
                            if str(tp.get_pin_name()) == "then":
                                for c in conn(tp):
                                    log("  -> then {}".format(label(c.get_owning_node())))
                except Exception:
                    pass
