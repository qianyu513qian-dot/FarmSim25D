# -*- coding: utf-8 -*-
"""Find existing root on new WBP; try SubobjectData add WidgetComponent; slot layout props."""
import unreal

def log(m):
    unreal.log("[UI_P6] " + str(m))
    print("[UI_P6] " + str(m))

bel = unreal.BlueprintEditorLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
UI_DIR = "/Game/Farm/UI"

# Fresh empty WBP to see default root
NAME = "WBP_RestProbeRoot"
PATH = UI_DIR + "/" + NAME
if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    unreal.EditorAssetLibrary.delete_asset(PATH)
factory = unreal.WidgetBlueprintFactory()
factory.set_editor_property("parent_class", unreal.UserWidget)
wbp = tools.create_asset(NAME, UI_DIR, unreal.WidgetBlueprint, factory)
tree = unreal.load_object(wbp, "WidgetTree")

# Find all UObject children of tree
log("tree subobjects:")
# iterate package
pkg = wbp.get_package()
for obj in unreal.EditorAssetLibrary.list_assets(PATH, recursive=False) or []:
    log("  assetlist " + str(obj))

# Use find_object for common names
for name in ("Root", "RootCanvas", "CanvasPanel_0", "CanvasPanel", "WidgetTree"):
    o = unreal.find_object(tree, name)
    log("find {} = {}".format(name, o))

# Export text of wbp?
try:
    # iterate outer chain objects via unreal.ObjectIterator? 
    pass
except Exception:
    pass

# Use AssetRegistry / get_objects_with_outer
try:
    objs = unreal.EditorAssetLibrary.find_asset_data(PATH)
    log("assetdata=" + str(objs))
except Exception as e:
    log(str(e))

# Python: get all objects with outer=tree
try:
    import gc
    # unreal has ObjectIterator in some versions
    it = getattr(unreal, "ObjectIterator", None)
    log("ObjectIterator=" + str(it))
    if it:
        for o in it(unreal.Widget):
            if o.get_outer() == tree:
                log("  widget in tree: {} {}".format(o.get_name(), o.get_class().get_name()))
except Exception as e:
    log("iter " + str(e))

# Try UMGWidgetBlueprintInfo from somewhere
# Check WidgetBlueprint methods for get_widget_tree / set_root
log("wbp dirs widgetish=" + str([x for x in dir(wbp) if not x.startswith("_")]))

# CanvasPanelSlot layout - LayoutData
wbp2 = unreal.load_asset("/Game/Farm/UI/WBP_RestOrderList")
tree2 = unreal.load_object(wbp2, "WidgetTree")
canvas = unreal.find_object(tree2, "RootCanvas")
log("existing RootCanvas=" + str(canvas))
if canvas:
    try:
        # get slots
        slots = canvas.get_slots() if hasattr(canvas, "get_slots") else None
        log("slots=" + str(slots))
    except Exception as e:
        log("slots " + str(e))
    # children
    try:
        log("canvas dirs=" + str([x for x in dir(canvas) if "child" in x.lower() or "slot" in x.lower()][:30]))
    except Exception:
        pass

# SubobjectDataSubsystem add WidgetComponent to Table
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
# Need parent handle - usually the DefaultSceneRoot / root component handle
# k2_gather_subobject_data_for_blueprint?
log("sub all=" + str([x for x in dir(sub) if not x.startswith("_")]))

# Try create_new_bp_component
try:
    # create_new_bp_component(component_class, ...) 
    log("create_new_bp_component=" + str(sub.create_new_bp_component))
except Exception as e:
    log(str(e))

# Factory-created WBP - compile and check widget_count via info struct somehow
# Look at Default__ for widget tree on CDO of generated class
try:
    gen = wbp.generated_class()
    cdo = unreal.get_default_object(gen)
    log("cdo=" + str(cdo))
    # WidgetTree on UserWidget?
    for prop in ("WidgetTree", "widget_tree"):
        try:
            log("{}={}".format(prop, cdo.get_editor_property(prop)))
        except Exception as e:
            log("{} {}".format(prop, e))
except Exception as e:
    log("cdo " + str(e))

# CRITICAL: Does factory WBP already have a canvas as RootWidget that we can't read but exists?
# Try adding child via Blueprint graph Event Construct: Create Widget is wrong.
# Alternative: use Native approach - Manager creates widgets at runtime with
# WidgetBlueprintLibrary.create + dynamically? Can't add text without designer root.

# Another approach: use HUD class DrawHUD / AHUD
log("HUD=" + str(getattr(unreal, "HUD", None)))

# Check if we can use set_editor_property with disable_error_handling / force
try:
    # Some UE python have set_editor_property(name, value, notify_change)
    tree.set_editor_property("RootWidget", canvas if canvas else unreal.new_object(unreal.CanvasPanel, tree, "R2"))
except Exception as e:
    log("force set " + str(e))

# Try unreal.SystemLibrary.execute_console_command to run py?
log("DONE6")
