"""Prepare offscreen SceneCapture; never reads or manipulates the desktop."""
import unreal
import math
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=list(eas.get_all_level_actors())
clock=next(a for a in actors if isinstance(a,unreal.FarmClock))
clock.apply_lighting(12)
capture=next((a for a in actors if a.get_actor_label()=='Farm_QA_Capture'),None)
if not capture:
    capture=eas.spawn_actor_from_class(unreal.SceneCapture2D,unreal.Vector(0,0,0)); capture.set_actor_label('Farm_QA_Capture')
rotation=unreal.Rotator(pitch=-40,yaw=135,roll=0)
forward=unreal.MathLibrary.get_forward_vector(rotation)
capture.set_actor_location(unreal.Vector(2000,2000,0)-forward*6500,False,False)
capture.set_actor_rotation(rotation,False)
c=capture.get_component_by_class(unreal.SceneCaptureComponent2D)
c.set_editor_property('projection_type',unreal.CameraProjectionMode.ORTHOGRAPHIC)
c.set_editor_property('ortho_width',6200.0)
c.set_editor_property('capture_source',unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
c.set_editor_property('capture_every_frame',True)
c.set_editor_property('always_persist_rendering_state',True)
rt=unreal.RenderingLibrary.create_render_target2d(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),1440,1000,unreal.TextureRenderTargetFormat.RTF_RGBA8)
c.set_editor_property('texture_target',rt)
REPORT={'capture':capture.get_path_name(),'target':rt.get_path_name(),'methods':[x for x in dir(unreal.RenderingLibrary) if 'export' in x or 'pixel' in x]}
