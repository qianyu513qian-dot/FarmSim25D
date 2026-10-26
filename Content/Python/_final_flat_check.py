# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
for n in ge.list_all_nodes():
    if "Format" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            unreal.log("[FMT] pin=%s dv=%r" % (p.get_pin_name(), p.get_default_as_string()))
        # try editor props
        for prop in ("format", "Format", "text", "Text"):
            try:
                unreal.log("[FMT] prop %s=%r" % (prop, n.get_editor_property(prop)))
            except Exception as e:
                pass
# water mat blend / sample
for path in ("/Game/Farm/Art/Mats/M_Water", "/Game/Farm/Art/T_Water"):
    a = unreal.EditorAssetLibrary.load_asset(path)
    unreal.log("[WAT] %s -> %s" % (path, a))
    if a and "Material" in a.get_class().get_name():
        try:
            unreal.log("[WAT] blend=%s two_sided=%s" % (
                a.get_editor_property("blend_mode"), a.get_editor_property("two_sided")))
        except Exception as e:
            unreal.log("[WAT] " + str(e))
# Final character + house confirm
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if "TopDownCharacter" in a.get_class().get_name():
        loc = a.get_actor_location()
        unreal.log("[FINAL] Char (%.0f,%.0f,%.0f) Grid~%d,%d" % (
            loc.x, loc.y, loc.z, int(loc.x//100), int(loc.y//100)))
    if a.get_actor_label() == "Scene_House":
        rr = a.get_actor_rotation()
        o, e = a.get_actor_bounds(False)
        unreal.log("[FINAL] House rot=(%.1f,%.1f,%.1f) extent=(%.0f,%.0f,%.0f)" % (
            rr.pitch, rr.yaw, rr.roll, e.x, e.y, e.z))