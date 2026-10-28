# -*- coding: utf-8 -*-
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
la = None
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "") == "RestLabel_OpenSign":
        la = a
        break
tr = la.get_component_by_class(unreal.TextRenderComponent)

def rr(r):
    return [round(r.pitch,2), round(r.yaw,2), round(r.roll,2)]
def vv(v):
    return [round(v.x,3), round(v.y,3), round(v.z,3)]

out = {"start_actor": rr(la.get_actor_rotation()), "start_world": rr(tr.get_world_rotation()), "start_fwd": vv(tr.get_forward_vector()),
       "abs_rot": bool(tr.absolute_rotation) if hasattr(tr,"absolute_rotation") else None,
       "rel": rr(tr.relative_rotation), "always_text": bool(tr.always_render_as_text) if hasattr(tr,"always_render_as_text") else None}

# reset relative
tr.reset_relative_transform()
out["after_reset_rel"] = rr(tr.relative_rotation)
out["after_reset_actor"] = rr(la.get_actor_rotation())

# try set actor only
desired = unreal.Rotator(50.0, 135.0, 0.0)
la.set_actor_rotation(desired, True)  # teleport
out["set_P50_Y135"] = {"actor": rr(la.get_actor_rotation()), "world": rr(tr.get_world_rotation()), "fwd": vv(tr.get_forward_vector()), "rel": rr(tr.relative_rotation)}

# try set_world_rotation on component
tr.set_world_rotation(desired, False, True)
out["set_world_P50_Y135"] = {"actor": rr(la.get_actor_rotation()), "world": rr(tr.get_world_rotation()), "fwd": vv(tr.get_forward_vector()), "rel": rr(tr.relative_rotation)}

# try quat from rotator
q = desired.quaternion()
la.set_actor_rotation(q.rotator(), True)
out["via_quat"] = {"actor": rr(la.get_actor_rotation()), "fwd": vv(tr.get_forward_vector())}

# try find look-at rotation toward camera-ish point (NW up from label)
loc = la.get_actor_location()
cam_approx = unreal.Vector(loc.x - 800.0, loc.y + 800.0, loc.z + 900.0)
# make rotator that looks from label to cam_approx - but TextRender faces +X = look direction
look = unreal.MathLibrary.find_look_at_rotation(loc, cam_approx)
la.set_actor_rotation(look, True)
out["look_at_cam"] = {"look_rot": rr(look), "actor": rr(la.get_actor_rotation()), "fwd": vv(tr.get_forward_vector()),
                      "desired_dir": vv((cam_approx - loc).normal())}

# also try Pitch=0 Yaw=135 (vertical text facing NW)
la.set_actor_rotation(unreal.Rotator(0.0, 135.0, 0.0), True)
out["P0_Y135"] = {"actor": rr(la.get_actor_rotation()), "fwd": vv(tr.get_forward_vector())}

# Pitch=-40 to match camera (parallel to view plane? no)
# For text plane facing camera: text +X toward camera
la.set_actor_rotation(unreal.Rotator(40.0, 135.0, 0.0), True)
out["P40_Y135"] = {"actor": rr(la.get_actor_rotation()), "fwd": vv(tr.get_forward_vector())}

print(json.dumps(out, indent=2))
