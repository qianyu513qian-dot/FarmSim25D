# -*- coding: utf-8 -*-
"""Find where 1020/1380 branches live; dump RefreshTableBubble full data graph; open E path."""
import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
TBL="/Game/Farm/Restaurant/BP_RestaurantTable"

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

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string","get_default_value","get_pin_value"):
        if hasattr(p,fn):
            try: return str(getattr(p,fn)())[:80]
            except: pass
    return None

def dump(n):
    pins={}
    for p in bel.list_all_pins(n):
        links=["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        d=pin_def(p)
        if d or links: pins[str(p.get_pin_name())]={"def":d,"links":links[:8]}
    return {"t":title(n),"cls":n.get_class().get_name(),"pins":pins,"guid":str(n.get_name())}

mbp=eas.load_asset(MGR); mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# For each >=1020/1380 node, walk exec BACKWARD from Branch that uses it
def exec_parents(node, depth=6):
    out=[]; seen=set(); q=[(node,0)]
    while q:
        cur,d=q.pop(0)
        if id(cur) in seen or d>depth: continue
        seen.add(id(cur))
        exe=find_pin(cur,"execute","Input")
        if not exe:
            # custom event / event has 'then' only
            out.append({"t":title(cur),"cls":cur.get_class().get_name(),"is_root":True})
            continue
        froms=list(exe.list_connected_pins() or [])
        out.append({"t":title(cur),"cls":cur.get_class().get_name(),"from_count":len(froms)})
        for c in froms:
            q.append((c.get_owning_node(),d+1))
    return out

clock_info=[]
for n in mge.list_all_nodes():
    if title(n)!="integer >= integer": continue
    b=pin_def(find_pin(n,"B","Input")) or ""
    if b not in ("1020","1380"): continue
    rv=find_pin(n,"ReturnValue","Output")
    for c in (rv.list_connected_pins() or []):
        br=c.get_owning_node()
        if title(br)!="Branch": continue
        then=[title(x.get_owning_node()) for x in ((find_pin(br,"then","Output").list_connected_pins() or []) if find_pin(br,"then","Output") else [])]
        els=[title(x.get_owning_node()) for x in ((find_pin(br,"else","Output").list_connected_pins() or []) if find_pin(br,"else","Output") else [])]
        # deeper then chain
        def chain(start_pin_name, limit=8):
            tp=find_pin(br,start_pin_name,"Output")
            if not tp: return []
            links=list(tp.list_connected_pins() or [])
            if not links: return []
            cur=links[0].get_owning_node(); names=[title(cur)]
            for _ in range(limit):
                t2=find_pin(cur,"then","Output")
                if not t2: break
                ls=list(t2.list_connected_pins() or [])
                if not ls: break
                cur=ls[0].get_owning_node(); names.append(title(cur))
            return names
        clock_info.append({"B":b,"parents":exec_parents(br,8),"then_chain":chain("then"),"else_chain":chain("else"),"branch":dump(br)})
REPORT["clock_info"]=clock_info

# Find open sign E: look for Set bIsOpenBusiness true parents
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=pin_def(find_pin(n,"bIsOpenBusiness","Input"))
    if val!="true": continue
    REPORT["open_true_parents"]=exec_parents(n,10)
    then=find_pin(n,"then","Output")
    REPORT["open_true_then"]=[title(x.get_owning_node()) for x in (then.list_connected_pins() or [])] if then else []

# Table RefreshTableBubble: all nodes in exec chain + data for DrawDebugString Text
tbp=eas.load_asset(TBL); tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
rb=None
for n in tge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RefreshTableBubble":
        rb=n
# collect DrawDebugString and its Text source fully
dds=[]
for n in tge.list_all_nodes():
    if title(n)=="DrawDebugString":
        textp=find_pin(n,"Text","Input")
        # walk back data
        nodes=[]; seen=set(); q=[n]
        while q:
            cur=q.pop(0)
            if id(cur) in seen: continue
            seen.add(id(cur)); nodes.append(dump(cur))
            for p in bel.list_all_pins(cur):
                if "INPUT" not in str(p.get_pin_direction()): continue
                for c in p.list_connected_pins() or []:
                    q.append(c.get_owning_node())
        # exec from
        exe=find_pin(n,"execute","Input")
        dds.append({"exec_from":[title(c.get_owning_node()) for c in (exe.list_connected_pins() or [])] if exe else [], "data":nodes[:30]})
REPORT["drawdebug"]=dds

# PrintStrings that are in RefreshTableBubble chain
def walk_then(start,max_d=30):
    thenp=find_pin(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return seen

if rb:
    chain=walk_then(rb,40)
    REPORT["bubble_exec"]=[title(x) for x in chain]
    # For each PrintString in chain, get Key pin links and InString
    ps=[]
    for x in chain:
        if title(x)!="PrintString": continue
        keyp=find_pin(x,"Key","Input")
        isp=find_pin(x,"InString","Input")
        ps.append({
            "key_def":pin_def(keyp),
            "key_links":["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (keyp.list_connected_pins() or [])] if keyp else [],
            "in_def":pin_def(isp),
            "in_links":["{}.{}".format(title(c.get_owning_node()),c.get_pin_name()) for c in (isp.list_connected_pins() or [])] if isp else [],
            "exec_from":[title(c.get_owning_node()) for c in ((find_pin(x,"execute","Input").list_connected_pins() or []) if find_pin(x,"execute","Input") else [])],
            "then":[title(c.get_owning_node()) for c in ((find_pin(x,"then","Output").list_connected_pins() or []) if find_pin(x,"then","Output") else [])],
        })
    REPORT["bubble_prints"]=ps

# Does table tick pause patience when eating? already designed
for n in tge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "Tick" in title(n):
        REPORT["tick_titles"]=[title(x) for x in walk_then(n,40)]

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat5.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print("clock",len(clock_info),"dds",len(dds),"bubble_prints",len(REPORT.get("bubble_prints") or []))
