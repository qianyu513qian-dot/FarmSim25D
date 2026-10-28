# -*- coding: utf-8 -*-
"""Restore BeginPlay -> ApplySignClosed -> EnsureOrderUI."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
CALL="/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:"
R={"steps":[],"errors":[]}
def log(m):
    unreal.log("[BPFIX] "+str(m)); print("[BPFIX] "+str(m)); R["steps"].append(str(m))
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
def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); R["errors"].append(label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok))
    if not ok: R["errors"].append("fail "+label)
    return ok
def pos(x,y): return unreal.IntPoint(int(x),int(y))

mbp=eas.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

bp_ev=None
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        bp_ev=n; break

# Find ApplySignClosed called from BeginPlay
apply=None
thenp=find_pin(bp_ev,"then","Output")
for c in (thenp.list_connected_pins() if thenp else []) or []:
    if title(c.get_owning_node())=="ApplySignClosed":
        apply=c.get_owning_node()

if not apply:
    R["errors"].append("no ApplySignClosed from BeginPlay")
else:
    cthen=find_pin(apply,"then","Output")
    # already has EnsureOrderUI?
    already=False
    for c in (cthen.list_connected_pins() if cthen else []) or []:
        if "EnsureOrderUI" in title(c.get_owning_node()):
            already=True
    if already:
        log("already EnsureOrderUI")
    else:
        # Prefer reconnect orphaned EnsureOrderUI call with empty preds
        orphan=None
        for n in mge.list_all_nodes():
            if title(n)=="EnsureOrderUI" and n.get_class().get_name()=="K2Node_CallFunction":
                ep=find_pin(n,"execute","Input")
                if ep and not list(ep.list_connected_pins() or []):
                    orphan=n; break
        if orphan:
            connect(cthen, find_pin(orphan,"execute","Input"), "closed->EnsureOrderUI orphan")
        else:
            call=mge.add_call_function_node(CALL+"EnsureOrderUI")
            bel.set_node_pos(call, pos(700,-500))
            connect(cthen, find_pin(call,"execute","Input"), "closed->EnsureOrderUI new")

bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# verify chain
cur=bp_ev; chain=[]
for _ in range(8):
    tp=find_pin(cur,"then","Output")
    if not tp or not tp.list_connected_pins(): break
    cur=tp.list_connected_pins()[0].get_owning_node(); chain.append(title(cur))
R["BeginPlay_chain"]=chain
log("BeginPlay chain="+str(chain))

try: unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
except Exception: pass
out=unreal.Paths.project_saved_dir()+"restaurant_beginplay_fix.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("DONE err="+str(R["errors"]))
