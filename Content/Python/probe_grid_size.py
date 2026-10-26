import unreal
gm = None
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "BP_GridManager":
        gm = a
        break
if not gm:
    unreal.log("[PROBE] NO GridManager")
else:
    for name in ["GridWidth","GridHeight","CellSize","Origin","GridOrigin","Width","Height"]:
        try:
            v = gm.get_editor_property(name)
            unreal.log("[PROBE] {} = {}".format(name, v))
        except Exception as e:
            unreal.log("[PROBE] {} FAIL {}".format(name, e))
    # list all editor properties that look like grid
    try:
        for p in gm.get_editor_property("grid_width"), :
            pass
    except Exception:
        pass
fg = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "FarmGround":
        fg = a
        break
if fg:
    unreal.log("[PROBE] FarmGround loc={} scale={} rot={}".format(
        fg.get_actor_location(), fg.get_actor_scale3d(), fg.get_actor_rotation()))
ps = None
for a in eas.get_all_level_actors():
    if a.get_actor_label() == "PlayerStart":
        ps = a
        break
if ps:
    unreal.log("[PROBE] PlayerStart loc={}".format(ps.get_actor_location()))
# M_Grass tiling
mat = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Art/Mats/M_Grass")
if mat:
    unreal.log("[PROBE] M_Grass loaded")
