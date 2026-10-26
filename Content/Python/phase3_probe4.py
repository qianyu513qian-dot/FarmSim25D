# -*- coding: utf-8 -*-
"""Probe enum count via graph nodes + BeginPlay fill values."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"


def main():
    unreal.log("=== phase3_probe4 ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    eg = bel.find_event_graph(bp)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if any(k in t for k in ("BeginPlay", "Array", "Plot", "Empty", "Add", "ForLoop", "Clear", "Enum", "MakeLiteral")):
            unreal.log("EG: " + t)
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = ""
                unreal.log("  {} = [{}] conn={}".format(p.get_pin_name(), v, len(list(p.list_connected_pins()))))

    # Create temp EnumLiteral / GetNumEnumEntries in a scratch way via TillCell graph
    tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    # Add GetNumEnumEntries node
    try:
        node = tge.create_node_from_name("Utilities|Enum|Get Number of Enum Entries", unreal.Vector2D(50, 800), [])
        unreal.log("GetNum node=" + str(node) + " title=" + bel.get_node_title(node))
        for p in bel.list_all_pins(node):
            unreal.log("  pin {} val=[{}]".format(p.get_pin_name(), p.get_pin_value() if hasattr(p, "get_pin_value") else ""))
            # try set enum
            if "Enum" in str(p.get_pin_name()) or "enum" in str(p.get_pin_name()).lower():
                for cand in ("E_PlotState", "/Game/Farm/Grid/E_PlotState.E_PlotState", "E_PlotState::Empty"):
                    try:
                        p.set_pin_value(cand)
                        unreal.log("set enum pin -> " + str(p.get_pin_value()))
                    except Exception as ex:
                        unreal.log_warning(str(ex))
        # remove after probe
        tge.remove_nodes([node])
    except Exception as ex:
        unreal.log_warning("GetNum: " + str(ex))

    # Try EnumLiteral node
    try:
        lit = tge.create_node_from_name("Utilities|Enum|Enum Literal", unreal.Vector2D(50, 900), [])
        unreal.log("lit title=" + bel.get_node_title(lit))
        for p in bel.list_all_pins(lit):
            try:
                v = p.get_pin_value()
            except Exception:
                v = ""
            unreal.log("  lit pin {} = [{}]".format(p.get_pin_name(), v))
        # remove
        tge.remove_nodes([lit])
    except Exception as ex:
        unreal.log_warning("lit: " + str(ex))

    # Try K2Node_GetNumEnumEntries via add
    try:
        n2 = tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetEnumeratorNameAsString")  # wrong
    except Exception:
        pass

    # Use unreal.Enum base: NumEnums is C++ - try ctypes? skip.
    # Recreate enum properly with names via factory duplicate approach
    en = unreal.EditorAssetLibrary.load_asset(ENUM)
    # Try set_editor_property DisplayNames via python reflection of UUserDefinedEnum
    # In UE source: TMap<FName, FText> DisplayNameMap is protected
    # Try EditorUtilityLibrary or AssetTools rename
    try:
        # Duplicate approach: delete and recreate? RISKY - would break PlotStates type
        # Instead add enumerators if API exists on EditorScripting
        for name in dir(unreal):
            if "EditorScripting" in name or "AssetEditor" in name:
                pass
        # Check unreal.EditorAssetLibrary for enum helpers - none
        unreal.log("trying FEnumEditorUtils via exec? skip")
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Count via Array_Add on PlotStates default - BeginPlay fills Empty
    # Read compiled bytecode? Too hard.
    # Simply: set LitTilled default to 1 and LitEmpty to 0 - LitEmpty already 0
    try:
        tge.set_local_variable_default_value("LitTilled", "1")
        unreal.log("LitTilled after set1=" + str(tge.get_local_variable_default_value("LitTilled")))
        tge.set_local_variable_default_value("LitTilled", "NewEnumerator1")
        unreal.log("LitTilled after NewEnumerator1=" + str(tge.get_local_variable_default_value("LitTilled")))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Probe how many NewEnumerator exist by setting Equal.B to 0,1,2,3 and reading back
    for n in tge.list_all_nodes():
        if "Equal" in bel.get_node_title(n).lower():
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "B":
                    for cand in ("0", "1", "2", "NewEnumerator0", "NewEnumerator1", "NewEnumerator2", "Empty", "Tilled", "Seeded", "Planted"):
                        try:
                            p.set_pin_value(cand)
                            unreal.log("Equal.B set {!r} -> {!r}".format(cand, p.get_pin_value()))
                        except Exception as ex:
                            unreal.log_warning("equal.B {}: {}".format(cand, ex))
                    # restore Empty=0
                    p.set_pin_value("0")
                    unreal.log("restored equal.B=" + str(p.get_pin_value()))

    unreal.log("=== done ===")


if __name__ == "__main__":
    main()
