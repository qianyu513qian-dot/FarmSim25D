# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
R = {"statuses": {}, "trash": [], "notes": []}

def find_pin(node, substr, direction=None):
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def follow(start, max_d=20):
    out = []; vis=set(); q=[(start,0)]
    while q:
        cur,d=q.pop(0)
        if id(cur) in vis or d>max_d: continue
        vis.add(id(cur)); out.append(bel.get_node_title(cur))
        for pn in ("then","else","LoopBody"):
            p=find_pin(cur,pn,"Output")
            if not p: continue
            for cp in p.list_connected_pins():
                q.append((cp.get_owning_node(), d+1))
    return out

paths = [
    "/Game/Farm/Restaurant/BP_RestaurantManager",
    "/Game/Farm/Restaurant/BP_RestaurantStove",
    "/Game/Farm/Restaurant/BP_RestaurantTable",
]
for a in unreal.EditorAssetLibrary.list_assets("/Game", True, False):
    if a.rstrip("/").endswith("BP_TopDownCharacter") or a.endswith("BP_TopDownCharacter.BP_TopDownCharacter"):
        paths.append(a.split(".")[0])
        break

for path in paths:
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        continue
    bp = unreal.EditorAssetLibrary.load_asset(path)
    bel.compile_blueprint(bp)
    st = str(bp.get_editor_property("status"))
    R["statuses"][path.split("/")[-1]] = st
    if "ERROR" not in st:
        unreal.EditorAssetLibrary.save_asset(path)

mbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
for n in mge.list_all_nodes():
    if bel.get_node_title(n) == "HandleTrashE":
        R["trash"] = follow(n)
        break

# TableId on instances
try:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = subsystem.get_all_level_actors()
    tids = []
    for a in actors:
        name = a.get_name()
        if "RestaurantTable" in name or "Restaurant_Table" in name:
            try:
                tid = a.get_editor_property("TableId")
            except Exception:
                tid = "?"
            tids.append((name, tid))
    R["table_ids"] = tids
except Exception as e:
    R["notes"].append(str(e))

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_final.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False))