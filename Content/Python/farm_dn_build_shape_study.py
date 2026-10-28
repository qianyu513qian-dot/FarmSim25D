"""Rebuild leaf masses and flower anatomy for two isolated art review assets."""
import unreal,math,json,random
from pathlib import Path
assert not unreal.EditorLevelLibrary.get_game_world()
ROOT='/Game/Farm/Art/Studies/'
palette=json.loads((Path(unreal.Paths.project_saved_dir())/'ArtReview/rounded_originals/palette.json').read_text())
colors={}
for i,rgb in enumerate(palette['pixels']):
    colors.setdefault(tuple(rgb),((i%palette['width']+.5)/palette['width'],(i//palette['width']+.5)/palette['height']))
def color(rgb): return colors[min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(c,rgb)))]
GREEN=color((80,120,43)); LIGHT=color((119,153,62)); DARK=color((49,87,33))
WHITE=color((234,229,207)); CREAM=color((210,207,178)); GOLD=color((218,157,45))
BARK=color((106,71,39))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def box(asset):
    b=asset.get_bounding_box(); lo=[b.min.x,b.min.y,b.min.z]; hi=[b.max.x,b.max.y,b.max.z]
    return [(a+b)/2 for a,b in zip(lo,hi)],[(b-a)/2 for a,b in zip(lo,hi)]
class Builder:
    def __init__(self): self.vertices=[]; self.normals=[]; self.uvs=[]; self.tris=[]
    def tri(self,a,b,c,uv,inside=None):
        n=cross(sub(b,a),sub(c,a)); length=math.sqrt(dot(n,n))
        if length<1e-6: return
        if inside is not None and dot(n,sub(a,inside))<0: b,c=c,b; n=tuple(-v for v in n)
        idx=len(self.vertices)
        self.vertices.extend(unreal.Vector(*(x*100 for x in p)) for p in (a,b,c))
        self.normals.extend([unreal.Vector(*(v/length for v in n))]*3)
        self.uvs.extend([unreal.Vector2D(*uv)]*3)
        # Unreal front faces use clockwise winding; normals above point outwards.
        self.tris.append(unreal.IntVector(idx,idx+2,idx+1))
    def ellipsoid(self,c,r,seed=1,uv=GREEN,segments=10,rings=5):
        rng=random.Random(seed)
        shape=[1+rng.uniform(-.085,.085) for _ in range(segments)]
        def p(j,i):
            theta=2*math.pi*(i%segments)/segments; phi=math.pi*j/rings
            s=math.sin(phi)*shape[i%segments]
            return (c[0]+r[0]*s*math.cos(theta),c[1]+r[1]*s*math.sin(theta),c[2]+r[2]*math.cos(phi))
        for j in range(rings):
            for i in range(segments):
                shade=uv
                for a,b,d in [(p(j,i),p(j+1,i),p(j+1,i+1)),(p(j,i),p(j+1,i+1),p(j,i+1))]: self.tri(a,b,d,shade,c)
    def leaf(self,base,angle,length,width,rise,uv=GREEN,petal=False):
        co,si=math.cos(angle),math.sin(angle)
        def p(t,lane,back=False):
            w=math.sin(math.pi*t)**(.52 if petal else .85)*width*.5
            x=length*t; y=w*lane
            z=rise*t+math.sin(math.pi*t)*length*(.08 if petal else .16)-abs(lane)*w*.18
            if back: z-=.38 if petal else .65
            return (base[0]+x*co-y*si,base[1]+x*si+y*co,base[2]+z)
        ts=[0,.18,.4,.65,.85,1]
        for a,b in zip(ts,ts[1:]):
            for l,h in [(-1,0),(0,1)]:
                for back in (False,True):
                    pts=[p(a,l,back),p(b,l,back),p(b,h,back),p(a,h,back)]
                    for indices in [(0,1,2),(0,2,3)]:
                        x,y,z=[pts[i] for i in indices]
                        self.tri(x,z,y,uv) if back else self.tri(x,y,z,uv)
            for lane in (-1,1):
                pts=[p(a,lane),p(b,lane),p(b,lane,True),p(a,lane,True)]
                self.tri(pts[0],pts[1],pts[2],uv); self.tri(pts[0],pts[2],pts[3],uv)
    def stem(self,c,height,seed):
        def center(t): return (c[0]+math.sin(math.pi*t)*1.8,c[1]+math.sin(math.pi*t)*1.2,c[2]-height*(1-t))
        for j in range(6):
            lo=center(j/6); hi=center((j+1)/6)
            for i in range(6):
                a=i*math.pi/3; b=(i+1)*math.pi/3
                def p(o,theta,r): return (o[0]+math.cos(theta)*r,o[1]+math.sin(theta)*r,o[2])
                pts=[p(lo,a,1.0),p(lo,b,1.0),p(hi,b,.9),p(hi,a,.9)]
                self.tri(pts[0],pts[1],pts[2],DARK,lo); self.tri(pts[0],pts[2],pts[3],DARK,lo)
        for i,t in enumerate([.3,.52,.7]): self.leaf(center(t),seed+i*2.4,13-i*2,5.5-i*.6,5.5,GREEN)
    def branch(self,start,end,r0,r1,sides=7):
        axis=sub(end,start); size=math.sqrt(dot(axis,axis)); axis=tuple(v/size for v in axis)
        u=cross(axis,(0,0,1) if abs(axis[2])<.9 else (0,1,0))
        size=math.sqrt(dot(u,u)); u=tuple(v/size for v in u); v=cross(axis,u)
        def p(c,r,i):
            angle=math.tau*i/sides
            return tuple(c[k]+r*(u[k]*math.cos(angle)+v[k]*math.sin(angle)) for k in range(3))
        for i in range(sides):
            a,b,c,d=p(start,r0,i),p(start,r0,i+1),p(end,r1,i+1),p(end,r1,i)
            self.tri(a,b,c,BARK,start); self.tri(a,c,d,BARK,start)
            self.tri(end,d,c,BARK,start)
    def append(self,mesh):
        for t in self.tris:
            p=[self.vertices[i] for i in (t.x,t.y,t.z)]
            a,b,c=[(v.x,v.y,v.z) for v in p]
            n=cross(sub(c,a),sub(b,a)); length=math.sqrt(dot(n,n))
            for i in (t.x,t.y,t.z): self.normals[i]=unreal.Vector(*(v/length for v in n))
        buffers=unreal.GeometryScriptSimpleMeshBuffers(vertices=self.vertices,normals=self.normals,uv0=self.uvs,triangles=self.tris)
        unreal.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,buffers)
REPORT={'assets':[]}
for suffix in ['Tree_Broadleaf','FlowerPatch_White']:
    asset=unreal.load_asset(ROOT+'SM_'+suffix+'_ShapeStudy'); assert asset
    original=unreal.load_asset('/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix)
    mesh=unreal.DynamicMesh(); builder=Builder()
    def keep_part(name):
        temp=unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(unreal.load_asset(ROOT+name),temp,unreal.GeometryScriptCopyMeshFromAssetOptions(),unreal.GeometryScriptMeshReadLOD())
        unreal.GeometryScript_MeshEdits.append_mesh(mesh,temp,unreal.Transform(scale=unreal.Vector(100,100,100)))
    if suffix.startswith('Tree'):
        trunk=[((0,0,0),21),((2,-1,82),17),((-1,2,194),12),((2,2,291),5)]
        for (a,r0),(b,r1) in zip(trunk,trunk[1:]): builder.branch(a,b,r0,r1,8)
        for i in range(5):
            angle=i*math.tau/5+.3
            builder.branch((0,0,24),(math.cos(angle)*37,math.sin(angle)*31,3),10,2.5,6)
        parts=sorted(p for p in unreal.EditorAssetLibrary.list_assets(ROOT) if 'Tree_Broadleaf_Canopy_' in p)
        for index,path in enumerate(parts):
            c,r=box(unreal.load_asset(path)); rng=random.Random(210+index)
            builder.branch((0,0,min(c[2]*.72,225)),(c[0]*.87,c[1]*.87,c[2]-r[2]*.18),6.5 if index<5 else 5,2.8,7)
            # Broad primary mass plus unequal lateral lobes, keeping the original branch anchors.
            builder.ellipsoid(c,[r[0]*.79,r[1]*.83,r[2]*.86],seed=index+2,uv=GREEN)
            for side in [-1,1]:
                offset=[c[0]+side*r[0]*.48,c[1]+side*r[1]*.18,c[2]-r[2]*.18]
                builder.ellipsoid(offset,[r[0]*.5,r[1]*.63,r[2]*.61],seed=index*7+side+15,uv=GREEN)
            for k in range(9):
                angle=k*math.tau/9+index*.62
                base=(c[0]+math.cos(angle)*r[0]*.52,c[1]+math.sin(angle)*r[1]*.52,c[2]+r[2]*(.15 if k%2 else .46))
                builder.leaf(base,angle+.12, min(r[0],r[1])*.75, min(r[0],r[1])*.44, r[2]*rng.uniform(-.12,.14), LIGHT if k%3==0 else GREEN)
    else:
        keep_part('SM_VMF_Nature_FlowerPatch_White_OptionalGround_Soil')
        # Four flower heads retain their original centers and heights.
        for i in range(1,5):
            c,r=box(unreal.load_asset(ROOT+f'Flower{i}_SM_VMF_Nature_Flower_White_FlowerCenter'))
            head=[c[0],c[1],c[2]+1.8]
            builder.stem(head,head[2]-3,seed=i*.8)
            for k in range(6):
                a=k*math.tau/6+i*.43
                base=(head[0]+math.cos(a)*1.5,head[1]+math.sin(a)*1.5,head[2]-1.8)
                builder.leaf(base,a,8.0+(k%2)*.6,6.3,1.2,WHITE if k%3 else CREAM,petal=True)
            builder.ellipsoid(head,[3.1,3.1,1.7],seed=i,uv=GOLD,segments=10,rings=4)
        for i,(x,y) in enumerate([(-27,9),(-14,21),(12,20),(27,-12),(-24,-17),(7,-22)]):
            for k in range(5): builder.leaf((x*.74,y*.74,6),i*.85+k*math.tau/5,15+k*.6,8.8,4+k*.9,GREEN if k else DARK)
    if suffix.startswith('Tree'):
        # Keep the original canopy footprint while changing its internal silhouette.
        for axis,low,high in [('x',-13200,12039),('y',-7268,8400)]:
            current_low=min(getattr(p,axis) for p in builder.vertices)
            current_high=max(getattr(p,axis) for p in builder.vertices)
            for p in builder.vertices:
                setattr(p,axis,low+(getattr(p,axis)-current_low)*(high-low)/(current_high-current_low))
    builder.append(mesh)
    # Keep the duplicated original material and collision definitions.
    collision=asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()
    options=unreal.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=False,apply_nanite_settings=False)
    _,result=unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh,asset,options,unreal.GeometryScriptMeshWriteLOD())
    assert result==unreal.GeometryScriptOutcomePins.SUCCESS
    assert asset.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()==collision
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'FarmShapeStudy','anatomy-v1')
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    REPORT['assets'].append({'asset':asset.get_path_name(),'triangles':mesh.get_triangle_count(),'bounds':str(asset.get_bounding_box()),'collision_preserved':True})
