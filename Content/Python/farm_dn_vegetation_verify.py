"""Verify saved anatomy assets and complete in-level vegetation coverage."""
import unreal,json,math,hashlib
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
expected=json.loads((Path(unreal.Paths.project_saved_dir())/'ArtReview/full_anatomy_manifest.json').read_text())['assets']
assert len(expected)==9
REPORT={'assets':[],'instances':{},'unprocessed':[]}
paths={row['asset']:row['name'] for row in expected}
for row in expected:
    asset=unreal.load_asset(row['asset'])
    assert unreal.EditorAssetLibrary.get_metadata_tag(asset,'FarmVegetationRevision')=='anatomy-v2'
    assert [s.material_interface.get_path_name() for s in asset.static_materials]==row['materials']
    collision=asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()
    assert hashlib.sha256(collision.encode()).hexdigest()==row['collision_hash']
    mesh=unreal.DynamicMesh()
    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,mesh,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
    assert result==unreal.GeometryScriptOutcomePins.SUCCESS
    assert mesh.get_triangle_count()==row['triangles']
    q=unreal.GeometryScript_MeshQueries
    ids=unreal.GeometryScript_List.convert_index_list_to_array(q.get_all_triangle_i_ds(mesh)[1])
    for tid in ids:
        valid,*positions=q.get_triangle_positions(mesh,tid)
        assert valid and all(math.isfinite(v) for p in positions for v in (p.x,p.y,p.z))
        a,b,c,valid=q.get_triangle_u_vs(mesh,0,tid)
        assert valid and all(0<=v<=1 for uv in (a,b,c) for v in (uv.x,uv.y))
    REPORT['assets'].append({'name':row['name'],'triangles':mesh.get_triangle_count(),'saved_revision':'anatomy-v2','palette_and_collision_preserved':True})
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    component=actor.get_component_by_class(unreal.StaticMeshComponent)
    if not component or not component.static_mesh: continue
    path=component.static_mesh.get_path_name()
    if path in paths:
        name=paths[path]; REPORT['instances'][name]=REPORT['instances'].get(name,0)+1
    elif any(x in path for x in ['Nature_Tree_','Nature_Flower','Nature_Shrub','Nature_Bush']):
        REPORT['unprocessed'].append({'actor':actor.get_actor_label(),'mesh':path})
assert not REPORT['unprocessed'],REPORT['unprocessed']
assert sum(REPORT['instances'].values())==123,REPORT['instances']
assert len(REPORT['instances'])==9,REPORT['instances']
