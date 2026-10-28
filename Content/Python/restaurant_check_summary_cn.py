# -*- coding: utf-8 -*-
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()
def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ev=find_custom(mge,"PrintDayEndSummary")
seen=set(); q=[ev]; nodes=[]
while q:
    cur=q.pop(0)
    if not cur or id(cur) in seen: continue
    seen.add(id(cur)); nodes.append(cur)
    for p in bel.list_all_pins(cur):
        for c in (p.list_connected_pins() or []):
            q.append(c.get_owning_node())
vals=[]
for n in nodes:
    if "Append" in title(n) or "Concat" in title(n):
        for pn in ("A","B"):
            p=find_pin(n,pn,"Input")
            if not p or (p.list_connected_pins()): continue
            try: vals.append(str(p.get_pin_value()))
            except: pass
exp_prefix="\u6253\u70c8 | \u4eca\u65e5\u9910\u5385\u8425\u6536 $"
exp_mid=" | \u670d\u52a1 "
exp_suf=" \u684c"
R={"vals":vals,"match_prefix":exp_prefix in vals,"match_mid":exp_mid in vals,"match_suf":exp_suf in vals,
   "reprs":[repr(v) for v in vals]}
open(r"E:\UE\FarmSim25D\Saved\rest_summary_cn_check.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print("MATCH", R["match_prefix"], R["match_mid"], R["match_suf"])
print("REPRS", R["reprs"])