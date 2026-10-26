# -*- coding: utf-8 -*-
"""Probe WBP widget tree access and build TextBlocks."""
import unreal

WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[UMG] " + str(m))
    print("[UMG] " + str(m))

wbp = unreal.load_asset(WBP)
log("wbp=" + str(wbp))
log("class=" + wbp.get_class().get_name())
# list editor properties that look useful
props = []
for p in dir(wbp):
    if p.startswith("_"):
        continue
    pl = p.lower()
    if any(k in pl for k in ("widget", "tree", "root", "designer", "graph")):
        props.append(p)
log("interesting attrs=" + str(props))
for p in props:
    try:
        v = getattr(wbp, p)
        if callable(v):
            continue
        log("  {}={!r}".format(p, v))
    except Exception as e:
        log("  {} ERR {}".format(p, e))
# try get_editor_property for common names
for name in ("widget_tree", "WidgetTree", "root_widget", "RootWidget",
             "simplified_controls", "palette_category"):
    try:
        v = wbp.get_editor_property(name)
        log("prop {}={!r}".format(name, v))
    except Exception as e:
        log("prop {} ERR {}".format(name, e))

# Generated class CDO?
try:
    gc = wbp.generated_class()
    log("gc=" + str(gc))
    cdo = unreal.get_default_object(gc)
    log("cdo=" + str(cdo))
    # widget tree on generated class?
    for name in ("widget_tree", "WidgetTree"):
        try:
            log("gc.{}={}".format(name, gc.get_editor_property(name)))
        except Exception as e:
            log("gc.{} ERR {}".format(name, e))
    for name in ("widget_tree", "WidgetTree"):
        try:
            log("cdo.{}={}".format(name, cdo.get_editor_property(name)))
        except Exception as e:
            log("cdo.{} ERR {}".format(name, e))
except Exception as e:
    log("gc err " + str(e))

# WidgetBlueprintLibrary / helpers
log("UMG helpers: " + str([x for x in dir(unreal) if "WidgetBlueprint" in x or "WidgetTree" in x]))
# Try loading WidgetTree as subobject
try:
    tree = unreal.load_object(wbp, "WidgetTree")
    log("load_object WidgetTree=" + str(tree))
except Exception as e:
    log("load_object " + str(e))
try:
    tree = unreal.find_object(wbp, "WidgetTree")
    log("find_object WidgetTree=" + str(tree))
except Exception as e:
    log("find_object " + str(e))

# SubobjectDataSubsystem approach
try:
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(wbp)
    log("subobjects=" + str(len(handles)))
    for h in handles:
        data = lib.get_data(h)
        name = str(lib.get_variable_name(data))
        obj = lib.get_object_for_blueprint(data, wbp)
        log("  sub {} class={}".format(name, obj.get_class().get_name() if obj else None))
except Exception as e:
    log("sds " + str(e))
