# -*- coding: utf-8 -*-
"""Probe ge.cast and Tags member access."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PLOT = "/Game/Farm/Grid/BP_PlotVisual"


def main():
    bp = unreal.load_asset(MGR)
    bel.add_function_graph(bp, "ProbeCastTmp")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ProbeCastTmp"))

    unreal.log("ge.cast doc=" + str(ge.cast.__doc__))
    try:
        import inspect
        unreal.log("ge.cast sig=" + str(inspect.signature(ge.cast)))
    except Exception as e:
        unreal.log("sig: " + str(e))

    created = []
    # Try cast with class path / loaded class
    plot_bp = unreal.load_asset(PLOT)
    plot_cls = plot_bp.generated_class()
    unreal.log("plot_cls=" + str(plot_cls))

    for arg in (plot_cls, PLOT, PLOT + "_C", "BP_PlotVisual_C", "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C"):
        try:
            n = ge.cast(arg)
            unreal.log("cast({!r}) -> {}".format(arg, n))
            if n:
                unreal.log("  pins " + str([(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(n)]))
                created.append(n)
                break
        except Exception as e:
            unreal.log("cast fail {!r}: {}".format(arg, e))

    # Tags get
    try:
        n = ge.add_get_member_variable_node("Tags")
        # This gets Tags on self (GridManager) — need target pin for other actor
        unreal.log("get Tags pins=" + str([str(p.get_pin_name()) for p in bel.list_all_pins(n)]))
        created.append(n)
    except Exception as e:
        unreal.log("get Tags: " + str(e))

    # ForEach via ge
    for m in dir(ge):
        if "for" in m.lower() or "loop" in m.lower() or "each" in m.lower():
            unreal.log("ge." + m)

    if hasattr(unreal, "K2Node_ForEachElementInEnum"):
        unreal.log("has foreach enum")
    if hasattr(unreal, "K2Node_MacroInstance"):
        unreal.log("has macro instance")

    # Try add_call for component Tags via Actor
    # Actually use Array_Add on a Make Array? 
    
    if created:
        ge.remove_nodes(created)
    bel.remove_graph(bp, bel.find_graph(bp, "ProbeCastTmp"))
    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("done")


if __name__ == "__main__":
    main()
