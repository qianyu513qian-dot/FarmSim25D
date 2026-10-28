"""Apply the anatomy pass to every tree, flower and shrub resource used in the level."""
import unreal,json,math,random,hashlib
from pathlib import Path
import farm_vegetation_geometry as g
assert not unreal.EditorLevelLibrary.get_game_world()
saved=Path(unreal.Paths.project_saved_dir())/'ArtReview'
prepared=json.loads((saved.parent/'DayNight/farm_dn_prepare_vegetation.py.json').read_text())['report']['assets']
assert len(prepared)==9
backup=saved/'before_full_anatomy'; backup.mkdir(exist_ok=True)
REPORT={'assets':[]}
def bounds(parts):
    return [min(p['min'][i] for p in parts) for i in range(3)],[max(p['max'][i] for p in parts) for i in range(3)]
def center(part): return [(a+b)/2 for a,b in zip(part['min'],part['max'])],[(b-a)/2 for a,b in zip(part['min'],part['max'])]
def fit(builder,lo,hi,axes=(0,1)):
    for axis in axes:
        key='xyz'[axis]; low=min(getattr(p,key) for p in builder.vertices); high=max(getattr(p,key) for p in builder.vertices)
        for p in builder.vertices: setattr(p,key,lo[axis]*100+(getattr(p,key)-low)*(hi[axis]-lo[axis])*100/(high-low))
for row in prepared:
    suffix=row['name']; parts=row['parts']; lo,hi=bounds(parts)
    asset=unreal.load_asset(row['original']); assert asset
    disk=Path(unreal.Paths.project_content_dir())/(asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
    copy=backup/disk.name
    if not copy.exists(): copy.write_bytes(disk.read_bytes())
    mesh=unreal.DynamicMesh(); builder=g.Builder(); g.configure_palette(suffix=='Bush')
    materials=[s.material_interface.get_path_name() for s in asset.static_materials]
    collision=asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()
    collision_hash=hashlib.sha256(collision.encode()).hexdigest()
    def keep_part(part):
        obj=unreal.load_asset('/Game/Farm/Art/VegetationBuild/'+suffix+'/'+part['name'])
        source=unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(obj,source,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
        unreal.GeometryScript_MeshEdits.append_mesh(mesh,source,unreal.Transform(scale=unreal.Vector(100,100,100)))
    if suffix in ['Tree_Broadleaf','FlowerPatch_White']:
        study=unreal.load_asset('/Game/Farm/Art/Studies/SM_'+suffix+'_ShapeStudy'); assert study
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(study,mesh,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
    elif suffix=='Tree_Tall':
        height=next(p['max'][2] for p in parts if 'TrunkAndBranches' in p['name'])*.983
        trunk=[((0,0,0),18),((2,-1,height*.28),14),((-1,2,height*.67),10),((2,2,height),4)]
        for (a,r0),(b,r1) in zip(trunk,trunk[1:]): builder.branch(a,b,r0,r1,8)
        for i in range(5):
            angle=i*math.tau/5+.3
            builder.branch((0,0,24),(math.cos(angle)*31,math.sin(angle)*28,3),8,2,6)
        for index,part in enumerate(p for p in parts if 'Canopy_' in p['name']):
            c,r=center(part); rng=random.Random(510+index)
            builder.branch((0,0,min(c[2]*.72,height*.77)),(c[0]*.87,c[1]*.87,c[2]-r[2]*.18),5.5,2.4,7)
            builder.ellipsoid(c,[r[0]*.79,r[1]*.83,r[2]*.86],seed=index+2,uv=g.GREEN)
            for side in [-1,1]:
                offset=[c[0]+side*r[0]*.48,c[1]+side*r[1]*.18,c[2]-r[2]*.18]
                builder.ellipsoid(offset,[r[0]*.5,r[1]*.63,r[2]*.61],seed=index*7+side+15,uv=g.GREEN)
            for k in range(9):
                a=k*math.tau/9+index*.62
                base=(c[0]+math.cos(a)*r[0]*.52,c[1]+math.sin(a)*r[1]*.52,c[2]+r[2]*(.15 if k%2 else .46))
                builder.leaf(base,a+.12,min(r[0],r[1])*.75,min(r[0],r[1])*.44,r[2]*rng.uniform(-.12,.14),g.LIGHT if k%3==0 else g.GREEN)
        fit(builder,lo,hi,(0,1,2))
    elif suffix.startswith('Flower'):
        patch=suffix.startswith('FlowerPatch'); yellow=suffix.endswith('Yellow')
        if patch: keep_part(next(p for p in parts if 'OptionalGround_Soil' in p['name']))
        flower_centers=[p for p in parts if p['name'].endswith('FlowerCenter')]
        assert len(flower_centers)==(3 if patch else 1)
        for i,part in enumerate(flower_centers,1):
            c,r=center(part); head=[c[0],c[1],c[2]+1.8]
            builder.stem(head,head[2]-(3 if patch else 0),seed=i*.8)
            n=8 if yellow else 6
            for k in range(n):
                a=k*math.tau/n+i*.43
                base=(head[0]+math.cos(a)*1.5,head[1]+math.sin(a)*1.5,head[2]-1.8)
                uv=g.color((238,190,45)) if yellow else (g.WHITE if k%3 else g.CREAM)
                builder.leaf(base,a,(10 if yellow else 8)+(k%2)*.6,5.8 if yellow else 6.3,1.2,uv,petal=True)
            builder.ellipsoid(head,[3.7 if yellow else 3.1,3.7 if yellow else 3.1,1.7],seed=i,uv=g.color((164,98,28)) if yellow else g.GOLD,segments=10,rings=4)
        if patch:
            for i,(x,y) in enumerate([(-27,9),(-14,21),(12,20),(27,-12),(-24,-17),(7,-22)]):
                for k in range(5): builder.leaf((x*.74,y*.74,6),i*.85+k*math.tau/5,15+k*.6,8.8,4+k*.9,g.GREEN if k else g.DARK)
        else:
            for k in range(3): builder.leaf((0,0,1.8),k*math.tau/3+.8,8,3.7,3,g.GREEN)
    else:
        # Low, tall and base-pack shrubs retain their distinct envelopes and palettes.
        c=[(a+b)/2 for a,b in zip(lo,hi)]; r=[(b-a)/2 for a,b in zip(lo,hi)]
        for i,(ox,oy,z,s) in enumerate([(-.36,-.12,.48,.72),(.32,.2,.49,.7),(0,-.04,.72,.66),(.05,.44,.36,.53)]):
            p=(c[0]+r[0]*ox,c[1]+r[1]*oy,hi[2]*z)
            builder.ellipsoid(p,(r[0]*s,r[1]*s,hi[2]*.31),seed=i+43,uv=g.GREEN)
            for k in range(9):
                a=k*math.tau/9+i*.7
                base=(p[0]+math.cos(a)*r[0]*s*.55,p[1]+math.sin(a)*r[1]*s*.55,p[2]+hi[2]*.13)
                builder.leaf(base,a,min(r[:2])*.58,min(r[:2])*.31,hi[2]*.025,g.LIGHT if k%3==0 else g.GREEN)
        for k in range(7):
            a=k*math.tau/7
            builder.leaf((c[0],c[1],1),a,min(r[:2])*.9,min(r[:2])*.34,hi[2]*.24,g.DARK)
        fit(builder,lo,hi,(0,1,2))
    if builder.tris: builder.append(mesh)
    assert 300<mesh.get_triangle_count()<10000,(suffix,mesh.get_triangle_count())
    options=unreal.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=False,apply_nanite_settings=False)
    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,options,unreal.GeometryScriptMeshWriteLOD())
    assert result==unreal.GeometryScriptOutcomePins.SUCCESS
    assert asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()==collision
    assert [s.material_interface.get_path_name() for s in asset.static_materials]==materials
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'FarmVegetationRevision','anatomy-v2')
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'FarmRoundedEdges','superseded')
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    REPORT['assets'].append({'name':suffix,'asset':asset.get_path_name(),'triangles':mesh.get_triangle_count(),'materials':materials,'collision_hash':collision_hash,'bounds':str(asset.get_bounding_box())})
(saved/'full_anatomy_manifest.json').write_text(json.dumps(REPORT,indent=2))
