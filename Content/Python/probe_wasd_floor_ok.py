# -*- coding: utf-8 -*-
import unreal

def log(m):
    print("[V] " + str(m))
    unreal.log("[V] " + str(m))

BP = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bp = unreal.EditorAssetLibrary.load_asset(BP)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    name = str(lib.get_variable_name(data))
    cname = obj.get_class().get_name()
    if "SpringArm" in cname or name == "SpringArm":
        r = obj.get_editor_property("relative_rotation")
        log("SpringArm p={:.0f} y={:.0f} arm={}".format(r.pitch, r.yaw, obj.get_editor_property("target_arm_length")))
    if cname == "CameraComponent" or name == "Camera":
        log("Camera ortho={}".format(obj.get_editor_property("ortho_width")))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hoe = 0
floor = None
ps = None
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("VMF_Hoe_"):
        hoe += 1
    if lab == "FarmCollisionFloor":
        smc = a.static_mesh_component
        floor = (round(a.get_actor_location().x), round(a.get_actor_location().y),
                 round(a.get_actor_scale3d().x), str(smc.get_collision_enabled()),
                 a.is_hidden_ed() if hasattr(a, "is_hidden_ed") else "?",
                 a.is_actor_hidden_in_game() if hasattr(a, "is_actor_hidden_in_game") else a.b_hidden)
    if lab == "PlayerStart" or a.get_class().get_name() == "PlayerStart":
        loc = a.get_actor_location()
        ps = (round(loc.x), round(loc.y), round(loc.z), int(loc.x // 100), int(loc.y // 100))
log("Hoe leftover={}".format(hoe))
log("Floor={}".format(floor))
log("PS={}".format(ps))
# template floor still parked?
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "") == "Floor":
        loc = a.get_actor_location()
        log("Template Floor at ({:.0f},{:.0f},{:.0f}) hidden_game={}".format(
            loc.x, loc.y, loc.z, a.b_hidden))
log("DONE")
