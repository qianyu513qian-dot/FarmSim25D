"""Swap exactly two meshes in PIE for art review; never save level changes."""
import unreal,json
from pathlib import Path
world=unreal.EditorLevelLibrary.get_game_world(); assert world
request=json.loads((Path(unreal.Paths.project_saved_dir())/'VisualReview/request.json').read_text())
study=request.get('shape_study',True)
mapping={'VMF_Tree_Edge5':'Tree_Broadleaf','VMF_Flower_4':'FlowerPatch_White'}
REPORT={'preview_only':True,'study':study,'actors':[]}
for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor):
    label=actor.get_actor_label()
    if label not in mapping: continue
    suffix=mapping[label]
    path='/Game/Farm/Art/Studies/SM_'+suffix+'_ShapeStudy' if study else '/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    mesh=unreal.load_asset(path)
    component.set_static_mesh(mesh)
    assert component.static_mesh==mesh
    REPORT['actors'].append(label)
assert len(REPORT['actors'])==2
unreal.GameplayStatics.get_player_pawn(world,0).set_actor_hidden_in_game(True)
