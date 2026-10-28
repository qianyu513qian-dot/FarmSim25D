# -*- coding: utf-8 -*-
"""Trace GetDisplayMinutes branches and bubble Append text; RefreshOrderUI prints."""
import unreal, json
REPORT = {}
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"

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

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string", "get_default_value", "get_pin_value"):
        if hasattr(p, fn):
            try: return str(getattr(p, fn)())[:120]
            except Exception: pass
    return None

def dump(n):
    pins = {}
    for p in bel.list_all_pins(n):
        links = ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in (p.list_connected_pins() or [])]
        d = pin_def(p)
        if d or links:
            pins[str(p.get_pin_name())] = {"def": d, "links": links[:10]}
    return {"t": title(n), "cls": n.get_class().get_name(), "pins": pins}

def walk_back(node, max_d=8):
    """Walk data inputs backward."""
    out = []; seen=set(); q=[(node,0)]
    while q:
        cur,d = q.pop(0)
        if id(cur) in seen or d>max_d: continue
        seen.add(id(cur)); out.append(dump(cur))
        for p in bel.list_all_pins(cur):
            if "INPUT" not in str(p.get_pin_direction()): continue
            for c in p.list_connected_pins() or []:
                q.append((c.get_owning_node(), d+1))
    return out

mbp = eas.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# For each integer >= with B=1020 or 1380, find who uses ReturnValue and exec parents
time_uses = []
for n in mge.list_all_nodes():
    if title(n) != "integer >= integer":
        continue
    bp = find_pin(n, "B", "Input")
    bdef = pin_def(bp) or ""
    if bdef not in ("1020", "1380"):
        continue
    rv = find_pin(n, "ReturnValue", "Output")
    users = []
    for c in (rv.list_connected_pins() or []):
        un = c.get_owning_node()
        users.append({"to": title(un), "pin": str(c.get_pin_name()), "dump": dump(un)})
        # if Branch, get then/else targets
        if title(un) == "Branch":
            for pn in ("then", "else"):
                tp = find_pin(un, pn, "Output")
                tgts = [title(x.get_owning_node()) for x in (tp.list_connected_pins() or [])] if tp else []
                users[-1][pn] = tgts
            # who feeds execute of this branch
            exe = find_pin(un, "execute", "Input")
            users[-1]["exec_from"] = [title(x.get_owning_node()) for x in (exe.list_connected_pins() or [])] if exe else []
    ap = find_pin(n, "A", "Input")
    time_uses.append({"B": bdef, "A_links": ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in (ap.list_connected_pins() or [])] if ap else [], "users": users})
REPORT["time_uses"] = time_uses

# RefreshOrderUI PrintString InString links (header text build)
for n in mge.list_all_nodes():
    if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == "RefreshOrderUI":
        # walk then to PrintString
        thenp = find_pin(n, "then", "Output")
        q = [c.get_owning_node() for c in (thenp.list_connected_pins() or [])]
        seen=set(); chain=[]
        while q:
            cur=q.pop(0)
            if id(cur) in seen: continue
            seen.add(id(cur)); chain.append(cur)
            tp=find_pin(cur,"then","Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
        prints=[]
        for cur in chain:
            if title(cur)=="PrintString":
                isp=find_pin(cur,"InString","Input")
                prints.append({"def": pin_def(isp), "back": walk_back(cur, 6), "key": pin_def(find_pin(cur,"Key","Input"))})
        REPORT["refresh_prints"] = prints

# Also scan ALL PrintString with Key containing Rest
rest_prints=[]
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    key=pin_def(find_pin(n,"Key","Input")) or ""
    instr=pin_def(find_pin(n,"InString","Input")) or ""
    if "Rest" in key or "Order" in key or "order" in instr.lower() or "桌" in instr or "Table" in instr:
        rest_prints.append({"key":key,"instr":instr,"back_titles":[x["t"] for x in walk_back(n,5)]})
REPORT["rest_prints"] = rest_prints[:40]

# Table bubble DrawDebugString Text backwalk + PrintString
tbp = eas.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
bubble_info=[]
for n in tge.list_all_nodes():
    if title(n) in ("DrawDebugString","PrintString"):
        # only those near RefreshTableBubble - check if somehow connected; dump all with Rest key or bubble
        key=pin_def(find_pin(n,"Key","Input")) or ""
        textp=find_pin(n,"Text","Input") or find_pin(n,"InString","Input")
        bubble_info.append({"t":title(n),"key":key,"def":pin_def(textp),"back":walk_back(n,7)})
REPORT["tbl_debug_strings"] = bubble_info[:20]

# Marker check OpenHint
vars=[str(n) for n in bel.list_member_variable_names(mbp, False)]
REPORT["has_OpenHint"] = "OpenHintShownToday" in vars or "bOpenHintShownToday" in vars

open(r"E:\UE\FarmSim25D\Saved\rest_probe_open_eat4.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print("time_uses", len(time_uses), "refresh_prints", len(REPORT.get("refresh_prints") or []), "rest_prints", len(rest_prints))
