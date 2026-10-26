# -*- coding: utf-8 -*-
"""Ensure E_PlotState has Empty/Tilled/Planted by recreating asset (same path)."""
import unreal

ENUM_PATH = "/Game/Farm/Grid/E_PlotState"
GRID_DIR = "/Game/Farm/Grid"
NAMES = ["Empty", "Tilled", "Planted", "Watered", "Grown"]


def try_set_names(enum_asset, names):
    ok = False
    # Method A: UserDefinedEnumLibrary
    if hasattr(unreal, "UserDefinedEnumLibrary"):
        try:
            display_names = unreal.Array(unreal.Text)
            for n in names:
                display_names.append(unreal.Text(n))
            unreal.UserDefinedEnumLibrary.set_display_names(enum_asset, display_names)
            unreal.log("set_display_names ok")
            return True
        except Exception as ex:
            unreal.log_warning("UDELib: " + str(ex))

    # Method B: EnumEditorLibrary
    if hasattr(unreal, "EnumEditorLibrary"):
        try:
            lib = unreal.EnumEditorLibrary
            for i, n in enumerate(names):
                if i > 0:
                    for addm in ("add_enumerator", "insert_enumerator"):
                        if hasattr(lib, addm):
                            try:
                                if addm == "insert_enumerator":
                                    getattr(lib, addm)(enum_asset, i)
                                else:
                                    getattr(lib, addm)(enum_asset)
                            except Exception:
                                pass
                for setm in ("set_enumerator_user_facing_name", "set_enumerator_display_name",
                             "set_enumerator_display_name_string"):
                    if hasattr(lib, setm):
                        try:
                            if "string" in setm:
                                getattr(lib, setm)(enum_asset, i, n)
                            else:
                                getattr(lib, setm)(enum_asset, i, unreal.Text(n))
                            unreal.log("set name {} via {}".format(n, setm))
                            ok = True
                            break
                        except Exception as ex:
                            unreal.log_warning("{}: {}".format(setm, ex))
            return ok
        except Exception as ex:
            unreal.log_warning("EnumEditorLibrary: " + str(ex))

    # Method C: direct property / rename NewEnumerator
    try:
        # Some UE builds: enum_asset.set_enums
        if hasattr(enum_asset, "set_enums"):
            enum_asset.set_enums(names)
            unreal.log("set_enums ok")
            return True
    except Exception as ex:
        unreal.log_warning("set_enums: " + str(ex))

    # Method D: use AssetImport / factory with initial
    return False


def main():
    unreal.log("=== phase3_enum_fix start ===")
    # Delete and recreate
    if unreal.EditorAssetLibrary.does_asset_exist(ENUM_PATH):
        # Don't delete if referenced - instead try duplicate+replace
        # First try set names on existing
        en = unreal.EditorAssetLibrary.load_asset(ENUM_PATH)
        if try_set_names(en, NAMES):
            unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
            unreal.log("updated existing enum")
        else:
            unreal.log("could not set names on existing - recreate")
            # Backup: delete and create fresh
            try:
                unreal.EditorAssetLibrary.delete_asset(ENUM_PATH)
                unreal.log("deleted old enum")
            except Exception as ex:
                unreal.log_warning("delete: " + str(ex))
            factory = unreal.EnumFactory()
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            en = tools.create_asset("E_PlotState", GRID_DIR, unreal.UserDefinedEnum, factory)
            unreal.log("created " + str(en))
            try_set_names(en, NAMES)
            unreal.EditorAssetLibrary.save_asset(ENUM_PATH)

    # Verify via Equal pin experiments after soft compile of mgr
    bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
    try:
        bel = unreal.BlueprintEditorLibrary
        bel.compile_blueprint(bp)
        unreal.log("mgr compile after enum")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))

    # Dump uasset-ish via python: create EnumEquality node and list options - skip
    # Fix BeginPlay NewItem and LitTilled via numeric after enum rebuild
    bel = unreal.BlueprintEditorLibrary
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "Add":
            item = None
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) in ("NewItem", "New Item"):
                    item = p
            if item:
                for cand in ("Empty", "NewEnumerator0", "0"):
                    try:
                        item.set_pin_value(cand)
                        unreal.log("BeginPlay Add NewItem set {!r} -> {!r}".format(cand, item.get_pin_value()))
                        if str(item.get_pin_value()) not in ("", "E_PlotState_MAX", "None"):
                            break
                    except Exception as ex:
                        unreal.log_warning(str(ex))

    tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    try:
        tge.set_local_variable_default_value("LitTilled", "1")
        unreal.log("LitTilled=" + str(tge.get_local_variable_default_value("LitTilled")))
        tge.set_local_variable_default_value("LitTilled", "Tilled")
        unreal.log("LitTilled=" + str(tge.get_local_variable_default_value("LitTilled")))
        tge.set_local_variable_default_value("LitEmpty", "0")
        unreal.log("LitEmpty=" + str(tge.get_local_variable_default_value("LitEmpty")))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Break LitTilled->Item and set Item=1
    for n in tge.list_all_nodes():
        if "Set Array" in bel.get_node_title(n):
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "Item":
                    try:
                        p.break_pin_links()
                    except Exception:
                        pass
                    for cand in ("1", "Tilled", "NewEnumerator1"):
                        try:
                            p.set_pin_value(cand)
                            unreal.log("Till Set.Item {!r} -> {!r}".format(cand, p.get_pin_value()))
                        except Exception as ex:
                            unreal.log_warning(str(ex))
                    # Prefer numeric 1
                    try:
                        p.set_pin_value("1")
                        unreal.log("final Till Item=" + str(p.get_pin_value()))
                    except Exception:
                        pass

    # Equal.B ensure 0
    for n in tge.list_all_nodes():
        if "equal" in bel.get_node_title(n).lower():
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "B":
                    p.set_pin_value("0")
                    unreal.log("Equal.B=" + str(p.get_pin_value()))

    try:
        bel.compile_blueprint(bp)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset("/Game/Farm/Grid/BP_GridManager")
    unreal.EditorAssetLibrary.save_asset(ENUM_PATH)
    unreal.log("=== phase3_enum_fix done ===")


if __name__ == "__main__":
    main()
