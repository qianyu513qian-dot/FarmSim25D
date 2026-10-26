# -*- coding: utf-8 -*-
import unreal

IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"
ACTIONS_DIR = "/Game/TopDown/Input/Actions"
IMC = "/Game/TopDown/Input/IMC_Default"
SRC = "/Game/TopDown/Input/Actions/IA_Interact"


def main():
    unreal.log("=== phase3_mk_ia2 ===")
    if unreal.EditorAssetLibrary.does_asset_exist(IA_PLANT):
        ia = unreal.EditorAssetLibrary.load_asset(IA_PLANT)
        unreal.log("exists")
    else:
        # Try duplicate
        try:
            ok = unreal.EditorAssetLibrary.duplicate_asset(SRC, IA_PLANT)
            unreal.log("duplicate_asset -> " + str(ok))
        except Exception as ex:
            unreal.log_warning("dup1: " + str(ex))
        if not unreal.EditorAssetLibrary.does_asset_exist(IA_PLANT):
            try:
                tools = unreal.AssetToolsHelpers.get_asset_tools()
                ok = tools.duplicate_asset("IA_Plant", ACTIONS_DIR, unreal.EditorAssetLibrary.load_asset(SRC))
                unreal.log("tools.duplicate -> " + str(ok))
            except Exception as ex:
                unreal.log_warning("dup2: " + str(ex))
        if not unreal.EditorAssetLibrary.does_asset_exist(IA_PLANT):
            factory = unreal.InputAction_Factory()
            tools = unreal.AssetToolsHelpers.get_asset_tools()
            ia = tools.create_asset("IA_Plant", ACTIONS_DIR, unreal.InputAction, factory)
            unreal.log("create via InputAction_Factory -> " + str(ia))
        ia = unreal.EditorAssetLibrary.load_asset(IA_PLANT)

    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(IA_PLANT)

    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception as ex:
        unreal.log_warning(str(ex))
    for attempt in (
        lambda: imc.map_key(ia, unreal.Key.F),
        lambda: imc.map_key(ia, unreal.Key("F")),
    ):
        try:
            m = attempt()
            unreal.log("mapped F -> " + str(m))
            break
        except Exception as ex:
            unreal.log_warning(str(ex))
    else:
        k = unreal.Key()
        k.set_editor_property("key_name", "F")
        m = imc.map_key(ia, k)
        unreal.log("mapped Key name F -> " + str(m))
    unreal.EditorAssetLibrary.save_asset(IMC)
    unreal.log("IMC mappings=" + str(imc.get_editor_property("mappings") if False else "saved"))
    # list mappings briefly
    try:
        maps = imc.get_editor_property("mappings")
        unreal.log("num mappings=" + str(len(list(maps))))
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.log("=== done ===")


if __name__ == "__main__":
    main()
