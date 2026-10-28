"""Import untouched source FBX parts into isolated build folders; no level edits."""
import unreal,json
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
SUFFIXES=['Tree_Broadleaf','Tree_Tall','Flower_White','Flower_Yellow','FlowerPatch_White','FlowerPatch_Yellow','Shrub_Low','Shrub_Tall','Bush']
REPORT={'assets':[]}
for suffix in SUFFIXES:
    rel='Farm/VoxelMicroFarm/Models/'+('Nature/' if suffix=='Bush' else 'Expansion02/Nature/')+'SM_VMF_Nature_'+suffix
    original=unreal.load_asset('/Game/'+rel); assert original
    folder='/Game/Farm/Art/VegetationBuild/'+suffix
    parts=unreal.EditorAssetLibrary.list_assets(folder) if unreal.EditorAssetLibrary.does_directory_exist(folder) else []
    if not parts:
        options=unreal.FbxImportUI()
        options.import_mesh=True
        options.import_materials=False
        options.import_textures=False
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
        options.static_mesh_import_data.import_uniform_scale=1
        task=unreal.AssetImportTask()
        task.filename=str(Path(unreal.Paths.project_content_dir())/(rel+'.fbx'))
        task.destination_path=folder
        task.automated=True
        task.save=True
        task.options=options
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        parts=unreal.EditorAssetLibrary.list_assets(folder)
    rows=[]
    for path in parts:
        asset=unreal.load_asset(path)
        if not isinstance(asset,unreal.StaticMesh): continue
        b=asset.get_bounding_box()
        rows.append({'name':asset.get_name(),'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]})
    assert rows,suffix
    REPORT['assets'].append({'name':suffix,'original':original.get_path_name(),'parts':rows})
