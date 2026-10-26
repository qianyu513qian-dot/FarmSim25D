# -*- coding: utf-8 -*-
"""Phase1 bootstrap: E_PlotState + BP_GridManager variables. Run with UnrealEditor-Cmd -ExecutePythonScript."""
import unreal

GRID_DIR = "/Game/Farm/Grid"
ENUM_NAME = "E_PlotState"
MGR_NAME = "BP_GridManager"
ENUM_PATH = GRID_DIR + "/" + ENUM_NAME
MGR_PATH = GRID_DIR + "/" + MGR_NAME


def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        unreal.log("mkdir " + path)


def create_or_get_enum():
    ensure_dir("/Game/Farm")
    ensure_dir(GRID_DIR)
    if unreal.EditorAssetLibrary.does_asset_exist(ENUM_PATH):
        unreal.log("enum exists")
        return unreal.EditorAssetLibrary.load_asset(ENUM_PATH)

    factory = unreal.EnumFactory()
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    enum_asset = tools.create_asset(ENUM_NAME, GRID_DIR, unreal.UserDefinedEnum, factory)
    if not enum_asset:
        unreal.log_error("create enum failed")
        return None

    names = ["Empty", "Tilled", "Seeded", "Growing", "Mature"]
    # Try several UE5 APIs to set enumerator display names
    ok = False
    try:
        # Preferred in newer UE: set_enums with list of names
        display_names = unreal.Array(unreal.Text)
        for n in names:
            display_names.append(unreal.Text(n))
        # Some builds expose set_enums on UserDefinedEnum via editor lib
        if hasattr(unreal, "UserDefinedEnumLibrary"):
            unreal.UserDefinedEnumLibrary.set_display_names(enum_asset, display_names)
            ok = True
    except Exception as e:
        unreal.log_warning("UserDefinedEnumLibrary: {}".format(e))

    if not ok and hasattr(unreal, "EnumEditorLibrary"):
        try:
            lib = unreal.EnumEditorLibrary
            # Ensure enough enumerators
            for i in range(len(names)):
                try:
                    # add if missing
                    if i > 0:
                        if hasattr(lib, "add_enumerator"):
                            lib.add_enumerator(enum_asset)
                        elif hasattr(lib, "insert_enumerator"):
                            lib.insert_enumerator(enum_asset, i)
                except Exception:
                    pass
            for i, n in enumerate(names):
                try:
                    if hasattr(lib, "set_enumerator_user_facing_name"):
                        lib.set_enumerator_user_facing_name(enum_asset, i, unreal.Text(n))
                    elif hasattr(lib, "set_enumerator_display_name"):
                        lib.set_enumerator_display_name(enum_asset, i, unreal.Text(n))
                    elif hasattr(lib, "set_enumerator_display_name_string"):
                        lib.set_enumerator_display_name_string(enum_asset, i, n)
                except Exception as e2:
                    unreal.log_warning("rename enum {}: {}".format(i, e2))
            ok = True
        except Exception as e:
            unreal.log_warning("EnumEditorLibrary: {}".format(e))

    unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
    unreal.log("enum saved ok={}".format(ok))
    return enum_asset


def create_or_get_manager_bp():
    if unreal.EditorAssetLibrary.does_asset_exist(MGR_PATH):
        unreal.log("manager exists")
        return unreal.EditorAssetLibrary.load_asset(MGR_PATH)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    bp = tools.create_asset(MGR_NAME, GRID_DIR, unreal.Blueprint, factory)
    if not bp:
        unreal.log_error("create BP_GridManager failed")
        return None
    unreal.EditorAssetLibrary.save_asset(MGR_PATH)
    unreal.log("manager created")
    return bp


def add_member_vars(bp):
    bel = unreal.BlueprintEditorLibrary
    # Signature differs by engine version; try common forms
    specs = [
        ("CellSize", "float", None),
        ("GridWidth", "int", None),
        ("GridHeight", "int", None),
        ("GridOrigin", "struct", "Vector"),
    ]
    for name, cat, sub in specs:
        added = False
        # try string type name
        for type_name in ([cat] if not sub else [sub, "Vector", cat]):
            try:
                result = bel.add_member_variable(bp, name, type_name)
                unreal.log("add {} as {} -> {}".format(name, type_name, result))
                added = bool(result)
                if added:
                    break
            except Exception as e:
                unreal.log_warning("add {} {}: {}".format(name, type_name, e))
        if not added:
            try:
                pin = unreal.EdGraphPinType()
                pin.set_editor_property("pin_category", unreal.Name(cat))
                if sub:
                    pin.set_editor_property("pin_sub_category", unreal.Name(sub))
                    # Vector is struct
                    if cat == "struct":
                        try:
                            pin.set_editor_property(
                                "pin_sub_category_object",
                                unreal.Vector.static_struct() if hasattr(unreal.Vector, "static_struct") else None,
                            )
                        except Exception:
                            try:
                                pin.set_editor_property("pin_sub_category_object", unreal.find_object(None, "/Script/CoreUObject.Vector"))
                            except Exception as e3:
                                unreal.log_warning("vector struct: {}".format(e3))
                result = bel.add_member_variable(bp, name, pin)
                unreal.log("add {} via pin -> {}".format(name, result))
            except Exception as e:
                unreal.log_warning("pin add {}: {}".format(name, e))

    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        unreal.log_warning("compile: {}".format(e))
    unreal.EditorAssetLibrary.save_asset(MGR_PATH)


def main():
    unreal.log("=== phase1_create_grid start ===")
    create_or_get_enum()
    bp = create_or_get_manager_bp()
    if bp:
        add_member_vars(bp)
    unreal.EditorAssetLibrary.save_directory(GRID_DIR, False, True)
    unreal.log("=== phase1_create_grid done ===")
    # List results
    assets = unreal.EditorAssetLibrary.list_assets(GRID_DIR, True, False)
    for a in assets:
        unreal.log("asset: " + a)


if __name__ == "__main__":
    main()
