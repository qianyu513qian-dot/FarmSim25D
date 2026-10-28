# -*- coding: utf-8 -*-
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ML = unreal.MathLibrary
# probe useful names
names = [n for n in dir(ML) if any(k in n.lower() for k in ("cross", "normal", "make_rot", "dot"))]
REPORT = {"probe": names[:80], "labels": {}, "errors": []}
TOWARD = unreal.Vector(-0.542, 0.542, 0.643)

# Prefer CrossProduct / Normal / MakeRotFromZX naming variants
def call_first(cands, *args):
    for n in cands:
        fn = getattr(ML, n, None)
        if fn:
            try:
                return fn(*args), n
            except Exception as e:
                REPORT.setdefault("tries", []).append(n + ":" + str(e)[:80])
    return None, None

z, zn = call_first(["normal", "Normal", "vector_normal", "NormalSafe", "normal_safe"], TOWARD)
if z is None:
    # manual normalize
    s = (TOWARD.x**2 + TOWARD.y**2 + TOWARD.z**2) ** 0.5
    z = unreal.Vector(TOWARD.x/s, TOWARD.y/s, TOWARD.z/s); zn = "manual"
cross, cn = call_first(
    ["cross_product_vector_vector", "CrossProduct", "cross_product", "Cross_VectorVector", "vector_cross"],
    unreal.Vector(0,0,1), z)
if cross is None:
    # manual cross world_up x z
    ux,uy,uz = 0.0,0.0,1.0
    cross = unreal.Vector(uy*z.z - uz*z.y, uz*z.x - ux*z.z, ux*z.y - uy*z.x); cn = "manual"
# normalize x
sx = (cross.x**2 + cross.y**2 + cross.z**2) ** 0.5
x = unreal.Vector(cross.x/sx, cross.y/sx, cross.z/sx) if sx > 1e-6 else unreal.Vector(1,0,0)
face, fn = call_first(["make_rot_from_zx", "MakeRotFromZX", "make_rotation_from_axes"], z, x)
if face is None:
    face, fn = call_first(["make_rot_from_z", "MakeRotFromZ"], z)
REPORT["method"] = {"z": zn, "cross": cn, "face": fn,
    "rot": [round(face.pitch,1), round(face.yaw,1), round(face.roll,1)] if face else None}

for key in ["OpenSign","Stove","Table1","Table2","Trash"]:
    name = "RestName_" + key
    actor = None
    for a in eas.get_all_level_actors():
        if (a.get_actor_label() or "") == name:
            actor = a; break
    if not actor:
        REPORT["errors"].append("missing "+name); continue
    if face:
        actor.set_actor_rotation(face, True)
    actor.set_actor_scale3d(unreal.Vector(2.6, 0.65, 1.0))
    up = actor.get_actor_up_vector()
    right = actor.get_actor_right_vector()
    REPORT["labels"][name] = {
        "rot": [round(actor.get_actor_rotation().pitch,1), round(actor.get_actor_rotation().yaw,1), round(actor.get_actor_rotation().roll,1)],
        "up": [round(up.x,3), round(up.y,3), round(up.z,3)],
        "right_z": round(right.z,3),
        "dot": round(up.x*TOWARD.x+up.y*TOWARD.y+up.z*TOWARD.z,3),
    }

ok=False
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level(); ok=True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level(); ok=True
    except Exception as e:
        REPORT["errors"].append(str(e))
REPORT["level_saved"]=ok
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception:
    pass
open(r"E:\\UE\\FarmSim25D\\Saved\\restaurant_texorient.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps({k:REPORT[k] for k in ("method","labels","errors","level_saved","tries") if k in REPORT}, ensure_ascii=False, indent=2))
