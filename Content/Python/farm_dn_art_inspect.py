import unreal
from collections import Counter
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=list(eas.get_all_level_actors())
REPORT={'groups':dict(Counter('_'.join(a.get_actor_label().split('_')[:2]) for a in actors)),'samples':[],'meshes':{}}
counts=Counter()
for a in actors:
    lab=a.get_actor_label()
    if not any(t in lab.lower() for t in ['grass','path','bridge','water','tree','cliff','bank']): continue
    group='_'.join(lab.split('_')[:2])
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    if not c: continue
    sm=c.static_mesh
    if sm:
        path=sm.get_path_name()
        REPORT['meshes'][path]={'bounds':str(sm.get_bounding_box()),'count':REPORT['meshes'].get(path,{}).get('count',0)+1}
    if counts[group]>=5: continue
    counts[group]+=1
    REPORT['samples'].append({'label':lab,'loc':str(a.get_actor_location()),'rotation':str(a.get_actor_rotation()),'scale':str(a.get_actor_scale3d()),'bounds':str(a.get_actor_bounds(False)),'mesh':str(sm),'materials':[str(c.get_material(i)) for i in range(c.get_num_materials())],'collision':str(c.get_collision_enabled())})
mel=unreal.MaterialEditingLibrary
m=unreal.load_asset('/Game/Farm/Art/Mats/M_Water')
REPORT['water']={'shading':str(m.get_editor_property('shading_model')),'inputs':{}}
def walk(e,seen):
    if not e or e.get_path_name() in seen: return None
    seen.add(e.get_path_name())
    d={'class':e.get_class().get_name()}
    for k in ['constant','r','const_a','const_b','texture','parameter_name','default_value','speed_x','speed_y','coordinate_index','u_tiling','v_tiling']:
        try: d[k]=str(e.get_editor_property(k))
        except Exception: pass
    d['inputs']=[walk(x,seen) for x in mel.get_inputs_for_material_expression(m,e)]
    return d
for p in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_EMISSIVE_COLOR]:
    REPORT['water']['inputs'][str(p)]=walk(mel.get_material_property_input_node(m,p),set())
