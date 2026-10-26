import unreal
bel = unreal.BlueprintEditorLibrary
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
nodes = cge.list_available_nodes([])
for n in nodes:
    s = str(n)
    if "IA_Interact" in s or "IA_Move" in s or "Enhanced Input Action" in s or "EnhancedInputAction" in s:
        unreal.log("EI " + s)
for n in nodes:
    s = str(n)
    if "Keyboard Events" in s and ("|E" in s or s.endswith("E") or "|F|" in s or "Space" in s):
        unreal.log("KB " + s)
# also Input Key
for n in nodes:
    s = str(n)
    if s.startswith("Input|") and ("Key" in s or "Keyboard" in s):
        unreal.log("IN " + s)
# count Input|
ins = [str(n) for n in nodes if str(n).startswith("Input|")]
unreal.log("Input| count " + str(len(ins)))
for s in ins[:50]:
    unreal.log("IN2 " + s)