# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
# docs for key methods
keys=["add_function_graph","add_member_variable","add_event_override","compile_blueprint","find_graph","get_graph_editor"]
out={}
for k in keys:
    fn=getattr(bel,k,None)
    out[k]=str(fn.__doc__)[:500] if fn else None
# BlueprintGraphEditor methods
ge_cls=unreal.BlueprintGraphEditor
out["ge_methods"]=[m for m in dir(ge_cls) if not m.startswith("_") and any(x in m.lower() for x in ("create","add","custom","event","function","call","node"))]
# try create custom event node names
out["sample"]=out["ge_methods"]
open(r"E:\UE\FarmSim25D\Saved\bp_api.json","w",encoding="utf-8").write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2)[:3000])
