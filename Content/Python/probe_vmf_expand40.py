# -*- coding: utf-8 -*-
import unreal

def log(m):
    unreal.log("[VMF40] " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
gm = None
ps = None
vmf = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab == "BP_GridManager":
        gm = a
    if lab == "PlayerStart" or "PlayerStart" in a.get_class().get_name():
        ps = a
    if lab.startswith("VMF_"):
        vmf += 1

if gm:
    log("Grid W={} H={} Cell={} Origin={}".format(
        gm.get_editor_property("GridWidth"),
        gm.get_editor_property("GridHeight"),
        gm.get_editor_property("CellSize"),
        gm.get_editor_property("GridOrigin"),
    ))
else:
    log("NO GridManager")

if ps:
    loc = ps.get_actor_location()
    log("PlayerStart @ ({:.0f},{:.0f},{:.0f})".format(loc.x, loc.y, loc.z))
else:
    log("NO PlayerStart")

log("VMF_*=%d" % vmf)

bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cn = obj.get_class().get_name()
    if "SpringArm" in cn:
        try:
            log("SpringArm len={}".format(obj.get_editor_property("target_arm_length")))
        except Exception as e:
            log("arm read " + str(e))
    if cn == "CameraComponent" or name == "Camera":
        try:
            log("Camera ortho={} proj={}".format(
                obj.get_editor_property("ortho_width"),
                obj.get_editor_property("projection_mode")))
        except Exception as e:
            log("cam read " + str(e))

fg = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "FarmGround":
        fg = a
        break
if fg:
    loc = fg.get_actor_location()
    log("FarmGround loc=({:.0f},{:.0f},{:.0f}) hidden_game={}".format(
        loc.x, loc.y, loc.z, fg.is_hidden_ed() if hasattr(fg, "is_hidden_ed") else "?"))
else:
    log("FarmGround absent")
