# -*- coding: utf-8 -*-
"""Probe BP meshes + nearby props that look like a second character."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[PROBE3] " + str(m))
    print("[PROBE3] " + str(m))

bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sds.k2_gather_subobject_data_for_blueprint(bp)
for h in handles:
    data = lib.get_data(h)
    name = str(lib.get_variable_name(data))
    obj = lib.get_object_for_blueprint(data, bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    extra = ""
    try:
        if "Mesh" in cname or "Skeletal" in cname or "Static" in cname:
            try:
                sm = obj.get_editor_property("skeletal_mesh")
                extra += " skel={}".format(sm.get_name() if sm else None)
            except Exception:
                pass
            try:
                sm = obj.get_editor_property("static_mesh")
                extra += " static={}".format(sm.get_name() if sm else None)
            except Exception:
                pass
            try:
                vis = obj.get_editor_property("visible")
                extra += " vis={}".format(vis)
            except Exception:
                pass
    except Exception as e:
        extra += " err=" + str(e)
    log("sub name={} class={}{}".format(name, cname, extra))

# Actors near PlayerStart that could look like a character
ps = None
for a in eas.get_all_level_actors():
    if a.get_class().get_name() == "PlayerStart":
        ps = a
        break
if ps:
    pl = ps.get_actor_location()
    log("near PS scan:")
    for a in eas.get_all_level_actors():
        loc = a.get_actor_location()
        dx, dy = loc.x - pl.x, loc.y - pl.y
        if dx*dx + dy*dy > 600*600:
            continue
        lab = a.get_actor_label() or ""
        cls = a.get_class().get_name()
        if lab.startswith("VMF_Grass") or lab.startswith("VMF_Path") or lab.startswith("FarmCollision"):
            continue
        log("  near lab={} cls={} d=({:.0f},{:.0f},{:.0f})".format(lab, cls, dx, dy, loc.z - pl.z))

# Any VMF with Farmer/Character/Villager/Man/Woman/Player in name
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if any(k in lab for k in ("Farmer", "Villager", "Character", "Mannequin", "PlayerMesh", "Scarecrow", "NPC", "Hero")):
        loc = a.get_actor_location()
        log("CHARISH {} @ ({:.0f},{:.0f},{:.0f})".format(lab, loc.x, loc.y, loc.z))
