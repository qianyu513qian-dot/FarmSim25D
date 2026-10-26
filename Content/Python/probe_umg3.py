# -*- coding: utf-8 -*-
import unreal

wbp = unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD")
tree = unreal.load_object(wbp, "WidgetTree")
print("[T]", [x for x in dir(tree) if not x.startswith("__")])
print("[TDOC]", type(tree))
# try call_method
for name in ("ConstructWidget", "construct_widget", "CreateWidget", "SetRootWidget", "set_root_widget",
             "FindWidget", "find_widget", "RemoveWidget", "GetAllWidgets"):
    print(name, hasattr(tree, name), hasattr(unreal.WidgetTree, name))

# WidgetBlueprintLibrary
print("WBL", [x for x in dir(unreal.WidgetBlueprintLibrary) if "Create" in x or "text" in x.lower()][:30])
# Editor libraries
print("ed umg", [x for x in dir(unreal) if "umg" in x.lower() or "WidgetEditor" in x or "Designer" in x][:40])

# Try creating TextBlock as package outer under tree
try:
    tb = unreal.TextBlock(outer=tree, name="TxtMoney")
    print("TextBlock create", tb)
except Exception as e:
    print("TB create", e)

# try new_object
try:
    tb = unreal.new_object(unreal.TextBlock, outer=tree, name="TxtMoney")
    print("new_object", tb)
except Exception as e:
    print("new_object", e)

# BaseWidgetBlueprint methods
print("BaseWBP", [x for x in dir(unreal.BaseWidgetBlueprint) if not x.startswith("_")][:40])
print("WBP methods", [x for x in dir(wbp) if not x.startswith("_") and ("widget" in x.lower() or "tree" in x.lower() or "bind" in x.lower())])
