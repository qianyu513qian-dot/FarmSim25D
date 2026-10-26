# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))

unreal.log("locals: " + str([str(x) for x in ge.list_local_variable_names()]))
for name in ("LitTilled", "LitEmpty"):
    try:
        unreal.log(name + " type=" + str(ge.get_local_variable_type(name)))
        unreal.log(name + " def=" + str(ge.get_local_variable_default_value(name)))
    except Exception as ex:
        unreal.log_warning(str(ex))

# Try many default formats
for val in [
    "Tilled",
    "NewEnumerator1", 
    "E_PlotState::Tilled",
    "1",
    "(E_PlotState)Tilled",
    '"Tilled"',
    "Empty",
    "NewEnumerator0",
    "0",
]:
    try:
        ge.set_local_variable_default_value("LitTilled", val)
        d = ge.get_local_variable_default_value("LitTilled")
        unreal.log("set LitTilled={!r} -> {!r}".format(val, d))
        if d and str(d) not in ("", "None"):
            break
    except Exception as ex:
        unreal.log_warning("val {}: {}".format(val, ex))

for val in ["Empty", "NewEnumerator0", "0", "E_PlotState::Empty"]:
    try:
        ge.set_local_variable_default_value("LitEmpty", val)
        d = ge.get_local_variable_default_value("LitEmpty")
        unreal.log("set LitEmpty={!r} -> {!r}".format(val, d))
        if d and str(d) not in ("", "None"):
            break
    except Exception as ex:
        unreal.log_warning(str(ex))

# Member variable approach as backup
names = [str(x) for x in bel.list_member_variable_names(bp)]
if "StateTilled" not in names:
    pin = unreal.EdGraphPinType()
    pin.import_text('(PinCategory="byte",PinSubCategory="",PinSubCategoryObject="/Game/Farm/Grid/E_PlotState.E_PlotState",ContainerType=None)')
    bel.add_member_variable(bp, "StateTilled", pin)
    unreal.log("added StateTilled member")
if "StateEmpty" not in names and "StateEmpty" not in [str(x) for x in bel.list_member_variable_names(bp)]:
    pin = unreal.EdGraphPinType()
    pin.import_text('(PinCategory="byte",PinSubCategory="",PinSubCategoryObject="/Game/Farm/Grid/E_PlotState.E_PlotState",ContainerType=None)')
    bel.add_member_variable(bp, "StateEmpty", pin)
    unreal.log("added StateEmpty member")

# Construction script or BeginPlay set them? Defaults via CDO
try:
    cdo = unreal.get_default_object(unreal.load_object(None, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C"))
    unreal.log("cdo=" + str(cdo))
    if cdo:
        for prop in ("StateTilled", "StateEmpty"):
            try:
                unreal.log(prop + " before=" + str(cdo.get_editor_property(prop)))
            except Exception as ex:
                unreal.log_warning(str(ex))
except Exception as ex:
    unreal.log_warning("cdo: " + str(ex))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)

# After compile try CDO again
try:
    gen = unreal.load_object(None, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C")
    cdo = unreal.get_default_object(gen)
    # set enum - might need byte
    for prop, idx in (("StateTilled", 1), ("StateEmpty", 0)):
        try:
            cdo.set_editor_property(prop, idx)
            unreal.log("cdo.{}={}".format(prop, cdo.get_editor_property(prop)))
        except Exception as ex:
            unreal.log_warning("set {}: {}".format(prop, ex))
except Exception as ex:
    unreal.log_warning(str(ex))

# Wire Get StateTilled -> Item instead of local if member works
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
set_elem = None
for n in ge.list_all_nodes():
    if "Set Array" in bel.get_node_title(n):
        set_elem = n
get_t = ge.add_get_member_variable_node("StateTilled")
item = None
for p in bel.list_all_pins(set_elem):
    if str(p.get_pin_name()) == "Item":
        item = p
try:
    item.break_pin_links()
except Exception:
    pass
out = None
for p in bel.list_all_pins(get_t):
    if "OUTPUT" in str(p.get_pin_direction()):
        out = p
ok = out.try_create_connection(item)
unreal.log("StateTilled->Item " + str(ok))

# Equal: Get StateEmpty -> need byte. Use EnumToByte or connect if types match
# Current Equal is Byte - Get returns Enum. Use EnumEquality or cast.
# Simpler: keep Equal.B=0 since Empty=0 and StateEmpty default 0.

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.log("final locals tilled def=" + str(ge.get_local_variable_default_value("LitTilled")))
unreal.log("done")