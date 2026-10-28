# -*- coding: utf-8 -*-
"""Inspect Manny materials; customize RestOrderList; create Bubble WBP; configure WidgetComponent."""
import unreal

def log(m):
    unreal.log("[UI_C4] " + str(m))
    print("[UI_C4] " + str(m))

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# Manny materials
skel = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
log("skel=" + str(skel))
try:
    mats = skel.get_editor_property("materials")
    log("mats type=" + str(type(mats)) + " len=" + str(len(list(mats))))
    for i, m in enumerate(list(mats)):
        try:
            mi = m.get_editor_property("material_interface")
            log("  [{}] slot={} mat={}".format(i, m.get_editor_property("material_slot_name"), mi.get_path_name() if mi else None))
        except Exception:
            log("  [{}] {}".format(i, m))
except Exception as e:
    log("mats " + str(e))

# Find mannequin materials folder
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for a in list(ar.get_assets_by_path("/Game/Characters/Mannequins", True) or [])[:40]:
    log("  mannequin asset {}/{} {}".format(a.package_path, a.asset_name, a.asset_class_path.asset_name))

# ---- Customize WBP_RestOrderList (dup of FarmHUD) ----
wbp = unreal.load_asset("/Game/Farm/UI/WBP_RestOrderList")
tree = unreal.load_object(wbp, "WidgetTree")
font_cjk = unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")

widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    pn = o.get_path_name()
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in pn:
        widgets[o.get_name()] = o
        log("list widget " + o.get_name() + " " + o.get_class().get_name())

def set_tb_text(tb, text, size=20):
    try:
        tb.set_text(text)
    except Exception:
        try:
            tb.set_editor_property("text", text)
        except Exception as e:
            log("set_text fail " + str(e))
    try:
        fi = tb.get_editor_property("font")
        fi.set_editor_property("size", float(size))
        if font_cjk:
            fi.set_editor_property("font_object", font_cjk)
        tb.set_editor_property("font", fi)
    except Exception as e:
        log("font " + str(e))

# Repurpose texts
if "TxtMoney" in widgets:
    set_tb_text(widgets["TxtMoney"], "\u8ba2\u5355", 22)  # 订单
    widgets["TxtMoney"].rename("TxtTitle")
    # rename may not work on widget; keep name, just change text
if "TxtSeeds" in widgets:
    set_tb_text(widgets["TxtSeeds"], "1 ---", 18)
if "TxtHarvest" in widgets:
    set_tb_text(widgets["TxtHarvest"], "2 ---", 18)
if "TxtClock" in widgets:
    set_tb_text(widgets["TxtClock"], "", 16)
if "TxtStamina" in widgets:
    try:
        widgets["TxtStamina"].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
    except Exception as e:
        log("hide stamina " + str(e))
if "TxtControls" in widgets:
    try:
        widgets["TxtControls"].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
    except Exception as e:
        log("hide controls " + str(e))
if "BarStamina" in widgets:
    try:
        widgets["BarStamina"].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
    except Exception as e:
        log("hide bar " + str(e))

# Add two progress bars + ensure order text names usable via GetWidgetFromName
# We'll keep TxtSeeds as line1, TxtHarvest as line2, and use BarStamina for line1 patience by unhiding and renaming conceptually
# Better: create new ProgressBars under HUDLayout
layout = widgets.get("HUDLayout")
canvas = widgets.get("HUDCanvas")
if layout:
    bar1 = unreal.new_object(unreal.ProgressBar, tree, "BarPatience1")
    bar2 = unreal.new_object(unreal.ProgressBar, tree, "BarPatience2")
    txtp1 = unreal.new_object(unreal.TextBlock, tree, "TxtOrder1")
    txtp2 = unreal.new_object(unreal.TextBlock, tree, "TxtOrder2")
    set_tb_text(txtp1, "1 ---", 18)
    set_tb_text(txtp2, "2 ---", 18)
    try:
        layout.add_child_to_vertical_box(txtp1)
        layout.add_child_to_vertical_box(bar1)
        layout.add_child_to_vertical_box(txtp2)
        layout.add_child_to_vertical_box(bar2)
        log("added order rows to layout")
    except Exception as e:
        log("add rows " + str(e))
    # style bars
    for bar in (bar1, bar2):
        try:
            bar.set_editor_property("percent", 1.0)
        except Exception:
            pass
        try:
            fill = unreal.SlateBrush()
            # leave default
        except Exception:
            pass

# Collapse old farm texts that we don't need (keep TxtMoney as title)
for name in ("TxtSeeds", "TxtHarvest", "TxtClock"):
    if name in widgets:
        try:
            widgets[name].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        except Exception:
            pass

bel.compile_blueprint(wbp)
eas.save_asset("/Game/Farm/UI/WBP_RestOrderList")
log("RestOrderList saved")

# ---- Create Bubble WBP ----
bub_name = "WBP_RestOrderBubble"
bub_path = "/Game/Farm/UI/" + bub_name
if eas.does_asset_exist(bub_path):
    eas.delete_asset(bub_path)
bub = tools.duplicate_asset(bub_name, "/Game/Farm/UI", unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD"))
log("bubble=" + str(bub))
btree = unreal.load_object(bub, "WidgetTree")
bwidgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderBubble.WBP_RestOrderBubble:WidgetTree." in o.get_path_name():
        bwidgets[o.get_name()] = o
# Simplify: title=dish, one bar, hide rest
if "TxtMoney" in bwidgets:
    set_tb_text(bwidgets["TxtMoney"], "\u756a\u8304\u6c99\u62c9", 16)
for name in ("TxtSeeds", "TxtHarvest", "TxtClock", "TxtStamina", "TxtControls"):
    if name in bwidgets:
        try:
            bwidgets[name].set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        except Exception:
            pass
# Keep BarStamina as patience, add dish color image
if "HUDLayout" in bwidgets:
    img = unreal.new_object(unreal.Image, btree, "ImgDish")
    try:
        bwidgets["HUDLayout"].add_child_to_vertical_box(img)
        # move? order may be wrong; ok for v1
        log("added ImgDish")
    except Exception as e:
        log("img " + str(e))
    try:
        bwidgets["BarStamina"].set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
        bwidgets["BarStamina"].set_editor_property("percent", 1.0)
    except Exception as e:
        log("barvis " + str(e))

bel.compile_blueprint(bub)
eas.save_asset(bub_path)
log("bubble saved")

# ---- Configure Table WidgetComponent ----
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
# Find Widget_GEN_VARIABLE template
wc = None
for o in unreal.ObjectIterator(unreal.WidgetComponent):
    if "BP_RestaurantTable" in o.get_path_name() and "Widget_GEN_VARIABLE" in o.get_path_name():
        wc = o
        log("found WC " + o.get_path_name())
        break
if wc:
    # Set widget class
    bub_class = bub.generated_class()
    for prop, val in (
        ("widget_class", bub_class),
        ("WidgetClass", bub_class),
    ):
        try:
            wc.set_editor_property(prop, val)
            log("set {} ok".format(prop))
        except Exception as e:
            log("set {} {}".format(prop, e))
    # Space / draw size / pivot
    for prop, val in (
        ("draw_size", unreal.Vector2D(180.0, 90.0)),
        ("pivot", unreal.Vector2D(0.5, 1.0)),
        ("space", unreal.WidgetSpace.SCREEN),  # screen-space more readable under ortho
        ("timing_policy", unreal.WidgetTimingPolicy.REAL_TIME),
        ("geometry_mode", unreal.WidgetGeometryMode.PLANE),
        ("relative_location", unreal.Vector(0.0, 0.0, 120.0)),
        ("relative_rotation", unreal.Rotator(0.0, 0.0, 0.0)),
        ("visibility", True),
        ("hidden_in_game", False),
    ):
        try:
            wc.set_editor_property(prop, val)
            log("wc.{} ok".format(prop))
        except Exception as e:
            log("wc.{} {}".format(prop, e))
    # Try enum alternatives for space
    try:
        wc.set_editor_property("space", unreal.WidgetSpace.WORLD)
        log("space WORLD set")
    except Exception as e:
        log("space world " + str(e))

# Rename component to OrderBubble
try:
    handles = list(sub.k2_gather_subobject_data_for_blueprint(tbp) or [])
    for h in handles:
        ex = sub.k2_find_subobject_data_from_handle(h).export_text()
        if "Widget_GEN_VARIABLE" in ex:
            ok = sub.rename_subobject(h, "OrderBubble")
            log("rename OrderBubble=" + str(ok))
except Exception as e:
    log("rename " + str(e))

bel.compile_blueprint(tbp)
eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
log("table saved")
log("DONE_C4")
