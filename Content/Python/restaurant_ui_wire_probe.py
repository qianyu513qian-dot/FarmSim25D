# -*- coding: utf-8 -*-
"""Probe graph editor spawn APIs and Manager BeginPlay/Tick splice points."""
import unreal

def log(m):
    unreal.log("[WIREP] " + str(m))
    print("[WIREP] " + str(m))

bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
log("ge add methods=" + str([x for x in dir(ge) if x.startswith("add_")][:80]))

# Test spawn node paths
for path in (
    "/Script/Engine.GameplayStatics:SpawnActorFromClass",
    "/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass",
    "/Script/Engine.Actor:K2_DestroyActor",
    "/Script/UMG.WidgetBlueprintLibrary:Create",
    "/Script/UMG.UserWidget:AddToViewport",
    "/Script/UMG.UserWidget:GetWidgetFromName",
    "/Script/UMG.TextBlock:SetText",
    "/Script/UMG.ProgressBar:SetPercent",
    "/Script/Engine.Actor:SetActorHiddenInGame",
    "/Script/UMG.WidgetComponent:SetHiddenInGame",
    "/Script/Engine.SceneComponent:SetHiddenInGame",
    "/Script/Engine.PrimitiveComponent:SetMaterial",
    "/Script/Engine.KismetSystemLibrary:DrawDebugBox",
    "/Script/Engine.KismetSystemLibrary:DrawDebugString",
):
    n = ge.add_call_function_node(path)
    log("add {} -> {}".format(path.split(":")[-1], n.get_class().get_name() if n else None))
    if n:
        # remove immediately to avoid polluting
        try:
            for p in bel.list_all_pins(n):
                p.break_pin_links()
        except Exception:
            pass
        try:
            ge.remove_node(n)
        except Exception:
            try:
                bel.remove_node(n)
            except Exception as e:
                log("  cannot remove " + str(e))

# Find end of TrySeat chain on Table
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))

def title(n):
    return str(bel.get_node_title(n))

def find_pin(node, substr, direction=None):
    for p in bel.list_all_pins(node):
        if substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

for evname in ("TrySeat", "ClearSeat", "TimeoutLeave", "PayAndClear", "WrongLeave"):
    ev = None
    for n in tge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==evname:
            ev = n; break
    if not ev:
        log(evname + " MISSING"); continue
    thenp = find_pin(ev, "then", "Output")
    # walk to find terminal PrintString nodes (no then out connected)
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=set(); terminals=[]
    while queue:
        cur,d = queue.pop(0)
        if id(cur) in seen or d>25: continue
        seen.add(id(cur))
        then = find_pin(cur, "then", "Output")
        elsep = find_pin(cur, "else", "Output")
        outs = []
        if then: outs += list(then.list_connected_pins() or [])
        if elsep: outs += list(elsep.list_connected_pins() or [])
        if not outs and cur.get_class().get_name() in ("K2Node_CallFunction", "K2Node_VariableSet"):
            terminals.append(title(cur))
        for c in outs:
            queue.append((c.get_owning_node(), d+1))
    log(evname + " terminals=" + str(terminals[:8]) + " nodes_seen=" + str(len(seen)))

log("DONE_WIREP")
