# -*- coding: utf-8 -*-
"""EMERGENCY: rewire stove cook tick SetCTL -> FX -> done Branch -> ready."""
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

def out_data(node):
    if not node: return None
    for name in ("ReturnValue","CookTimeLeft","bCooking"):
        p=find_pin(node,name,"Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n=str(p.get_pin_name()).lower()
            if n not in ("outputdelegate","then","else"): return p
    return None

def connect(a,b,label,R):
    if a is None or b is None:
        R["errors"].append("skip "+label); return False
    ok=a.try_create_connection(b)
    R["steps"].append("conn[{}] {}".format(label,ok))
    return ok

R={"steps":[],"errors":[]}
sbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
sge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))

# Find Event Tick -> Branch (cook)
tick=None
for n in sge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        tick=n
cook_br=None
if tick:
    for c in (find_pin(tick,"then","Output").list_connected_pins() or []):
        if title(c.get_owning_node())=="Branch":
            cook_br=c.get_owning_node(); break

# Find Set CookTimeLeft fed by cook_br then
tick_set=None
if cook_br:
    for c in (find_pin(cook_br,"then","Output").list_connected_pins() or []):
        if title(c.get_owning_node())=="Set CookTimeLeft":
            tick_set=c.get_owning_node(); break
R["steps"].append("cook_br={} tick_set={}".format(cook_br is not None, tick_set is not None))

# Find DrawDebugBox that was our progress (near Y negative or exec empty / from SetCTL)
boxes=[]
for n in sge.list_all_nodes():
    if title(n)=="DrawDebugBox":
        ex=find_pin(n,"execute","Input")
        feed=[title(c.get_owning_node()) for c in (ex.list_connected_pins() or [])] if ex else []
        th=find_pin(n,"then","Output")
        tos=[title(c.get_owning_node()) for c in (th.list_connected_pins() or [])] if th else []
        boxes.append({"node":n,"feed":feed,"tos":tos})
R["steps"].append("boxes="+str([{"feed":b["feed"],"tos":b["tos"]} for b in boxes]))

# Find done Branch: the one whose then goes to Set bCooking (false) then Set bCookReady
done_br=None
for n in sge.list_all_nodes():
    if title(n)!="Branch": continue
    then_nodes=[c.get_owning_node() for c in (find_pin(n,"then","Output").list_connected_pins() or [])]
    if any(title(t)=="Set bCooking" for t in then_nodes):
        # confirm it's the ready path: Set bCooking then -> Set bCookReady
        for t in then_nodes:
            if title(t)=="Set bCooking":
                nxt=[title(c.get_owning_node()) for c in (find_pin(t,"then","Output").list_connected_pins() or [])]
                if "Set bCookReady" in nxt:
                    done_br=n
                    break
    if done_br: break
R["steps"].append("done_br={}".format(done_br is not None))

# Find progress chain start box: prefer one with then -> PrintString
box=None
for b in boxes:
    if "PrintString" in b["tos"] or any("Print" in t for t in b["tos"]):
        box=b["node"]; break
if box is None and boxes:
    box=boxes[0]["node"]

# Walk FX chain to end then pin
def chain_end(start):
    cur=start; seen=set(); last_then=find_pin(start,"then","Output")
    while cur and id(cur) not in seen:
        seen.add(id(cur))
        tp=find_pin(cur,"then","Output")
        if not tp: break
        nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        if not nxts:
            return tp, cur, list(seen)
        # stop before Branch that is done_br
        if done_br and any(n==done_br for n in nxts):
            return tp, cur, list(seen)
        cur=nxts[0]; last_then=find_pin(cur,"then","Output")
    return last_then, cur, list(seen)

if tick_set and box and done_br:
    # SetCTL then -> box only
    th=find_pin(tick_set,"then","Output")
    th.break_pin_links()
    connect(th, find_pin(box,"execute","Input"), "SetCTL->box", R)

    end_then, end_node, _ = chain_end(box)
    R["steps"].append("fx_end="+title(end_node))
    # disconnect end from anything, then to done_br
    if end_then:
        # if already linked to done_br ok; else break and link
        cur_links=[c.get_owning_node() for c in (end_then.list_connected_pins() or [])]
        R["steps"].append("fx_end_links="+str([title(n) for n in cur_links]))
        if done_br not in cur_links:
            end_then.break_pin_links()
            connect(end_then, find_pin(done_br,"execute","Input"), "fx->doneBr", R)
        else:
            R["steps"].append("already linked to done_br")

    # Ensure done_br execute not also fed by SetCTL (already broke)
    # Ensure cook_br else still has ready highlight branch
    elsep=find_pin(cook_br,"else","Output")
    R["steps"].append("cook_else="+str([title(c.get_owning_node()) for c in (elsep.list_connected_pins() or [])]))
else:
    R["errors"].append("missing pieces tick_set={} box={} done_br={}".format(tick_set is not None, box is not None, done_br is not None))
    # FALLBACK rebuild minimal without FX if needed
    if tick_set and done_br and not box:
        th=find_pin(tick_set,"then","Output")
        th.break_pin_links()
        connect(th, find_pin(done_br,"execute","Input"), "FALLBACK SetCTL->doneBr", R)

bel.compile_blueprint(sbp)
R["status"]=str(sbp.get_editor_property("status"))
if "ERROR" not in R["status"]:
    eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantStove")

# verify then-only walk
def walk_then(start, limit=25):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        tp=find_pin(cur,"then","Output")
        if tp:
            for c in tp.list_connected_pins() or []:
                q.append(c.get_owning_node())
    return chain
R["tick_then"]=walk_then(tick) if tick else []
# also else path
if cook_br:
    R["cook_else_then"]=[]
    for c in (find_pin(cook_br,"else","Output").list_connected_pins() or []):
        R["cook_else_then"]=walk_then(c.get_owning_node(),15)

open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_held_cook_repair.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print(json.dumps(R,indent=2,ensure_ascii=False))
