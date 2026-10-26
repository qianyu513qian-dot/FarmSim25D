# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "print" in t.lower():
        for p in bel.list_all_pins(n):
            if "string" in str(p.get_pin_name()).lower() and "INPUT" in str(p.get_pin_direction()):
                try:
                    cur = p.get_pin_value()
                except Exception:
                    cur = ""
                unreal.log("title={!r} pin={!r} val={!r}".format(t, p.get_pin_name(), cur))
                # Ensure plant messages
                ein = None
                for pp in bel.list_all_pins(n):
                    if str(pp.get_pin_name()) == "execute":
                        ein = pp
                src = ""
                if ein and list(ein.list_connected_pins()):
                    src = str(list(ein.list_connected_pins())[0].get_pin_name())
                # Walk back: if branch then/else from plant chain - heuristic by position y
                pos = bel.get_node_pos(n)
                unreal.log("  pos={} src_pin={}".format(pos, src))
