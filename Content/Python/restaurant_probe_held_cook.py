# -*- coding: utf-8 -*-
"""Probe stove/manager tick & held/cook related nodes."""
import unreal, json
bel = unreal.BlueprintEditorLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def pins_summary(n):
    out = []
    for p in bel.list_all_pins(n):
        links = []
        for c in (p.list_connected_pins() or []):
            try: links.append(title(c.get_owning_node())[:40])
            except: links.append("?")
        out.append({"name": str(p.get_pin_name()), "dir": str(p.get_pin_direction()), "links": links[:4]})
    return out

R = {"stove": {}, "mgr": {}}
for path, key in [
    ("/Game/Farm/Restaurant/BP_RestaurantStove", "stove"),
    ("/Game/Farm/Restaurant/BP_RestaurantManager", "mgr"),
]:
    bp = unreal.EditorAssetLibrary.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    nodes = []
    tick = None
    customs = []
    for n in ge.list_all_nodes():
        t = title(n); c = n.get_class().get_name()
        if c == "K2Node_Event" and "Tick" in t:
            tick = {"title": t, "pins": pins_summary(n)}
        if c == "K2Node_CustomEvent":
            customs.append(t)
        if any(k in t for k in ("PrintString", "DrawDebug", "CookTimeLeft", "bCooking", "bCookReady", "HeldDish", "ReceiveSalad", "ReceiveStew", "ClearHeld", "RestCook", "RestHeld")):
            nodes.append({"title": t, "class": c})
    R[key] = {
        "status": str(bp.get_editor_property("status")),
        "tick": tick,
        "customs": customs[:80],
        "interesting": nodes[:80],
        "node_count": len(list(ge.list_all_nodes())),
    }

# also dump stove tick chain titles
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
chain = []
for n in ge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_Event" and "Tick" in title(n):
        thenp = None
        for p in bel.list_all_pins(n):
            if "then" in str(p.get_pin_name()).lower() and "OUTPUT" in str(p.get_pin_direction()):
                thenp = p; break
        q = []
        if thenp:
            q = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
        seen=set()
        while q:
            cur = q.pop(0)
            if id(cur) in seen: continue
            seen.add(id(cur))
            chain.append(title(cur))
            for pn in ("then","else","LoopBody","Completed"):
                for p in bel.list_all_pins(cur):
                    if pn.lower() in str(p.get_pin_name()).lower() and "OUTPUT" in str(p.get_pin_direction()):
                        for c in p.list_connected_pins() or []:
                            q.append(c.get_owning_node())
R["stove_tick_chain"] = chain[:40]

open(r"E:\UE\FarmSim25D\Saved\restaurant_probe_held_cook.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:8000])
