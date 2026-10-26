# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
DAY_LENGTH = 75.0

def log(m):
    unreal.log("[DAY_A] " + str(m)); print("[DAY_A] " + str(m))

def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p

def var_names(bp):
    return [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]

bp = unreal.load_asset(MGR)
try:
    t = bel.get_member_variable_type(bp, "CellSize")
    log("CellSize type=" + str(t))
    try:
        log("export=" + t.export_text())
    except Exception as e:
        log("export err " + str(e))
except Exception as e:
    log("get type " + str(e))

names = var_names(bp)
log("have=" + str([v for v in names if v in ("CurrentDay","TimeOfDay","DayLengthSeconds","SunActor","SkyLightActor","CellSize")]))

# UE5.8: real MUST have subcategory float or double (empty crashes)
specs = [
    ("CurrentDay", '(PinCategory="int",PinSubCategory="")'),
    ("TimeOfDay", '(PinCategory="real",PinSubCategory="double")'),
    ("DayLengthSeconds", '(PinCategory="real",PinSubCategory="double")'),
    ("SunActor", '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")'),
    ("SkyLightActor", '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")'),
]
for name, pin in specs:
    if name in names:
        log("exists " + name)
        continue
    ok = bel.add_member_variable(bp, name, make_pin(pin))
    log("add {} -> {}".format(name, ok))

unreal.EditorAssetLibrary.save_asset(MGR)
try:
    cdo = unreal.get_default_object(bp.generated_class())
    for prop, val in (("CurrentDay", 1), ("TimeOfDay", 0.25), ("DayLengthSeconds", DAY_LENGTH)):
        try:
            cdo.set_editor_property(prop, val)
            log("CDO.{}={}".format(prop, cdo.get_editor_property(prop)))
        except Exception as e:
            log("CDO {} {}".format(prop, e))
except Exception as e:
    log("CDO " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE " + str([v for v in var_names(bp) if v in ("CurrentDay","TimeOfDay","DayLengthSeconds","SunActor","SkyLightActor")]))