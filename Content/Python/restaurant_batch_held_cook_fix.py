# -*- coding: utf-8 -*-
"""Fix stove tick: Set CookTimeLeft must ONLY feed progress FX then done Branch (no double exec)."""
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

def connect(a, b, label, R):
    if a is None or b is None:
        R["errors"].append("skip "+label); return False
    ok=a.try_create_connection(b)
    R["steps"].append("conn[{}] {}".format(label, ok))
    if not ok: R["errors"].append("fail "+label)
    return ok

R={"steps":[], "errors":[], "before":{}, "after":{}}

sbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
sge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(sbp))

# Find tick Set CookTimeLeft: the one whose then currently links include Branch and/or DrawDebugBox
tick_set=None
for n in sge.list_all_nodes():
    if title(n)!="Set CookTimeLeft": continue
    ex=find_pin(n,"execute","Input")
    th=find_pin(n,"then","Output")
    froms=[title(c.get_owning_node()) for c in (ex.list_connected_pins() or [])] if ex else []
    tos=[title(c.get_owning_node()) for c in (th.list_connected_pins() or [])] if th else []
    if "Branch" in froms and ("Branch" in tos or "DrawDebugBox" in tos):
        tick_set=n
        R["before"]={"froms":froms,"tos":tos}
        break

if not tick_set:
    R["errors"].append("tick_set not found")
else:
    th=find_pin(tick_set,"then","Output")
    linked=list(th.list_connected_pins() or [])
    box=None; done_br=None; other=[]
    for lp in linked:
        node=lp.get_owning_node()
        t=title(node)
        if t=="DrawDebugBox":
            box=node
        elif t=="Branch":
            done_br=node
        else:
            other.append(t)
    R["steps"].append("box={} done_br={} other={}".format(box is not None, done_br is not None, other))

    # Break ALL then links from SetCTL
    th.break_pin_links()
    R["steps"].append("broke SetCTL then")

    # Find DrawDebugString that is in progress chain (has Key RestCook via Print before it)
    # Prefer: reconnect SetCTL -> DrawDebugBox -> ... -> last DrawDebugString in cooking path -> done_br
    if box is None:
        for n in sge.list_all_nodes():
            if title(n)=="DrawDebugBox":
                # one that is not orphaned — check if execute has no links now
                ex=find_pin(n,"execute","Input")
                if not (ex.list_connected_pins() or []):
                    box=n; break
        if box is None:
            for n in sge.list_all_nodes():
                if title(n)=="DrawDebugBox":
                    box=n; break

    if box and done_br:
        connect(th, find_pin(box,"execute","Input"), "SetCTL->box", R)
        # Walk from box along then until we find a node whose then is empty or points to done_br
        cur=box
        seen=set()
        last_then=find_pin(box,"then","Output")
        while cur and id(cur) not in seen:
            seen.add(id(cur))
            tp=find_pin(cur,"then","Output")
            if not tp: break
            nxts=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
            # remove accidental link to done_br mid-chain
            for lp in list(tp.list_connected_pins() or []):
                if lp.get_owning_node()==done_br:
                    # break only that link — UE may not support single break; break all and rewire properly later
                    pass
            if not nxts:
                last_then=tp
                break
            # if next is done_br, this is the end connector
            if any(n==done_br for n in nxts):
                last_then=tp
                # break and reconnect cleanly once
                tp.break_pin_links()
                break
            cur=nxts[0]
            last_then=find_pin(cur,"then","Output")

        # Ensure done_br execute only from last_then (and not still from SetCTL)
        dex=find_pin(done_br,"execute","Input")
        # Who currently feeds done_br?
        feeders=[title(c.get_owning_node()) for c in (dex.list_connected_pins() or [])] if dex else []
        R["steps"].append("done_br feeders before rewire: "+str(feeders))
        # Break done_br execute links then reconnect only from last FX then
        if dex:
            # break from the other side: each feeder's then that points here
            for lp in list(dex.list_connected_pins() or []):
                feeder_pin=lp  # this is the then pin of feeder
                try:
                    # break all links on that then pin if it's connecting to us — safer break_pin_links on feeder then
                    feeder_pin.break_pin_links()
                except Exception as e:
                    R["errors"].append("break feeder "+str(e)[:60])
        connect(last_then, find_pin(done_br,"execute","Input"), "fxEnd->doneBr", R)

        # Verify
        th2=find_pin(tick_set,"then","Output")
        R["after"]={
            "SetCTL_then":[title(c.get_owning_node()) for c in (th2.list_connected_pins() or [])],
            "done_br_exec":[title(c.get_owning_node()) for c in (find_pin(done_br,"execute","Input").list_connected_pins() or [])],
        }
    else:
        R["errors"].append("missing box or done_br")

bel.compile_blueprint(sbp)
R["status"]=str(sbp.get_editor_property("status"))
if "ERROR" not in R["status"]:
    eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
else:
    for n in sge.list_all_nodes():
        try:
            em=n.get_editor_property("error_msg")
            if em and str(em).strip():
                R["errors"].append(title(n)+":"+str(em)[:160])
        except Exception:
            pass

# final tick walk then-only
def walk_then(start, limit=20):
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

tick=None
for n in sge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        tick=n
R["tick_then_only"]=walk_then(tick) if tick else []

open(r"E:\UE\FarmSim25D\Saved\restaurant_batch_held_cook_fix.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False))
print(json.dumps(R,indent=2,ensure_ascii=False))
