# -*- coding: utf-8 -*-
"""Fix ApplySign insertion after Set bIsOpenBusiness + BeginPlay; verify compile."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
CHAR="/Game/TopDown/Blueprints/BP_TopDownCharacter"
R={"steps":[],"errors":[],"ok":[]}
def log(m):
    unreal.log("[FIXSIGN] "+str(m)); print("[FIXSIGN] "+str(m)); R["steps"].append(str(m))
def pos(x,y): return unreal.IntPoint(int(x),int(y))
def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()
def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); R["errors"].append("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok))
    if not ok: R["errors"].append("fail "+label)
    return ok
def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name: return n
    return None

mbp=eas.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Ensure ApplySign customs exist
for nm in ("ApplySignOpen","ApplySignClosed"):
    log(nm+" exists="+str(find_custom(mge,nm) is not None))

# Probe call node creation
for path in [
 MGR+".BP_RestaurantManager_C:ApplySignOpen",
 "/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplySignOpen",
]:
    try:
        n=mge.add_call_function_node(path)
        log("call "+path+" -> "+(title(n) if n else "None")+" class="+(n.get_class().get_name() if n else ""))
        if n:
            pins=[str(p.get_pin_name()) for p in bel.list_all_pins(n)]
            log(" pins "+str(pins))
            mge.remove_nodes([n])
    except Exception as e:
        log("fail "+path+" "+str(e)[:100])

# Find orphaned broken Set bIsOpenBusiness thens (no links)
sets=[]
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    v=val.get_pin_value() if val else "?"
    thenp=find_pin(n,"then","Output")
    links=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
    sets.append({"val":v,"links":links})
R["sets"]=sets
log("sets="+str(sets))

# BeginPlay links
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        thenp=find_pin(n,"then","Output")
        links=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
        R["beginplay"]=links
        log("BeginPlay -> "+str(links))

# Fix: rewire Sets that don't have ApplySign
CALL="/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:"
ybase=100
for n in list(mge.list_all_nodes()):
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    v=(val.get_pin_value() if val else "") or ""
    is_open=str(v).lower() in ("true","1")
    call_name="ApplySignOpen" if is_open else "ApplySignClosed"
    thenp=find_pin(n,"then","Output")
    if not thenp: continue
    links=list(thenp.list_connected_pins() or [])
    if any("ApplySign" in title(c.get_owning_node()) for c in links):
        log("ok already "+call_name); continue
    # Save old targets
    old_tgts=list(links)
    try: thenp.break_pin_links()
    except Exception: pass
    call=mge.add_call_function_node(CALL+call_name)
    if not call:
        R["errors"].append("cannot create "+call_name)
        # restore old
        for t in old_tgts:
            connect(thenp, t, "restore")
        continue
    bel.set_node_pos(call, pos(1200, ybase)); ybase+=200
    connect(thenp, find_pin(call,"execute","Input"), "Set->"+call_name)
    # If call has no then (latent?), still try
    cthen=find_pin(call,"then","Output")
    for t in old_tgts:
        connect(cthen, t, call_name+"->old")
    log("fixed insert "+call_name+" val="+str(v)+" old="+str([title(t.get_owning_node()) for t in old_tgts]))

# Fix BeginPlay
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        thenp=find_pin(n,"then","Output")
        links=list(thenp.list_connected_pins() if thenp else [])
        if any("ApplySignClosed" in title(c.get_owning_node()) for c in links):
            log("BP already closed"); break
        old=list(links)
        try: thenp.break_pin_links()
        except Exception: pass
        call=mge.add_call_function_node(CALL+"ApplySignClosed")
        if call:
            bel.set_node_pos(call, pos(300,-500))
            connect(thenp, find_pin(call,"execute","Input"), "BP->closed")
            for t in old:
                connect(find_pin(call,"then","Output"), t, "closed->old")
            log("fixed BeginPlay")
        else:
            for t in old: connect(thenp,t,"restoreBP")
            R["errors"].append("BP call fail")

bel.compile_blueprint(mbp)
eas.save_asset(MGR)
bel.compile_blueprint(eas.load_asset(CHAR))
eas.save_asset(CHAR)

# re-check sets
sets2=[]
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    v=val.get_pin_value() if val else "?"
    thenp=find_pin(n,"then","Output")
    links=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
    sets2.append({"val":v,"links":links})
R["sets_after"]=sets2
log("sets_after="+str(sets2))

# Verify IA on character
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(eas.load_asset(CHAR)))
ia_nodes=[title(n) for n in cge.list_all_nodes() if "IA_SkipTo17" in title(n) or "RestoreClock" in title(n)]
R["ia_nodes"]=ia_nodes
log("ia="+str(ia_nodes))

# IMC check
imc=eas.load_asset("/Game/TopDown/Input/IMC_Default")
txt=imc.get_editor_property("default_key_mappings").export_text()
R["imc_has_T"]=("Key=T" in txt and "IA_SkipTo17" in txt)
log("IMC T="+str(R["imc_has_T"]))

try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception: pass
try: unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
except Exception: pass

out=unreal.Paths.project_saved_dir()+"restaurant_fixsign.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("DONE err="+str(R["errors"]))
