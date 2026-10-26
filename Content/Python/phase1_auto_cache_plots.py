# -*- coding: utf-8 -*-
"""Auto: PlotStates array on GridManager + GridManagerRef on character (variables).
Graph wiring for BeginPlay/Tick is best-effort; logs what it could do.
"""
import unreal

MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
bel = unreal.BlueprintEditorLibrary


def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p


def ensure_var(bp, name, pin_text):
    try:
        ok = bel.add_member_variable(bp, name, make_pin(pin_text))
        unreal.log("add_member_variable {} -> {}".format(name, ok))
        return ok
    except Exception as ex:
        unreal.log_warning("add {} : {}".format(name, ex))
        return False


def main():
    unreal.log("=== phase1_auto_cache_plots start ===")

    # PlotStates: array of E_PlotState on GridManager
    mgr = unreal.EditorAssetLibrary.load_asset(MGR)
    if not mgr:
        unreal.log_error("missing " + MGR)
        return
    enum_path = ENUM + ".E_PlotState"
    # byte/enum array pin
    pin = (
        '(PinCategory="byte",PinSubCategory="",PinSubCategoryObject="' + ENUM + '.E_PlotState",'
        'ContainerType=Array)'
    )
    # Try alternate container syntax if needed
    ensure_var(mgr, "PlotStates", pin)
    try:
        bel.compile_blueprint(mgr)
    except Exception as ex:
        unreal.log_warning("compile mgr: {}".format(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)

    # GridManagerRef on character
    ch = unreal.EditorAssetLibrary.load_asset(CHAR)
    if not ch:
        unreal.log_error("missing " + CHAR)
        return
    pin_obj = (
        '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="' + MGR + '.BP_GridManager_C")'
    )
    ensure_var(ch, "GridManagerRef", pin_obj)
    try:
        bel.compile_blueprint(ch)
    except Exception as ex:
        unreal.log_warning("compile char: {}".format(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)

    unreal.log("=== phase1_auto_cache_plots done ===")
    unreal.log("NOTE: BeginPlay Set + Tick Get still need graph (or next script). Variables created.")


if __name__ == "__main__":
    main()