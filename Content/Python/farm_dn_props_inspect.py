"""Inventory art subjects and their palette inputs before editing."""
import unreal
from collections import Counter
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before inspecting saved editor actors.'
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT={'actors':[],'materials':{},'assets':{}}
mel=unreal.MaterialEditingLibrary
def vec(v): return [v.x,v.y,v.z]
def walk(m,e,seen):
    if not e or e.get_path_name() in seen: return None
    seen.add(e.get_path_name()); d={'class':e.get_class().get_name()}
    for k in ['texture','constant','default_value','parameter_name']:
        try: d[k]=str(e.get_editor_property(k))
        except Exception: pass
    d['inputs']=[walk(m,x,seen) for x in mel.get_inputs_for_material_expression(m,e)]
    return d
for a in eas.get_all_level_actors():
    lab=a.get_actor_label()
    if not any(lab.startswith('VMF_'+s) for s in ['Tree','House','Fence','Flower','Shrub','Bush','Clump','TallGrass','Well','ChickenCoop','ToolShelter']): continue
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    if not c: continue
    o,e=a.get_actor_bounds(False)
    REPORT['actors'].append({'label':lab,'loc':vec(a.get_actor_location()),'scale':vec(a.get_actor_scale3d()),'rot':str(a.get_actor_rotation()),'bounds':[vec(o),vec(e)],'mesh':c.static_mesh.get_path_name(),'mats':[c.get_material(i).get_path_name() for i in range(c.get_num_materials())]})
    for i in range(c.get_num_materials()):
        m=c.get_material(i)
        if m.get_path_name() not in REPORT['materials']:
            REPORT['materials'][m.get_path_name()]={str(p):walk(m,mel.get_material_property_input_node(m,p),set()) for p in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_ROUGHNESS]} if isinstance(m,unreal.Material) else {'instance':str(m)}
for path in unreal.EditorAssetLibrary.list_assets('/Game/Farm/VoxelMicroFarm/Models',recursive=True):
    if any(s in path.split('/')[-1] for s in ['Tree','Flower','Fence_Picket','FarmGate']):
        a=unreal.load_asset(path)
        if isinstance(a,unreal.StaticMesh): REPORT['assets'][path]={'bounds':str(a.get_bounding_box()),'slots':[str(s.material_interface) for s in a.static_materials]}
