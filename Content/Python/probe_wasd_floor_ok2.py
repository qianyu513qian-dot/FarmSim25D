import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
hoe=0
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Hoe_"): hoe+=1
    if lab=="FarmCollisionFloor":
        smc=a.static_mesh_component
        print("[OK] Floor loc={} scale={} coll={}".format(a.get_actor_location(), a.get_actor_scale3d(), smc.get_collision_enabled()))
    if lab=="PlayerStart" or a.get_class().get_name()=="PlayerStart":
        loc=a.get_actor_location()
        print("[OK] PS={} grid={},{}".format(loc, int(loc.x//100), int(loc.y//100)))
print("[OK] Hoe leftover", hoe)
