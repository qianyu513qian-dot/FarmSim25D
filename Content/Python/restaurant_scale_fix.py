# -*- coding: utf-8 -*-
"""Scale Restaurant_*/RestChair_* to VMF prop magnitude (档B: 0.01). Ground Z. Save level."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"tier": "B_standard_0.01", "tier_note": "档A=0.02(偏栅栏偏大); 档B=0.01(与VMF_Crate/地砖同级，本轮采用); 参考VMF_Crate_1 scale=0.01 size~67",
          "before": [], "after": [], "refs": {}, "errors": []}

# Target world scales by role (档 B)
# Tables/chairs/sign/trash/stove all VMF meshes authored at ~cm*100; scene uses 0.01
SCALE = {
    "Restaurant_Table1": 0.01,
    "Restaurant_Table2": 0.01,
    "Restaurant_Stove": 0.008,   # crate stack taller/wider — slightly smaller
    "Restaurant_Trash": 0.008,   # compost bin bulky
    "Restaurant_OpenSign": 0.01,
    "Restaurant_Manager": 1.0,   # no visual mesh of note; leave
    "RestChair_t1a": 0.01,
    "RestChair_t1b": 0.01,
    "RestChair_t2a": 0.01,
    "RestChair_t2b": 0.01,
}
GROUND_Z = 2.0  # match nearby props / previous place Z
COMP_REL = 1.0  # neutralize BP PropMesh 1.2 so actor scale alone controls

def snap(a):
    origin, extent = a.get_actor_bounds(False)
    sc = a.get_actor_scale3d()
    return {
        "label": a.get_actor_label(),
        "scale": [round(sc.x, 4), round(sc.y, 4), round(sc.z, 4)],
        "size": [round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1)],
        "bottom_z": round(origin.z - extent.z, 1),
        "loc_z": round(a.get_actor_location().z, 1),
    }

# ref snapshot
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab in ("VMF_Crate_1", "VMF_ShippingChest", "VMF_Scarecrow", "VMF_Well"):
        origin, extent = a.get_actor_bounds(False)
        sc = a.get_actor_scale3d()
        REPORT["refs"][lab] = {
            "scale": [round(sc.x, 4), round(sc.y, 4), round(sc.z, 4)],
            "size": [round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1)],
        }

actors = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        actors.append(a)

for a in actors:
    REPORT["before"].append(snap(a))

for a in actors:
    lab = a.get_actor_label() or ""
    if lab not in SCALE:
        continue
    s = SCALE[lab]
    # Actor world scale
    a.set_actor_scale3d(unreal.Vector(s, s, s))
    # Reset visible mesh component relative scale to 1 (avoid 1.2 compounding)
    if lab != "Restaurant_Manager":
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if not sm:
                continue
            try:
                c.set_editor_property("relative_scale3d", unreal.Vector(COMP_REL, COMP_REL, COMP_REL))
            except Exception as e:
                REPORT["errors"].append("{} relscale {}".format(lab, e))
    # Ground: set Z so bottom sits near GROUND_Z
    # After scale, recompute bounds and nudge Z
    loc = a.get_actor_location()
    if lab == "Restaurant_Manager":
        # keep elevated/hidden
        a.set_actor_location(unreal.Vector(loc.x, loc.y, 80.0), False, False)
        continue
    # First put loc Z = GROUND_Z, then adjust by bottom offset
    a.set_actor_location(unreal.Vector(loc.x, loc.y, GROUND_Z), False, False)
    origin, extent = a.get_actor_bounds(False)
    bottom = origin.z - extent.z
    # want bottom ≈ GROUND_Z (or 0 for grass); use 0 for crates that sit on grass
    target_bottom = 0.0 if lab.startswith("RestChair_") else GROUND_Z
    dz = target_bottom - bottom
    if abs(dz) > 0.5:
        loc2 = a.get_actor_location()
        a.set_actor_location(unreal.Vector(loc2.x, loc2.y, loc2.z + dz), False, False)

for a in actors:
    REPORT["after"].append(snap(a))

# safety: only restaurant touched — recount farm
from collections import Counter
c = Counter()
rest_n = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        rest_n += 1
    if lab.startswith("VMF_Grass"): c["grass"] += 1
    elif "Bridge" in lab: c["bridge"] += 1
    elif "Tree" in lab: c["tree"] += 1
REPORT["farm_check"] = dict(c)
REPORT["restaurant_n"] = rest_n
REPORT["total"] = len(eas.get_all_level_actors())

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["saved"] = True
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        REPORT["saved"] = True
    except Exception as e2:
        REPORT["saved"] = False
        REPORT["errors"].append(str(e2))

open(r"E:\UE\FarmSim25D\Saved\restaurant_scale_fix.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
