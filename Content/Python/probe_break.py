# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
for m in dir(ge):
    if any(k in m.lower() for k in ("break","link","connect","disconnect","wire","remove_pin")):
        if not m.startswith("_"):
            unreal.log("ge." + m)
# also pin methods
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "DrawDebugBox":
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "then":
                for m in dir(p):
                    if any(k in m.lower() for k in ("break","link","connect","split")):
                        if not m.startswith("_"):
                            unreal.log("pin." + m)
                break
        break
