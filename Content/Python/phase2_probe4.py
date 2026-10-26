import unreal
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# list available with empty array for context
try:
    nodes = cge.list_available_nodes([])
    hits = [str(x) for x in nodes if "Interact" in str(x) or "Enhanced" in str(x) or "Input Key" in str(x) or str(x).endswith("|E") or "Keyboard" in str(x)]
    unreal.log("hits count " + str(len(hits)))
    for h in hits[:40]:
        unreal.log("AVAIL " + h)
except Exception as ex:
    unreal.log_warning("list_available: " + str(ex))

# Try create by class path tricks
for name in [
    "Enhanced Input Action",
    "K2Node_EnhancedInputAction",
    "Input Action Event",
    "Input|Enhanced Action Events|IA_Interact",
    "Add Enhanced Input Action Mapping",
]:
    n = cge.create_node_from_name(name, unreal.Vector2D(100,100), [])
    unreal.log("try {} -> {}".format(name, bool(n)))
    if n:
        unreal.log("  class " + n.get_class().get_name())
        cge.remove_nodes([n])

# Can we set InputAction on existing? Duplicate approach: create node then set property
# Inspect IA_Move InputAction pin
for n in cge.list_all_nodes():
    if "IA_Move" in bel.get_node_title(n):
        ip = None
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "InputAction":
                ip = p
                unreal.log("InputAction pin value=" + str(p.get_default_as_string() if hasattr(p,"get_default_as_string") else "n/a"))
                try:
                    unreal.log("get_pin_value " + str(p.get_pin_value() if hasattr(p,"get_pin_value") else ""))
                except Exception as ex:
                    unreal.log(str(ex))
                for m in dir(p):
                    if "value" in m.lower() or "default" in m.lower() or "text" in m.lower():
                        pass
                unreal.log("pin methods: " + str([m for m in dir(p) if not m.startswith("_") and ("pin" in m.lower() or "value" in m.lower() or "default" in m.lower() or "set" in m.lower())][:40]))

# Try unreal.EditorAssetLibrary load IA and make node via macro
ia = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/Actions/IA_Interact")
unreal.log("ia=" + str(ia))

# Key via Name
try:
    import unreal as u
    # FKey construction
    k = unreal.Key()
    k.set_editor_property("key_name", "E")
    unreal.log("key set by name ok " + str(k))
except Exception as ex:
    unreal.log_warning("key name: " + str(ex))
try:
    k2 = unreal.Name("E")
    unreal.log("Name E " + str(k2))
except Exception as ex:
    unreal.log(str(ex))