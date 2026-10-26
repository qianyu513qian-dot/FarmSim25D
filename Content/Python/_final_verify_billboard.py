import unreal
def log(m): unreal.log("[FINAL] "+str(m))
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for lab in ("Scene_House","Scene_Tree_NE","Scene_Path_V","FarmGround"):
  for a in eas.get_all_level_actors():
    if a.get_actor_label()==lab:
      r=a.get_actor_rotation(); loc=a.get_actor_location()
      log("{} rot=({},{},{}) z={}".format(lab,round(r.pitch,1),round(r.yaw,1),round(r.roll,1),round(loc.z,1)))
bp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cls=unreal.EditorAssetLibrary.load_blueprint_class("/Game/TopDown/Blueprints/BP_TopDownCharacter")
actor=eas.spawn_actor_from_class(cls, unreal.Vector(-9300,-9300,200), unreal.Rotator())
for c in actor.get_components_by_class(unreal.SceneComponent):
  if "SpringArm" in c.get_class().get_name():
    rr=c.get_editor_property("relative_rotation")
    log("SpringArm p={} y={} r={}".format(rr.pitch,rr.yaw,rr.roll))
  if c.get_name()=="Camera":
    log("Camera ortho={} proj={}".format(c.get_editor_property("ortho_width"), c.get_editor_property("projection_mode")))
eas.destroy_actor(actor)