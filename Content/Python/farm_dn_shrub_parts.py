import unreal,json
from pathlib import Path
REPORT={}
for suffix in ['Shrub_Low','Shrub_Tall','Bush']:
    path=unreal.EditorAssetLibrary.list_assets('/Game/Farm/Art/VegetationBuild/'+suffix)[0]
    asset=unreal.load_asset(path); mesh=unreal.DynamicMesh()
    unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,mesh,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
    layer=unreal.GeometryScriptGroupLayer()
    unreal.GeometryScript_PolyGroups.convert_components_to_polygroups(mesh,layer)
    q=unreal.GeometryScript_MeshQueries
    groups={}
    for tid in unreal.GeometryScript_List.convert_index_list_to_array(q.get_all_triangle_i_ds(mesh)[1]):
        g,valid=unreal.GeometryScript_PolyGroups.get_triangle_polygroup_id(mesh,layer,tid)
        valid,*p=q.get_triangle_positions(mesh,tid)
        a,b,c,valid=q.get_triangle_u_vs(mesh,0,tid)
        data=groups.setdefault(g,{'p':[],'uv':[]})
        data['p'].extend([[v.x,v.y,v.z] for v in p]); data['uv'].append([a.x,a.y])
    REPORT[suffix]=[{'id':g,'min':[min(p[i] for p in d['p']) for i in range(3)],'max':[max(p[i] for p in d['p']) for i in range(3)],'uv':d['uv'][0],'triangles':len(d['uv'])} for g,d in groups.items()]
