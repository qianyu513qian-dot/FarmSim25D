# -*- coding: utf-8 -*-
import unreal

GRID = "/Game/Farm/Grid"
PATH = GRID + "/BP_GridManager"

def pin(txt):
    p = unreal.EdGraphPinType()
    p.import_text(txt)
    return p

def main():
    unreal.log("hardmk start")
    for d in ["/Game/Farm", GRID]:
        if not unreal.EditorAssetLibrary.does_directory_exist(d):
            unreal.EditorAssetLibrary.make_directory(d)

    # sync delete if still registered
    if unreal.EditorAssetLibrary.does_asset_exist(PATH):
        unreal.EditorAssetLibrary.delete_asset(PATH)
        unreal.log("registry delete")

    actor_cls = unreal.load_class(None, "/Script/Engine.Actor")
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", actor_cls)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BP_GridManager", GRID, unreal.Blueprint, factory
    )
    unreal.log("bp={}".format(bp))
    if not bp:
        return
    unreal.EditorAssetLibrary.save_asset(PATH)

    bel = unreal.BlueprintEditorLibrary
    for name, txt in [
        ("CellSize", '(PinCategory="real",PinSubCategory="")'),
        ("GridWidth", '(PinCategory="int",PinSubCategory="")'),
        ("GridHeight", '(PinCategory="int",PinSubCategory="")'),
        ("GridOrigin", '(PinCategory="struct",PinSubCategory="",PinSubCategoryObject="/Script/CoreUObject.Vector")'),
    ]:
        ok = bel.add_member_variable(bp, name, pin(txt))
        unreal.log("{} -> {}".format(name, ok))

    unreal.EditorAssetLibrary.save_asset(PATH)
    unreal.log("hardmk done")

if __name__ == "__main__":
    main()
