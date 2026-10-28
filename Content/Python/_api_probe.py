import unreal
ge_cls = unreal.BlueprintGraphEditor
print([x for x in dir(ge_cls) if "link" in x.lower() or "remove" in x.lower() or "connect" in x.lower() or "break" in x.lower()])
pin_cls = unreal.EdGraphPin
print("PIN", [x for x in dir(pin_cls) if "link" in x.lower() or "break" in x.lower() or "connect" in x.lower()])
