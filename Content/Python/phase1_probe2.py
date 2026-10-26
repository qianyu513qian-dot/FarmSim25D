# -*- coding: utf-8 -*-
import unreal

pin = unreal.EdGraphPinType()
try:
    unreal.log("export: " + str(pin.export_text()))
except Exception as e:
    unreal.log("export fail " + str(e))

# Inspect add_member_variable __doc__ / annotations
fn = unreal.BlueprintEditorLibrary.add_member_variable
unreal.log("doc=" + str(getattr(fn, "__doc__", None)))
unreal.log("text=" + str(fn))

# Try to read pin type from TopDown character if any new variables - or from engine BP
# Create float pin via import_text common format
samples = [
    "(PinCategory=\"bool\")",
    "(PinCategory=bool)",
    "(PinCategory=\"real\",PinSubCategory=\"\")",
    "(PinCategory=\"float\")",
]
for s in samples:
    p = unreal.EdGraphPinType()
    try:
        p.import_text(s)
        unreal.log("import OK " + s + " -> " + str(p.export_text()))
        bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
        try:
            r = unreal.BlueprintEditorLibrary.add_member_variable(bp, "TestBool", p)
            unreal.log("add TestBool -> " + str(r))
        except Exception as e2:
            unreal.log("add with imported pin fail: " + str(e2))
    except Exception as e:
        unreal.log("import fail " + s + " : " + str(e))

# Enum details
e = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
unreal.log("enum class=" + e.get_class().get_name())
for prop in ["Names", "DisplayNameMap", "EnumDisplayNameFn"]:
    try:
        unreal.log(prop + "=" + str(e.get_editor_property(prop)))
    except Exception as ex:
        unreal.log(prop + " err " + str(ex))
# EnumEditorLibrary methods
if hasattr(unreal, "EnumEditorLibrary"):
    lib = unreal.EnumEditorLibrary
    unreal.log("EnumEditorLibrary funcs: " + ",".join([x for x in dir(lib) if not x.startswith("_")][:40]))
