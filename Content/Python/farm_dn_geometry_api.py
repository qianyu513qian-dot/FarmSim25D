import unreal,json
from pathlib import Path
names={
'GeometryScript_AssetUtils':['copy_mesh_from_static_mesh','copy_mesh_to_static_mesh'],
'GeometryScript_PolyGroups':['compute_polygroups_from_angle_threshold'],
'GeometryScript_MeshModeling':['apply_mesh_bevel_selection','apply_mesh_polygroup_bevel'],
'GeometryScript_MeshQueries':['get_all_triangle_i_ds','get_triangle_u_vs','get_triangle_positions','get_triangle_count','get_mesh_bounding_box'],
'GeometryScript_MeshSelection':['convert_index_array_to_mesh_selection'],
'GeometryScript_UVs':['set_mesh_triangle_u_vs'],
'GeometryScript_Normals':['recompute_normals','compute_split_normals'],
'GeometryScript_MeshSpatial':['build_bvh_for_mesh','find_nearest_point_on_mesh'],
'GeometryScript_MeshEdits':['append_mesh'],
'GeometryScript_List':['convert_index_list_to_array'],
}
REPORT={}
for cls,methods in names.items():
    c=getattr(unreal,cls)
    REPORT[cls]={m:getattr(c,m).__doc__ if hasattr(c,m) else [n for n in dir(c) if any(s in n for s in ['triangle','nearest','normal','bvh'])] for m in methods}
for cls in ['GeometryScriptCopyMeshToAssetOptions','GeometryScriptCopyMeshFromAssetOptions','GeometryScriptMeshBevelSelectionOptions','GeometryScriptMeshBevelOptions','GeometryScriptSplitNormalsOptions']:
    REPORT[cls]=getattr(unreal,cls).__doc__
for cls in ['GeometryScriptMeshReadLOD','GeometryScriptMeshWriteLOD','GeometryScriptTrianglePoint','GeometryScriptUVTriangle']:
    REPORT[cls]=getattr(unreal,cls).__doc__
REPORT['DynamicMesh']=[n for n in dir(unreal.DynamicMesh) if any(x in n for x in ['copy','triangle','reset'])]
