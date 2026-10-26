# -*- coding: utf-8 -*-
import unreal
en = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
# EnumEditorLibrary methods
if hasattr(unreal, "EnumEditorLibrary"):
    lib = unreal.EnumEditorLibrary
    unreal.log("EnumEditorLibrary methods:")
    for m in dir(lib):
        if not m.startswith("_"):
            unreal.log("  " + m)
else:
    unreal.log("NO EnumEditorLibrary")
# Try KismetSystemLibrary / Blueprint enums
for name in dir(unreal):
    if "Enum" in name:
        unreal.log("unreal." + name)
# NumEnums via generated header style - try get_editor_property on all
try:
    # FEnumEditorUtils style through python
    from unreal import UserDefinedEnum
    unreal.log("UDE ok")
except Exception as ex:
    unreal.log_warning(str(ex))

# Try AssetRegistry tags
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    data = ar.get_asset_by_object_path("/Game/Farm/Grid/E_PlotState.E_PlotState")
    unreal.log("asset_data=" + str(data))
    if data:
        tags = data.get_tag_value_names() if hasattr(data, "get_tag_value_names") else None
        unreal.log("tags=" + str(tags))
except Exception as ex:
    unreal.log_warning(str(ex))
