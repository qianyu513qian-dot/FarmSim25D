"""Scene-matched lantern meshes and shared water/night material parameters."""
import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
mel=unreal.MaterialEditingLibrary
folder='/Game/Farm/Lighting'
unreal.EditorAssetLibrary.make_directory(folder)
path=folder+'/MPC_FarmLighting'
mpc=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else tools.create_asset('MPC_FarmLighting',folder,unreal.MaterialParameterCollection,unreal.MaterialParameterCollectionFactoryNew())
if not mpc.get_editor_property('vector_parameters'):
    vector=unreal.CollectionVectorParameter()
    vector.set_editor_property('parameter_name','WaterTint')
    vector.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
    mpc.set_editor_property('vector_parameters',[vector])
    scalar=unreal.CollectionScalarParameter()
    scalar.set_editor_property('parameter_name','NightBlend')
    scalar.set_editor_property('default_value',0.0)
    mpc.set_editor_property('scalar_parameters',[scalar])
unreal.EditorAssetLibrary.save_loaded_asset(mpc)

water=unreal.load_asset('/Game/Farm/Art/Mats/M_Water')
root=mel.get_material_property_input_node(water,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
assert root, 'Expected existing water emissive graph'
if str(root.get_editor_property('desc'))!='Farm clock water tint':
    mul=mel.create_material_expression(water,unreal.MaterialExpressionMultiply,400,100)
    mul.set_editor_property('desc','Farm clock water tint')
    param=mel.create_material_expression(water,unreal.MaterialExpressionCollectionParameter,100,260)
    param.set_editor_property('collection',mpc)
    param.set_editor_property('parameter_name','WaterTint')
    assert mel.connect_material_expressions(root,'',mul,'A')
    mask=mel.create_material_expression(water,unreal.MaterialExpressionComponentMask,250,260)
    for p,v in [('r',True),('g',True),('b',True),('a',False)]: mask.set_editor_property(p,v)
    assert mel.connect_material_expressions(param,'',mask,'')
    assert mel.connect_material_expressions(mask,'',mul,'B')
    assert mel.connect_material_property(mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(water)
    unreal.EditorAssetLibrary.save_loaded_asset(water)
else:
    inputs=mel.get_inputs_for_material_expression(water,root)
    for param in inputs:
        if isinstance(param,unreal.MaterialExpressionCollectionParameter):
            mask=mel.create_material_expression(water,unreal.MaterialExpressionComponentMask,250,260)
            for p,v in [('r',True),('g',True),('b',True),('a',False)]: mask.set_editor_property(p,v)
            assert mel.connect_material_expressions(param,'',mask,'')
            assert mel.connect_material_expressions(mask,'',root,'B')
            mel.recompile_material(water); unreal.EditorAssetLibrary.save_loaded_asset(water)

def material(name,color,glow=False):
    p=folder+'/'+name
    if unreal.EditorAssetLibrary.does_asset_exist(p): return unreal.load_asset(p)
    m=tools.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    col=mel.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-300,0)
    col.set_editor_property('constant',unreal.LinearColor(*color,1))
    mel.connect_material_property(col,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=mel.create_material_expression(m,unreal.MaterialExpressionConstant,-300,200)
    rough.set_editor_property('r',0.8)
    mel.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    if glow:
        param=mel.create_material_expression(m,unreal.MaterialExpressionCollectionParameter,-500,300)
        param.set_editor_property('collection',mpc); param.set_editor_property('parameter_name','NightBlend')
        mul=mel.create_material_expression(m,unreal.MaterialExpressionMultiply,-50,100)
        mel.connect_material_expressions(col,'',mul,'A'); mel.connect_material_expressions(param,'',mul,'B')
        mel.connect_material_property(mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m); unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m
wood=material('M_LanternWood',(.12,.065,.028))
glass=material('M_LanternGlow',(2.0,.8,.18),True)
cube=unreal.load_asset('/Engine/BasicShapes/Cube')
actors=list(eas.get_all_level_actors()); by_label={a.get_actor_label():a for a in actors}
for light in [a for a in actors if isinstance(a,unreal.PointLight) and a.get_actor_label().startswith('Farm_Lantern_')]:
    loc=light.get_actor_location(); base=light.get_actor_label()
    for part,z,scale,mat in [('Post',70,(.12,.12,1.4),wood),('Cap',160,(.38,.38,.10),wood),('Glass',145,(.26,.26,.24),glass),('Base',129,(.34,.34,.08),wood)]:
        name=base+'_'+part
        a=by_label.get(name)
        if not a:
            a=eas.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(loc.x,loc.y,z)); a.set_actor_label(name)
        a.set_actor_location(unreal.Vector(loc.x,loc.y,z),False,False)
        a.modify()
        a.set_actor_scale3d(unreal.Vector(*scale))
        c=a.get_component_by_class(unreal.StaticMeshComponent)
        c.set_static_mesh(cube); c.set_material(0,mat)
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('cast_shadow',False)
REPORT={'material_collection':mpc.get_path_name(),'water_material':water.get_path_name(),'lanterns':6}
