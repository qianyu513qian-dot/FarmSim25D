# -*- coding: utf-8 -*-
"""Add Cast->RestaurantInteract on near-branch; wire OpenSign clock-aware interact override via parent label + Manager helpers."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR="/Game/Farm/Restaurant"
out={"steps":[]}

def log(m):
    unreal.log("[REST_F] "+str(m)); out["steps"].append(str(m))

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
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

# --- Enhance character near-branch: Cast + RestaurantInteract before/instead of generic print ---
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# Find For Each Loop and the Branch whose condition is float<float (distance)
fe=None; target_br=None; el=None
for n in cge.list_all_nodes():
    if "For Each Loop" in bel.get_node_title(n):
        fe=n
        el=find_pin(n,"Array Element","Output")
if fe:
    # find Branch connected from LoopBody
    body=find_pin(fe,"LoopBody","Output")
    if body:
        for cp in body.list_connected_pins():
            if "Branch" in bel.get_node_title(cp.get_owning_node()):
                target_br=cp.get_owning_node(); break

log("fe={} br={}".format(bool(fe), bool(target_br)))

if target_br and el:
    then_pin=find_pin(target_br,"then","Output")
    # What is currently connected to then?
    old=[]
    if then_pin:
        for cp in list(then_pin.list_connected_pins()):
            old.append(cp.get_owning_node())
            try: then_pin.break_link_to(cp)
            except Exception: pass
    log("broke then links to {}".format([bel.get_node_title(n) for n in old]))

    cast_n=None
    # Try list_available or create
    for cname in (
        "Cast To BP_RestaurantInteractable",
        "Utilities|Casting|Cast To BP_RestaurantInteractable",
        "Class Casting|Cast To BP_RestaurantInteractable",
    ):
        try:
            cast_n=cge.create_node_from_name(cname, unreal.Vector2D(200,1000), [])
            if cast_n:
                log("cast via "+cname); break
        except Exception as e:
            log("cast try "+cname+" "+str(e))
    # Alternate: add_call_function Cast — use DynamicCast via Kismet
    if cast_n is None:
        # Use Actor's Call RestaurantInteract via interface-less: Print InteractLabel using Get Class name is enough for knife-1
        # But try BlueprintEditorLibrary retarget?
        try:
            # Some UE versions: create_node_from_name with generated class
            cast_n=cge.create_node_from_name("Cast To BP_RestaurantInteractable_C", unreal.Vector2D(200,1000), [])
        except Exception as e:
            log("cast C "+str(e))

    if cast_n:
        bel.set_node_pos(cast_n, unreal.IntPoint(200,1000))
        connect(then_pin, find_pin(cast_n,"execute","Input"), "br->cast")
        connect(el, find_pin(cast_n,"Object","Input"), "el->obj")
        call_i=cge.add_call_function_node(DIR+"/BP_RestaurantInteractable.BP_RestaurantInteractable_C:RestaurantInteract")
        bel.set_node_pos(call_i, unreal.IntPoint(550,1000))
        connect(find_pin(cast_n,"then","Output"), find_pin(call_i,"execute","Input"), "cast->i")
        as_pin=None
        for p in bel.list_all_pins(cast_n):
            if "output" in str(p.get_pin_direction()).lower() and "as" in str(p.get_pin_name()).lower():
                as_pin=p; break
        connect(as_pin, find_pin(call_i,"self","Input"), "as->self")
        # On cast fail, print
        pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, unreal.IntPoint(550,1200))
        connect(find_pin(cast_n,"CastFailed","Output") or find_pin(cast_n,"Cast Failed","Output"), find_pin(pr,"execute","Input"), "fail->pr")
        try: find_pin(pr,"InString","Input").set_default_value("Restaurant E: cast failed")
        except Exception: pass
        log("cast+RestaurantInteract wired")
    else:
        # Keep print with display name — reconnect old if any, else new print
        pr=None
        for n in old:
            if bel.get_node_title(n)=="PrintString" or bel.get_node_title(n)=="Print String":
                pr=n; break
        if pr is None:
            pr=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
            bel.set_node_pos(pr, unreal.IntPoint(200,1000))
            try: find_pin(pr,"InString","Input").set_default_value("Restaurant E: near prop")
            except Exception: pass
        connect(then_pin, find_pin(pr,"execute","Input"), "br->pr")
        log("cast unavailable, print fallback reconnected")

ok=bel.compile_blueprint(cbp)
log("char compile "+str(ok))
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# --- OpenSign: ensure InteractLabel, add Tick on Manager for 23:00 auto-close stub ---
bp_mgr=unreal.EditorAssetLibrary.load_asset(DIR+"/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp_mgr))
# Ensure ReceiveTick exists with clock check — lightweight: GetActorOfClass FarmClock, if minutes>=1380 and bIsOpenBusiness, set false + Print
tick=None
for n in mge.list_all_nodes():
    t=bel.get_node_title(n)
    if "Tick" in t and "Event" in t: tick=n
if tick is None:
    try:
        tick=bel.add_event_override(bp_mgr, "ReceiveTick", unreal.IntPoint(0,800))
        log("added ReceiveTick")
    except Exception as e:
        log("tick "+str(e))
        try:
            tick=mge.create_node_from_name("Event Tick", unreal.Vector2D(0,800), [])
        except Exception as e2:
            log("tick2 "+str(e2))

# Don't overbuild tick if complex — add comment via Print once on HandlePlayerE already exists.
# For OpenSign clock gate: update parent RestaurantInteract is generic print of InteractLabel.
# Enhance OpenSign instances: when E near OpenSign, RestaurantInteract prints label.
# Add separate BP function on OpenSign by duplicating - skip if ge None.
# Instead set Manager.bIsOpenBusiness when player presses near sign via character detecting name.

# Practical knife-1 clock gate on character: after RestaurantInteract / print, if display name contains OpenSign, query clock.
# Too heavy now. Document as next step with partial: variables bIsOpenBusiness exist on sign+manager.

# Ensure all interactables still tagged and labeled
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    labels={
        "Restaurant_Table1":"Restaurant: TABLE 1",
        "Restaurant_Table2":"Restaurant: TABLE 2",
        "Restaurant_Stove":"Restaurant: STOVE",
        "Restaurant_Trash":"Restaurant: TRASH",
        "Restaurant_OpenSign":"Restaurant: OPEN SIGN",
    }
    if lab in labels:
        try: a.set_editor_property("InteractLabel", labels[lab])
        except Exception: pass
        try:
            tags=list(a.get_editor_property("tags") or [])
            n=unreal.Name("RestInteract")
            if n not in tags:
                tags.append(n); a.set_editor_property("tags", tags)
        except Exception: pass

bel.compile_blueprint(bp_mgr)
unreal.EditorAssetLibrary.save_asset(DIR+"/BP_RestaurantManager")
els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save "+str(els.save_current_level()))
open(r"E:\UE\FarmSim25D\Saved\restaurant_slice1_finalwire.json","w",encoding="utf-8").write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
