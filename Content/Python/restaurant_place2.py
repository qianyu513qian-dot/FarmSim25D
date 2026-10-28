# -*- coding: utf-8 -*-
"""Place south-dock restaurant ONLY. No E wiring. Never touch non-Restaurant actors."""
import unreal, json
from collections import Counter

bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
DIR = "/Game/Farm/Restaurant"
REPORT = {"steps": [], "placed": [], "errors": [], "e_changed": False}

MESH = {
    "Restaurant_Table1": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Table2": "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest",
    "Restaurant_Stove": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Storage/SM_VMF_Set_CrateStack",
    "Restaurant_Trash": "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Facilities/SM_VMF_Facility_CompostBin",
    "Restaurant_OpenSign": "/Game/Farm/VoxelMicroFarm/Models/Expansion01/SM_VMF_Prop_FarmSign",
}
CHAIR_MESH = "/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_Crate"

# Tight to south bridge east exit (bridge xmax~1680, deck y~450-550)
ZONE = {
    "Restaurant_OpenSign": (1720.0, 500.0, 2.0),
    "Restaurant_Table1":   (1820.0, 450.0, 2.0),
    "RestChair_t1a":       (1820.0, 380.0, 2.0),
    "RestChair_t1b":       (1820.0, 520.0, 2.0),
    "Restaurant_Table2":   (1950.0, 450.0, 2.0),
    "RestChair_t2a":       (1950.0, 380.0, 2.0),
    "RestChair_t2b":       (1950.0, 520.0, 2.0),
    "Restaurant_Stove":    (1850.0, 620.0, 2.0),
    "Restaurant_Trash":    (1720.0, 620.0, 2.0),
    "Restaurant_Manager":  (1880.0, 540.0, 80.0),
}

LABELS = {
    "Restaurant_Table1": "Restaurant: TABLE 1",
    "Restaurant_Table2": "Restaurant: TABLE 2",
    "Restaurant_Stove": "Restaurant: STOVE",
    "Restaurant_Trash": "Restaurant: TRASH",
    "Restaurant_OpenSign": "Restaurant: OPEN SIGN",
}

def log(m):
    unreal.log("[REST_PLACE2] " + str(m))
    REPORT["steps"].append(str(m))

def farm_census():
    c = Counter()
    total = 0
    rest = 0
    for a in eas.get_all_level_actors():
        total += 1
        lab = a.get_actor_label() or ""
        if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
            rest += 1
        if lab.startswith("VMF_Grass"): c["VMF_Grass"] += 1
        elif lab.startswith("VMF_Path"): c["Path"] += 1
        elif "Bridge" in lab or "Pier" in lab: c["BridgePier"] += 1
        elif "Tree" in lab: c["Tree"] += 1
        elif lab.startswith("VMF_Water") or (lab.startswith("VMF_") and "Water" in lab): c["Water"] += 1
        elif "House" in lab or "FarmShed" in lab or "Well" in lab or "Chicken" in lab: c["Buildings"] += 1
        elif "PlayerStart" in lab: c["PlayerStart"] += 1
    return {"total": total, "restaurant": rest, "farm": dict(c)}

def tag_rest(actor):
    try:
        tags = list(actor.get_editor_property("tags") or [])
    except Exception:
        tags = []
    n = unreal.Name("RestInteract")
    if n not in tags:
        tags.append(n)
        try:
            actor.set_editor_property("tags", tags)
        except Exception as e:
            log("tag fail " + str(e))

def force_mesh(actor, mesh_path):
    need = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if not need:
        REPORT["errors"].append("missing mesh " + mesh_path)
        return
    comps = list(actor.get_components_by_class(unreal.StaticMeshComponent))
    order = ["PropMesh_0", "PropMesh", "StaticMeshComponent0", "StaticMesh"]
    chosen = None
    for name in order:
        for c in comps:
            if c.get_name() == name:
                chosen = c
                break
        if chosen:
            break
    if not chosen and comps:
        chosen = comps[0]
    for c in comps:
        if c is chosen:
            c.set_editor_property("static_mesh", need)
            try:
                c.set_visibility(True)
                c.set_hidden_in_game(False)
            except Exception:
                pass
        else:
            try:
                c.set_editor_property("static_mesh", None)
            except Exception:
                pass
            try:
                c.set_visibility(False)
                c.set_hidden_in_game(True)
            except Exception:
                pass

def set_label_prop(actor, text):
    for k in ("InteractLabel", "interact_label"):
        try:
            actor.set_editor_property(k, text)
            return
        except Exception:
            pass

# ---- 0) BEFORE census ----
before = farm_census()
REPORT["before"] = before
log("before total={} farm={}".format(before["total"], before["farm"]))
if before["farm"].get("VMF_Grass", 0) < 1000:
    REPORT["errors"].append("ABORT: grass suspiciously low before place")
    open(r"E:\UE\FarmSim25D\Saved\restaurant_place2.json", "w", encoding="utf-8").write(
        json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    raise SystemExit(0)

# ---- 1) Clear ONLY leftover Restaurant_*/RestChair_* (should be 0) ----
removed = 0
for a in list(eas.get_all_level_actors()):
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        eas.destroy_actor(a)
        removed += 1
log("cleared_old_restaurant={}".format(removed))

mid = farm_census()
REPORT["after_clear"] = mid
# farm keys must match before (totals may drop by restaurant only)
for k, v in before["farm"].items():
    if mid["farm"].get(k, 0) != v:
        REPORT["errors"].append("ABORT: farm key {} changed {}->{}".format(k, v, mid["farm"].get(k)))
        open(r"E:\UE\FarmSim25D\Saved\restaurant_place2.json", "w", encoding="utf-8").write(
            json.dumps(REPORT, ensure_ascii=False, indent=2))
        print(json.dumps(REPORT, ensure_ascii=False, indent=2))
        raise SystemExit(0)

# ---- 2) Load BPs ----
bps = {}
for name in ("BP_RestaurantTable", "BP_RestaurantStove", "BP_RestaurantTrash",
             "BP_RestaurantOpenSign", "BP_RestaurantManager"):
    path = DIR + "/" + name
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        REPORT["errors"].append("missing BP " + path)
        continue
    bps[name] = unreal.EditorAssetLibrary.load_asset(path)

if REPORT["errors"]:
    open(r"E:\UE\FarmSim25D\Saved\restaurant_place2.json", "w", encoding="utf-8").write(
        json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    raise SystemExit(0)

def spawn_bp(bp, location, label, extra=None):
    cls = bp.generated_class()
    if not cls:
        bel.compile_blueprint(bp)
        cls = bp.generated_class()
    actor = eas.spawn_actor_from_class(cls, unreal.Vector(*location), unreal.Rotator())
    if not actor:
        REPORT["errors"].append("spawn fail " + label)
        return None
    actor.set_actor_label(label)
    if label != "Restaurant_Manager":
        tag_rest(actor)
    if label in LABELS:
        set_label_prop(actor, LABELS[label])
    if extra:
        for k, v in extra.items():
            try:
                actor.set_editor_property(k, v)
            except Exception as e:
                log("prop {} {}: {}".format(label, k, e))
    if label in MESH:
        force_mesh(actor, MESH[label])
    REPORT["placed"].append({"label": label, "x": location[0], "y": location[1], "z": location[2]})
    log("spawn " + label)
    return actor

# Tables
spawn_bp(bps["BP_RestaurantTable"], ZONE["Restaurant_Table1"], "Restaurant_Table1",
         {"table_id": 1})
spawn_bp(bps["BP_RestaurantTable"], ZONE["Restaurant_Table2"], "Restaurant_Table2",
         {"table_id": 2})
spawn_bp(bps["BP_RestaurantStove"], ZONE["Restaurant_Stove"], "Restaurant_Stove")
spawn_bp(bps["BP_RestaurantTrash"], ZONE["Restaurant_Trash"], "Restaurant_Trash")
spawn_bp(bps["BP_RestaurantOpenSign"], ZONE["Restaurant_OpenSign"], "Restaurant_OpenSign",
         {"b_is_open_business": False})
mgr = spawn_bp(bps["BP_RestaurantManager"], ZONE["Restaurant_Manager"], "Restaurant_Manager",
               {"b_is_open_business": False, "interact_range": 280.0})
if mgr:
    try:
        mgr.set_editor_property("tags", [])
    except Exception:
        pass
    try:
        mgr.set_is_temporarily_hidden_in_editor(True)
    except Exception:
        try:
            mgr.set_actor_hidden_in_game(True)
        except Exception:
            pass

# Chairs (StaticMeshActor, RestChair_ prefix)
chair_mesh = unreal.EditorAssetLibrary.load_asset(CHAIR_MESH)
for key in ("RestChair_t1a", "RestChair_t1b", "RestChair_t2a", "RestChair_t2b"):
    loc = ZONE[key]
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator())
    if not a:
        REPORT["errors"].append("chair fail " + key)
        continue
    a.set_actor_label(key)
    try:
        a.static_mesh_component.set_editor_property("static_mesh", chair_mesh)
        a.set_actor_scale3d(unreal.Vector(0.7, 0.7, 0.55))
    except Exception as e:
        log("chair mesh " + str(e))
    REPORT["placed"].append({"label": key, "x": loc[0], "y": loc[1], "z": loc[2]})
    log("spawn " + key)

# ---- 3) AFTER census + safety ----
after = farm_census()
REPORT["after"] = after
log("after total={} restaurant={} farm={}".format(after["total"], after["restaurant"], after["farm"]))

delta = after["total"] - before["total"]
REPORT["delta_total"] = delta
# Expected: +10 if no prior restaurant, or +10 - removed
expected_min = 8  # at least tables+stove+trash+sign
expected_max = 12
if after["total"] < before["total"]:
    REPORT["errors"].append("ABORT SIGNAL: total DECREASED {} -> {}".format(before["total"], after["total"]))
for k, v in before["farm"].items():
    if after["farm"].get(k, 0) != v:
        REPORT["errors"].append("FARM CHANGED {}: {} -> {}".format(k, v, after["farm"].get(k)))

# Only save if farm intact
if not any("FARM CHANGED" in e or "DECREASED" in e for e in REPORT["errors"]):
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("level_saved")
        REPORT["level_saved"] = True
    except Exception as e:
        try:
            unreal.EditorLevelLibrary.save_current_level()
            log("level_saved_legacy")
            REPORT["level_saved"] = True
        except Exception as e2:
            REPORT["errors"].append("save fail " + str(e2))
            REPORT["level_saved"] = False
else:
    REPORT["level_saved"] = False
    log("SKIP save due to farm safety fail")

# Verify IA untouched
cbp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
chain = []
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "Started":
                for cp in p.list_connected_pins():
                    chain.append(bel.get_node_title(cp.get_owning_node()))
REPORT["ia_started_chain"] = chain

open(r"E:\UE\FarmSim25D\Saved\restaurant_place2.json", "w", encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
