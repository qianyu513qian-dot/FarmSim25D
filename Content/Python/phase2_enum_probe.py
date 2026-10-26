# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"

def find_pin(node, sub, direction=None):
    for p in bel.list_all_pins(node):
        if sub.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

e = unreal.EditorAssetLibrary.load_asset(ENUM)
unreal.log("enum libs:")
for name in dir(unreal):
    if "Enum" in name:
        unreal.log("  " + name)

# Try EnumEditorLibrary
try:
    lib = unreal.EnumEditorLibrary
    for i in range(8):
        try:
            n = lib.get_enumerator_user_facing_name(e, i)
            unreal.log("face[{}]={}".format(i, n))
        except Exception as ex:
            unreal.log("face[{}] err {}".format(i, ex))
            break
    for i in range(8):
        try:
            n = lib.get_enumerator_display_name(e, i) if hasattr(lib, "get_enumerator_display_name") else None
            nm = lib.get_enumerator_name_string(e, i) if hasattr(lib, "get_enumerator_name_string") else None
            unreal.log("disp[{}]={} name={}".format(i, n, nm))
        except Exception as ex:
            unreal.log("disp[{}] {}".format(i, ex))
            break
except Exception as ex:
    unreal.log_warning(str(ex))

# UserDefinedEnumEditorData?
try:
    for i in range(10):
        name = e.get_name_string_by_index(i) if hasattr(e, "get_name_string_by_index") else None
        unreal.log("by_index[{}]={}".format(i, name))
except Exception as ex:
    unreal.log_warning(str(ex))

for m in dir(e):
    if "enum" in m.lower() or "name" in m.lower() or "index" in m.lower():
        if not m.startswith("_"):
            unreal.log("e." + m)

# Fix Equal B and Set Item using byte cast approach:
# Create "Byte To Enum" / "Enum Authority" — or set B via set_pin_value on promotable operator differently
bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
equal = set_elem = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    # title starts with equal (case variants)
    if "Byte" in t and ("qual" in t or "eq" in t.lower()):
        equal = n
        unreal.log("found equal via Byte: " + t)
    if "Set Array" in t:
        set_elem = n

b = find_pin(equal, "B", "Input") if equal else None
item = find_pin(set_elem, "Item", "Input") if set_elem else None

# Try setting as raw byte on Equal B (Empty=0)
if b:
    for v in ["0", "Empty", "NewEnumerator0"]:
        b.set_pin_value(v)
        unreal.log("Equal.B set {} -> {}".format(v, b.get_pin_value()))
    try:
        b.import_text("0")
        unreal.log("B import 0 export="+b.export_text()+" val="+str(b.get_pin_value()))
    except Exception as ex:
        unreal.log_warning(str(ex))

# For Item (enum by ref) - try creating Get enum from a temporary local
# Add local variable? Or use Select node
# Try: call function EnumToByte inverse — ByteToEnum
for path in [
    "/Script/Engine.KismetMathLibrary:Conv_ByteToEnum",
    "/Script/Engine.KismetNodeHelperLibrary:GetEnumeratorName",
]:
    try:
        n = ge.add_call_function_node(path)
        unreal.log("path {} -> {}".format(path, n))
        if n:
            for p in bel.list_all_pins(n):
                unreal.log("  " + str(p.get_pin_name()))
            ge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning(str(ex))

# create_node Enum
for name in [
    "Enum Authority",
    "Byte to Enum",
    "To Enum",
    "E_PlotState literal",
    "Make Literal Byte",
    "Literal Byte",
    "Utilities|Enum|Enum to Byte",
]:
    try:
        n = ge.create_node_from_name(name, unreal.Vector2D(0, 0), [])
        unreal.log("create {} -> {}".format(name, bel.get_node_title(n) if n else None))
        if n:
            for p in bel.list_all_pins(n):
                unreal.log("  " + str(p.get_pin_name()) + " " + p.get_pin_type_display_string())
            ge.remove_nodes([n])
    except Exception as ex:
        unreal.log_warning("{}: {}".format(name, ex))

# Verify center still linked
for n in ge.list_all_nodes():
    if "DrawDebug" in bel.get_node_title(n):
        c = find_pin(n, "Center", "Input")
        unreal.log("dbg center conn=" + str(len(list(c.list_connected_pins()))))
        for cp in list(c.list_connected_pins()):
            unreal.log("  from " + bel.get_node_title(cp.get_owning_node()) + "." + str(cp.get_pin_name()))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.log("done")