# -*- coding: utf-8 -*-
import unreal

MGR = "/Game/Farm/Grid/BP_GridManager"

def pin(txt):
    p = unreal.EdGraphPinType()
    p.import_text(txt)
    return p

def main():
    unreal.log("vars2 start")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    bel = unreal.BlueprintEditorLibrary
    for name, txt in [
        ("CellSize", '(PinCategory="real",PinSubCategory="")'),
        ("GridWidth", '(PinCategory="int",PinSubCategory="")'),
        ("GridHeight", '(PinCategory="int",PinSubCategory="")'),
    ]:
        try:
            unreal.log("trying " + name)
            ok = bel.add_member_variable(bp, name, pin(txt))
            unreal.log("{} -> {}".format(name, ok))
        except Exception as e:
            unreal.log_error("{} err {}".format(name, e))
    # try vector separately
    try:
        unreal.log("trying GridOrigin")
        ok = bel.add_member_variable(
            bp,
            "GridOrigin",
            pin('(PinCategory="struct",PinSubCategory="",PinSubCategoryObject="/Script/CoreUObject.Vector")'),
        )
        unreal.log("GridOrigin -> {}".format(ok))
    except Exception as e:
        unreal.log_error("GridOrigin err {}".format(e))
    saved = unreal.EditorAssetLibrary.save_asset(MGR, only_if_is_dirty=False)
    unreal.log("saved={}".format(saved))
    unreal.log("vars2 done")

if __name__ == "__main__":
    main()
