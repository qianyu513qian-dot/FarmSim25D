import unreal
w=unreal.EditorLevelLibrary.get_game_world()
p=unreal.GameplayStatics.get_player_pawn(w,0)
c=p.get_component_by_class(unreal.CameraComponent)
a=p.get_component_by_class(unreal.SpringArmComponent)
pc=unreal.GameplayStatics.get_player_controller(w,0)
REPORT={'pawn':str(p.get_actor_location()),'camera':str(c.get_world_location()),'rotation':str(c.get_world_rotation()),'manager_location':str(pc.player_camera_manager.get_camera_location()),'manager_rotation':str(pc.player_camera_manager.get_camera_rotation()),'manager_fov':pc.player_camera_manager.get_fov_angle(),'fov':c.field_of_view,'projection':str(c.projection_mode),'arm':a.target_arm_length,'arm_rotation':str(a.get_world_rotation())}
