# -*- coding: utf-8 -*-
"""Probe UMGWidgetTreeInfo / SubobjectData / add component APIs."""
import unreal

def log(m):
    unreal.log("[UI_P5] " + str(m))
    print("[UI_P5] " + str(m))

# UMGWidgetTreeInfo
info_cls = unreal.UMGWidgetTreeInfo
log("UMGWidgetTreeInfo=" + str(info_cls))
log("dirs=" + str([x for x in dir(info_cls) if not x.startswith("_")][:60]))

bp_info = unreal.UMGWidgetBlueprintInfo
log("UMGWidgetBlueprintInfo dirs=" + str([x for x in dir(bp_info) if not x.startswith("_")][:60]))

# SubobjectDataSubsystem
try:
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    log("SubobjectDataSubsystem=" + str(sub))
    log("sub dirs=" + str([x for x in dir(sub) if not x.startswith("_") and ("add" in x.lower() or "create" in x.lower() or "component" in x.lower() or "handle" in x.lower())][:40]))
except Exception as e:
    log("sub " + str(e))

# BlueprintEditorLibrary add component?
bel = unreal.BlueprintEditorLibrary
log("bel componentish=" + str([x for x in dir(bel) if "comp" in x.lower() or "scs" in x.lower() or "add_" in x.lower()][:50]))

# EditorActorSubsystem spawn + WidgetComponent at runtime in PIE? 
# Can we set WidgetTree via find_object after constructing with NewObject?
wbp = unreal.load_asset("/Game/Farm/UI/WBP_RestOrderList_TMP")
tree = unreal.load_object(wbp, "WidgetTree")
# Try NewObject canvas as outer=tree
try:
    canvas = unreal.CanvasPanel()
    log("CanvasPanel()=" + str(canvas))
except Exception as e:
    log("CanvasPanel() " + str(e))
try:
    canvas = unreal.new_object(unreal.CanvasPanel, tree, "RootCanvas")
    log("new_object canvas=" + str(canvas))
except Exception as e:
    log("new_object " + str(e))

# try unreal.WidgetTree methods via get_cname / export
import json
# Package dump of WBP_FarmHUD as text?
# Check if there's WidgetBlueprintEditor
for name in dir(unreal):
    if "WidgetBlueprint" in name or "UMGEditor" in name or "WidgetTree" in name:
        log("cls " + name)

# Font from FontFace for Slate - create Font asset?
# Check FontFactory
log("FontFactory=" + str(getattr(unreal, "FontFactory", None)))
log("CompositeFont=" + str(getattr(unreal, "CompositeFont", None)))

# DroidSansFallback - good for CJK in engine Print?
log("DONE5")
