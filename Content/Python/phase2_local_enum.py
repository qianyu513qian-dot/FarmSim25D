# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))

# Search available nodes for Enum
try:
    avail = ge.list_available_nodes()
    unreal.log("avail type=" + str(type(avail)) + " len=" + str(len(avail) if hasattr(avail,"__len__") else "?"))
    count = 0
    for a in avail:
        s = str(a)
        if "enum" in s.lower() or "Enum" in s or "literal" in s.lower():
            unreal.log("AVAIL: " + s)
            count += 1
            if count > 40:
                break
    unreal.log("enum-related count shown")
except Exception as ex:
    unreal.log_warning(str(ex))

# add_local_variable of enum type, set default Tilled, Get it
try:
    # add local TilledVal
    pin = unreal.EdGraphPinType()
    pin.import_text('(PinCategory="byte",PinSubCategory="",PinSubCategoryObject="/Game/Farm/Grid/E_PlotState.E_PlotState",ContainerType=None)')
    ge.add_local_variable("LitTilled", pin)
    unreal.log("added local LitTilled")
    ge.set_local_variable_default_value("LitTilled", "Tilled")
    unreal.log("default=" + str(ge.get_local_variable_default_value("LitTilled")))
    getn = ge.add_get_local_variable_node("LitTilled")
    unreal.log("get local " + str(getn))
    if getn:
        for p in bel.list_all_pins(getn):
            unreal.log("  {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
        # connect to Set Item
        set_elem = None
        for n in ge.list_all_nodes():
            if "Set Array" in bel.get_node_title(n):
                set_elem = n
        out = None
        for p in bel.list_all_pins(getn):
            if "OUTPUT" in str(p.get_pin_direction()):
                out = p
        item = None
        for p in bel.list_all_pins(set_elem):
            if str(p.get_pin_name()) == "Item":
                item = p
        try:
            item.break_pin_links()
        except Exception:
            pass
        ok = out.try_create_connection(item)
        unreal.log("local->item " + str(ok))
except Exception as ex:
    unreal.log_warning("local var: " + str(ex))

# Also Empty local for Equal.B - Equal is byte so need EnumToByte
try:
    pin = unreal.EdGraphPinType()
    pin.import_text('(PinCategory="byte",PinSubCategory="",PinSubCategoryObject="/Game/Farm/Grid/E_PlotState.E_PlotState",ContainerType=None)')
    if "LitEmpty" not in [str(x) for x in ge.list_local_variable_names()]:
        ge.add_local_variable("LitEmpty", pin)
    ge.set_local_variable_default_value("LitEmpty", "Empty")
    unreal.log("LitEmpty default=" + str(ge.get_local_variable_default_value("LitEmpty")))
except Exception as ex:
    unreal.log_warning(str(ex))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.log("done")