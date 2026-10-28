# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary
# find pin type helpers
apis = [x for x in dir(bel) if "pin" in x.lower() or "type" in x.lower() or "variable" in x.lower()]
print("bel apis", apis)
# check docs
for name in apis:
    f=getattr(bel,name)
    doc=getattr(f,"__doc__",None)
    if doc and ("pin_type" in doc.lower() or "variable" in doc.lower() or "make" in name.lower()):
        print("---", name, "---")
        print(doc[:400])

# also check how to change variable type after add
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
# list variables somehow
print("bp methods", [x for x in dir(bp) if "var" in x.lower() or "new" in x.lower()])

# try make pin type
for name in ["make_pin_type","create_pin_type","get_pin_type_from_string"]:
    if hasattr(bel, name):
        print("has", name, bel.__dict__.get(name))
