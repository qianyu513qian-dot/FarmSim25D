"""Remove only temporary FBX imports after the saved resources pass verification."""
import unreal
assert not unreal.EditorLevelLibrary.get_game_world()
root='/Game/Farm/Art/VegetationBuild/'
allowed={'Tree_Broadleaf','Tree_Tall','Flower_White','Flower_Yellow','FlowerPatch_White','FlowerPatch_Yellow','Shrub_Low','Shrub_Tall','Bush'}
REPORT={'removed':[]}
for path in unreal.EditorAssetLibrary.list_assets(root):
    assert path.startswith(root) and path[len(root):].split('/')[0] in allowed,path
    assert unreal.EditorAssetLibrary.delete_asset(path),path
    REPORT['removed'].append(path)
