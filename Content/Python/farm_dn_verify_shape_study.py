"""Check art-study geometry, original palette/collision, and isolate review assets."""
import unreal,math,json
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
REPORT={'studies':[],'temporary_imports_removed':[]}
for suffix,expected in [('Tree_Broadleaf',5994),('FlowerPatch_White',4244)]:
    asset=unreal.load_asset('/Game/Farm/Art/Studies/SM_'+suffix+'_ShapeStudy')
    original=unreal.load_asset('/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix)
    assert asset and unreal.EditorAssetLibrary.get_metadata_tag(asset,'FarmShapeStudy')=='anatomy-v1'
    assert [str(x.material_interface) for x in asset.static_materials]==[str(x.material_interface) for x in original.static_materials]
    assert asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()==original.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()
    mesh=unreal.DynamicMesh()
    unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,mesh,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
    assert mesh.get_triangle_count()==expected
    q=unreal.GeometryScript_MeshQueries
    ids=unreal.GeometryScript_List.convert_index_list_to_array(q.get_all_triangle_i_ds(mesh)[1])
    for tid in ids:
        valid,*p=q.get_triangle_positions(mesh,tid)
        assert valid and all(math.isfinite(v) for a in p for v in (a.x,a.y,a.z))
        a,b,c,valid=q.get_triangle_u_vs(mesh,0,tid)
        assert valid and all(0<=v<=1 for uv in (a,b,c) for v in (uv.x,uv.y))
    REPORT['studies'].append({'name':suffix,'triangles':expected,'palette_material_preserved':True,'collision_preserved':True})
# Imported semantic parts are reproducible from the untouched FBX, and not used by the studies.
for path in unreal.EditorAssetLibrary.list_assets('/Game/Farm/Art/Studies'):
    name=path.split('/')[-1].split('.')[0]
    if name.startswith('SM_VMF_Nature_') or (name.startswith('Flower') and '_SM_VMF_Nature_Flower_White_' in name):
        assert path.startswith('/Game/Farm/Art/Studies/')
        assert unreal.EditorAssetLibrary.delete_asset(path),path
        REPORT['temporary_imports_removed'].append(name)
