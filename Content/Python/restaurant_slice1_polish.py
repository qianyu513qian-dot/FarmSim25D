# -*- coding: utf-8 -*-
"""Polish restaurant slice1: fix meshes/labels, IA exec chain, Print actor label, OpenSign clock gate."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT={"fixes":[],"actors":[]}

def log(m):
    unreal.log("[REST_P] "+str(m)); REPORT["fixes"].append(str(m))

def find_pin(node, name_substr, direction=None):
    if not node: return None
    name_substr=name_substr.lower()
    for p in bel.list_all_pins(node):
        if name_substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

MESH={
    "Restaurant_Table1":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Table2":"/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Stove":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "Restaurant_Trash":"/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "Restaurant_OpenSign":"/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}
LABELS={
    "Restaurant_Table1":"Restaurant: TABLE 1",
    "Restaurant_Table2":"Restaurant: TABLE 2",
    "Restaurant_Stove":"Restaurant: STOVE",
    "Restaurant_Trash":"Restaurant: TRASH",
    "Restaurant_OpenSign":"Restaurant: OPEN SIGN",
}

for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab not in MESH: continue
    need=unreal.EditorAssetLibrary.load_asset(MESH[lab])
    comps=list(a.get_components_by_class(unreal.StaticMeshComponent))
    # Prefer PropMesh_0 / PropMesh; hide empty StaticMesh root duplicates
    chosen=None
    for c in comps:
        if c.get_name() in ("PropMesh_0","PropMesh"):
            chosen=c; break
    if chosen is None and comps:
        chosen=comps[0]
    for c in comps:
        if c is chosen:
            c.set_editor_property("static_mesh", need)
            try: c.set_visibility(True)
            except Exception: pass
            try: c.set_hidden_in_game(False)
            except Exception: pass
            try: c.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
            except Exception: pass
        else:
            # hide extras
            try: c.set_editor_property("static_mesh", None)
            except Exception: pass
            try: c.set_visibility(False)
            except Exception: pass
            try: c.set_hidden_in_game(True)
            except Exception: pass
    try: a.set_editor_property("InteractLabel", LABELS[lab])
    except Exception as e: log("label "+lab+" "+str(e))
    if lab=="Restaurant_Table1":
        try: a.set_editor_property("TableId", 1)
        except Exception: pass
    if lab=="Restaurant_Table2":
        try: a.set_editor_property("TableId", 2)
        except Exception: pass
    # tag
    try:
        tags=list(a.get_editor_property("tags") or [])
        n=unreal.Name("RestInteract")
        if n not in tags:
            tags.append(n); a.set_editor_property("tags", tags)
    except Exception as e: log("tag "+str(e))
    # scale sign a bit taller visibility
    if lab=="Restaurant_OpenSign":
        a.set_actor_scale3d(unreal.Vector(1.4,1.4,1.4))
    if lab=="Restaurant_Stove":
        a.set_actor_scale3d(unreal.Vector(1.2,1.2,1.2))
    log("polished "+lab)

# Hide manager if it has a visible mesh
for a in eas.get_all_level_actors():
    if a.get_actor_label()=="Restaurant_Manager":
        a.set_actor_hidden_in_game(True)
        try: a.set_is_temporarily_hidden_in_editor(True)
        except Exception: pass
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            try: c.set_visibility(False); c.set_hidden_in_game(True)
            except Exception: pass

# ---- Fix character graph: IA->GetPlayerPawn->GetAllActorsWithTag; Print GetActorLabel ----
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

# Find key nodes
ia=None; gat=None; foreach=None; get_pawn=None; till=None; br_near=None; pr_near=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="GetAllActorsWithTag": gat=n
    if "ForEachLoop" in t: foreach=n
    if t=="Get Player Pawn" or t=="GetPlayerPawn": get_pawn=n
    if t=="TillSoil": till=n

# Find branch that feeds Print String with restaurant text
for n in cge.list_all_nodes():
    if bel.get_node_title(n)=="Print String":
        insp=find_pin(n,"InString","Input")
        val=""
        if insp:
            try: val=insp.get_default_as_string()
            except Exception:
                try: val=str(insp.get_pin_value())
                except Exception: val=""
        if "Restaurant" in str(val) or "RestInteract" in str(val) or "near" in str(val).lower():
            pr_near=n
            # find branch feeding it
            ein=find_pin(n,"execute","Input")
            if ein:
                for cp in ein.list_connected_pins():
                    if "Branch" in bel.get_node_title(cp.get_owning_node()):
                        br_near=cp.get_owning_node()

log("ia={} gat={} fe={} pawn={} pr={}".format(bool(ia),bool(gat),bool(foreach),bool(get_pawn),bool(pr_near)))

# Fix exec: IA Started -> GetPlayerPawn -> GetAllActorsWithTag
if ia and gat:
    started=find_pin(ia,"Started","Output")
    if get_pawn is None:
        get_pawn=cge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
        bel.set_node_pos(get_pawn, unreal.IntPoint(-1900,1250))
        try: find_pin(get_pawn,"PlayerIndex","Input").set_default_value("0")
        except Exception: pass
        log("created GetPlayerPawn")
    # break started links and gat execute inbound
    if started:
        try: bel.break_pin_links(started)
        except Exception:
            for cp in list(started.list_connected_pins()):
                try: started.break_link_to(cp)
                except Exception: pass
    gat_exec=find_pin(gat,"execute","Input")
    if gat_exec:
        try: bel.break_pin_links(gat_exec)
        except Exception:
            for cp in list(gat_exec.list_connected_pins()):
                try: gat_exec.break_link_to(cp)
                except Exception: pass
    connect(started, find_pin(get_pawn,"execute","Input"), "IA->pawn")
    connect(find_pin(get_pawn,"then","Output"), gat_exec, "pawn->gat")

# Improve near print: Format with actor label
# Replace pr_near InString connection with Format / GetDisplayName
if pr_near and foreach and br_near:
    # Get actor label from element
    get_label=cge.add_call_function_node("/Script/Engine.Actor:GetActorLabel")
    # may not be available in packaged; use GetHumanReadableName or GetName
    if get_label is None:
        get_label=cge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetDisplayName")
    bel.set_node_pos(get_label, unreal.IntPoint(50,900))
    el=find_pin(foreach,"Array Element","Output") or find_pin(foreach,"Element","Output")
    # GetDisplayName takes Object
    connect(el, find_pin(get_label,"self","Input") or find_pin(get_label,"Object","Input"), "el->name")

    # Build append: "E: " + name
    append=cge.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    bel.set_node_pos(append, unreal.IntPoint(300,900))
    try: find_pin(append,"A","Input").set_default_value("Restaurant E -> ")
    except Exception:
        try: find_pin(append,"A","Input").set_pin_value("Restaurant E -> ")
        except Exception: pass
    connect(find_pin(get_label,"ReturnValue","Output"), find_pin(append,"B","Input"), "name->B")
    # Connect append to Print InString (break old default)
    insp=find_pin(pr_near,"InString","Input")
    if insp:
        try: bel.break_pin_links(insp)
        except Exception: pass
        connect(find_pin(append,"ReturnValue","Output"), insp, "fmt->print")
    log("print uses actor label")

# OpenSign clock-aware: add parallel check — when near and name contains OpenSign, also print clock status
# Optional second branch: keep simple; Manager Tick later.
# Add BeginPlay note on OpenSign via instance? Skip — document FarmClock gate as next knife partial.

# Compile + save
ok=bel.compile_blueprint(cbp)
log("char compile "+str(ok))
# list compile errors
try:
    errs=cge.list_nodes_with_errors()
    REPORT["graph_errors"]=[bel.get_node_title(n) for n in errs]
except Exception as e:
    REPORT["graph_errors"]=str(e)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# Snapshot actors
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if not (lab.startswith("Restaurant_") or lab.startswith("RestChair_")): continue
    loc=a.get_actor_location()
    meshes=[]
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm=c.get_editor_property("static_mesh")
        if sm: meshes.append({"comp":c.get_name(),"mesh":sm.get_name(),"vis":True})
    label=""
    try: label=a.get_editor_property("InteractLabel")
    except Exception: pass
    REPORT["actors"].append({"label":lab,"x":loc.x,"y":loc.y,"meshes":meshes,"InteractLabel":label,"tags":[str(t) for t in (a.get_editor_property("tags") or [])]})

els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save level "+str(els.save_current_level()))
open(r"E:\UE\FarmSim25D\Saved\restaurant_slice1_polish.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps(REPORT,ensure_ascii=False,indent=2))
