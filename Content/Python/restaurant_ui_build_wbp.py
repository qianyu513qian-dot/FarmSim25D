# -*- coding: utf-8 -*-
"""Try building WBP widget tree via new_object + import_text / mark dirty."""
import unreal

def log(m):
    unreal.log("[UI_BUILD] " + str(m))
    print("[UI_BUILD] " + str(m))

bel = unreal.BlueprintEditorLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
UI_DIR = "/Game/Farm/UI"
NAME = "WBP_RestOrderList"
PATH = UI_DIR + "/" + NAME

# cleanup tmp
for p in (UI_DIR + "/WBP_RestOrderList_TMP", PATH):
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        unreal.EditorAssetLibrary.delete_asset(p)
        log("deleted " + p)

factory = unreal.WidgetBlueprintFactory()
try:
    factory.set_editor_property("parent_class", unreal.UserWidget)
except Exception as e:
    log("parent " + str(e))
wbp = tools.create_asset(NAME, UI_DIR, unreal.WidgetBlueprint, factory)
log("wbp=" + str(wbp))
tree = unreal.load_object(wbp, "WidgetTree")
log("tree=" + str(tree))

# Create hierarchy
canvas = unreal.new_object(unreal.CanvasPanel, tree, "RootCanvas")
vbox = unreal.new_object(unreal.VerticalBox, tree, "VBoxOrders")
row1 = unreal.new_object(unreal.HorizontalBox, tree, "Row1")
row2 = unreal.new_object(unreal.HorizontalBox, tree, "Row2")
bg1 = unreal.new_object(unreal.Border, tree, "Bg1")
bg2 = unreal.new_object(unreal.Border, tree, "Bg2")
txt1 = unreal.new_object(unreal.TextBlock, tree, "TxtOrder1")
txt2 = unreal.new_object(unreal.TextBlock, tree, "TxtOrder2")
bar1 = unreal.new_object(unreal.ProgressBar, tree, "BarPatience1")
bar2 = unreal.new_object(unreal.ProgressBar, tree, "BarPatience2")
title = unreal.new_object(unreal.TextBlock, tree, "TxtTitle")
log("created widgets")

# Try set text
for tb, text in ((title, "\u8ba2\u5355"), (txt1, "1 \u756a\u8304\u6c99\u62c9"), (txt2, "2 \u7096\u83dc")):
    try:
        tb.set_text(text)
        log("set_text ok " + tb.get_name())
    except Exception as e:
        try:
            tb.set_editor_property("text", text)
            log("set text prop ok " + tb.get_name())
        except Exception as e2:
            log("text fail {} {} {}".format(tb.get_name(), e, e2))

# Font: use SlateFontInfo with Font_SimHei_TR or DroidSansFallback
font_asset = unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
face = unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei")
for tb in (title, txt1, txt2):
    try:
        fi = tb.get_editor_property("font")
        log("font type=" + str(type(fi)) + " dirs=" + str([x for x in dir(fi) if not x.startswith("_")][:30]))
        try:
            fi.set_editor_property("size", 22)
        except Exception as e:
            log("size " + str(e))
        # try font_object / font_material / composite
        for prop in ("font_object", "FontObject", "typeface_font_name", "typeface_font_name"):
            try:
                fi.set_editor_property(prop, font_asset)
                log("set {} ok".format(prop))
            except Exception as e:
                pass
        tb.set_editor_property("font", fi)
    except Exception as e:
        log("font get " + str(e))

# Parenting: add_child
try:
    slot = canvas.add_child_to_canvas(vbox)
    log("add vbox slot=" + str(slot))
    for prop, val in (
        ("anchors", unreal.Anchors(minimum=unreal.Vector2D(1.0, 0.0), maximum=unreal.Vector2D(1.0, 0.0))),
        ("alignment", unreal.Vector2D(1.0, 0.0)),
        ("position", unreal.Vector2D(-24.0, 120.0)),
        ("size", unreal.Vector2D(320.0, 160.0)),
        ("auto_size", True),
    ):
        try:
            slot.set_editor_property(prop, val)
            log("slot.{} ok".format(prop))
        except Exception as e:
            log("slot.{} {}".format(prop, e))
except Exception as e:
    log("add vbox " + str(e))

try:
    vbox.add_child_to_vertical_box(title)
    # rows with text+bar
    for row, bg, txt, bar in ((row1, bg1, txt1, bar1), (row2, bg2, txt2, bar2)):
        try:
            bg.add_child(row)  # Border
        except Exception:
            try:
                bg.set_content(row)
            except Exception as e:
                log("border content " + str(e))
        try:
            row.add_child_to_horizontal_box(txt)
            row.add_child_to_horizontal_box(bar)
        except Exception as e:
            log("hbox " + str(e))
        try:
            vbox.add_child_to_vertical_box(bg)
        except Exception as e:
            log("vbox add bg " + str(e))
    log("hierarchy ok-ish")
except Exception as e:
    log("hier " + str(e))

# Set RootWidget - protected read, try write via call_method / modify
for attempt in range(1):
    try:
        tree.set_editor_property("RootWidget", canvas)
        log("set RootWidget ok")
    except Exception as e:
        log("set RootWidget " + str(e))
    try:
        # Sometimes lowercase
        tree.set_editor_property("root_widget", canvas)
        log("set root_widget ok")
    except Exception as e:
        log("set root_widget " + str(e))

# Try WidgetBlueprint set
for prop in ("WidgetTree",):
    try:
        log("wbp.{} via gep exists".format(prop))
    except Exception:
        pass

# UMGWidgetTreeInfo import?
try:
    # Get info somehow?
    log("try export empty tree")
except Exception:
    pass

# Compile
try:
    bel.compile_blueprint(wbp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))

# Check generated class default for root?
try:
    gen = wbp.generated_class()
    log("gen=" + str(gen))
except Exception as e:
    log("gen " + str(e))

unreal.EditorAssetLibrary.save_asset(PATH)
log("saved")

# Also try SubobjectDataSubsystem add WidgetComponent to Table BP
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
log("add_new_subobject sig try")
try:
    # inspect signature via help
    import inspect
    log("add_new_subobject=" + str(sub.add_new_subobject))
except Exception as e:
    log(str(e))

# Document SubobjectData parameters
try:
    params = unreal.AddNewSubobjectParams()
    log("AddNewSubobjectParams dirs=" + str([x for x in dir(params) if not x.startswith("_")]))
except Exception as e:
    log("params " + str(e))

log("DONE_BUILD")
