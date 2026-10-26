# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
def log(m): unreal.log("[GRID] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if "GridManager" in a.get_actor_label() or a.get_class().get_name().startswith("BP_GridManager"):
        log("actor " + a.get_actor_label())
        for p in ("cell_size","CellSize","grid_width","GridWidth","grid_height","GridHeight","grid_origin","GridOrigin","plot_states","PlotStates"):
            try:
                log("  inst {}={}".format(p, a.get_editor_property(p)))
            except Exception as e:
                pass
        # try all editor props with grid/cell/plot
        try:
            for pname in dir(a):
                if any(k in pname.lower() for k in ("grid","cell","plot","origin")) and not pname.startswith("_"):
                    try:
                        log("  attr {}={}".format(pname, getattr(a, pname)))
                    except Exception:
                        pass
        except Exception:
            pass

# Dump GridToWorld graph values / WorldToGrid
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
for gname in ("GridToWorld","WorldToGrid","IsValidCell"):
    g = bel.find_graph(bp, gname)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    log("=== "+gname+" ===")
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        for p in bel.list_all_pins(n):
            val=""
            try: val=str(p.get_pin_value())
            except: pass
            cps=list(p.list_connected_pins())
            if val or cps:
                log("  {}.{} val=[{}] conn={}".format(t, p.get_pin_name(), val, 
                    [bel.get_node_title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in cps[:3]]))

# EventGraph BeginPlay init of PlotStates size?
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
log("=== EventGraph titles ===")
titles=[]
for n in ge.list_all_nodes():
    try: titles.append(bel.get_node_title(n))
    except: titles.append(n.get_class().get_name())
log(str(titles))
