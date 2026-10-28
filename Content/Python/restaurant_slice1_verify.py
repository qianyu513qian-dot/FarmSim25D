import unreal, json
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel=unreal.BlueprintEditorLibrary
actors=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        loc=a.get_actor_location()
        meshes=[(c.get_name(), c.get_editor_property("static_mesh").get_name() if c.get_editor_property("static_mesh") else None)
                for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        tags=[str(t) for t in (a.get_editor_property("tags") or [])]
        label=""
        try: label=a.get_editor_property("InteractLabel")
        except Exception: pass
        actors.append({"label":lab,"xy":[round(loc.x),round(loc.y)],"meshes":meshes,"tags":tags,"InteractLabel":label})
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
chain=[]
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name())=="Started":
                q=[cp.get_owning_node() for cp in p.list_connected_pins()]; seen=set()
                while q and len(chain)<15:
                    x=q.pop(0)
                    if id(x) in seen: continue
                    seen.add(id(x)); chain.append(bel.get_node_title(x))
                    for pp in bel.list_all_pins(x):
                        if "output" in str(pp.get_pin_direction()).lower():
                            for cp in pp.list_connected_pins(): q.append(cp.get_owning_node())
assets=[p for p in [
 "/Game/Farm/Restaurant/BP_RestaurantInteractable",
 "/Game/Farm/Restaurant/BP_RestaurantTable",
 "/Game/Farm/Restaurant/BP_RestaurantStove",
 "/Game/Farm/Restaurant/BP_RestaurantTrash",
 "/Game/Farm/Restaurant/BP_RestaurantOpenSign",
 "/Game/Farm/Restaurant/BP_RestaurantManager"] if unreal.EditorAssetLibrary.does_asset_exist(p)]
rep={"actor_count":len(actors),"actors":actors,"ia_chain":chain,"assets":assets}
open(r"E:\UE\FarmSim25D\Saved\restaurant_slice1_verify.json","w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print(json.dumps(rep,ensure_ascii=False,indent=2))
