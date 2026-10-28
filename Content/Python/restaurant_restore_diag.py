# -*- coding: utf-8 -*-
"""Diagnose broken open/close chains after ApplySign insert; restore Print/GuestTimer."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
R={"steps":[]}
def log(m):
    unreal.log("[RESTORE] "+str(m)); print("[RESTORE] "+str(m)); R["steps"].append(str(m))
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
def walk(start, max_d=40):
    thenp=find_pin(start,"then","Output")
    queue=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    # also Started etc
    seen=[]; ids=set()
    while queue:
        cur,d=queue.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(),d+1))
    return seen

mbp=eas.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Dump all PrintString with Restaurant open/close text and their exec preds
prints=[]
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    inp=find_pin(n,"InString","Input")
    v=(inp.get_pin_value() if inp else "") or ""
    if any(k in v for k in ("OPEN","CLOSED","AUTO CLOSE","too early","too late","Guests","Sign:")):
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
        thenp=find_pin(n,"then","Output")
        succs=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
        prints.append({"text":v[:90],"preds":preds,"succs":succs})
R["prints"]=prints
log("prints="+str(prints))

# Set GuestTimer nodes
for n in mge.list_all_nodes():
    if title(n)=="Set GuestTimer":
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
        thenp=find_pin(n,"then","Output")
        succs=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
        log("Set GuestTimer preds="+str(preds)+" succs="+str(succs))

# ApplySign then chains
for nm in ("ApplySignOpen","ApplySignClosed"):
    for n in mge.list_all_nodes():
        if title(n)==nm and n.get_class().get_name()=="K2Node_CallFunction":
            thenp=find_pin(n,"then","Output")
            succs=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
            ep=find_pin(n,"execute","Input")
            preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
            log("CALL "+nm+" preds="+str(preds)+" succs="+str(succs))

# HandlePlayerE full-ish dump: all Contains OpenSign related
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="HandlePlayerE":
        chain=[title(x) for x in walk(n,60)]
        R["HandlePlayerE"]=chain
        log("HPE "+str(chain))

# RestaurantTick
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)=="RestaurantTick":
        chain=[title(x) for x in walk(n,80)]
        R["RestaurantTick"]=chain
        log("RT "+str(chain[:60]))

# Orphaned Print with OPEN that has no preds
orphans=[]
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    inp=find_pin(n,"InString","Input")
    v=(inp.get_pin_value() if inp else "") or ""
    if "OPEN for business" in v or "CLOSED (early)" in v or "AUTO CLOSE" in v:
        ep=find_pin(n,"execute","Input")
        preds=list(ep.list_connected_pins() if ep else [])
        if not preds:
            orphans.append(v[:80])
R["orphan_prints"]=orphans
log("orphans="+str(orphans))

out=unreal.Paths.project_saved_dir()+"restaurant_restore_diag.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("WROTE")
