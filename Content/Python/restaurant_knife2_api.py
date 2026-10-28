import unreal, json
bel=unreal.BlueprintEditorLibrary
bp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantInteractable")
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,"RestaurantInteract") if hasattr(bel,"find_graph") else None)
# list function graphs via uber
graphs=[]
# try get ubergraph from asset
from unreal import BlueprintEditorLibrary as B
# dump function names via BlueprintEditorLibrary
print("has find_event", hasattr(bel,"find_event_graph"))
# OpenSign graphs
for name in ("BP_RestaurantOpenSign","BP_RestaurantTable","BP_RestaurantManager","BP_RestaurantStove","BP_RestaurantTrash"):
    p="/Game/Farm/Restaurant/"+name
    b=unreal.EditorAssetLibrary.load_asset(p)
    # member functions via K2
    try:
        ub=b
        # list editable properties of CDO custom
        cdo=unreal.get_default_object(b.generated_class()) if b.generated_class() else None
    except Exception as e:
        cdo=None
    custom=[v for v in bel.list_member_variable_names(b) if not str(v).startswith("/Script") and "BP_Restaurant" not in str(v) and "Actor." not in str(v)]
    print(name, "custom_vars", custom)
# Can we add CallFunction RestaurantInteract?
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
# try paths
for path in [
 "/Game/Farm/Restaurant/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract",
 "/Script/Engine.GameplayStatics:GetAllActorsOfClass",
 "/Script/Engine.GameplayStatics:GetAllActorsWithTag",
]:
    try:
        n=cge.add_call_function_node(path)
        print("OK", path, bel.get_node_title(n) if n else None)
        if n: cge.remove_nodes([n])
    except Exception as e:
        print("FAIL", path, e)
