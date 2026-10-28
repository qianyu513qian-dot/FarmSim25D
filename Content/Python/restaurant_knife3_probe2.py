# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rows = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if not lab.startswith("Restaurant_"):
        continue
    row = {"label": lab, "cls": a.get_class().get_name()}
    for prop in ("table_id", "TableId", "b_occupied", "bOccupied", "current_order", "CurrentOrder"):
        try:
            row[prop] = str(a.get_editor_property(prop))
        except Exception:
            pass
    rows.append(row)
# search blueprints for AddMoney / Gold
hits = []
reg = unreal.AssetRegistryHelpers.get_asset_registry()
# grep project python/cpp mentions
import os
for root, dirs, files in os.walk(r"E:\UE\FarmSim25D\Source"):
    for f in files:
        if f.endswith((".h", ".cpp")):
            p = os.path.join(root, f)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read().lower()
            except Exception:
                continue
            if "money" in txt or "gold" in txt or "currency" in txt or "wallet" in txt:
                hits.append(p)
R = {"actors": rows, "src_hits": hits[:30]}
# Can custom event have inputs?
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")))
print("add_graph_input", hasattr(ge, "add_graph_input_parameter"), ge.add_graph_input_parameter.__doc__[:200] if hasattr(ge, "add_graph_input_parameter") else None)
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_probe2.json","w",encoding="utf-8").write(json.dumps(R, indent=2))
print(json.dumps(R, indent=2, ensure_ascii=False)[:4000])