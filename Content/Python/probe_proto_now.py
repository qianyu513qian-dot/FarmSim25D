# -*- coding: utf-8 -*-
"""Probe Lvl_TopDown actors: list non-VMF/kept, PlayerStart, proto candidates."""
import unreal

def log(m):
    unreal.log("[PROBE_PROTO] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
KEEP_PREFIX = ("VMF_", "Scene_", "Farm_", "BP_")
KEEP_EXACT = {
    "PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
    "ExponentialHeightFog", "VolumetricCloud", "SM_SkySphere", "BP_Sky_Sphere",
    "NavMeshBoundsVolume", "RecastNavMesh-Default", "WorldDataLayers",
    "WorldPartitionMiniMap0", "WorldSettings", "AbstractNavData",
    "DefaultPhysicsVolume", "Landscape", "PostProcessVolume",
}

proto = []
kept = []
other = []
ps_info = None

for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cn = a.get_class().get_name()
    loc = a.get_actor_location()
    hidden_ed = False
    hidden_game = False
    try:
        hidden_ed = a.is_temporarily_hidden_in_editor()
    except Exception:
        try:
            hidden_ed = a.is_hidden_ed()
        except Exception:
            pass
    try:
        hidden_game = a.is_hidden()
    except Exception:
        try:
            hidden_game = a.get_actor_hidden_in_game()
        except Exception:
            pass
    mesh_name = mesh_path = ""
    try:
        smc = a.static_mesh_component
        if smc and smc.static_mesh:
            mesh_name = smc.static_mesh.get_name()
            mesh_path = smc.static_mesh.get_path_name()
    except Exception:
        pass

    if cn == "PlayerStart" or lab == "PlayerStart":
        ps_info = (lab, cn, round(loc.x), round(loc.y), round(loc.z), hidden_ed, hidden_game)
        kept.append(ps_info)
        continue

    is_keep = False
    for p in KEEP_PREFIX:
        if lab.startswith(p):
            is_keep = True
            break
    if lab in KEEP_EXACT or cn in ("PlayerStart", "DirectionalLight", "SkyLight", "SkyAtmosphere",
                                    "ExponentialHeightFog", "VolumetricCloud", "WorldSettings",
                                    "AbstractNavData", "DefaultPhysicsVolume", "NavMeshBoundsVolume"):
        is_keep = True
    if "Sky" in lab or "Sky" in cn:
        is_keep = True

    info = (lab, cn, mesh_name, round(loc.x), round(loc.y), round(loc.z), hidden_ed, hidden_game, mesh_path[:80])
    if is_keep:
        kept.append(info)
        continue

    looks_proto = False
    if lab.startswith(("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_Quarter", "SM_Chamfer")):
        looks_proto = True
    if lab in ("Floor", "Arena", "Wall", "PrototypeFloor") or "Floor" in lab or "Wall" in lab:
        looks_proto = True
    if "LevelPrototyping" in mesh_path or "Prototype" in mesh_path or "Prototype" in lab:
        looks_proto = True
    if mesh_name in ("SM_Cube", "SM_Ramp", "SM_Cylinder", "SM_QuarterCylinder", "SM_Template_Map_Floor", "SM_ChamferCube"):
        looks_proto = True
    if "Template" in lab or "Template" in mesh_name:
        looks_proto = True
    if lab.startswith("FarmBorder") or lab == "FarmGround":
        looks_proto = True

    if looks_proto:
        proto.append(info)
    else:
        other.append(info)

log("=== PLAYERSTART ===")
log(str(ps_info))
log("=== PROTO candidates visible(ed=False) count={} total={} ===".format(
    sum(1 for p in proto if not p[6]), len(proto)))
for p in sorted(proto, key=lambda x: x[0])[:120]:
    log("PROTO lab={} class={} mesh={} xyz=({},{},{}) hidEd={} hidGame={}".format(
        p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]))
log("=== OTHER non-keep count={} ===".format(len(other)))
for p in sorted(other, key=lambda x: x[0])[:80]:
    log("OTHER lab={} class={} mesh={} xyz=({},{},{}) hidEd={} hidGame={} path={}".format(
        p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8]))
log("kept_count={} (VMF/Scene/BP/lights/sky/etc)".format(len(kept)))
vmf_n = sum(1 for k in kept if (k[0] or "").startswith("VMF_"))
log("VMF_count={}".format(vmf_n))
log("=== END ===")
