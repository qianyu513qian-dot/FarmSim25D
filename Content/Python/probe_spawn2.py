# -*- coding: utf-8 -*-
"""Find SpawnActorFromClass / K2Node spawn APIs."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def main():
    unreal.log("=== probe spawn2 ===")
    # List unreal classes with Spawn in name
    for name in dir(unreal):
        if "Spawn" in name and ("Actor" in name or "K2" in name or "Node" in name):
            unreal.log("unreal." + name)

    bp = unreal.load_asset(MGR)
    # Use a NEW temp function graph so we don't touch EventGraph
    graphs = [str(n) for n in bel.list_graph_names(bp)]
    if "ProbeSpawnTmp" in graphs:
        # clear it
        pass
    else:
        bel.add_function_graph(bp, "ProbeSpawnTmp")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ProbeSpawnTmp"))

    # Try add_node_by_class if exists
    for m in dir(ge):
        if not m.startswith("_") and any(k in m.lower() for k in ("spawn", "create_node", "add_node", "k2")):
            unreal.log("ge." + m)

    created = []
    # Try function paths for spawning
    paths = [
        "/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass",
        "/Script/Engine.GameplayStatics:FinishSpawningActor",
        "/Script/Engine.GameplayStatics:SpawnActor",
        "/Script/Engine.KismetSystemLibrary:SpawnActor",
    ]
    for path in paths:
        try:
            n = ge.add_call_function_node(path)
            if n and len(bel.list_all_pins(n)) > 0:
                pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
                unreal.log("CALL OK {} {}".format(path, pins))
                created.append(n)
            else:
                unreal.log("CALL empty " + path)
                if n:
                    created.append(n)
        except Exception as e:
            unreal.log("CALL FAIL {}: {}".format(path, e))

    # Try K2Node_SpawnActorFromClass via create
    if hasattr(unreal, "K2Node_SpawnActorFromClass"):
        unreal.log("has K2Node_SpawnActorFromClass")
        try:
            # BlueprintGraphEditor may have add_node
            if hasattr(ge, "create_node"):
                n = ge.create_node(unreal.K2Node_SpawnActorFromClass)
                unreal.log("create_node spawn=" + str(n))
                if n:
                    created.append(n)
                    for p in bel.list_all_pins(n):
                        unreal.log("  spawn pin " + str(p.get_pin_name()))
        except Exception as e:
            unreal.log("create_node: " + str(e))
        try:
            if hasattr(ge, "add_node_of_class"):
                n = ge.add_node_of_class(unreal.K2Node_SpawnActorFromClass)
                unreal.log("add_node_of_class=" + str(n))
                if n:
                    created.append(n)
        except Exception as e:
            unreal.log("add_node_of_class: " + str(e))

    # Search create_node_from_name with partial - try many
    names = [
        "SpawnActorFromClass",
        "K2Node_SpawnActorFromClass",
        "Spawn Actor",
        "SpawnActor",
        "Add Actor from Class",
        "Spawn AIController",
    ]
    for name in names:
        try:
            n = ge.create_node_from_name(name, unreal.Vector2D(100, 100), [])
            unreal.log("name {!r} -> {} pins={}".format(
                name, n, len(bel.list_all_pins(n)) if n else 0))
            if n:
                created.append(n)
                for p in bel.list_all_pins(n):
                    unreal.log("  " + str(p.get_pin_name()))
        except Exception as e:
            unreal.log("name fail {}: {}".format(name, e))

    if created:
        ge.remove_nodes(created)

    # Remove temp graph if API exists
    try:
        if hasattr(bel, "remove_graph"):
            bel.remove_graph(bp, bel.find_graph(bp, "ProbeSpawnTmp"))
            unreal.log("removed ProbeSpawnTmp")
        elif hasattr(bel, "delete_graph"):
            bel.delete_graph(bp, "ProbeSpawnTmp")
            unreal.log("deleted ProbeSpawnTmp")
    except Exception as e:
        unreal.log("remove graph: " + str(e))

    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        unreal.log("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("graphs now=" + str([str(n) for n in bel.list_graph_names(bp)]))
    unreal.log("=== probe spawn2 done ===")


if __name__ == "__main__":
    main()
