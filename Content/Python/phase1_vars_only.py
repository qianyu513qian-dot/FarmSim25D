# -*- coding: utf-8 -*-
import unreal

MGR_PATH = "/Game/Farm/Grid/BP_GridManager"
GRID_DIR = "/Game/Farm/Grid"

def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p

def main():
    unreal.log("=== phase1_vars_only start ===")
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm"):
        unreal.EditorAssetLibrary.make_directory("/Game/Farm")
    if not unreal.EditorAssetLibrary.does_directory_exist(GRID_DIR):
        unreal.EditorAssetLibrary.make_directory(GRID_DIR)

    if not unreal.EditorAssetLibrary.does_asset_exist(MGR_PATH):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BP_GridManager", GRID_DIR, unreal.Blueprint, factory
        )
        unreal.EditorAssetLibrary.save_asset(MGR_PATH)

    if not unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Grid/E_PlotState"):
        factory = unreal.EnumFactory()
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "E_PlotState", GRID_DIR, unreal.UserDefinedEnum, factory
        )
        unreal.EditorAssetLibrary.save_asset("/Game/Farm/Grid/E_PlotState")

    bp = unreal.EditorAssetLibrary.load_asset(MGR_PATH)
    bel = unreal.BlueprintEditorLibrary

    pins = {
        "CellSize": '(PinCategory="real",PinSubCategory="")',
        "GridWidth": '(PinCategory="int",PinSubCategory="")',
        "GridHeight": '(PinCategory="int",PinSubCategory="")',
        "GridOrigin": '(PinCategory="struct",PinSubCategory="",PinSubCategoryObject="/Script/CoreUObject.Vector")',
    }
    for name, pin_text in pins.items():
        try:
            ok = bel.add_member_variable(bp, name, make_pin(pin_text))
            unreal.log("add {} -> {}".format(name, ok))
        except Exception as ex:
            unreal.log_warning("add {} : {}".format(name, ex))

    # Save WITHOUT compile to avoid KismetCompiler crash
    unreal.EditorAssetLibrary.save_asset(MGR_PATH)
    unreal.log("=== phase1_vars_only done (no compile) ===")

if __name__ == "__main__":
    main()
