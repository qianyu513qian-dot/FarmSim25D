# -*- coding: utf-8 -*-
"""Probe Tags / Array_Add / Cast / ForEach / Array_Length."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def main():
    bp = unreal.load_asset(MGR)
    bel.add_function_graph(bp, "ProbeTagsTmp")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ProbeTagsTmp"))
    created = []
    paths = [
        "/Script/Engine.KismetArrayLibrary:Array_Add",
        "/Script/Engine.KismetArrayLibrary:Array_Length",
        "/Script/Engine.KismetArrayLibrary:Array_Get",
        "/Script/Engine.KismetArrayLibrary:Array_Clear",
        "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte",
        "/Script/Engine.KismetMathLibrary:Greater_IntInt",
        "/Script/Engine.KismetMathLibrary:MakeVector",
        "/Script/Engine.KismetMathLibrary:Add_VectorVector",
        "/Script/Engine.KismetMathLibrary:MakeTransform",
        "/Script/Engine.KismetMathLibrary:MakeRotator",
        "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GridToWorld",
        "/Script/Engine.Actor:K2_SetActorTransform",
        "/Script/Engine.Actor:K2_SetActorLocation",
        "/Script/Engine.Actor:SetActorScale3D",
        "/Script/Engine.Actor:GetActorScale3D",
    ]
    for path in paths:
        try:
            n = ge.add_call_function_node(path)
            if n and len(bel.list_all_pins(n)) > 0:
                unreal.log("OK {} {}".format(path, [str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
                created.append(n)
            else:
                unreal.log("empty " + path)
                if n:
                    created.append(n)
        except Exception as e:
            unreal.log("FAIL {}: {}".format(path, e))

    # ForEach / Cast nodes
    for name in ("For Each Loop", "Utilities|Array|For Each Loop", "Cast To BP_PlotVisual", "Cast to BP_PlotVisual_C"):
        try:
            n = ge.create_node_from_name(name, unreal.Vector2D(10, 10), [])
            unreal.log("name {!r} -> {}".format(name, n))
            if n:
                unreal.log("  pins " + str([str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
                created.append(n)
        except Exception as e:
            unreal.log("name fail {}: {}".format(name, e))

    # Cast via class
    if hasattr(unreal, "K2Node_DynamicCast"):
        unreal.log("has K2Node_DynamicCast")
    if hasattr(ge, "add_cast_node"):
        unreal.log("has add_cast_node")
    for m in dir(ge):
        if "cast" in m.lower() or "foreach" in m.lower() or "loop" in m.lower():
            unreal.log("ge." + m)

    if created:
        ge.remove_nodes(created)
    try:
        bel.remove_graph(bp, bel.find_graph(bp, "ProbeTagsTmp"))
    except Exception as e:
        unreal.log("rm: " + str(e))
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        unreal.log(str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("done graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))


if __name__ == "__main__":
    main()
