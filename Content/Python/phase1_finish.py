# -*- coding: utf-8 -*-
"""Phase1 finish: enum names + GridManager variables via EdGraphPinType.import_text."""
import unreal

GRID_DIR = "/Game/Farm/Grid"
ENUM_PATH = GRID_DIR + "/E_PlotState"
MGR_PATH = GRID_DIR + "/BP_GridManager"


def make_pin(category, sub="", sub_object_path=None):
    p = unreal.EdGraphPinType()
    if sub_object_path:
        text = '(PinCategory="{}",PinSubCategory="{}",PinSubCategoryObject="{}")'.format(
            category, sub, sub_object_path
        )
    else:
        text = '(PinCategory="{}",PinSubCategory="{}")'.format(category, sub)
    p.import_text(text)
    return p


def ensure_enum():
    if not unreal.EditorAssetLibrary.does_asset_exist(ENUM_PATH):
        factory = unreal.EnumFactory()
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        tools.create_asset("E_PlotState", GRID_DIR, unreal.UserDefinedEnum, factory)
    e = unreal.EditorAssetLibrary.load_asset(ENUM_PATH)
    names = ["Empty", "Tilled", "Seeded", "Growing", "Mature"]
    lib = getattr(unreal, "EnumEditorLibrary", None)
    if lib:
        # Ensure 5 entries
        for i in range(len(names)):
            try:
                if hasattr(lib, "add_enumerator") and i > 0:
                    lib.add_enumerator(e)
            except Exception as ex:
                unreal.log_warning("add_enumerator {}: {}".format(i, ex))
        for i, n in enumerate(names):
            for meth in ("set_enumerator_user_facing_name", "set_enumerator_display_name"):
                if hasattr(lib, meth):
                    try:
                        getattr(lib, meth)(e, i, unreal.Text(n))
                        unreal.log("enum[{}]={}".format(i, n))
                        break
                    except Exception as ex:
                        unreal.log_warning("{}: {}".format(meth, ex))
    unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
    return e


def ensure_manager_vars():
    if not unreal.EditorAssetLibrary.does_asset_exist(MGR_PATH):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.Actor)
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BP_GridManager", GRID_DIR, unreal.Blueprint, factory
        )
    bp = unreal.EditorAssetLibrary.load_asset(MGR_PATH)
    bel = unreal.BlueprintEditorLibrary

    # Remove TestBool if present
    try:
        if hasattr(bel, "remove_member_variable"):
            bel.remove_member_variable(bp, "TestBool")
            unreal.log("removed TestBool")
    except Exception as ex:
        unreal.log_warning("remove TestBool: {}".format(ex))

    # float = real in UE pin types; int = int; vector = struct + Vector
    specs = [
        ("CellSize", make_pin("real")),
        ("GridWidth", make_pin("int")),
        ("GridHeight", make_pin("int")),
        ("GridOrigin", make_pin("struct", "", "/Script/CoreUObject.Vector")),
    ]
    for name, pin in specs:
        try:
            ok = bel.add_member_variable(bp, name, pin)
            unreal.log("add {} -> {}".format(name, ok))
        except Exception as ex:
            unreal.log_warning("add {} fail: {}".format(name, ex))

    # Mark instance editable if API exists
    try:
        # compile first so variables exist
        bel.compile_blueprint(bp)
    except Exception as ex:
        unreal.log_warning("compile: {}".format(ex))

    # Set defaults via CDO if possible
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        cdo.set_editor_property("cell_size", 100.0)
        cdo.set_editor_property("grid_width", 20)
        cdo.set_editor_property("grid_height", 20)
        cdo.set_editor_property("grid_origin", unreal.Vector(0, 0, 0))
        unreal.log("defaults set on CDO")
    except Exception as ex:
        unreal.log_warning("CDO defaults: {}".format(ex))

    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(MGR_PATH)
    unreal.log("manager saved")


def main():
    unreal.log("=== phase1_finish start ===")
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm"):
        unreal.EditorAssetLibrary.make_directory("/Game/Farm")
    if not unreal.EditorAssetLibrary.does_directory_exist(GRID_DIR):
        unreal.EditorAssetLibrary.make_directory(GRID_DIR)
    ensure_enum()
    ensure_manager_vars()
    unreal.log("=== phase1_finish done ===")


if __name__ == "__main__":
    main()
