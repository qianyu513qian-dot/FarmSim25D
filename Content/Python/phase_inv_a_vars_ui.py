# -*- coding: utf-8 -*-
"""Phase A: add Money/SeedCount/CropCount/FarmHUDWidget vars + create WBP_FarmHUD."""
import unreal
import os

TAG = "[INV_A] "
bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
UI_DIR = "/Game/Farm/UI"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)

def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p

def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)
        log("mkdir " + path)

def add_int_var(bp, name):
    names = [str(n) for n in bel.list_member_variable_names(bp)]
    # list includes inherited - check short name
    short = [n.split(".")[-1] for n in names]
    if name in short:
        log("var exists " + name)
        return True
    ok = bel.add_member_variable(bp, name, make_pin('(PinCategory="int",PinSubCategory="")'))
    log("add {} -> {}".format(name, ok))
    return ok

def add_obj_var(bp, name, class_path):
    names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
    if name in names:
        log("var exists " + name)
        return True
    txt = '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="{}")'.format(class_path)
    ok = bel.add_member_variable(bp, name, make_pin(txt))
    log("add {} -> {} ({})".format(name, ok, class_path))
    return ok

def create_wbp():
    ensure_dir("/Game/Farm")
    ensure_dir(UI_DIR)
    if unreal.EditorAssetLibrary.does_asset_exist(WBP):
        log("WBP exists")
        return unreal.load_asset(WBP)

    factory = unreal.WidgetBlueprintFactory()
    try:
        factory.set_editor_property("parent_class", unreal.UserWidget)
    except Exception as e:
        log("parent_class set: " + str(e))
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    wbp = tools.create_asset("WBP_FarmHUD", UI_DIR, unreal.WidgetBlueprint, factory)
    log("created WBP=" + str(wbp))
    if not wbp:
        return None

    # Build minimal hierarchy: Canvas > VerticalBox > 3 TextBlocks
    try:
        tree = wbp.get_editor_property("widget_tree")
    except Exception:
        try:
            tree = wbp.widget_tree
        except Exception as e:
            log("no widget_tree: " + str(e))
            tree = None
    log("tree=" + str(tree))
    if tree:
        try:
            canvas = tree.construct_widget(unreal.CanvasPanel, "RootCanvas")
            tree.set_editor_property("root_widget", canvas)
            log("root canvas ok")
        except Exception as e:
            log("canvas fail: " + str(e))
            # try alternate
            try:
                canvas = unreal.CanvasPanel()
                tree.root_widget = canvas
            except Exception as e2:
                log("canvas alt fail: " + str(e2))
                canvas = None
        if canvas:
            try:
                vbox = tree.construct_widget(unreal.VerticalBox, "VBoxHUD")
                slot = canvas.add_child_to_canvas(vbox)
                # anchors top-left
                try:
                    anchors = unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(0, 0))
                    slot.set_editor_property("anchors", anchors)
                    slot.set_editor_property("position", unreal.Vector2D(20, 20))
                    slot.set_editor_property("auto_size", True)
                except Exception as e:
                    log("slot props: " + str(e))
                for name, default in (
                    ("TxtMoney", "Money: 50"),
                    ("TxtSeeds", "Seeds: 5"),
                    ("TxtCrops", "Crops: 0"),
                ):
                    tb = tree.construct_widget(unreal.TextBlock, name)
                    try:
                        tb.set_editor_property("text", unreal.Text(default))
                    except Exception:
                        try:
                            tb.set_text(default)
                        except Exception as e:
                            log("set text {}: {}".format(name, e))
                    try:
                        # font size
                        font = tb.get_editor_property("font")
                        font.size = 22
                        tb.set_editor_property("font", font)
                    except Exception as e:
                        log("font {}: {}".format(name, e))
                    try:
                        vbox.add_child_to_vertical_box(tb)
                        log("added " + name)
                    except Exception as e:
                        log("add child {}: {}".format(name, e))
            except Exception as e:
                log("vbox fail: " + str(e))

    unreal.EditorAssetLibrary.save_asset(WBP)
    return unreal.load_asset(WBP)

def set_defaults(bp):
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile warn: " + str(e))
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        for prop, val in (("Money", 50), ("SeedCount", 5), ("CropCount", 0), ("TomatoSellPrice", 10)):
            try:
                cdo.set_editor_property(prop, val)
                got = cdo.get_editor_property(prop)
                log("CDO {}={}".format(prop, got))
            except Exception as e:
                # try snake_case
                try:
                    snake = "".join(("_" + c.lower() if c.isupper() else c) for c in prop).lstrip("_")
                    # Money -> money, SeedCount -> seed_count
                    import re
                    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', prop).lower()
                    cdo.set_editor_property(snake, val)
                    log("CDO {}={} via {}".format(prop, cdo.get_editor_property(snake), snake))
                except Exception as e2:
                    log("CDO {} FAIL {} / {}".format(prop, e, e2))
    except Exception as e:
        log("defaults FAIL " + str(e))

def main():
    wbp = create_wbp()
    bp = unreal.load_asset(CHAR)
    add_int_var(bp, "Money")
    add_int_var(bp, "SeedCount")
    add_int_var(bp, "CropCount")
    add_int_var(bp, "TomatoSellPrice")
    # FarmHUDWidget as UserWidget object
    wbp_class_path = "/Script/UMG.UserWidget"
    if wbp:
        try:
            gc = wbp.generated_class()
            if gc:
                wbp_class_path = gc.get_path_name()
                log("wbp class=" + wbp_class_path)
        except Exception as e:
            log("wbp class err " + str(e))
    add_obj_var(bp, "FarmHUDWidget", wbp_class_path)
    set_defaults(bp)
    unreal.EditorAssetLibrary.save_asset(CHAR)
    if wbp:
        unreal.EditorAssetLibrary.save_asset(WBP)
    # verify vars
    names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
    for v in ("Money", "SeedCount", "CropCount", "TomatoSellPrice", "FarmHUDWidget"):
        log("has {}={}".format(v, v in names))
    log("DONE A")

main()
