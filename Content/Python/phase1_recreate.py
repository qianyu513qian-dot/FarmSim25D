# -*- coding: utf-8 -*-
import unreal

GRID = "/Game/Farm/Grid"

def pin(txt):
    p = unreal.EdGraphPinType()
    p.import_text(txt)
    return p

def main():
    unreal.log("recreate start")
    # Delete broken manager
    path = GRID + "/BP_GridManager"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
        unreal.log("deleted old manager")

    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm"):
        unreal.EditorAssetLibrary.make_directory("/Game/Farm")
    if not unreal.EditorAssetLibrary.does_directory_exist(GRID):
        unreal.EditorAssetLibrary.make_directory(GRID)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BP_GridManager", GRID, unreal.Blueprint, factory
    )
    unreal.log("created {}".format(bp))
    unreal.EditorAssetLibrary.save_asset(path)

    # enum ensure
    epath = GRID + "/E_PlotState"
    if not unreal.EditorAssetLibrary.does_asset_exist(epath):
        ef = unreal.EnumFactory()
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "E_PlotState", GRID, unreal.UserDefinedEnum, ef
        )
        unreal.EditorAssetLibrary.save_asset(epath)
        unreal.log("enum created")
    else:
        unreal.log("enum ok")

    # Try ONE variable add
    bel = unreal.BlueprintEditorLibrary
    try:
        ok = bel.add_member_variable(bp, "CellSize", pin('(PinCategory="real",PinSubCategory="")'))
        unreal.log("CellSize -> {}".format(ok))
    except Exception as e:
        unreal.log_error("CellSize exception " + str(e))

    unreal.EditorAssetLibrary.save_asset(path)
    unreal.log("recreate done")

if __name__ == "__main__":
    main()
