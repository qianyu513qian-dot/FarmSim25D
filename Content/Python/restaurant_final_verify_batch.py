# -*- coding: utf-8 -*-
"""Final verify: BeginPlay, pay chains, IA, compile status, BeginPlay parent."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
R={"steps":[]}
def log(m):
    unreal.log("[VERIFY] "+str(m)); print("[VERIFY] "+str(m)); R["steps"].append(str(m))
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
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name: return n
    return None
def chain(ge,name,maxn=12):
    ev=find_custom(ge,name)
    if not ev: return []
    out=[]; cur=ev
    for _ in range(maxn):
        tp=find_pin(cur,"then","Output")
        if not tp or not tp.list_connected_pins(): break
        cur=tp.list_connected_pins()[0].get_owning_node(); out.append(title(cur))
    return out

MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
CHAR="/Game/TopDown/Blueprints/BP_TopDownCharacter"
mbp=eas.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
cbp=eas.load_asset(CHAR)
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# BeginPlay
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
        thenp=find_pin(n,"then","Output")
        links=[title(c.get_owning_node()) for c in (thenp.list_connected_pins() if thenp else [])]
        R["BeginPlay"]=links
        log("BeginPlay="+str(links))
        # Is there Parent BeginPlay node orphaned?
    if "Parent" in title(n) and "BeginPlay" in title(n):
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
        log("Parent BeginPlay preds="+str(preds))

# If Parent BeginPlay orphaned, wire ApplySignClosed -> Parent
parent_bp=None
for n in mge.list_all_nodes():
    if "Parent" in title(n) and "BeginPlay" in title(n):
        parent_bp=n
if parent_bp:
    ep=find_pin(parent_bp,"execute","Input")
    if ep and not list(ep.list_connected_pins() or []):
        # find BeginPlay -> ApplySignClosed
        for n in mge.list_all_nodes():
            if n.get_class().get_name()=="K2Node_Event" and "BeginPlay" in title(n):
                thenp=find_pin(n,"then","Output")
                for c in thenp.list_connected_pins() or []:
                    own=c.get_owning_node()
                    if title(own)=="ApplySignClosed":
                        cthen=find_pin(own,"then","Output")
                        if cthen:
                            ok=cthen.try_create_connection(ep)
                            log("ApplySignClosed->Parent BeginPlay "+str(ok))

R["salad"]=chain(mge,"OnGuestPaidSalad")
R["stew"]=chain(mge,"OnGuestPaidStew")
R["grant"]=chain(cge,"GrantMoney_Salad")
log("salad="+str(R["salad"]))
log("grant="+str(R["grant"]))

# IA
ia=[title(n) for n in cge.list_all_nodes() if "SkipTo17" in title(n) or title(n)=="RestoreClock"]
R["ia"]=ia
# Started connected?
for n in cge.list_all_nodes():
    if "IA_SkipTo17" in title(n):
        st=find_pin(n,"Started","Output")
        R["ia_started"]=[title(c.get_owning_node()) for c in (st.list_connected_pins() if st else [])]
        log("IA started="+str(R["ia_started"]))

# IMC
imc=eas.load_asset("/Game/TopDown/Input/IMC_Default")
txt=imc.get_editor_property("default_key_mappings").export_text()
R["imc_T"]=("Key=T" in txt and "IA_SkipTo17" in txt)

# Tag check
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor.static_class()):
    if a.get_actor_label()=="RestMark_OpenSign":
        R["mark_tags"]=[str(t) for t in (a.tags or [])]
        log("mark tags="+str(R["mark_tags"]))

bel.compile_blueprint(mbp)
bel.compile_blueprint(cbp)
eas.save_asset(MGR); eas.save_asset(CHAR)
try: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception: pass
try: unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
except Exception: pass

out=unreal.Paths.project_saved_dir()+"restaurant_final_verify.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("DONE")
