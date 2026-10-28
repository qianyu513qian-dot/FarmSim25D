"""Read-only geometry tooling and vegetation asset inspection."""
import unreal
REPORT={'geometry_tools':[n for n in dir(unreal) if n.startswith('GeometryScript_')],
        'dirty_content':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
        'dirty_maps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        'assets':[]}
for suffix in ['Tree_Broadleaf','Tree_Tall','Flower_White','Flower_Yellow','FlowerPatch_White','FlowerPatch_Yellow']:
    m=unreal.load_asset('/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature/SM_VMF_Nature_'+suffix)
    REPORT['assets'].append({'name':suffix,'bounds':str(m.get_bounding_box()),'body_setup':str(m.get_editor_property('body_setup'))})
