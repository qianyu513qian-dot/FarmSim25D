# -*- coding: utf-8 -*-
"""Add EnumLiteral for Tilled/Empty; keep DrawDebug visual. Conservative."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, sub, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if sub.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def main():
    unreal.log("=== phase2_enum_literal start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))

    # Try create EnumLiteral node
    lit = None
    for name in [
        "EnumLiteral",
        "Enum Literal",
        "Utilities|Enum|EnumLiteral",
        "K2Node_EnumLiteral",
    ]:
        try:
            lit = ge.create_node_from_name(name, unreal.Vector2D(600, 350), [])
            if lit:
                unreal.log("created via name " + name + " title=" + bel.get_node_title(lit))
                break
        except Exception as ex:
            unreal.log_warning(name + ": " + str(ex))

    if not lit:
        # construct node class directly
        try:
            lit = ge.add_node(unreal.K2Node_EnumLiteral.static_class(), unreal.Vector2D(600, 350))
            unreal.log("add_node EnumLiteral -> " + str(lit))
        except Exception as ex:
            unreal.log_warning("add_node: " + str(ex))
        try:
            # alternate APIs on graph editor
            for m in dir(ge):
                if "enum" in m.lower() or "literal" in m.lower() or "add_node" in m.lower():
                    unreal.log("ge." + m)
        except Exception:
            pass

    if lit:
        for p in bel.list_all_pins(lit):
            unreal.log("lit pin {} type={} val={}".format(
                p.get_pin_name(), p.get_pin_type_display_string(),
                (p.get_pin_value() if hasattr(p, "get_pin_value") else "")))
        # Set enum type / value via properties
        for prop in dir(lit):
            if "enum" in prop.lower() or "value" in prop.lower() or "class" in prop.lower():
                if not prop.startswith("_"):
                    unreal.log("lit." + prop)
        try:
            lit.set_editor_property("enum", unreal.EditorAssetLibrary.load_asset(ENUM))
            unreal.log("set enum prop ok")
        except Exception as ex:
            unreal.log_warning("set enum: " + str(ex))
        try:
            # EnumLiteral has Enum property and maybe pin
            unreal.log("after set pins:")
            for p in bel.list_all_pins(lit):
                unreal.log("  {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
        except Exception:
            pass
        # Try set value index 1 = Tilled
        for method in ("set_enum_value", "set_value", "select_enumerator"):
            if hasattr(lit, method):
                unreal.log("has " + method)

    # CastByteToEnum approach: literal byte 1 -> cast to E_PlotState
    cast = None
    try:
        cast = ge.add_node(unreal.K2Node_CastByteToEnum.static_class(), unreal.Vector2D(600, 500))
        unreal.log("cast node " + str(cast))
    except Exception as ex:
        unreal.log_warning(str(ex))
    if cast:
        for p in bel.list_all_pins(cast):
            unreal.log("cast pin {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
        for prop in ("enum", "Enum", "bSafe"):
            try:
                cast.set_editor_property(prop, unreal.EditorAssetLibrary.load_asset(ENUM) if "enum" in prop.lower() else True)
                unreal.log("cast set " + prop)
            except Exception as ex:
                unreal.log_warning(prop + ": " + str(ex))
        for p in bel.list_all_pins(cast):
            unreal.log("cast2 {} {} val={}".format(p.get_pin_name(), p.get_pin_type_display_string(), p.get_pin_value() if hasattr(p,'get_pin_value') else ''))

    # EnumEquality instead of Equal Byte?
    try:
        eqe = ge.add_node(unreal.K2Node_EnumEquality.static_class(), unreal.Vector2D(400, 600))
        unreal.log("EnumEquality " + str(eqe))
        if eqe:
            for p in bel.list_all_pins(eqe):
                unreal.log("  eqe {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
            ge.remove_nodes([eqe])
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Wire cast(1) -> Set Item if cast works
    set_elem = None
    equal = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if "Set Array" in t:
            set_elem = n
        if "Byte" in t and "qual" in t:
            equal = n

    if cast and set_elem:
        # set byte input to 1
        binp = find_pin(cast, "Byte", "Input") or find_pin(cast, "InByte", "Input") or find_pin(cast, "b", "Input")
        # find any input that's not exec
        for p in bel.list_all_pins(cast):
            if "INPUT" in str(p.get_pin_direction()):
                unreal.log("cast input candidate " + str(p.get_pin_name()))
                try:
                    p.set_pin_value("1")
                    unreal.log("  set to 1 -> " + str(p.get_pin_value()))
                except Exception as ex:
                    unreal.log_warning(str(ex))
        out = find_pin(cast, "Return", "Output") or find_pin(cast, "Out", "Output")
        for p in bel.list_all_pins(cast):
            if "OUTPUT" in str(p.get_pin_direction()):
                unreal.log("cast out " + str(p.get_pin_name()))
                out = p
        item = find_pin(set_elem, "Item", "Input")
        try:
            item.break_pin_links()
        except Exception:
            pass
        connect(out, item, "cast->item")

    # Also make Empty literal byte 0 on Equal.B (already 0)
    if equal:
        b = find_pin(equal, "B", "Input")
        b.set_pin_value("0")
        unreal.log("Equal.B=" + str(b.get_pin_value()))

    # Clean failed lit if unused
    # Keep cast if connected

    # Verify full success chain: Set -> GridToWorld -> DrawDebug -> Return
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t in ("Set Array Elem", "GridToWorld", "DrawDebugBox", "Return Node", "MakeVector"):
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) in ("then", "execute", "Center", "Item", "Success", "World Location"):
                    cps = list(p.list_connected_pins())
                    unreal.log("{} .{} conn={} val={}".format(
                        t, p.get_pin_name(), len(cps),
                        (p.get_pin_value() if hasattr(p, "get_pin_value") else "")))
                    for cp in cps:
                        unreal.log("    -> {} .{}".format(bel.get_node_title(cp.get_owning_node()), cp.get_pin_name()))

    try:
        bel.compile_blueprint(bp)
        unreal.log("compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("=== done ===")


if __name__ == "__main__":
    main()