# -*- coding: utf-8 -*-
import unreal

def dump(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    unreal.log("BP " + path + " type=" + str(type(bp)))
    for attr in ("ubergraph_pages", "function_graphs", "macro_graphs", "delegate_signature_graphs"):
        if hasattr(bp, attr):
            try:
                pages = list(getattr(bp, "get_editor_property")(attr))
                unreal.log(attr + " count=" + str(len(pages)))
                for g in pages:
                    unreal.log("  graph=" + str(g.get_name()) + " nodes=" + str(len(g.nodes) if hasattr(g,"nodes") else "?"))
            except Exception as ex:
                unreal.log_warning(attr + ": " + str(ex))
    # BlueprintEditorLibrary helpers
    for name in dir(unreal.BlueprintEditorLibrary):
        if "graph" in name.lower() or "variable" in name.lower() or "event" in name.lower():
            pass
    bel_methods = [m for m in dir(unreal.BlueprintEditorLibrary) if not m.startswith("_")]
    unreal.log("BEL sample: " + ", ".join(bel_methods[:40]))
    # Kismet
    ks = [m for m in dir(unreal) if "EdGraph" in m or "K2Node" in m or "Blueprint" in m]
    unreal.log("types: " + ", ".join(ks[:60]))

dump("/Game/Farm/Grid/BP_GridManager")
dump("/Game/TopDown/Blueprints/BP_TopDownCharacter")
# list member vars
for path in ("/Game/Farm/Grid/BP_GridManager", "/Game/TopDown/Blueprints/BP_TopDownCharacter"):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    try:
        names = unreal.BlueprintEditorLibrary.get_new_variables(bp) if hasattr(unreal.BlueprintEditorLibrary, "get_new_variables") else None
        unreal.log("vars api " + str(names))
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        gen = bp.generated_class()
        unreal.log("gen " + str(gen))
        cdo = unreal.get_default_object(gen)
        for prop in ("plot_states", "PlotStates", "grid_manager_ref", "GridManagerRef", "cell_size"):
            try:
                unreal.log("prop " + prop + "=" + str(cdo.get_editor_property(prop)))
            except Exception as ex:
                unreal.log_warning("no " + prop + " " + str(ex))
    except Exception as ex:
        unreal.log_warning("cdo " + str(ex))