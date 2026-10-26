# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary

def log(m):
    unreal.log("[DUMP2] " + str(m))
    print("[DUMP2] " + str(m))

# Enum values
enum = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
log("enum=" + str(enum))
try:
    for i, e in enumerate(enum.get_editor_property("names") if hasattr(enum, "get_editor_property") else []):
        log("enum name " + str(e))
except Exception as e:
    log("names " + str(e))
try:
    # UserDefinedEnum
    entries = enum.get_editor_property("display_name_map")
    log("display_name_map=" + str(entries))
except Exception as e:
    log("dnm " + str(e))
try:
    log("enums python: " + str(dir(enum))[:500])
except Exception:
    pass
try:
    n = unreal.UserDefinedEnum.get_enum_entries_count(enum) if hasattr(unreal.UserDefinedEnum, "get_enum_entries_count") else None
    log("count " + str(n))
except Exception as e:
    log(str(e))
# Better approach
try:
    for i in range(0, 16):
        try:
            name = unreal.EnumBase.get_name_string_by_index(enum, i) if False else None
        except Exception:
            name = None
        try:
            # UEnum
            dname = enum.get_display_name_text_by_index(i)
            aname = enum.get_name_string_by_index(i)
            log("i={} display={} name={}".format(i, dname, aname))
        except Exception as ex:
            if i < 8:
                log("i={} fail {}".format(i, ex))
            break
except Exception as e:
    log("loop " + str(e))

# TillCell titles properly
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
for n in ge.list_all_nodes():
    try:
        t = bel.get_node_title(n)
    except Exception:
        t = "?"
    log("TillCell TITLE=[{}] class={}".format(t, n.get_class().get_name()))
    if "Visualize" in str(t) or "DrawDebug" in str(t) or "Set Array" in str(t) or "Return" in str(t):
        for p in bel.list_all_pins(n):
            cps = list(p.list_connected_pins())
            if cps or "then" in str(p.get_pin_name()).lower() or "exec" in str(p.get_pin_name()).lower():
                log("  pin {} dir={} -> {}".format(p.get_pin_name(), p.get_pin_direction(),
                    [(bel.get_node_title(c.get_owning_node()), c.get_pin_name()) for c in cps]))

# Character Enhanced Input - get action asset names
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(cbp, "EventGraph"))
for n in cge.list_all_nodes():
    cls = n.get_class().get_name()
    try:
        t = bel.get_node_title(n)
    except Exception:
        t = cls
    if "Input" in cls or "Move" in str(t) or "AddMovement" in str(t) or "Break" in str(t) or "Vector" in str(t):
        log("CHAR [{}] {}".format(cls, t))
        # input action
        for prop in ("input_action", "Action"):
            try:
                v = n.get_editor_property(prop)
                log("  prop {}={}".format(prop, v))
            except Exception:
                pass
        for p in bel.list_all_pins(n):
            cps = list(p.list_connected_pins())
            if cps:
                log("  {} -> {}".format(p.get_pin_name(),
                    [(bel.get_node_title(c.get_owning_node()), c.get_pin_name()) for c in cps[:4]]))

log("DONE")
