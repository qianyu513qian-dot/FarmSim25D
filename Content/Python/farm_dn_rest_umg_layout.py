# -*- coding: utf-8 -*-
"""Layout WBP_RestOrderList as right-edge order strip; hide FarmHUD leftovers; verify fonts."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
WBP="/Game/Farm/UI/WBP_RestOrderList"
REPORT={"steps":[]}

def log(m):
    unreal.log("[UMGLAY] "+str(m)); print("[UMGLAY] "+str(m)); REPORT["steps"].append(str(m))

wbp=unreal.load_asset(WBP)
widgets={}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()]=o
log("widgets="+str(sorted(widgets.keys())))

font=unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
log("font="+str(font))

# Hide FarmHUD leftovers not used for orders
hide_names=("TxtClock","TxtControls","TxtStamina","BarStamina","BarPatience1","BarPatience2","TxtLine1","TxtLine2")
for name in hide_names:
    w=widgets.get(name)
    if not w: continue
    try:
        w.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        log("hide "+name)
    except Exception as e:
        log("hide fail "+name+" "+str(e)[:60])

# Show order texts
show_names=("TxtTitle","TxtSeeds","TxtHarvest","HUDCanvas","HUDLayout","HUDPanel")
for name in show_names:
    w=widgets.get(name)
    if not w: continue
    try:
        w.set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
        log("show "+name)
    except Exception as e:
        log("show fail "+name+" "+str(e)[:60])

def set_text_style(tb, text, size, color=(1,1,1,1)):
    if not tb: return
    try:
        tb.set_text(text)
    except Exception:
        pass
    try:
        fi=tb.get_editor_property("font")
        fi.set_editor_property("size", float(size))
        if font:
            fi.set_editor_property("font_object", font)
        tb.set_editor_property("font", fi)
    except Exception as e:
        log("font "+str(e)[:80])
    try:
        c=unreal.SlateColor()
        c.set_editor_property("specified_color", unreal.LinearColor(color[0],color[1],color[2],color[3]))
        tb.set_editor_property("color_and_opacity", c)
    except Exception as e:
        log("color "+str(e)[:60])

set_text_style(widgets.get("TxtTitle"), "\u8ba2\u5355", 24, (1.0, 0.92, 0.55, 1.0))
set_text_style(widgets.get("TxtSeeds"), "", 18, (1,1,1,1))
set_text_style(widgets.get("TxtHarvest"), "", 18, (1,1,1,1))

# Try place on right edge via slot if Canvas children
canvas=widgets.get("HUDCanvas")
panel=widgets.get("HUDPanel") or widgets.get("HUDLayout")
log("canvas="+str(canvas)+" panel="+str(panel))

# Inspect slot API on TextBlocks
for name in ("TxtTitle","TxtSeeds","TxtHarvest"):
    tb=widgets.get(name)
    if not tb: continue
    slot=None
    try: slot=tb.get_editor_property("slot")
    except Exception: pass
    log("{} slot={}".format(name, slot))
    if slot:
        try:
            # CanvasPanelSlot
            slot.set_editor_property("anchors", unreal.Anchors(1.0, 0.0, 1.0, 0.0))  # top-right
        except Exception as e:
            log("anchors "+str(e)[:80])
        try:
            # position relative to right: negative X
            y={"TxtTitle":40.0,"TxtSeeds":80.0,"TxtHarvest":110.0}[name]
            slot.set_editor_property("position", unreal.Vector2D(-280.0, y))
            slot.set_editor_property("size", unreal.Vector2D(260.0, 36.0))
            slot.set_editor_property("alignment", unreal.Vector2D(0.0, 0.0))
            log("pos "+name)
        except Exception as e:
            log("pos fail "+name+" "+str(e)[:100])
        # auto size
        try:
            slot.set_editor_property("auto_size", True)
        except Exception:
            pass

# Dark panel backdrop if HUDPanel exists
if panel:
    try:
        panel.set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
    except Exception:
        pass
    slot=None
    try: slot=panel.get_editor_property("slot")
    except Exception: pass
    if slot:
        try:
            slot.set_editor_property("anchors", unreal.Anchors(1.0, 0.0, 1.0, 0.0))
            slot.set_editor_property("position", unreal.Vector2D(-300.0, 20.0))
            slot.set_editor_property("size", unreal.Vector2D(280.0, 160.0))
            log("panel placed")
        except Exception as e:
            log("panel slot "+str(e)[:100])
    # try set color on border/image
    try:
        if hasattr(panel, "set_brush_color") or True:
            c=unreal.LinearColor(0.05, 0.05, 0.08, 0.75)
            for prop in ("brush_color","ColorAndOpacity","color_and_opacity"):
                try:
                    panel.set_editor_property(prop, c if "Linear" in prop or "brush" in prop else unreal.SlateColor(specified_color=c))
                    log("panel color "+prop)
                except Exception:
                    pass
    except Exception as e:
        log(str(e)[:60])

bel.compile_blueprint(wbp)
log("status="+str(wbp.get_editor_property("status")))
eas.save_asset(WBP)

# Confirm Manager bOrderDebugPrint default false if exists
mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
try:
    names=[str(n) for n in bel.list_member_variable_names(mbp, False)]
    log("mgr vars sample="+str([n for n in names if "Order" in n or "Debug" in n or "Print" in n]))
except Exception as e:
    log(str(e))
# try set default
try:
    # BlueprintEditorLibrary set default value
    bel.set_blueprint_variable_default_value(mbp, "bOrderDebugPrint", "False")
    log("bOrderDebugPrint=False")
except Exception as e:
    log("debugflag "+str(e)[:80])

bel.compile_blueprint(mbp)
eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
open(unreal.Paths.project_saved_dir()+"rest_umg_layout.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print("DONE_LAYOUT")
