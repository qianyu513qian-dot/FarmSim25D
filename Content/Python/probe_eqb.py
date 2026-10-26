# -*- coding: utf-8 -*-
"""Dump WaterCell/PlantCell Equal.B only."""
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
for fname in ("WaterCell", "PlantCell", "GrowCell", "HarvestCell"):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    for n in ge.list_all_nodes():
        t = str(bel.get_node_title(n))
        cls = n.get_class().get_name()
        if "Equal" in t.lower() or "Equal" in cls.lower() or "Promotable" in cls:
            for p in bel.list_all_pins(n):
                try: v = p.get_pin_value()
                except: v = "?"
                cps = [(str(bel.get_node_title(c.get_owning_node())), str(c.get_pin_name())) for c in p.list_connected_pins()]
                unreal.log("[EQB] {} | {} | {}.{}={!r} conn={}".format(fname, cls, t, p.get_pin_name(), v, cps))
                print("[EQB] {} | {} | {}.{}={!r} conn={}".format(fname, cls, t, p.get_pin_name(), v, cps))
