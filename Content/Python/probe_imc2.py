# -*- coding: utf-8 -*-
import unreal
# find IMC assets
ar = unreal.AssetRegistryHelpers.get_asset_registry()
ar.search_all_assets(True)
assets = ar.get_assets_by_path("/Game/TopDown/Input", recursive=True)
for a in assets:
    unreal.log("ASSET " + str(a.package_name) + " " + str(a.asset_name) + " class=" + str(a.asset_class_path.asset_name))
# try load variants
for p in (
    "/Game/TopDown/Input/IMC_Default",
    "/Game/TopDown/Input/IMC_Default.IMC_Default",
    "/Game/Input/IMC_Default",
):
    obj = unreal.EditorAssetLibrary.load_asset(p)
    unreal.log("load " + p + " -> " + str(obj))
