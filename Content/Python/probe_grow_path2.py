# -*- coding: utf-8 -*-
"""Deep probe: IsValidCell exec on Grow vs Water; IMC DefaultKeyMappings; VisualizeCell update path."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
IMC = "/Game/TopDown/Input/IMC_Default"


def log(m):
    unreal.log("[GROW2] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


def dump_exec_chain(fname):
    bp = unreal.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    log("=== EXEC " + fname + " ===")
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        # dump all exec pins
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            d = str(p.get_pin_direction())
            if pn.lower() in ("execute", "then", "else", "completed", "loopbody") or "exec" in pn.lower():
                cps = list(p.list_connected_pins())
                if cps or pn.lower() == "execute":
                    log("  {}.{} {} -> {}".format(
                        t, pn, d,
                        [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps]))
        if "IsValidCell" in t:
            for p in bel.list_all_pins(n):
                log("  IsValidCell.{} dir={} val=[{}] conn={}".format(
                    p.get_pin_name(), p.get_pin_direction(), pin_val(p),
                    [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]))


for fn in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
    dump_exec_chain(fn)

# IsValidCell function - pure?
log("=== IsValidCell def ===")
bp = unreal.load_asset(MGR)
iv = bel.find_graph(bp, "IsValidCell")
if iv:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(iv)
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            for p in bel.list_all_pins(n):
                log("entry.{} dir={}".format(p.get_pin_name(), p.get_pin_direction()))
            # purity
            try:
                log("entry extras: " + str(n.get_editor_property("meta_data") if False else ""))
            except Exception:
                pass
    # check function flags via bel
    for f in bel.list_functions(bp):
        if str(f.name) == "IsValidCell":
            log("func IsValidCell: " + str(f))
            for attr in ("is_pure", "bIsPureFunc", "function_flags"):
                try:
                    log("  {}: {}".format(attr, f.get_editor_property(attr) if hasattr(f, "get_editor_property") else getattr(f, attr, "?")))
                except Exception as e:
                    log("  {} err {}".format(attr, e))

# IMC DefaultKeyMappings
log("=== IMC DefaultKeyMappings ===")
imc = unreal.load_asset(IMC)
if imc:
    for prop in ("default_key_mappings", "DefaultKeyMappings", "mappings", "Mappings"):
        try:
            val = imc.get_editor_property(prop)
            log("prop {} type={} len={}".format(prop, type(val), len(val) if val is not None and hasattr(val, "__len__") else "n/a"))
            if val:
                for i, m in enumerate(list(val)[:30]):
                    try:
                        # EnhancedActionKeyMapping fields
                        action = None
                        key = None
                        for ap in ("action", "Action", "input_action", "InputAction"):
                            try:
                                action = m.get_editor_property(ap)
                                if action:
                                    break
                            except Exception:
                                pass
                        for kp in ("key", "Key"):
                            try:
                                key = m.get_editor_property(kp)
                                if key:
                                    break
                            except Exception:
                                pass
                        an = action.get_name() if action and hasattr(action, "get_name") else str(action)
                        log("  [{}] action={} key={}".format(i, an, key))
                    except Exception as e:
                        log("  [{}] err {}".format(i, e))
        except Exception as e:
            log("prop {} fail {}".format(prop, e))

# VisualizeCell: valid+update path ApplyState
log("=== VisualizeCell update path ===")
vge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
for n in vge.list_all_nodes():
    t = bel.get_node_title(n)
    if t in ("ApplyState", "Cast To BP_PlotVisual", "Branch", "IsValid", "Get") or "HideGrass" in t or "Print" in t or "SetActor" in t:
        for p in bel.list_all_pins(n):
            pn = str(p.get_pin_name())
            d = str(p.get_pin_direction())
            cps = list(p.list_connected_pins())
            if cps or pn in ("State", "NewHidden", "execute", "then", "else", "Condition"):
                log("  {}.{} {} val=[{}] conn={}".format(
                    t, pn, d, pin_val(p),
                    [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:4]))

log("=== DONE ===")
