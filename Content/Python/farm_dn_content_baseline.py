"""Record unchanged scene content and validate the baseline palette connections."""
import unreal,re,json
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before inspecting saved editor actors.'
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
data=[]
for a in eas.get_all_level_actors():
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    if not c: continue
    if not a.get_actor_label().startswith(('VMF_','Farm_Lantern','FarmArt_')): continue
    p=a.get_actor_location(); r=a.get_actor_rotation(); s=a.get_actor_scale3d()
    data.append({'label':a.get_actor_label(),'mesh':c.static_mesh.get_path_name(),'location':[p.x,p.y,p.z],'rotation':[r.pitch,r.yaw,r.roll],'scale':[s.x,s.y,s.z],'materials':[c.get_material(i).get_path_name() for i in range(c.get_num_materials())],'collision':str(c.get_collision_enabled())})
data.sort(key=lambda x:x['label'])
assert data
assert not any(x['label'].startswith('FarmArt_') for x in data)
out=Path(unreal.Paths.project_saved_dir())/'ArtReview'
path=out/'restored_1cf2610_scene.json'
if path.exists():
    previous=json.loads(path.read_text())
    assert previous==data,'Scene content changed during the surface-only pass'
    mode='matched'
else:
    path.write_text(json.dumps(data,indent=2)); mode='recorded'
counts={prefix:len([x for x in data if x['label'].startswith(prefix)]) for prefix in ['VMF_Tree_','VMF_Flower_','VMF_Path','VMF_Fence','VMF_Grass_']}
REPORT={'scene_content':mode,'static_mesh_actors':len(data),'counts':counts,'new_art_actors':0}
