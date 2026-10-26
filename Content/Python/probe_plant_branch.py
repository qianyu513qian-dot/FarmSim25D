# -*- coding: utf-8 -*-
"""Find Plant Branch.then connections; probe var defaults + UMG create."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[P4] " + str(m))
    print("[P4] " + str(m))

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

# Find IA_Plant -> follow to Branch
plant_ia = None
for n in nodes:
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "InputAction":
            try:
                if "IA_Plant" in (p.get_pin_value() or ""):
                    plant_ia = n
            except Exception:
                pass
log("plant_ia=" + str(bool(plant_ia)))
started = find_pin(plant_ia, "Started", "Output")
w2g = conn(started)[0].get_owning_node()
then1 = find_pin(w2g, "then", "Output")
cell = conn(then1)[0].get_owning_node()
then2 = find_pin(cell, "then", "Output")
br = conn(then2)[0].get_owning_node()
log("Branch class=" + br.get_class().get_name())
then_br = find_pin(br, "then", "Output")
else_br = find_pin(br, "else", "Output")
log("Branch.then -> " + str([(c.get_owning_node().get_name(), str(c.get_pin_name())) for c in conn(then_br)]))
log("Branch.else -> " + str([(c.get_owning_node().get_name(), str(c.get_pin_name())) for c in conn(else_br)]))

# Find Planted! node and its execute connections
planted = None
for n in nodes:
    p = find_pin(n, "InString", "Input")
    if p:
        try:
            if p.get_pin_value() == "Planted!":
                planted = n
        except Exception:
            pass
log("Planted node=" + str(planted.get_name() if planted else None))
if planted:
    ex = find_pin(planted, "execute", "Input")
    th = find_pin(planted, "then", "Output")
    log("Planted.execute <- " + str([(c.get_owning_node().get_name(), c.get_pin_name()) for c in conn(ex)]))
    log("Planted.then -> " + str([(c.get_owning_node().get_name(), c.get_pin_name()) for c in conn(th)]))

# Same for Harvest
harv_ia = None
for n in nodes:
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "InputAction":
            try:
                if "IA_Harvest" in (p.get_pin_value() or ""):
                    harv_ia = n
            except Exception:
                pass
started = find_pin(harv_ia, "Started", "Output")
w2g = conn(started)[0].get_owning_node()
cell = conn(find_pin(w2g, "then", "Output"))[0].get_owning_node()
br = conn(find_pin(cell, "then", "Output"))[0].get_owning_node()
log("Harvest Branch.then -> " + str([(c.get_owning_node().get_name(), c.get_pin_name()) for c in conn(find_pin(br, "then", "Output"))]))
log("Harvest Branch.else -> " + str([(c.get_owning_node().get_name(), c.get_pin_name()) for c in conn(find_pin(br, "else", "Output"))]))

# Default value: try CDO after adding a test int? First check existing GridManagerRef
cdo = bel.get_default_object(bp)
log("CDO GridManagerRef type ok")
# How to set default on new var - check new_variables
try:
    nvs = bp.get_editor_property("new_variables")
    for v in nvs:
        log("nvar name={} default={!r} type={}".format(v.var_name, getattr(v, "default_value", "?"), v.var_type))
except Exception as e:
    log("new_variables " + str(e))

# Widget factory probe
factory = unreal.WidgetBlueprintFactory()
log("WBP factory parent=" + str(factory.get_editor_property("parent_class")))
# WidgetTree helpers
log("WidgetTree methods sample=" + str([x for x in dir(unreal.WidgetTree) if not x.startswith("_")][:40]))
log("has construct_widget=" + str(hasattr(unreal.WidgetTree, "construct_widget")))
