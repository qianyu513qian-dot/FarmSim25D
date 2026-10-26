# -*- coding: utf-8 -*-
import unreal
for name in dir(unreal):
    if "InputAction" in name or "Factory" in name and "Input" in name:
        unreal.log(name)
# Also duplicate IA_Interact
src = "/Game/TopDown/Input/Actions/IA_Interact"
dst_dir = "/Game/TopDown/Input/Actions"
if unreal.EditorAssetLibrary.does_asset_exist(src):
    ia = unreal.EditorAssetLibrary.load_asset(src)
    unreal.log("IA_Interact class=" + str(ia.get_class()))
    unreal.log("value_type=" + str(ia.get_editor_property("value_type")))
# Try AssetTools duplicate
if not unreal.EditorAssetLibrary.does_asset_exist(dst_dir + "/IA_Plant"):
    ok = unreal.EditorAssetLibrary.duplicate_asset("IA_Plant", dst_dir, src)
    unreal.log("duplicate -> " + str(ok))
    unreal.EditorAssetLibrary.save_asset(dst_dir + "/IA_Plant")
else:
    unreal.log("IA_Plant already exists")
