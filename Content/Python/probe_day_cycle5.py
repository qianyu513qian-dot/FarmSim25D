# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
def log(m):
    unreal.log("[P5] "+str(m)); print("[P5] "+str(m))

# existing For Loop macro path?
for n in ge.list_all_nodes():
    if "For" in str(bel.get_node_title(n)):
        log("for class="+n.get_class().get_name())
        for prop in ("macro_graph_reference", "macro", "macro_graph"):
            try:
                log("  prop {}={}".format(prop, n.get_editor_property(prop)))
            except Exception as e:
                pass
        # try all editor props with macro
        try:
            for pname in dir(n):
                if "macro" in pname.lower() and not pname.startswith("_"):
                    try:
                        log("  attr {}={}".format(pname, getattr(n, pname)))
                    except Exception:
                        pass
        except Exception:
            pass

# try add_macro_node paths
candidates = [
    "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop",
    "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:For Loop",
    "/Engine/EditorBlueprintResources/StandardMacros:ForLoop",
    "ForLoop",
    "For Loop",
]
for c in candidates:
    try:
        n = ge.add_macro_node(c)
        log("add_macro {} -> {} title={}".format(c, n, bel.get_node_title(n) if n else None))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("add_macro {} FAIL {}".format(c, e))

# get_default_object
log("get_default_object doc="+str(bel.get_default_object.__doc__))
try:
    d = bel.get_default_object()
    log("noarg="+str(d))
except Exception as e:
    log("noarg fail "+str(e))

# cast API
log("cast doc="+str(ge.cast.__doc__))
try:
    # create a temp get then cast?
    pass
except Exception:
    pass

# How to set CDO property without get_default_object(bp)?
try:
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    log("unreal.get_default_object gen works, CellSize="+str(cdo.get_editor_property("CellSize")))
except Exception as e:
    log("unreal.get_default_object "+str(e))

# float operator create names that work
for name in [
    "Utilities|Operators|float * float",
    "Utilities|Operators|float + float",
    "Utilities|Operators|float - float",
    "Utilities|Operators|float / float",
    "Utilities|Operators|float >= float",
    "Utilities|Operators|integer * integer",
    "Utilities|Operators|integer / integer",
    "Utilities|Operators|integer % integer",
    "Utilities|Operators|integer + integer",
    "Utilities|Operators|integer - integer",
    "Utilities|String|Append",
    "Utilities|FlowControl|ForLoop",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(0,0), [])
        log("create {} -> {}".format(name, bel.get_node_title(n) if n else None))
        if n:
            ge.remove_nodes([n])
    except Exception as e:
        log("create {} FAIL {}".format(name, e))

log("DONE")
