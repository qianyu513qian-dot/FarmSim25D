# -*- coding: utf-8 -*-
"""SAFE: only restore IMC E->IA_Interact and F->IA_Plant. No blueprint graph edits."""
import unreal

IMC = "/Game/TopDown/Input/IMC_Default"
IA_INTERACT = "/Game/TopDown/Input/Actions/IA_Interact"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"
IA_WATER = "/Game/TopDown/Input/Actions/IA_Water"


def map_key(imc, ia, key_name):
    k = unreal.Key()
    k.import_text(key_name)
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception as ex:
        unreal.log_warning("unmap {}: {}".format(key_name, ex))
    m = imc.map_key(ia, k)
    unreal.log("map {} -> action={} key={}".format(
        key_name,
        m.get_editor_property("action"),
        m.get_editor_property("key").export_text(),
    ))
    return m


def main():
    unreal.log("=== fix_ef_keys start ===")
    for path in (IMC, IA_INTERACT, IA_PLANT):
        ok = unreal.EditorAssetLibrary.does_asset_exist(path)
        unreal.log("exists {} = {}".format(path, ok))
        if not ok:
            unreal.log_error("MISSING " + path)
            return

    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    ia_i = unreal.EditorAssetLibrary.load_asset(IA_INTERACT)
    ia_p = unreal.EditorAssetLibrary.load_asset(IA_PLANT)

    map_key(imc, ia_i, "E")
    map_key(imc, ia_p, "F")

    # Keep Water mapped if asset exists, but do not create wiring
    if unreal.EditorAssetLibrary.does_asset_exist(IA_WATER):
        ia_w = unreal.EditorAssetLibrary.load_asset(IA_WATER)
        map_key(imc, ia_w, "R")
        unreal.log("IA_Water kept on R (no character wiring expected)")

    saved = unreal.EditorAssetLibrary.save_asset(IMC)
    unreal.log("save IMC: " + str(saved))

    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("IMC dump has Key=E:{} Key=F:{} Key=R:{} IA_Interact:{} IA_Plant:{} IA_Water:{}".format(
        "Key=E" in txt or "E)" in txt,
        "Key=F" in txt or "F)" in txt,
        "Key=R" in txt or "R)" in txt,
        "IA_Interact" in txt,
        "IA_Plant" in txt,
        "IA_Water" in txt,
    ))
    unreal.log("IMC export snippet: " + txt[:800])
    unreal.log("=== fix_ef_keys done ===")


if __name__ == "__main__":
    main()
