# -*- coding: utf-8 -*-
"""Deep probe: MakeVector move dirs, Interact chain, IMC, holes, PlotVisual."""
import unreal

bel = unreal.BlueprintEditorLibrary
CELL = 100.0
PS_CX, PS_CY = 23, 16

def log(m):
    unreal.log("[PROBE2] " + str(m))
    print("[PROBE2] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

log("=== MOVE MakeVector details ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    cn = n.get_class().get_name()
    if t == "Make Vector" or "MakeVector" in cn or t == "MakeVector":
        # see what consumes ReturnValue
        rp = find_pin(n, "ReturnValue", "Output") or find_pin(n, "Return", "Output")
        consumers = []
        if rp:
            for c in rp.list_connected_pins():
                consumers.append(bel.get_node_title(c.get_owning_node()) + "." + str(c.get_pin_name()))
        vals = {}
        for p in bel.list_all_pins(n):
            try:
                vals[str(p.get_pin_name())] = str(p.get_pin_value())
            except Exception:
                pass
        log("MakeVector vals={} consumers={}".format(vals, consumers))

log("=== IA_Move / AddMovementInput full ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Move" in t or t == "AddMovementInput":
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), val, cps))

log("=== IA_Interact full chain ===")
interact = None
for n in ge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        interact = n
        break
if interact:
    for p in bel.list_all_pins(interact):
        cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name()), c.get_owning_node()) for c in p.list_connected_pins()]
        log("Interact.{} -> {}".format(p.get_pin_name(), [(a,b) for a,b,_ in cps]))
        # BFS from Started
        if "Started" in str(p.get_pin_name()) or "Triggered" in str(p.get_pin_name()):
            queue = [c[2] for c in cps]
            seen = set()
            depth = 0
            while queue and depth < 15:
                depth += 1
                nxt = []
                for node in queue:
                    nid = str(node.get_path_name())
                    if nid in seen:
                        continue
                    seen.add(nid)
                    tt = bel.get_node_title(node)
                    log("  chain[{}] {}".format(depth, tt))
                    thenp = find_pin(node, "then", "Output")
                    if thenp:
                        for c in thenp.list_connected_pins():
                            nxt.append(c.get_owning_node())
                    # also True/False for Branch
                    for pname in ("True", "False", "then"):
                        pp = find_pin(node, pname, "Output")
                        if pp and pp is not thenp:
                            for c in pp.list_connected_pins():
                                nxt.append(c.get_owning_node())
                queue = nxt

log("=== All EnhancedInput actions in EventGraph ===")
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "EnhancedInput" in n.get_class().get_name() or t.startswith("EnhancedInput"):
        ia = ""
        for p in bel.list_all_pins(n):
            if "InputAction" in str(p.get_pin_name()):
                try:
                    ia = str(p.get_pin_value())
                except Exception:
                    pass
        outs = []
        for p in bel.list_all_pins(n):
            cps = list(p.list_connected_pins())
            if cps and ("OUTPUT" in str(p.get_pin_direction()).upper() or "output" in str(p.get_pin_direction()).lower()):
                outs.append("{}->{}".format(p.get_pin_name(), [bel.get_node_title(c.get_owning_node()) for c in cps]))
        log("EIA title={} ia={} outs={}".format(t, ia, outs))

# IMC
log("=== IMC mappings ===")
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
if imc:
    mappings = imc.get_editor_property("mappings")
    log("n={}".format(len(mappings)))
    for m in mappings:
        try:
            action = m.get_editor_property("action")
            key = m.get_editor_property("key")
            an = action.get_path_name() if action else None
            # key may be Key struct
            kn = ""
            try:
                kn = str(key.get_editor_property("key_name")) if hasattr(key, "get_editor_property") else str(key)
            except Exception:
                kn = str(key)
            log("  {} <= {}".format(an, kn))
        except Exception as e:
            # try export
            try:
                log("  map raw=" + str(m.export_text() if hasattr(m, "export_text") else m))
            except Exception as e2:
                log("  map err " + str(e) + " / " + str(e2))
else:
    log("NO IMC")

# List action assets
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in ar.get_assets_by_path("/Game/TopDown/Input", recursive=True):
    log("asset {} class={}".format(a.package_name, a.asset_class_path.asset_name if hasattr(a.asset_class_path, "asset_name") else a.asset_class_path))

# PlotVisual ApplyState soft paths
log("=== PlotVisual ===")
pv = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_PlotVisual")
if pv:
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(pv):
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object_for_blueprint(data, pv)
        if not obj:
            continue
        if "StaticMesh" in obj.get_class().get_name():
            try:
                sm = obj.get_editor_property("static_mesh")
                rel = obj.get_editor_property("relative_location")
                sc = obj.get_editor_property("relative_scale3d")
                vis = obj.get_editor_property("visible")
                log("SMC {} mesh={} rel=({:.1f},{:.1f},{:.1f}) scale=({:.3f},{:.3f},{:.3f}) vis={}".format(
                    name, sm.get_name() if sm else None, rel.x, rel.y, rel.z, sc.x, sc.y, sc.z, vis))
            except Exception as e:
                log("SMC {} {}".format(name, e))
    age = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
    try:
        log("ApplyState errs={} warns={}".format(len(age.list_nodes_with_errors()), len(age.list_nodes_with_warnings())))
        for n in age.list_nodes_with_errors():
            log("  ERR " + bel.get_node_title(n))
    except Exception as e:
        log(str(e))

# VisualizeCell spawn class
log("=== VisualizeCell spawn ===")
mgr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mgr, "VisualizeCell"))
for n in vge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Spawn" in t or "Make Transform" in t or t == "MakeTransform" or "ApplyState" in t or "Cast" in t:
        for p in bel.list_all_pins(n):
            val = ""
            try:
                val = str(p.get_pin_value())
            except Exception:
                pass
            cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            if val or cps:
                log("  {}.{} =[{}] <-{}".format(t, p.get_pin_name(), val[:80] if val else "", cps[:4]))

# Level: GM, PS, floor, holes
log("=== LEVEL ===")
covered = set()
grass = set()
path = set()
all_cells = {}
floor_ok = False
ps = None
gm_ok = False
for a in eas().get_all_level_actors():
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    loc = a.get_actor_location()
    gx, gy = int(loc.x // CELL), int(loc.y // CELL)
    if "GridManager" in cn or "GridManager" in lab:
        gm_ok = True
        log("GM actor {} at ({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))
    if "PlayerStart" in cn or lab == "PlayerStart":
        ps = (lab, loc.x, loc.y, loc.z, gx, gy)
        log("PS {} world=({:.0f},{:.0f},{:.0f}) grid=({},{})".format(lab, loc.x, loc.y, loc.z, gx, gy))
    if lab == "FarmCollisionFloor":
        sc = a.get_actor_scale3d()
        col = True
        try:
            col = a.get_actor_enable_collision()
        except Exception:
            pass
        log("FLOOR loc=({:.0f},{:.0f},{:.0f}) scale=({:.0f},{:.0f},{:.0f}) col={}".format(
            loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, col))
        floor_ok = True
    if lab.startswith("VMF_"):
        all_cells.setdefault((gx, gy), []).append(lab)
        kinds = ("Grass", "Path", "Water", "Bridge", "Cliff", "Bank", "Soil", "Hoe", "Yard")
        if any(k in lab for k in kinds):
            covered.add((gx, gy))
        if "Grass" in lab:
            grass.add((gx, gy))
        if "Path" in lab:
            path.add((gx, gy))

log("floor_ok={} gm_ok={} grass={} path={} covered={}".format(floor_ok, gm_ok, len(grass), len(path), len(covered)))
holes_near = []
for gy in range(10, 30):
    for gx in range(10, 35):
        if (gx, gy) not in covered:
            holes_near.append((gx, gy, all_cells.get((gx, gy), [])))
log("holes in [10-34,10-29] n={}".format(len(holes_near)))
for h in holes_near[:50]:
    log("  hole {}".format(h))

# Also check if there's a big rectangle of holes (the screenshot one)
# Path is around cols 21-22; spawn ~23,16; hole left of player
log("cells around PS:")
for gy in range(PS_CY - 3, PS_CY + 5):
    row = []
    for gx in range(PS_CX - 6, PS_CX + 4):
        labs = all_cells.get((gx, gy), [])
        tag = "?"
        for lab in labs:
            for k in ("Grass", "Path", "Water", "Bridge", "Soil", "Hoe", "Crop", "Tomato", "Fence"):
                if k in lab:
                    tag = k[0]
                    break
        if not labs:
            tag = "."
        row.append("{}{}{}".format(gx, tag, gy) if False else tag)
    log("  y={} {}".format(gy, "".join(row)))

log("=== DONE ===")
