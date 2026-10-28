# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {}

def vars_of(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    names = list(bel.list_member_variable_names(bp, False))
    out = {}
    for n in names:
        t = bel.get_member_variable_type(bp, n)
        out[n] = bel.pin_type_to_json_schema(t, None) if t else None
    return out

R["mgr"] = vars_of("/Game/Farm/Restaurant/BP_RestaurantManager")
R["tbl"] = vars_of("/Game/Farm/Restaurant/BP_RestaurantTable")
R["stove"] = vars_of("/Game/Farm/Restaurant/BP_RestaurantStove") if unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Restaurant/BP_RestaurantStove") else "missing"
R["trash"] = vars_of("/Game/Farm/Restaurant/BP_RestaurantTrash") if unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Restaurant/BP_RestaurantTrash") else "missing"
R["interact"] = vars_of("/Game/Farm/Restaurant/BP_RestaurantInteractable") if unreal.EditorAssetLibrary.does_asset_exist("/Game/Farm/Restaurant/BP_RestaurantInteractable") else "missing"

# list restaurant assets
assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant", True, False)
R["assets"] = [str(a) for a in assets]

# money / currency search
hits = []
for root in ["/Game", "/Game/Farm", "/Game/TopDown", "/Game/Cropout"]:
    try:
        for a in unreal.EditorAssetLibrary.list_assets(root, True, False):
            s = str(a).lower()
            if any(k in s for k in ("money", "currency", "wallet", "gold", "coin", "resource")):
                hits.append(str(a))
    except Exception:
        pass
R["money_assets"] = hits[:40]

# C++ classes?
for name in ["FarmMoney", "MoneyComponent", "ResourceStore", "InventoryComponent", "FarmPlayerState", "FarmGameState"]:
    o = unreal.load_object(None, "/Script/FarmSim25D." + name)
    R.setdefault("cpp", {})[name] = str(o) if o else None

# Manager graph customs
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
R["mgr_customs"] = [bel.get_node_title(n) for n in ge.list_all_nodes() if n.get_class().get_name() in ("K2Node_CustomEvent","K2Node_Event")]
R["mgr_status"] = str(bp.get_editor_property("status"))

# Table
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
R["tbl_status"] = str(tbp.get_editor_property("status"))
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
R["tbl_customs"] = [bel.get_node_title(n) for n in tge.list_all_nodes() if n.get_class().get_name() in ("K2Node_CustomEvent","K2Node_Event")]

# How HandlePlayerE branches labels now
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "Contains":
        pins = {}
        for p in bel.list_all_pins(n):
            pins[str(p.get_pin_name())] = {"val": p.get_pin_value(), "to": [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]}
        R.setdefault("contains", []).append(pins)

# Character
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
ia = {}
for n in cge.list_all_nodes():
    t = bel.get_node_title(n)
    if "IA_Interact" in t:
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "Started":
                ia["Started"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
    if t == "TillSoil":
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "execute":
                ia["TillSoil"] = [bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]
R["ia"] = ia

# FarmClock minutes ok
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_probe.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps({k:R[k] for k in ("mgr","tbl","stove","trash","interact","assets","money_assets","cpp","mgr_customs","tbl_customs","mgr_status","tbl_status","ia","contains")}, indent=2, ensure_ascii=False, default=str)[:12000])