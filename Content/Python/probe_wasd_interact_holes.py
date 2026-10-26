# -*- coding: utf-8 -*-
"""Probe: camera, WASD move graph, IMC, Till/Visualize, grass holes near spawn."""
import unreal

bel = unreal.BlueprintEditorLibrary
CELL = 100.0
PS_CX, PS_CY = 23, 16

def log(m):
    unreal.log("[PROBE] " + str(m))
    print("[PROBE] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def grid_of_loc(loc):
    return int(loc.x // CELL), int(loc.y // CELL)

# --- A) SpringArm + Camera on BP ---
BP = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(BP)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
log("=== CAMERA / SUBOBJECTS ===")
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    name = str(lib.get_variable_name(data))
    if "SpringArm" in cname or name == "CameraBoom" or name == "SpringArm":
        try:
            rot = obj.get_editor_property("relative_rotation")
            arm = obj.get_editor_property("target_arm_length")
            log("SpringArm name={} pitch={:.1f} yaw={:.1f} roll={:.1f} arm={}".format(
                name, rot.pitch, rot.yaw, rot.roll, arm))
        except Exception as e:
            log("SpringArm err " + str(e))
    if "Camera" in cname or name == "TopDownCamera" or name == "Camera":
        try:
            pm = obj.get_editor_property("projection_mode")
            ow = obj.get_editor_property("ortho_width")
            log("Camera name={} proj={} ortho={}".format(name, pm, ow))
        except Exception as e:
            log("Cam err " + str(e))
    if "CharacterMovement" in cname:
        try:
            ort = None
            for p in ("orient_rotation_to_movement", "b_orient_rotation_to_movement"):
                try:
                    ort = obj.get_editor_property(p)
                    break
                except Exception:
                    pass
            log("CharMove OrientRotToMove={}".format(ort))
        except Exception as e:
            log("CharMove " + str(e))

# --- Event Graph: Move / SetMovement / AddMovement / EnhancedInput ---
log("=== CHARACTER EVENT GRAPH (move-related) ===")
try:
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    log("graphs=" + str(graphs[:30]))
except Exception as e:
    log("list graphs " + str(e))

def dump_graph(bp_asset, gname, keywords):
    try:
        g = bel.find_graph(bp_asset, gname)
        if not g:
            log("no graph " + gname)
            return
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        hits = []
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            cn = n.get_class().get_name()
            blob = (t + " " + cn).lower()
            if any(k.lower() in blob for k in keywords):
                pins = []
                for p in bel.list_all_pins(n):
                    val = ""
                    try:
                        val = str(p.get_pin_value())
                    except Exception:
                        pass
                    cps = []
                    try:
                        cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
                    except Exception:
                        pass
                    if val or cps:
                        pins.append("{}={} <-{}".format(p.get_pin_name(), val, cps[:3]))
                hits.append("{} [{}] {}".format(t, cn, pins[:8]))
        for h in hits[:40]:
            log("  " + h)
        log("  hit_count=" + str(len(hits)))
    except Exception as e:
        log("dump " + gname + " " + str(e))

dump_graph(bp, "EventGraph", [
    "Move", "IA_Move", "Add Movement", "Get Forward", "Get Right", "Make Vector",
    "Break Vector2D", "EnhancedInput", "Interact", "IA_Interact", "Till", "Plant",
    "Water", "Grow", "Harvest", "GridManager", "Print", "WorldToGrid"
])

# IMC
log("=== IMC ===")
imc_paths = [
    "/Game/TopDown/Input/IMC_Default",
    "/Game/Input/IMC_Default",
    "/Game/TopDown/Blueprints/IMC_Default",
]
for p in imc_paths:
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        log("found IMC " + p)
        imc = unreal.EditorAssetLibrary.load_asset(p)
        try:
            # EnhancedInputMappingContext
            mappings = imc.get_editor_property("mappings")
            log("mappings n=" + str(len(mappings)))
            for m in mappings:
                try:
                    action = m.get_editor_property("action")
                    key = m.get_editor_property("key")
                    an = action.get_name() if action else None
                    kn = str(key)
                    log("  map action={} key={}".format(an, kn))
                except Exception as e:
                    log("  map err " + str(e))
        except Exception as e:
            log("IMC read " + str(e))
    else:
        log("no " + p)

# Search Input assets
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path("/Game/TopDown/Input", recursive=True)
    log("Input assets n=" + str(len(assets)))
    for a in assets:
        log("  " + str(a.package_name) + " " + str(a.asset_name) + " " + str(a.asset_class_path))
except Exception as e:
    log("AR " + str(e))

# --- GridManager ---
log("=== GRIDMANAGER ===")
mgr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
try:
    funcs = [str(f.name) for f in bel.list_functions(mgr)]
    log("funcs=" + str(funcs))
except Exception as e:
    log(str(e))
try:
    names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(mgr)]
    log("vars=" + str(names))
except Exception as e:
    log(str(e))

for fname in ("TillCell", "VisualizeCell", "WorldToGrid", "GridToWorld"):
    try:
        g = bel.find_graph(mgr, fname)
        ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
        titles = [bel.get_node_title(n) for n in ge.list_all_nodes()]
        log(fname + " nodes=" + str(titles[:25]))
        try:
            errs = ge.list_nodes_with_errors()
            log(fname + " errors=" + str(len(errs)) + " " + str([bel.get_node_title(n) for n in errs]))
        except Exception as e:
            log(fname + " errlist " + str(e))
    except Exception as e:
        log(fname + " " + str(e))

# Level actors
log("=== LEVEL ACTORS ===")
counts = {}
gm_actors = []
ps_info = []
floor_info = []
grass_cells = set()
path_cells = set()
all_vmf_cells = {}
for a in eas().get_all_level_actors():
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    counts[cn] = counts.get(cn, 0) + 1
    if "GridManager" in cn or "GridManager" in lab:
        loc = a.get_actor_location()
        gm_actors.append((lab, cn, (loc.x, loc.y, loc.z)))
        # try read props
        try:
            for prop in ("CellSize", "GridWidth", "GridHeight", "GridOrigin"):
                try:
                    v = a.get_editor_property(prop)
                    log("GM.{}={}".format(prop, v))
                except Exception:
                    try:
                        v = a.get_editor_property(prop[0].lower() + prop[1:])
                        log("GM.{}={}".format(prop, v))
                    except Exception:
                        pass
        except Exception:
            pass
    if "PlayerStart" in cn or lab == "PlayerStart":
        loc = a.get_actor_location()
        gx, gy = grid_of_loc(loc)
        ps_info.append((lab, (loc.x, loc.y, loc.z), (gx, gy)))
    if lab == "FarmCollisionFloor":
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        floor_info.append((loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, a.actor_enable_collision, a.is_hidden_ed() if hasattr(a, "is_hidden_ed") else None))
    if lab.startswith("VMF_"):
        loc = a.get_actor_location()
        gx, gy = grid_of_loc(loc)
        kind = lab.split("_")[1] if "_" in lab else "?"
        all_vmf_cells.setdefault((gx, gy), []).append(lab)
        if "Grass" in lab:
            grass_cells.add((gx, gy))
        if "Path" in lab:
            path_cells.add((gx, gy))

log("class counts (top): " + str(sorted(counts.items(), key=lambda x: -x[1])[:20]))
log("GM actors: " + str(gm_actors))
log("PlayerStart: " + str(ps_info))
log("FarmCollisionFloor: " + str(floor_info))
log("grass cells n={} path n={}".format(len(grass_cells), len(path_cells)))

# Holes near spawn: any cell in farm AABB lacking grass/path/water/bridge/soil tile
ground_kinds = ("Grass", "Path", "Water", "Bridge", "Cliff", "Bank", "Soil", "Hoe", "Yard")
covered = set()
for (gx, gy), labs in all_vmf_cells.items():
    if any(any(k in lab for k in ground_kinds) for lab in labs):
        covered.add((gx, gy))

# Check window around PS and path edge
holes = []
for gy in range(PS_CY - 6, PS_CY + 8):
    for gx in range(PS_CX - 8, PS_CX + 8):
        if 0 <= gx < 40 and 0 <= gy < 40:
            if (gx, gy) not in covered:
                holes.append((gx, gy, all_vmf_cells.get((gx, gy), [])))
log("holes near spawn n={} : {}".format(len(holes), holes[:40]))

# Also full farm hole count for interior
full_holes = []
for gy in range(0, 40):
    for gx in range(0, 40):
        if (gx, gy) not in covered:
            full_holes.append((gx, gy))
log("full farm uncovered n={} sample={}".format(len(full_holes), full_holes[:30]))

# Current level name
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    log("world=" + str(world.get_name()))
except Exception as e:
    log("world " + str(e))

log("=== DONE PROBE ===")
