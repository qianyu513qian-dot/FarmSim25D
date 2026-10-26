# -*- coding: utf-8 -*-
"""Identify IA nodes + success chains for Plant/Harvest."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[ID] " + str(m))
    print("[ID] " + str(m))

def pin_val(p):
    try:
        return p.get_pin_value()
    except Exception:
        return ""

def linked(p):
    try:
        return p.get_linked_to() or []
    except Exception:
        return []

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

for i, n in enumerate(nodes):
    cn = n.get_class().get_name()
    if cn == "K2Node_EnhancedInputAction":
        # find InputAction property
        ia = None
        try:
            ia = n.get_editor_property("input_action")
        except Exception:
            try:
                ia = n.get_editor_property("InputAction")
            except Exception:
                pass
        log("IA node[{}] action={}".format(i, ia.get_path_name() if ia else "?"))
        for p in bel.list_all_pins(n):
            if "Started" in str(p.get_pin_name()) or "Triggered" in str(p.get_pin_name()):
                for lp in linked(p):
                    own = lp.get_owning_node()
                    log("  {} -> {} pins_of_target_exec".format(p.get_pin_name(), own.get_class().get_name()))

    if cn == "K2Node_CallFunction":
        fname = ""
        try:
            fname = str(n.get_editor_property("function_reference").member_name)
        except Exception:
            try:
                fr = n.function_reference
                fname = str(fr.member_name)
            except Exception:
                pass
        if fname in ("PlantCell", "HarvestCell", "TillCell", "WaterCell", "GrowCell", "VisualizeCell", "PrintString"):
            in_str = ""
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "InString":
                    in_str = pin_val(p)
            log("CALL[{}] {} InString={!r}".format(i, fname, in_str))
            # show exec in/out links
            for p in bel.list_all_pins(n):
                pn = str(p.get_pin_name())
                if pn in ("execute", "then", "Success"):
                    outs = []
                    for lp in linked(p):
                        own = lp.get_owning_node()
                        oc = own.get_class().get_name()
                        ofn = ""
                        if oc == "K2Node_CallFunction":
                            try:
                                ofn = str(own.get_editor_property("function_reference").member_name)
                            except Exception:
                                pass
                        outs.append("{}:{}({})".format(lp.get_pin_name(), oc, ofn))
                    log("  pin {} links={}".format(pn, outs))

# BeginPlay / Event nodes
for i, n in enumerate(nodes):
    if n.get_class().get_name() == "K2Node_Event":
        en = ""
        try:
            en = str(n.get_editor_property("event_reference").member_name)
        except Exception:
            try:
                en = str(n.event_reference.member_name)
            except Exception:
                pass
        log("EVENT[{}] {}".format(i, en))
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "then":
                for lp in linked(p):
                    own = lp.get_owning_node()
                    ofn = own.get_class().get_name()
                    try:
                        ofn2 = str(own.get_editor_property("function_reference").member_name)
                        ofn = ofn + ":" + ofn2
                    except Exception:
                        pass
                    log("  Begin then -> " + ofn)

# How to add variable?
log("has add_member_variable=" + str(hasattr(bel, "add_member_variable")))
log("dir bel sample=" + str([x for x in dir(bel) if "var" in x.lower() or "member" in x.lower()][:40]))
