import unreal
REPORT={'materials':{},'surfaces':[]}
world=unreal.EditorLevelLibrary.get_game_world()
actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StaticMeshActor) if world else unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
mats={}
for a in actors:
    label=a.get_actor_label()
    if any(t in label.lower() for t in ['grass','ground','tree','bridge','house']):
        c=a.get_component_by_class(unreal.StaticMeshComponent)
        if not c: continue
        if len(REPORT['surfaces'])<12: REPORT['surfaces'].append({'label':label,'mats':[str(c.get_material(i)) for i in range(c.get_num_materials())]})
        for i in range(c.get_num_materials()):
            m=c.get_material(i)
            if m: mats[m.get_path_name()]=m
for path,m in mats.items():
    d={}
    for name in ['shading_model','blend_mode','roughness','specular','metallic']:
        try: d[name]=str(m.get_editor_property(name))
        except Exception: pass
    d['textures']=[]
    if isinstance(m,unreal.Material):
        for t in unreal.MaterialEditingLibrary.get_used_textures(m):
            d['textures'].append({'name':t.get_path_name(),'srgb':t.srgb})
        d['connections']={}
        for prop in [unreal.MaterialProperty.MP_BASE_COLOR,unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.MaterialProperty.MP_ROUGHNESS,unreal.MaterialProperty.MP_SPECULAR]:
            try:
                e=unreal.MaterialEditingLibrary.get_material_property_input_node(m,prop)
                d['connections'][str(prop)]=str(e)
            except Exception as ex: d['connections'][str(prop)]=str(ex)
    REPORT['materials'][path]=d
