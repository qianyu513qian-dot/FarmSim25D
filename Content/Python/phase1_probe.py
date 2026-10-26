# -*- coding: utf-8 -*-
import unreal

# Probe AddMemberVariable + EdGraphPinType fields
bel = unreal.BlueprintEditorLibrary
help_add = None
try:
    # print docs
    unreal.log(str(bel.add_member_variable))
except Exception as e:
    unreal.log(str(e))

pin = unreal.EdGraphPinType()
props = []
for p in dir(pin):
    if p.startswith("_"):
        continue
    props.append(p)
unreal.log("EdGraphPinType members: " + ",".join(props[:80]))

# Try property names used in UE5
for name in ["pin_category", "PinCategory", "pin_sub_category", "PinSubCategory", "pin_sub_category_object", "PinSubCategoryObject"]:
    try:
        pin.get_editor_property(name)
        unreal.log("HAS get " + name)
    except Exception as e:
        unreal.log("NO get {}: {}".format(name, e))

# Create pin type for float the documented way
try:
    pt = unreal.EdGraphPinType()
    pt.pin_category = "real"
    unreal.log("setattr pin_category real ok")
except Exception as e:
    unreal.log("setattr fail: {}".format(e))

try:
    pt = unreal.EdGraphPinType(pin_category="real")
    unreal.log("ctor ok")
except Exception as e:
    unreal.log("ctor fail: {}".format(e))

# Inspect existing assets
for path in ["/Game/Farm/Grid/E_PlotState", "/Game/Farm/Grid/BP_GridManager"]:
    a = unreal.EditorAssetLibrary.load_asset(path)
    unreal.log("{} -> {}".format(path, a))
    if isinstance(a, unreal.UserDefinedEnum) or a.__class__.__name__.find("Enum") >= 0:
        try:
            unreal.log("enum num={}".format(a.get_editor_property("Names") if False else "n/a"))
        except Exception:
            pass
        try:
            # list display names
            for i in range(0, 16):
                try:
                    dn = unreal.EnumEditorLibrary.get_enumerator_user_facing_name(a, i)
                    unreal.log("enum[{}]={}".format(i, dn))
                except Exception:
                    break
        except Exception as e:
            unreal.log("enum list: {}".format(e))
    if isinstance(a, unreal.Blueprint):
        try:
            vars = bel.get_new_variables(a) if hasattr(bel, "get_new_variables") else None
            unreal.log("vars={}".format(vars))
        except Exception as e:
            unreal.log("get vars: {}".format(e))
