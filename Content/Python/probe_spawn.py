# -*- coding: utf-8 -*-
"""Probe spawn/format/tag nodes available in GridManager graph editor."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def main():
    unreal.log("=== probe spawn ===")
    bp = unreal.load_asset(MGR)
    # Temporary graph for probing? Use EventGraph carefully — only add then remove
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    tests = [
        "Spawn Actor from Class",
        "Gameplay|Spawn Actor from Class",
        "Actor|Spawn Actor from Class",
        "Get All Actors with Tag",
        "Gameplay|Get All Actors with Tag",
        "Utilities|String|Format",
        "Format Text",
        "Concat_StrStr",
        "Build String (Integer)",
    ]
    created = []
    for name in tests:
        try:
            n = ge.create_node_from_name(name, unreal.Vector2D(50, 50), [])
            if n:
                pins = [(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(n)]
                unreal.log("OK {} pins={}".format(name, pins[:20]))
                created.append(n)
            else:
                unreal.log("NONE " + name)
        except Exception as e:
            unreal.log("FAIL {}: {}".format(name, e))

    # Also try add_call_function_node paths
    paths = [
        "/Script/Engine.GameplayStatics:GetAllActorsWithTag",
        "/Script/Engine.GameplayStatics:SpawnObject",
        "/Script/Engine.KismetSystemLibrary:GetActorListFromComponentList",
        "/Script/Engine.KismetStringLibrary:Concat_StrStr",
        "/Script/Engine.KismetStringLibrary:Conv_IntToString",
        "/Script/Engine.KismetStringLibrary:Conv_StringToName",
        "/Script/Engine.KismetMathLibrary:Add_VectorVector",
        "/Script/Engine.KismetMathLibrary:MakeTransform",
        "/Script/Engine.Actor:K2_DestroyActor",
        "/Script/Engine.Actor:AddActorWorldOffset",
        "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C:ApplyState",
    ]
    for path in paths:
        try:
            n = ge.add_call_function_node(path)
            if n and len(bel.list_all_pins(n)) > 0:
                pins = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
                unreal.log("CALL OK {} pins={}".format(path, pins))
                created.append(n)
            else:
                unreal.log("CALL empty/None " + path)
                if n:
                    created.append(n)
        except Exception as e:
            unreal.log("CALL FAIL {}: {}".format(path, e))

    if created:
        ge.remove_nodes(created)
        unreal.log("removed probe nodes " + str(len(created)))
    # Do NOT compile EventGraph churn if possible — still save? skip compile to be safe
    unreal.log("=== probe spawn done ===")


if __name__ == "__main__":
    main()
