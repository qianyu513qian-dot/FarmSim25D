# -*- coding: utf-8 -*-
"""Remap IMC with import_text; verify GrowCell + WaterCell Visualize states; force save."""
import unreal

bel = unreal.BlueprintEditorLibrary
IMC = "/Game/TopDown/Input/IMC_Default"
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_GROW2] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


IA_MAP = {
    "E": "/Game/TopDown/Input/Actions/IA_Interact",
    "F": "/Game/TopDown/Input/Actions/IA_Plant",
    "R": "/Game/TopDown/Input/Actions/IA_Water",
    "G": "/Game/TopDown/Input/Actions/IA_Grow",
    "H": "/Game/TopDown/Input/Actions/IA_Harvest",
}

imc = unreal.load_asset(IMC)
for key_name, ia_path in IA_MAP.items():
    ia = unreal.load_asset(ia_path)
    k = unreal.Key()
    k.import_text(key_name)
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception:
        pass
    m = imc.map_key(ia, k)
    try:
        kt = m.get_editor_property("key").export_text()
    except Exception:
        kt = str(m)
    log("map {} -> {} key_export={}".format(ia.get_name(), key_name, kt))

unreal.EditorAssetLibrary.save_asset(IMC)
txt = imc.get_editor_property("default_key_mappings").export_text()
for key_name, ia_path in IA_MAP.items():
    ia_name = ia_path.rsplit("/", 1)[-1]
    ok = ("Key=" + key_name) in txt and ia_name in txt
    log("IMC_OK {}→{} = {}".format(key_name, ia_name, ok))

# Confirm GrowCell: Equal B=3, Set Item=4, Visualize State=4, IsValidCell executed
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
iv_ok = False
viz_state = None
set_item = None
eq_b = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IsValidCell" in t:
        ep = find_pin(n, "execute", "Input")
        iv_ok = bool(ep and list(ep.list_connected_pins()))
    if "VisualizeCell" in t:
        sp = find_pin(n, "State", "Input")
        viz_state = sp.get_pin_value() if sp else None
    if t == "Set Array Elem" or "Array_Set" in t.replace(" ", ""):
        ip = find_pin(n, "Item", "Input")
        if ip:
            set_item = ip.get_pin_value()
    if "Equal" in t.lower():
        bp_ = find_pin(n, "B", "Input")
        if bp_:
            eq_b = bp_.get_pin_value()

log("GrowCell IsValidCell_exec={} Equal.B={} Set.Item={} Viz.State={}".format(
    iv_ok, eq_b, set_item, viz_state))

# WaterCell viz state
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "WaterCell"))
for n in ge.list_all_nodes():
    if "VisualizeCell" in bel.get_node_title(n):
        sp = find_pin(n, "State", "Input")
        log("WaterCell Viz.State=" + str(sp.get_pin_value() if sp else None))
    if "Equal" in bel.get_node_title(n).lower():
        log("WaterCell Equal.B=" + str(find_pin(n, "B", "Input").get_pin_value()))
    if bel.get_node_title(n) == "Set Array Elem":
        log("WaterCell Set.Item=" + str(find_pin(n, "Item", "Input").get_pin_value()))

# ApplyState 3/4 still Mesh_Grow / Mesh_Mature
pv = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
# Count Get Mesh_Grow / Mesh_Mature connections to SetStaticMesh
grow_links = mature_links = 0
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Mesh_Grow" in t:
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()).upper():
                grow_links += len(list(p.list_connected_pins()))
    if "Mesh_Mature" in t:
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()).upper():
                mature_links += len(list(p.list_connected_pins()))
log("ApplyState Mesh_Grow links={} Mesh_Mature links={}".format(grow_links, mature_links))

unreal.EditorAssetLibrary.save_asset(MGR)
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Grid/BP_PlotVisual")
unreal.EditorAssetLibrary.save_asset(IMC)
try:
    unreal.EditorAssetLibrary.save_directory("/Game/TopDown/Input", True, True)
    unreal.EditorAssetLibrary.save_directory("/Game/Farm/Grid", True, True)
except Exception:
    pass
log("=== DONE ===")
