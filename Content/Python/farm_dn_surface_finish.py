"""Art finish inside original materials; no scene geometry or layout edits."""
import unreal
mel=unreal.MaterialEditingLibrary
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before authoring.'
specs=[
    ('M_VMF_Palette','/Game/Farm/VoxelMicroFarm/Textures/T_VMF_Palette',0,.88),
    ('M_VMF_GroundStudy','/Game/Farm/VoxelMicroFarm/Textures/Expansion02/T_VMF_GroundStudy_Palette',0,.94),
    ('M_VMF_Expansion02_Nature','/Game/Farm/VoxelMicroFarm/Textures/Expansion02/T_VMF_Expansion02_Nature_Palette',1,.90),
    ('M_VMF_Expansion02','/Game/Farm/VoxelMicroFarm/Textures/Expansion02/T_VMF_Expansion02_Palette',2,.86),
    ('M_VMF_Expansion02_Facilities','/Game/Farm/VoxelMicroFarm/Textures/Expansion02/T_VMF_Expansion02_Facilities_Palette',2,.88),
]
code='''
float3 c=C;
float green=smoothstep(0.015,0.045,c.g-c.r)*smoothstep(0.025,0.08,c.g-c.b);
float ground=(1-step(0.5,Role))*(1-step(25.0,B.z));
// Compress palette noise without removing the original UV pattern or plank colors.
float broad=1.0+0.035*sin(P.x*0.0032+sin(P.y*0.002))*cos(P.y*0.0038);
float3 grass=(float3(0.18,0.28,0.065)+(c-float3(0.24,0.34,0.08))*0.16)*broad;
float3 leaf=lerp(float3(0.20,0.30,0.085),c,0.60);
float3 greenery=lerp(leaf,grass,ground);
c=lerp(c,greenery,green*(1-step(1.5,Role)));
float roof=smoothstep(2.5,3.0,C.r/max(C.g,0.001));
float wood=smoothstep(0.025,0.075,C.r-C.g)*smoothstep(0.02,0.06,C.g-C.b)*(1-roof);
float3 timber=C*float3(1.035,1.02,0.99)+float3(0.012,0.010,0.006);
c=lerp(c,timber,wood*step(1.5,Role));
// Fine, low-contrast grain follows the existing mesh orientation, not the world axes.
float grain=1.0+0.025*sin(L.x*0.018+0.6*sin(L.y*0.001))+0.012*sin(L.x*0.047+sin(L.y*0.002));
c*=lerp(1.0,grain,wood*saturate(ground+step(1.5,Role)));
return saturate(c);
'''
def expression(mat,cls,x,y,**props):
    node=mel.create_material_expression(mat,cls,x,y)
    for key,value in props.items(): node.set_editor_property(key,value)
    return node
REPORT={'materials':[]}
for name,texture,role,roughness in specs:
    mat=unreal.load_asset('/Game/Farm/VoxelMicroFarm/Materials/'+name)
    assert mat
    mat.modify(); mel.delete_all_material_expressions(mat)
    tex=expression(mat,unreal.MaterialExpressionTextureSample,-600,0,texture=unreal.load_asset(texture))
    p=expression(mat,unreal.MaterialExpressionWorldPosition,-600,180)
    bounds=expression(mat,unreal.MaterialExpressionObjectBounds,-600,300)
    vertex_local=expression(mat,unreal.MaterialExpressionPreSkinnedPosition,-850,360)
    local=expression(mat,unreal.MaterialExpressionVertexInterpolator,-600,360)
    assert mel.connect_material_expressions(vertex_local,'',local,'')
    role_node=expression(mat,unreal.MaterialExpressionScalarParameter,-600,420,parameter_name='SurfaceRole',default_value=role)
    inputs=[]
    for name_in in ['C','P','B','L','Role']:
        inp=unreal.CustomInput(); inp.set_editor_property('input_name',name_in); inputs.append(inp)
    grade=expression(mat,unreal.MaterialExpressionCustom,0,0,inputs=inputs,code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,description='Original palette: controlled grass contrast and foliage midtones')
    for node,out,pin in [(tex,'RGB','C'),(p,'','P'),(bounds,'','B'),(local,'','L'),(role_node,'','Role')]:
        assert mel.connect_material_expressions(node,out,grade,pin)
    assert mel.connect_material_property(grade,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=expression(mat,unreal.MaterialExpressionScalarParameter,0,250,parameter_name='SurfaceRoughness',default_value=roughness)
    assert mel.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat); assert unreal.EditorAssetLibrary.save_loaded_asset(mat)
    REPORT['materials'].append({'material':name,'original_texture':texture,'role':role,'roughness':roughness})
water=unreal.load_asset('/Game/Farm/Art/Mats/M_Water')
water.modify(); mel.delete_all_material_expressions(water)
uv=expression(water,unreal.MaterialExpressionTextureCoordinate,-800,0,u_tiling=6.0,v_tiling=30.0)
pan=expression(water,unreal.MaterialExpressionPanner,-600,0,speed_x=.004,speed_y=.006)
assert mel.connect_material_expressions(uv,'',pan,'Coordinate')
tex=expression(water,unreal.MaterialExpressionTextureSample,-400,0,texture=unreal.load_asset('/Game/Farm/Art/T_Water'))
assert mel.connect_material_expressions(pan,'',tex,'UVs')
inp=unreal.CustomInput(); inp.set_editor_property('input_name','C')
grade=expression(water,unreal.MaterialExpressionCustom,-100,0,inputs=[inp],code='float l=dot(C,float3(.2126,.7152,.0722)); return float3(.065,.245,.30)+(l-.4)*float3(.11,.15,.17);',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,description='Muted original ripple pattern; no white emissive stripes')
assert mel.connect_material_expressions(tex,'RGB',grade,'C')
tint=expression(water,unreal.MaterialExpressionCollectionParameter,-400,250,collection=unreal.load_asset('/Game/Farm/Lighting/MPC_FarmLighting'),parameter_name='WaterTint')
mask=expression(water,unreal.MaterialExpressionComponentMask,-100,250,r=True,g=True,b=True,a=False)
assert mel.connect_material_expressions(tint,'',mask,'')
multiply=expression(water,unreal.MaterialExpressionMultiply,200,0)
assert mel.connect_material_expressions(grade,'',multiply,'A')
assert mel.connect_material_expressions(mask,'',multiply,'B')
assert mel.connect_material_property(multiply,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.recompile_material(water); assert unreal.EditorAssetLibrary.save_loaded_asset(water)
REPORT['water']='Original texture and clock tint retained; corrected 5:1 UV aspect, slow movement and reduced stripe contrast.'
