"""Build a reviewable vegetation shape study without changing saved level actors."""
import unreal,json,math
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
REPORT={'assets':[]}
for suffix in ['Tree_Broadleaf','FlowerPatch_White']:
    source_path='/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix
    original=unreal.load_asset(source_path)
    target='/Game/Farm/Art/Studies/SM_'+suffix+'_ShapeStudy'
    prefix='/Game/Farm/Art/Studies/SM_VMF_Nature_'+suffix+'_'
    parts=[p for p in unreal.EditorAssetLibrary.list_assets('/Game/Farm/Art/Studies') if p.startswith(prefix)]
    if suffix=='FlowerPatch_White':
        parts += [p for p in unreal.EditorAssetLibrary.list_assets('/Game/Farm/Art/Studies') if '/Flower' in p and '_SM_VMF_Nature_Flower_White_' in p]
    if not parts:
        data=original.get_editor_property('asset_import_data')
        options=unreal.FbxImportUI()
        options.import_mesh=True
        options.import_materials=False
        options.import_textures=False
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
        options.static_mesh_import_data.import_uniform_scale=1.0
        task=unreal.AssetImportTask()
        task.filename=str(Path(unreal.Paths.project_content_dir())/'Farm/VoxelMicroFarm/Models/Expansion02/Nature'/('SM_VMF_Nature_'+suffix+'.fbx'))
        task.destination_path='/Game/Farm/Art/Studies'
        task.destination_name='SM_'+suffix+'_ShapeStudy'
        task.automated=True
        task.save=True
        task.options=options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        parts=[p for p in unreal.EditorAssetLibrary.list_assets('/Game/Farm/Art/Studies') if p.startswith(prefix)]
    if not unreal.EditorAssetLibrary.does_asset_exist(target):
        unreal.EditorAssetLibrary.duplicate_asset(source_path,target)
    asset=unreal.load_asset(target)
    assert asset,target
    mesh=unreal.DynamicMesh()
    part_report=[]
    for p in parts:
        part=unreal.load_asset(p)
        temp=unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(part,temp,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
        unreal.GeometryScript_MeshEdits.append_mesh(mesh,temp,unreal.Transform())
        part_report.append({'name':part.get_name(),'bounds':str(part.get_bounding_box())})
    if not hasattr(unreal,'_farm_shape_sources'): unreal._farm_shape_sources={}
    if suffix not in unreal._farm_shape_sources: unreal._farm_shape_sources[suffix]=mesh
    mesh=unreal._farm_shape_sources[suffix]
    layer=unreal.GeometryScriptGroupLayer()
    unreal.GeometryScript_PolyGroups.convert_components_to_polygroups(mesh,layer)
    ids=list(unreal.GeometryScript_List.convert_index_list_to_array(unreal.GeometryScript_MeshQueries.get_all_triangle_i_ds(mesh)[1]))
    groups={}
    for tid in ids:
        group,valid=unreal.GeometryScript_PolyGroups.get_triangle_polygroup_id(mesh,layer,tid)
        valid,a,b,c=unreal.GeometryScript_MeshQueries.get_triangle_positions(mesh,tid)
        groups.setdefault(group,[]).extend([[p.x,p.y,p.z] for p in (a,b,c)])
    REPORT['assets'].append({'name':suffix,'source_bounds':str(original.get_bounding_box()),'parts':part_report,'groups':[{'id':g,'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)],'triangles':len(pts)//3} for g,pts in groups.items()]})
REPORT['buffer_api']=unreal.GeometryScript_MeshEdits.append_buffers_to_mesh.__doc__
