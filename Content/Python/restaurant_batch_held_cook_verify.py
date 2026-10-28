# -*- coding: utf-8 -*-
"""Fix stove DrawDebugString Text (FText) + verify chains + WBP compile."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def walk(start, limit=25):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

R={"fixes":[], "errors":[]}

# Fix DrawDebugString Text on stove — set default 做菜中
sbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
sge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))
for n in sge.list_all_nodes():
    if title(n)!="DrawDebugString":
        continue
    tp=find_pin(n,"Text","Input")
    if not tp: continue
    links=tp.list_connected_pins() or []
    if links:
        continue
    # unconnected Text — set default
    try:
        tp.set_pin_value("做菜中")
        R["fixes"].append("dds Text set")
    except Exception:
        try:
            tp.set_default_value("做菜中"); R["fixes"].append("dds default")
        except Exception as e:
            R["errors"].append(str(e)[:100])
    # also try MakeLiteralText / Conv_StringToText if needed
    # Check pin type
    try:
        R["dds_text_type"]=str(tp.get_pin_type_display_string())
    except Exception:
        pass

bel.compile_blueprint(sbp)
R["stove"]=str(sbp.get_editor_property("status"))
if "ERROR" not in R["stove"]:
    eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantStove")

# verify tick chain
tick=None
for n in sge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        tick=n
R["stove_tick"]=walk(tick,20) if tick else []

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
bel.compile_blueprint(mbp)
R["mgr"]=str(mbp.get_editor_property("status"))
rt=None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        rt=n
R["RestaurantTick"]=walk(rt,20) if rt else []

# WBP
wbp=eas.load_asset("/Game/Farm/UI/WBP_RestOrderList")
if wbp:
    try:
        bel.compile_blueprint(wbp)
        R["wbp"]=str(wbp.get_editor_property("status"))
    except Exception as e:
        # WidgetBlueprint compile
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(wbp)
            R["wbp"]=str(wbp.get_editor_property("status"))
        except Exception as e2:
            R["wbp_err"]=str(e2)[:120]
    # look for TxtMoney
    try:
        wd=wbp.get_editor_property("widget_tree")
        R["has_widget_tree"]=wd is not None
    except Exception:
        pass

open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_held_cook_verify.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print(json.dumps(R,indent=2,ensure_ascii=False))
