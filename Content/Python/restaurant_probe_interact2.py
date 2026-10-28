# -*- coding: utf-8 -*-
"""Deep dump IA_Interact / TillSoil pins on character."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
out=[]
for n in ge.list_all_nodes():
    t=bel.get_node_title(n)
    cn=n.get_class().get_name()
    if any(k in str(t) for k in ("IA_Interact","TillSoil","TillCell","Money")) or cn in ("K2Node_CustomEvent","K2Node_CallFunction","K2Node_EnhancedInputAction"):
        pins=[]
        for p in bel.list_all_pins(n):
            conns=[]
            for c in p.list_connected_pins():
                try: ct=bel.get_node_title(c.get_owning_node())
                except: ct="?"
                conns.append({"node":ct,"pin":str(c.get_pin_name())})
            pins.append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"conns":conns})
        try:
            pos=n.get_editor_property("node_pos_x"), n.get_editor_property("node_pos_y")
        except Exception:
            pos=None
        out.append({"title":t,"class":cn,"pos":pos,"pins":pins})
open(r"E:\UE\FarmSim25D\Saved\interact_deep.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
# also list BlueprintEditorLibrary helpers of interest
helpers=[m for m in dir(bel) if any(k in m.lower() for k in ("custom","event","function","variable","compile","graph"))]
open(r"E:\UE\FarmSim25D\Saved\bel_helpers.json","w",encoding="utf-8").write(json.dumps(helpers,indent=2))
print("nodes",len(out),"helpers",len(helpers))
for o in out:
    if "IA_Interact" in o["title"] or o["title"]=="TillSoil":
        print(o["title"], o["class"], o["pos"])
        for p in o["pins"]:
            if p["conns"] or "exec" in p["name"].lower() or p["name"] in ("Started","Triggered","then","execute"):
                print(" ",p["name"],p["dir"],p["conns"][:3])
