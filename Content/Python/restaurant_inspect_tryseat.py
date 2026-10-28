# -*- coding: utf-8 -*-
"""Inspect TrySeat graph structure in detail and repair if Branch then is dangling."""
import unreal, json
bel = unreal.BlueprintEditorLibrary

TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

tryseat = find_custom(tge, "TrySeat")
# BFS with pin names
thenp = find_pin(tryseat, "then", "Output")
queue = [(c.get_owning_node(), "TrySeat.then", 0) for c in (thenp.list_connected_pins() if thenp else [])]
seen = set(); edges = []
while queue:
    cur, via, d = queue.pop(0)
    if id(cur) in seen or d > 35: continue
    seen.add(id(cur))
    edges.append("{} --{}--> {} [{}]".format(via, d, title(cur), cur.get_class().get_name()))
    for pn in ("then", "else", "Completed", "LoopBody"):
        tp = find_pin(cur, pn, "Output")
        if not tp: continue
        targets = list(tp.list_connected_pins() or [])
        if not targets:
            edges.append("  {} .{} -> EMPTY".format(title(cur), pn))
        for c in targets:
            queue.append((c.get_owning_node(), title(cur)+"."+pn, d+1))

# Also find Set bOccupied and who feeds it
for n in tge.list_all_nodes():
    if title(n) == "Set bOccupied":
        exe = find_pin(n, "execute", "Input")
        preds = []
        if exe:
            for c in exe.list_connected_pins() or []:
                preds.append(title(c.get_owning_node()) + "." + str(c.get_pin_name()))
        print("Set bOccupied preds:", preds)
        thenp = find_pin(n, "then", "Output")
        nxt = []
        if thenp:
            for c in thenp.list_connected_pins() or []:
                nxt.append(title(c.get_owning_node()))
        print("Set bOccupied then:", nxt)

for n in tge.list_all_nodes():
    if "SpawnGuestVisual" in title(n):
        exe = find_pin(n, "execute", "Input")
        preds = []
        if exe:
            for c in exe.list_connected_pins() or []:
                preds.append(title(c.get_owning_node()) + "." + str(c.get_pin_name()))
        print("Spawn node", n.get_class().get_name(), "preds:", preds)

print("=== EDGES ===")
for e in edges:
    print(e)

out = unreal.Paths.project_saved_dir() + "TrySeat_inspect.txt"
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(edges))
print("wrote", out)
