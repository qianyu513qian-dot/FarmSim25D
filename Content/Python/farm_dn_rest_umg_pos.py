# -*- coding: utf-8 -*-
"""Anchor HUDPanel/HUDLayout to top-right as order strip."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
WBP="/Game/Farm/UI/WBP_RestOrderList"

def log(m):
    unreal.log("[UMGPOS] "+str(m)); print("[UMGPOS] "+str(m))

wbp=unreal.load_asset(WBP)
widgets={}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()]=o

# Inspect HUDLayout / HUDPanel parent slots
for name in ("HUDLayout","HUDPanel","HUDCanvas"):
    w=widgets.get(name)
    if not w: continue
    slot=None
    try: slot=w.get_editor_property("slot")
    except Exception as e: log(name+" no slot "+str(e)[:60]); continue
    log("{} class={} slot={}".format(name, w.get_class().get_name(), slot.get_class().get_name() if slot else None))
    if not slot: continue
    # dump props
    props=[p for p in dir(slot) if not p.startswith("_")]
    log("slot props sample="+str([p for p in props if "pos" in p.lower() or "anchor" in p.lower() or "size" in p.lower() or "offset" in p.lower()][:30]))

# Position HUDPanel if CanvasPanelSlot
panel=widgets.get("HUDPanel")
layout=widgets.get("HUDLayout")
target=None
for cand in (panel, layout):
    if not cand: continue
    try:
        slot=cand.get_editor_property("slot")
        if slot and slot.get_class().get_name()=="CanvasPanelSlot":
            target=cand; break
    except Exception:
        pass
log("canvas-slot target="+str(target.get_name() if target else None))

if target:
    slot=target.get_editor_property("slot")
    # Anchors: Minimum=(1,0) Maximum=(1,0) = top-right
    try:
        a=unreal.Anchors()
        a.set_editor_property("minimum", unreal.Vector2D(1.0, 0.0))
        a.set_editor_property("maximum", unreal.Vector2D(1.0, 0.0))
        slot.set_editor_property("anchors", a)
        log("anchors set")
    except Exception as e:
        log("anchors "+str(e)[:100])
    try:
        # position from top-right: X negative
        slot.set_editor_property("position", unreal.Vector2D(-320.0, 24.0))
        slot.set_editor_property("size", unreal.Vector2D(300.0, 180.0))
        slot.set_editor_property("alignment", unreal.Vector2D(0.0, 0.0))
        log("position set")
    except Exception as e:
        log("pos "+str(e)[:100])
    try:
        slot.set_editor_property("b_auto_size", False)
    except Exception:
        try: slot.set_editor_property("auto_size", False)
        except Exception: pass

# Soften border
if panel:
    try:
        brush=panel.get_editor_property("background")
        log("bg="+str(brush))
    except Exception as e:
        log("bg "+str(e)[:60])
    try:
        c=unreal.LinearColor(0.02, 0.02, 0.05, 0.82)
        panel.set_editor_property("brush_color", c)
        log("brush_color ok")
    except Exception as e:
        log(str(e)[:80])

# Set bOrderDebugPrint default via member variable default
mbp=unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
try:
    # try CDO
    cdo=unreal.get_default_object(mbp.generated_class())
    cdo.set_editor_property("b_order_debug_print", False)
    log("CDO bOrderDebugPrint False")
except Exception as e:
    log("CDO "+str(e)[:100])
try:
    cdo=unreal.get_default_object(mbp.generated_class())
    cdo.set_editor_property("bOrderDebugPrint", False)
    log("CDO camel False")
except Exception as e:
    log("CDO2 "+str(e)[:100])

bel.compile_blueprint(wbp)
bel.compile_blueprint(mbp)
eas.save_asset(WBP)
eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
# verify final statuses
for path in (WBP, "/Game/Farm/Restaurant/BP_RestaurantManager", "/Game/Farm/Restaurant/BP_RestaurantTable"):
    bp=unreal.load_asset(path)
    bel.compile_blueprint(bp)
    st=str(bp.get_editor_property("status"))
    ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    errs=len(ge.list_nodes_with_errors() or [])
    # also UpdateOrders
    ug=bel.find_graph(bp,"UpdateOrders")
    if ug:
        uge=unreal.BlueprintGraphEditor.get_graph_editor(ug)
        errs += len(uge.list_nodes_with_errors() or [])
    log("CHK {} {} errs={}".format(path.split("/")[-1], st, errs))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
print("DONE_POS")
