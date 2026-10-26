# -*- coding: utf-8 -*-
"""Build WBP_FarmHUD TextBlocks via WidgetTree load_object."""
import unreal

WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[UMG2] " + str(m))
    print("[UMG2] " + str(m))

wbp = unreal.load_asset(WBP)
tree = unreal.load_object(wbp, "WidgetTree")
log("tree=" + str(tree))
log("methods=" + str([x for x in dir(tree) if not x.startswith("_") and ("widget" in x.lower() or "root" in x.lower() or "construct" in x.lower() or "child" in x.lower())]))

# current root
for name in ("root_widget", "RootWidget"):
    try:
        log("{}={}".format(name, tree.get_editor_property(name)))
    except Exception as e:
        log("{} ERR {}".format(name, e))

# construct
try:
    canvas = tree.construct_widget(unreal.CanvasPanel, "RootCanvas")
    log("canvas=" + str(canvas))
except Exception as e:
    log("construct canvas: " + str(e))
    canvas = None

if canvas:
    try:
        tree.set_editor_property("root_widget", canvas)
        log("set root ok")
    except Exception as e:
        log("set root: " + str(e))
        try:
            tree.root_widget = canvas
            log("set root attr ok")
        except Exception as e2:
            log("set root attr: " + str(e2))

    try:
        vbox = tree.construct_widget(unreal.VerticalBox, "VBoxHUD")
        log("vbox=" + str(vbox))
        slot = canvas.add_child_to_canvas(vbox)
        log("slot=" + str(slot) + " type=" + slot.get_class().get_name())
        # position
        for prop, val in (
            ("anchors", unreal.Anchors(minimum=unreal.Vector2D(0.0, 0.0), maximum=unreal.Vector2D(0.0, 0.0))),
            ("alignment", unreal.Vector2D(0.0, 0.0)),
            ("position", unreal.Vector2D(24.0, 24.0)),
            ("size", unreal.Vector2D(420.0, 120.0)),
            ("auto_size", True),
        ):
            try:
                slot.set_editor_property(prop, val)
                log("slot.{} ok".format(prop))
            except Exception as e:
                log("slot.{}: {}".format(prop, e))

        for name, default in (
            ("TxtMoney", "Money: 50"),
            ("TxtSeeds", "Seeds: 5"),
            ("TxtCrops", "Crops: 0"),
        ):
            tb = tree.construct_widget(unreal.TextBlock, name)
            log("tb {}={}".format(name, tb))
            try:
                tb.set_editor_property("text", default)
            except Exception:
                try:
                    from unreal import Text as UText
                    tb.set_editor_property("text", unreal.Text(default))
                except Exception as e:
                    log("text set {}: {}".format(name, e))
                    # try set_text
                    try:
                        tb.set_text(default)
                    except Exception as e2:
                        log("set_text {}: {}".format(name, e2))
            try:
                font = tb.get_editor_property("font")
                font.size = 24
                tb.set_editor_property("font", font)
            except Exception as e:
                log("font {}: {}".format(name, e))
            try:
                color = unreal.SlateColor()
                color.set_editor_property("specified_color", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
                tb.set_editor_property("color_and_opacity", color)
            except Exception as e:
                log("color {}: {}".format(name, e))
            try:
                vslot = vbox.add_child_to_vertical_box(tb)
                log("added {} slot={}".format(name, vslot))
            except Exception as e:
                log("add {}: {}".format(name, e))
    except Exception as e:
        log("vbox build fail: " + str(e))

# Also add named variables on WBP for BindWidget? Optional - we can GetWidgetFromName at runtime
# Or expose as variables
bel = unreal.BlueprintEditorLibrary
# Add object vars typed as TextBlock for easy Get in graph - BindWidget style is harder
# Instead character will Call function on widget OR use GetWidgetFromName

try:
    bel.compile_blueprint(wbp)
    log("compile ok")
except Exception as e:
    log("compile: " + str(e))
unreal.EditorAssetLibrary.save_asset(WBP)
# verify root
try:
    log("root now=" + str(tree.get_editor_property("root_widget")))
except Exception as e:
    log(str(e))
# list all widgets in tree
try:
    allw = tree.get_editor_property("all_widgets")
    log("all_widgets=" + str(allw))
except Exception as e:
    log("all_widgets: " + str(e))
log("DONE")
