"""Deterministic low-poly vegetation geometry used by the asset build scripts."""
import unreal,math,json,random
from pathlib import Path
colors={tuple(row[:3]):tuple(row[3:]) for row in json.loads(Path(__file__).with_name('vegetation_palette.json').read_text())}
def color(rgb): return colors[min(colors,key=lambda c:sum((a-b)**2 for a,b in zip(c,rgb)))]
GREEN=color((80,120,43)); LIGHT=color((119,153,62)); DARK=color((49,87,33))
WHITE=color((234,229,207)); CREAM=color((210,207,178)); GOLD=color((218,157,45))
BARK=color((106,71,39))
def configure_palette(base=False):
    global colors,GREEN,LIGHT,DARK,WHITE,CREAM,GOLD,BARK
    name='vegetation_base_palette.json' if base else 'vegetation_palette.json'
    colors={tuple(row[:3]):tuple(row[3:]) for row in json.loads(Path(__file__).with_name(name).read_text())}
    GREEN=color((80,120,43)); LIGHT=color((119,153,62)); DARK=color((49,87,33))
    WHITE=color((234,229,207)); CREAM=color((210,207,178)); GOLD=color((218,157,45)); BARK=color((106,71,39))
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
