"""Round the original vegetation edges in-place, retaining layout and palette UVs."""
import unreal,json,math
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
out=Path(unreal.Paths.project_saved_dir())/'ArtReview'
request=json.loads((out/'round_request.json').read_text()) if (out/'round_request.json').exists() else {}
palette=json.loads((out/'rounded_originals/palette.json').read_text())
if not hasattr(unreal,'_farm_original_vegetation'): unreal._farm_original_vegetation={}
cache=unreal._farm_original_vegetation
q=unreal.GeometryScript_MeshQueries
def ids(mesh): return list(unreal.GeometryScript_List.convert_index_list_to_array(q.get_all_triangle_i_ds(mesh)[1]))
def uv_color(mesh,tid):
    a,b,c,valid=q.get_triangle_u_vs(mesh,0,tid); assert valid
    uv=unreal.Vector2D((a.x+b.x+c.x)/3,(a.y+b.y+c.y)/3)
    x=min(palette['width']-1,max(0,int(uv.x*palette['width'])))
    y=min(palette['height']-1,max(0,int(uv.y*palette['height'])))
    return uv,palette['pixels'][y*palette['width']+x]
REPORT={'assets':[]}
for suffix in request.get('assets',['Tree_Broadleaf','Tree_Tall','Flower_White','Flower_Yellow','FlowerPatch_White','FlowerPatch_Yellow']):
    path='/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix
    asset=unreal.load_asset(path)
    if suffix not in cache:
        if unreal.EditorAssetLibrary.get_metadata_tag(asset,'FarmRoundedEdges')=='v2':
            REPORT['assets'].append({'asset':suffix,'already_processed':True})
            continue
        assert unreal.EditorAssetLibrary.get_metadata_tag(asset,'FarmRoundedEdges')=='', 'Restore the original backup before upgrading an earlier mesh revision.'
        source=unreal.DynamicMesh()
        _,result=unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,source,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
        assert result==unreal.GeometryScriptOutcomePins.SUCCESS,str(result)
        cache[suffix]=source
    source=cache[suffix]
    original_bounds=q.get_mesh_bounding_box(source)
    original_materials=[str(slot.material_interface) for slot in asset.static_materials]
    mesh=unreal.DynamicMesh()
    unreal.GeometryScript_MeshEdits.append_mesh(mesh,source,unreal.Transform())
    original_ids=ids(source); original_count=len(original_ids)
    selected=[]
    for tid in original_ids:
        uv,(r,g,b)=uv_color(source,tid)
        green=g>r*1.03 and g>b*1.3
        petal=r>110 and g>90 and (b>100 or r>b*1.5)
        if green or ('Flower' in suffix and petal): selected.append(tid)
    assert len(selected)>original_count*.15,(suffix,original_count,len(selected))
    layer=unreal.GeometryScriptGroupLayer()
    unreal.GeometryScript_PolyGroups.convert_components_to_polygroups(mesh,layer)
    components={}
    for tid in selected:
        group,valid=unreal.GeometryScript_PolyGroups.get_triangle_polygroup_id(mesh,layer,tid)
        components.setdefault(group,[]).append(tid)
    unreal.GeometryScript_PolyGroups.compute_polygroups_from_angle_threshold(mesh,layer,crease_angle=20,min_group_size=2)
    distance=request.get('tree_distance',450.0) if suffix.startswith('Tree_') else request.get('flower_distance',180.0)
    radii=[]
    for triangles in components.values():
        lengths=[]
        for tid in triangles:
            valid,a,b,c=q.get_triangle_positions(source,tid)
            for u,v in [(a,b),(b,c),(c,a)]:
                length=math.sqrt((u.x-v.x)**2+(u.y-v.y)**2+(u.z-v.z)**2)
                if length>1: lengths.append(length)
        # Clamp by the actual local part thickness to prevent bevel self-intersections.
        radius=min(distance,min(lengths)*.24)
        radii.append(radius)
        _,selection=unreal.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(mesh,triangles,unreal.GeometryScriptMeshSelectionType.TRIANGLES)
        options=unreal.GeometryScriptMeshBevelSelectionOptions(bevel_distance=radius,infer_material_id=True,subdivisions=2,round_weight=.65)
        unreal.GeometryScript_MeshModeling.apply_mesh_bevel_selection(mesh,selection,unreal.GeometryScriptMeshBevelSelectionMode.ALL_POLYGROUP_EDGES,options)
    after_ids=ids(mesh)
    assert original_count<len(after_ids)<original_count*20,(original_count,len(after_ids))
    # New bevel UV islands must remain in the original color swatches, not cross palette cells.
    _,bvh=unreal.GeometryScript_MeshSpatial.build_bvh_for_mesh(source)
    smooth_ids=[]
    for tid in after_ids:
        valid,a,b,c=q.get_triangle_positions(mesh,tid); assert valid
        point=unreal.Vector((a.x+b.x+c.x)/3,(a.y+b.y+c.y)/3,(a.z+b.z+c.z)/3)
        _,near,found=unreal.GeometryScript_MeshSpatial.find_nearest_point_on_mesh(source,bvh,point,unreal.GeometryScriptSpatialQueryOptions())
        assert near.valid
        uv,color=uv_color(source,near.triangle_id)
        if near.triangle_id in selected: smooth_ids.append(tid)
        unreal.GeometryScript_UVs.set_mesh_triangle_u_vs(mesh,0,tid,unreal.GeometryScriptUVTriangle(uv0=uv,uv1=uv,uv2=uv),defer_change_notifications=True)
    _,smooth_selection=unreal.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(mesh,smooth_ids,unreal.GeometryScriptMeshSelectionType.TRIANGLES)
    unreal.GeometryScript_MeshDeformers.apply_iterative_smoothing_to_mesh(mesh,smooth_selection,unreal.GeometryScriptIterativeMeshSmoothingOptions(num_iterations=request.get('smooth_iterations',12),alpha=.3))
    unreal.GeometryScript_Normals.compute_split_normals(mesh,unreal.GeometryScriptSplitNormalsOptions(split_by_opening_angle=True,opening_angle_deg=65,split_by_face_group=False),unreal.GeometryScriptCalculateNormalsOptions())
    final_bounds=q.get_mesh_bounding_box(mesh)
    for axis in ['x','y','z']:
        old_size=getattr(original_bounds.max,axis)-getattr(original_bounds.min,axis)
        new_size=getattr(final_bounds.max,axis)-getattr(final_bounds.min,axis)
        assert abs(new_size-old_size)/old_size<.04,(suffix,axis,old_size,new_size)
    body=asset.get_editor_property('body_setup')
    collision_before=body.get_editor_property('agg_geom').export_text()
    bounds_before=original_bounds
    write=unreal.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=False,apply_nanite_settings=False)
    asset.modify()
    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,write,unreal.GeometryScriptMeshWriteLOD())
    assert result==unreal.GeometryScriptOutcomePins.SUCCESS,str(result)
    assert asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()==collision_before,'Collision geometry changed'
    assert [str(slot.material_interface) for slot in asset.static_materials]==original_materials
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'FarmRoundedEdges','v2')
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    REPORT['assets'].append({'asset':suffix,'triangles_before':original_count,'triangles_after':len(after_ids),'selected_triangles':len(selected),'components':len(components),'radius_cm':[min(radii)*.01,max(radii)*.01],'bounds_before':str(bounds_before),'bounds_after':str(asset.get_bounding_box()),'collision_preserved':True})
