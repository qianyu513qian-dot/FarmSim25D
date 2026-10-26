# -*- coding: utf-8 -*-
"""Find what prints Grid and how WorldToGrid works."""
import unreal

def log(m):
    unreal.log("[GRIDPROBE] " + str(m))

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
graphs = [str(n) for n in bel.list_graph_names(bp)]
log("graphs=" + str(graphs))

# Dump EventGraph / relevant for WorldToGrid prints
for gname in graphs:
    try:
        g = bel.find_graph(bp, gname)
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    except Exception as e:
        log("graph %s fail %s" % (gname, e))
        continue
    # list nodes
    try:
        nodes = ge.get_nodes_in_graph() if hasattr(ge, "get_nodes_in_graph") else None
    except Exception:
        nodes = None
    # try list via bel
    try:
        # BlueprintEditorLibrary may have get_all_nodes
        if hasattr(bel, "get_graph_nodes"):
            nodes = bel.get_graph_nodes(g)
        elif hasattr(bel, "list_nodes"):
            nodes = bel.list_nodes(g)
    except Exception as e:
        log("list nodes %s" % e)

# Search string tables / print strings via asset search is hard.
# Instead: call WorldToGrid on the placed actor with known locations.
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gm = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "BP_GridManager":
        gm = a
        break

if gm:
    # Try calling WorldToGrid if exposed
    for fname in ("WorldToGrid", "world_to_grid", "WorldLocationToGrid", "ConvertWorldToGrid"):
        try:
            fn = getattr(gm, fname, None)
            log("getattr %s = %s" % (fname, fn))
        except Exception as e:
            log("getattr %s e %s" % (fname, e))

    # Use unreal call method
    test_locs = [
        unreal.Vector(1250, 1050, 100),
        unreal.Vector(1300, 1300, 100),
        unreal.Vector(0, 0, 0),
        unreal.Vector(1400, 1400, 100),
        unreal.Vector(-5000, -5000, 100),
    ]
    for loc in test_locs:
        # Manual formula matching expected
        ox = gm.get_editor_property("GridOrigin").x
        oy = gm.get_editor_property("GridOrigin").y
        cs = gm.get_editor_property("CellSize")
        gx = int((loc.x - ox) // cs)
        gy = int((loc.y - oy) // cs)
        log("manual WorldToGrid (%.0f,%.0f) -> %d,%d (origin=%.0f,%.0f cs=%.0f)" % (
            loc.x, loc.y, gx, gy, ox, oy, cs))

# Search character BP for Print String containing Grid
char_path = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
# Also Farm character if any
for path in (char_path, "/Game/Farm/BP_FarmCharacter", "/Game/TopDown/Blueprints/BP_TopDownPlayerController",
             "/Game/Farm/Grid/BP_GridManager"):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        log("missing " + path)
        continue
    log("exists " + path)

# Look for PrintString nodes by opening character EventGraph - heavy.
# Instead scan Python that set prints
log("DONE")