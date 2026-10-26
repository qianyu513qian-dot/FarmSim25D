# -*- coding: utf-8 -*-
"""Probe centroids, camera yaw, bridges, duplicate pawns."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[PROBE_YAW] " + str(m))
    print("[PROBE_YAW] " + str(m))

cats = {k: [] for k in ("house","water","tree","bridge","rail","path","player","pawn","ps","other")}

for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    cls = a.get_class().get_name()
    loc = a.get_actor_location()
    rot = a.get_actor_rotation()
    l = lab.lower()
    item = (lab, cls, round(loc.x), round(loc.y), round(loc.z), round(rot.pitch,1), round(rot.yaw,1), round(rot.roll,1))
    if "playerstart" in l:
        cats["ps"].append(item)
    elif "TopDownCharacter" in cls or "BP_TopDown" in cls or "Character" in cls and "TopDown" in lab:
        cats["pawn"].append(item)
    elif lab.startswith("VMF_") or lab.startswith("Scene_"):
        if any(k in lab for k in ("FarmShed","House","ToolShelter","ChickenCoop","Well")):
            cats["house"].append(item)
        elif "Water" in lab or "Pond" in lab or "Cliff" in lab:
            cats["water"].append(item)
        elif "Tree" in lab or "Bush" in lab or "Forest" in lab:
            cats["tree"].append(item)
        elif "Bridge" in lab and ("Rail" in lab or "Post" in lab):
            cats["rail"].append(item)
        elif "Bridge" in lab:
            cats["bridge"].append(item)
        elif "Path" in lab:
            cats["path"].append(item)

def centroid(items):
    if not items: return None
    return (sum(t[2] for t in items)/len(items), sum(t[3] for t in items)/len(items), sum(t[4] for t in items)/len(items))

for k in cats:
    c = centroid(cats[k])
    log("{} n={} centroid={}".format(k, len(cats[k]), None if not c else (round(c[0]), round(c[1]), round(c[2]))))
    for s in cats[k][:6]:
        log("  {} class={} xyz=({},{},{}) pyr=({},{},{})".format(s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]))

# SpringArm on BP
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
for h in handles:
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj: continue
    cname = obj.get_class().get_name()
    if "SpringArm" in cname or name == "CameraBoom" or name == "SpringArm":
        r = obj.get_editor_property("relative_rotation")
        log("BP SpringArm name={} relrot p={:.1f} y={:.1f} r={:.1f} arm={}".format(
            name, r.pitch, r.yaw, r.roll, obj.get_editor_property("target_arm_length")))
    if cname == "CameraComponent" or name == "FollowCamera" or name == "Camera":
        try:
            log("BP Camera name={} ortho={} proj={}".format(
                name, obj.get_editor_property("ortho_width"), obj.get_editor_property("projection_mode")))
        except Exception as e:
            log("cam err " + str(e))

# Level-placed character instances
for a in eas.get_all_level_actors():
    cls = a.get_class().get_name()
    lab = a.get_actor_label() or ""
    if "Character" in cls or "Pawn" in cls or "TopDown" in lab:
        loc = a.get_actor_location()
        log("ACTOR lab={} class={} @ ({:.0f},{:.0f},{:.0f})".format(lab, cls, loc.x, loc.y, loc.z))

log("DONE")
