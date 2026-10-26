# -*- coding: utf-8 -*-
"""Quick probe: centroids, camera, IMC, VisualizeCell, proto, floor, PlayerStart."""
import unreal
import os

TAG = "[PROBE_RESTORE] "
def log(m):
    s = TAG + str(m); unreal.log(s); print(s)

CELL = 100.0
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
GM = "/Game/Farm/Blueprints/BP_GridManager"
# try alternate paths
GM_CAND = [
    "/Game/Farm/Blueprints/BP_GridManager",
    "/Game/TopDown/Blueprints/BP_GridManager",
    "/Game/Blueprints/BP_GridManager",
]
PV_CAND = [
    "/Game/Farm/Blueprints/BP_PlotVisual",
    "/Game/TopDown/Blueprints/BP_PlotVisual",
]

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary

# Centroids
buckets = {"House": [], "Water": [], "Tree": [], "Path": [], "Soil": [], "Grass": [], "Hoe": []}
proto = []
floor = False
ps = None
vmf = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    loc = a.get_actor_location()
    cn = a.get_class().get_name()
    if lab.startswith("VMF_"):
        vmf += 1
    if lab == "FarmCollisionFloor":
        floor = True
    if cn == "PlayerStart" or lab == "PlayerStart":
        r = a.get_actor_rotation()
        ps = (round(loc.x), round(loc.y), round(loc.z), round(r.pitch,1), round(r.yaw,1))
    # proto check
    mesh_name = mesh_path = ""
    try:
        smc = a.static_mesh_component
        if smc and smc.static_mesh:
            mesh_name = smc.static_mesh.get_name()
            mesh_path = smc.static_mesh.get_path_name()
    except Exception:
        pass
    if ("LevelPrototyping" in mesh_path or mesh_name.startswith(("SM_Cube","SM_Ramp","SM_Cylinder","SM_Quarter","SM_Chamfer","SM_Template"))
        or lab.startswith(("SM_Cube","SM_Ramp")) or lab == "Floor" or "Template_Map_Floor" in mesh_name):
        if lab != "FarmCollisionFloor":
            proto.append(lab)
    for key, needles in (
        ("House", ("House","Home","Cabin","Building","Roof")),
        ("Water", ("Water",)),
        ("Tree", ("Tree","Forest")),
        ("Path", ("Path",)),
        ("Soil", ("Soil","Tilled")),
        ("Grass", ("Grass",)),
        ("Hoe", ("Hoe",)),
    ):
        if lab.startswith("VMF_") and any(n in lab for n in needles):
            buckets[key].append((loc.x, loc.y, loc.z, lab))
            break

def centroid(lst):
    if not lst: return None
    return (round(sum(p[0] for p in lst)/len(lst)),
            round(sum(p[1] for p in lst)/len(lst)),
            len(lst))

for k,v in buckets.items():
    log("{} centroid={} n={}".format(k, centroid(v), len(v)))
log("VMF_total={} proto_leftover={} floor={} PlayerStart={}".format(vmf, len(proto), floor, ps))
if proto:
    log("proto sample="+str(proto[:20]))

# Camera
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj: continue
    name = str(lib.get_variable_name(data))
    cname = obj.get_class().get_name()
    if "SpringArm" in cname or name == "SpringArm":
        r = obj.get_editor_property("relative_rotation")
        arm = obj.get_editor_property("target_arm_length")
        log("SpringArm p={:.1f} y={:.1f} r={:.1f} arm={}".format(r.pitch, r.yaw, r.roll, arm))
    if cname == "CameraComponent" or name == "Camera":
        try:
            ow = obj.get_editor_property("ortho_width")
            log("Camera ortho={}".format(ow))
        except Exception as e:
            log("cam "+str(e))

# Cam-relative move?
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
move_info = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "AddMovementInput": continue
    wd = None
    for p in bel.list_all_pins(n):
        if "WorldDirection" in str(p.get_pin_name()):
            wd = p
    sc = None
    for p in bel.list_all_pins(n):
        if "ScaleValue" in str(p.get_pin_name()):
            sc = p
    wds = [bel.get_node_title(c.get_owning_node()) for c in wd.list_connected_pins()] if wd else []
    scs = [str(c.get_pin_name()) for c in sc.list_connected_pins()] if sc else []
    move_info.append((scs, wds))
log("Move AMI="+str(move_info))

# Enhanced input events present?
ia_titles = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if any(k in t for k in ("IA_Interact","IA_Plant","IA_Water","IA_Grow","IA_Harvest","TillCell","VisualizeCell","PlantCell","WaterCell","GrowCell","HarvestCell")):
        ia_titles.append(t)
log("Char graph hits n={} sample={}".format(len(ia_titles), ia_titles[:40]))

# IMC
imc = unreal.EditorAssetLibrary.load_asset(IMC)
txt = imc.get_editor_property("default_key_mappings").export_text()
log("IMC E={} F={} R={} G={} H={} WASD={}".format(
    "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt,
    all(("Key="+k) in txt for k in "WASD")))
log("IMC IA_Interact={} Plant={} Water={} Grow={} Harvest={}".format(
    "IA_Interact" in txt, "IA_Plant" in txt, "IA_Water" in txt, "IA_Grow" in txt, "IA_Harvest" in txt))

# GridManager VisualizeCell
for p in GM_CAND:
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        log("GM exists "+p)
        gm = unreal.EditorAssetLibrary.load_asset(p)
        try:
            # list functions
            fns = []
            try:
                for f in gm.function_graphs if hasattr(gm, "function_graphs") else []:
                    fns.append(str(f.get_name()))
            except Exception:
                pass
            # try blueprint graphs via bel
            try:
                graphs = []
                # Bel may not list all; use get_all_graphs if available
                for gname in ("TillCell","VisualizeCell","PlantCell","WaterCell","GrowCell","HarvestCell","EventGraph"):
                    g = bel.find_graph(gm, gname)
                    graphs.append((gname, g is not None))
                log("GM graphs="+str(graphs))
            except Exception as e:
                log("GM graph list "+str(e))
            # Search EventGraph / TillCell for VisualizeCell call
            for gname in ("TillCell","EventGraph","PlantCell","WaterCell"):
                g = bel.find_graph(gm, gname)
                if not g: continue
                gge = unreal.BlueprintGraphEditor.get_graph_editor(g)
                hits = []
                for n in gge.list_all_nodes():
                    t = bel.get_node_title(n)
                    if "Visualize" in t or "Till" in t or "Plot" in t or "Soil" in t:
                        hits.append(t)
                log("GM.{} hits={}".format(gname, hits[:30]))
        except Exception as e:
            log("GM err "+str(e))
        break
else:
    log("GM not found in candidates; searching...")
    try:
        assets = unreal.EditorAssetLibrary.list_assets("/Game", True, False)
        for a in assets:
            if "GridManager" in a or "PlotVisual" in a:
                log("found asset "+a)
    except Exception as e:
        log("search "+str(e))

for p in PV_CAND:
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        log("PlotVisual exists "+p)

# mtimes
paths = [
    r"E:\UE\FarmSim25D\Content\TopDown\Lvl_TopDown.umap",
    r"E:\UE\FarmSim25D\Content\TopDown\Blueprints\BP_TopDownCharacter.uasset",
    r"E:\UE\FarmSim25D\Content\TopDown\Input\IMC_Default.uasset",
]
for p in paths:
    if os.path.exists(p):
        log("mtime {} = {}".format(p, os.path.getmtime(p)))
    else:
        log("missing file "+p)

log("DONE probe")
