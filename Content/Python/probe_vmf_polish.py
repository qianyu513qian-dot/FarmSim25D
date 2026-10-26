# -*- coding: utf-8 -*-
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
water = []
bridge = []
vmf = 0
pawns = []
ps = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    cn = a.get_class().get_name()
    loc = a.get_actor_location()
    if lab.startswith("VMF_"):
        vmf += 1
        if "Water_" in lab:
            water.append((lab, round(loc.x), round(loc.y), round(loc.z)))
        if "Bridge" in lab:
            bridge.append((lab, round(loc.x), round(loc.y), round(loc.z)))
    if "PlayerStart" in cn or lab == "PlayerStart":
        ps.append((lab, cn, round(loc.x), round(loc.y), round(loc.z)))
    if any(t in cn for t in ("TopDownCharacter", "Mannequin", "DefaultPawn")):
        pawns.append((lab, cn, round(loc.x), round(loc.y)))
    elif "Character" in cn and "PlayerStart" not in cn and not lab.startswith("VMF_"):
        pawns.append((lab, cn, round(loc.x), round(loc.y)))

unreal.log("[VMF_POLISH] VMF_*=%d water=%d bridge=%d PlayerStarts=%d pawns=%d" % (
    vmf, len(water), len(bridge), len(ps), len(pawns)))
for w in water:
    unreal.log("[VMF_POLISH] WATER %s @ %s" % (w[0], w[1:]))
for b in bridge[:12]:
    unreal.log("[VMF_POLISH] BRIDGE %s @ %s" % (b[0], b[1:]))
for p in ps:
    unreal.log("[VMF_POLISH] PS %s" % (p,))
for p in pawns:
    unreal.log("[VMF_POLISH] PAWN %s" % (p,))

# key layout
for key in ("VMF_House_FarmShed", "VMF_Soil_8_9", "VMF_PathV_12_10", "VMF_BridgeDeck_12_1",
            "VMF_Water_Left", "VMF_Water_Bottom", "FarmGround", "BP_GridManager"):
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == key:
            loc = a.get_actor_location()
            unreal.log("[VMF_POLISH] KEY %s loc=(%.0f,%.0f,%.0f)" % (key, loc.x, loc.y, loc.z))
            break
    else:
        unreal.log("[VMF_POLISH] MISSING " + key)
