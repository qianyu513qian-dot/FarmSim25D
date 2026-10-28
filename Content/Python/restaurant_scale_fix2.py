# -*- coding: utf-8 -*-
"""Fix restaurant scales properly: actor OR root-comp scale=0.01 like VMF props; ground Z."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"tier": "B_0.01_like_VMF_Crate", "before": [], "after": [], "comp_world": [], "errors": []}

# Match VMF_ShippingChest / VMF_Crate_1 world scale 0.01
# Bulky facility meshes slightly smaller
ACTOR_SCALE = {
    "Restaurant_Table1": 0.01,
    "Restaurant_Table2": 0.01,
    "Restaurant_OpenSign": 0.01,
    "Restaurant_Stove": 0.008,
    "Restaurant_Trash": 0.008,
    "Restaurant_Manager": None,  # skip visual
    "RestChair_t1a": 0.01,
    "RestChair_t1b": 0.01,
    "RestChair_t2a": 0.01,
    "RestChair_t2b": 0.01,
}

def snap(a):
    origin, extent = a.get_actor_bounds(False)
    sc = a.get_actor_scale3d()
    return {
        "label": a.get_actor_label(),
        "actor_scale": [round(sc.x, 4), round(sc.y, 4), round(sc.z, 4)],
        "bounds_size": [round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1)],
        "bottom_z": round(origin.z - extent.z, 1),
        "loc": [round(a.get_actor_location().x,1), round(a.get_actor_location().y,1), round(a.get_actor_location().z,1)],
    }

def mesh_world_size(a):
    """World-space AABB of visible static mesh comps (more reliable than actor bounds with empty roots)."""
    out = []
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if not sm:
            continue
        # get local bounds of mesh
        try:
            b = sm.get_bounds()
            ext = b.box_extent  # half-size in mesh space
        except Exception:
            continue
        ws = c.get_world_scale()
        # approx world half = ext * abs(scale) (ignore rotation for report)
        wh = [abs(ext.x * ws.x) * 2, abs(ext.y * ws.y) * 2, abs(ext.z * ws.z) * 2]
        loc = c.get_world_location()
        # bottom approx
        bottom = loc.z - abs(ext.z * ws.z)
        out.append({
            "comp": c.get_name(),
            "mesh": sm.get_name(),
            "world_scale": [round(ws.x, 4), round(ws.y, 4), round(ws.z, 4)],
            "world_size": [round(wh[0], 1), round(wh[1], 1), round(wh[2], 1)],
            "comp_z": round(loc.z, 1),
            "approx_bottom_z": round(bottom, 1),
        })
    return out

actors = [a for a in eas.get_all_level_actors()
          if (a.get_actor_label() or "").startswith(("Restaurant_", "RestChair_"))]

for a in actors:
    REPORT["before"].append({"snap": snap(a), "mesh": mesh_world_size(a)})

for a in actors:
    lab = a.get_actor_label() or ""
    s = ACTOR_SCALE.get(lab)
    if s is None:
        continue

    # For StaticMeshActor: ONLY set_actor_scale3d — root IS the mesh; do not touch relative after
    # For BP: set actor scale; set PropMesh relative to (1,1,1) so actor scale is the only factor
    is_sma = a.get_class().get_name() == "StaticMeshActor"

    if is_sma:
        a.set_actor_scale3d(unreal.Vector(s, s, s))
    else:
        a.set_actor_scale3d(unreal.Vector(s, s, s))
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if not c.get_editor_property("static_mesh"):
                continue
            try:
                c.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
            except Exception as e:
                REPORT["errors"].append(str(e))

    # Ground using MESH world size, not actor bounds (BP roots pollute bounds)
    if lab == "Restaurant_Manager":
        continue
    loc = a.get_actor_location()
    meshes = mesh_world_size(a)
    if not meshes:
        REPORT["errors"].append("no mesh " + lab)
        continue
    # use first visible mesh bottom
    m0 = meshes[0]
    # Want mesh bottom ≈ 0 (grass) or 2
    target_bottom = 0.0
    dz = target_bottom - m0["approx_bottom_z"]
    a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + dz), False, False)

for a in actors:
    REPORT["after"].append({"snap": snap(a), "mesh": mesh_world_size(a)})
    REPORT["comp_world"].append({"label": a.get_actor_label(), "mesh": mesh_world_size(a)})

# farm intact?
from collections import Counter
c = Counter()
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("VMF_Grass"): c["grass"] += 1
    elif "Bridge" in lab: c["bridge"] += 1
    elif "Tree" in lab: c["tree"] += 1
REPORT["farm"] = dict(c)
REPORT["total"] = len(eas.get_all_level_actors())

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["saved"] = True
except Exception:
    unreal.EditorLevelLibrary.save_current_level()
    REPORT["saved"] = True

# Also note alternate tier sizes if user wants A
REPORT["tier_A_preview"] = {
    "note": "档A scale=0.02 → 大约是档B的2倍边长",
    "table_would_be": "~160x120x112",
    "crate_chair_would_be": "~120x96x64",
}

open(r"E:\UE\FarmSim25D\Saved\restaurant_scale_fix2.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
