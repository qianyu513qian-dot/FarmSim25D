import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))

for path in [
    "/Script/Engine.KismetArrayLibrary:Array_Get",
    "/Script/Engine.KismetArrayLibrary:Array_Set",
    "/Script/Engine.KismetArrayLibrary:Get",
    "/Script/Engine.KismetArrayLibrary:SetArrayElem",
    "/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte",
    "/Script/Engine.KismetMathLibrary:NotEqual_ByteByte",
]:
    n = ge.add_call_function_node(path)
    unreal.log("call {} -> {}".format(path, n))
    if n:
        for p in bel.list_all_pins(n):
            unreal.log("  " + str(p.get_pin_name()) + " | " + str(p.get_pin_direction()))
        ge.remove_nodes([n])

# Enhanced input on character
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
# Find IA_Move node and dump class
for n in cge.list_all_nodes():
    if "IA_Move" in bel.get_node_title(n):
        unreal.log("IA_Move class=" + n.get_class().get_name() + " path=" + n.get_class().get_path_name())
        for p in bel.list_all_pins(n):
            unreal.log("  " + str(p.get_pin_name()))
        # properties
        try:
            unreal.log("props: " + str(n.get_editor_property("input_action") if False else "n/a"))
        except Exception as ex:
            unreal.log(str(ex))
        for prop in ("input_action", "InputAction", "action", "ActionAsset"):
            try:
                unreal.log(prop + "=" + str(n.get_editor_property(prop)))
            except Exception:
                pass

# try create enhanced input for IA_Interact
for name in [
    "EnhancedInputAction IA_Interact",
    "IA_Interact",
    "Add Enhanced Input Action Event",
]:
    n = cge.create_node_from_name(name, unreal.Vector2D(0, 0), [])
    unreal.log("create {} -> {}".format(name, n))
    if n:
        for p in bel.list_all_pins(n):
            unreal.log("  " + str(p.get_pin_name()))
        cge.remove_nodes([n])

# InputKey node
for name in ["Keyboard Events|E", "E", "Any Key", "InputKey"]:
    n = cge.create_node_from_name(name, unreal.Vector2D(0,0), [])
    unreal.log("keycreate {} -> {}".format(name, n))
    if n:
        dump = [(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(n)]
        unreal.log(str(dump))
        cge.remove_nodes([n])