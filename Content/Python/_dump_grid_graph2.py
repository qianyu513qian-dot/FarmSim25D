# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[GDUMP2] " + str(m))

def dump(path, gname=None):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if gname:
        g = bel.find_graph(bp, gname)
    else:
        g = bel.find_event_graph(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    log("=== %s / %s nodes=%d ===" % (path, gname or "EventGraph", len(list(ge.list_all_nodes()))))
    for n in ge.list_all_nodes():
        title = bel.get_node_title(n)
        cls = n.get_class().get_name()
        pin_bits = []
        for p in bel.list_all_pins(n):
            try:
                dv = str(p.get_default_as_string())
            except Exception:
                dv = ""
            pn = str(p.get_pin_name())
            if dv and dv not in ("", "0", "0.0", "None", "false", "true", "True", "False"):
                pin_bits.append("%s=%s" % (pn, dv[:60]))
            elif "string" in pn.lower() or "format" in pn.lower() or "text" in pn.lower():
                pin_bits.append("%s=%s" % (pn, dv[:60]))
        t = title + " " + cls
        if any(k in t for k in ("Print", "Format", "WorldToGrid", "Grid", "Location", "Tick", "Origin", "Cell", "Divide", "Floor", "Break", "Get Actor", "Player")):
            log("%s | %s | %s" % (cls, title[:120], "; ".join(pin_bits)[:220]))

dump("/Game/Farm/Grid/BP_GridManager", "WorldToGrid")
dump("/Game/Farm/Grid/BP_GridManager", "EventGraph")
dump("/Game/TopDown/Blueprints/BP_TopDownCharacter", None)
log("DONE")