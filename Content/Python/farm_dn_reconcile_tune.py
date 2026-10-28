# -*- coding: utf-8 -*-
"""Reconcile Codex level with Ziiilk lighting ownership after farm_dn_install."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
actors = list(eas.get_all_level_actors())
by_label = {a.get_actor_label(): a for a in actors}

REPORT = {"ok": True, "fixes": [], "snapshot": {}}

# Soft-disconnect remaining BeginPlay lighting discovery if still linked
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for n in ge.list_all_nodes():
    title = str(bel.get_node_title(n))
    for p in bel.list_all_pins(n):
        pname = str(p.get_pin_name())
        if title == "InitBlockedFromIndices" and pname == "then":
            targets = [str(bel.get_node_title(q.get_owning_node())) for q in p.list_connected_pins()]
            if any("GetAllActors" in t.replace(" ", "") or "ApplyDayNight" in t.replace(" ", "") for t in targets):
                p.break_pin_links()
                REPORT["fixes"].append("disconnected BeginPlay lighting: " + ",".join(targets))
        # Also break Tick then again if somehow reconnected
        if title == "Event Tick" and pname == "then":
            links = list(p.list_connected_pins())
            if links:
                p.break_pin_links()
                REPORT["fixes"].append("re-broke Event Tick then")
bel.compile_blueprint(bp)
errs = ge.list_nodes_with_errors()
REPORT["grid_compile_errors"] = len(errs) if errs else 0
unreal.EditorAssetLibrary.save_loaded_asset(bp)

clock = next((a for a in actors if isinstance(a, unreal.FarmClock)), None)
if not clock:
    REPORT["ok"] = False
    REPORT["error"] = "FarmClock missing"
else:
    clock.modify()
    # Ensure Ziiilk accepted numbers
    cdo_keys = unreal.get_default_object(unreal.FarmClock).get_editor_property("light_keys")
    clock.set_editor_property("light_keys", cdo_keys)
    clock.set_editor_property("lamp_intensity", 230.0)
    clock.set_editor_property("seconds_per_ten_minutes", 7.0)
    clock.set_editor_property("time_speed", 1.0)
    mpc = unreal.load_asset("/Game/Farm/Lighting/MPC_FarmLighting")
    if mpc:
        clock.set_editor_property("lighting_parameters", mpc)
    REPORT["fixes"].append("reset LightKeys from CDO + LampIntensity=230")

    # SkyLight Ziiilk preferred: Specified Cubemap, no RTC, lower hemisphere open
    sky = by_label.get("SkyLight")
    if sky:
        sc = sky.get_component_by_class(unreal.SkyLightComponent)
        sc.set_mobility(unreal.ComponentMobility.MOVABLE)
        sc.set_editor_property("real_time_capture", False)
        sc.set_editor_property("lower_hemisphere_is_black", False)
        sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        sc.set_editor_property("cubemap", unreal.load_asset("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
        sc.recapture_sky()
        REPORT["fixes"].append("SkyLight SpecifiedCubemap DaylightAmbient")

    # Exposure lock verify / repair
    pp = by_label.get("Farm_Exposure")
    if not pp:
        pp = next((a for a in actors if isinstance(a, unreal.PostProcessVolume) and "Exposure" in a.get_actor_label()), None)
    if pp:
        settings = pp.get_editor_property("settings")
        for name, value in [
            ("override_auto_exposure_min_brightness", True),
            ("override_auto_exposure_max_brightness", True),
            ("auto_exposure_min_brightness", 0.0),
            ("auto_exposure_max_brightness", 0.0),
            ("override_auto_exposure_bias", True),
            ("auto_exposure_bias", 0.0),
            ("override_bloom_intensity", True),
            ("bloom_intensity", 0.0),
        ]:
            settings.set_editor_property(name, value)
        pp.set_editor_property("settings", settings)
        pp.set_editor_property("unbound", True)
        pp.set_editor_property("priority", 10.0)
        clock.set_editor_property("ambient_grade", pp)
        REPORT["fixes"].append("Farm_Exposure EV100 lock verified")

    # Sample lighting at key hours
    samples = {}
    for hour, tag in [(12.0, "noon"), (18.0, "dusk"), (21.0, "night"), (6.0, "morning")]:
        clock.apply_lighting(hour)
        sun = by_label["SunLight"].get_component_by_class(unreal.DirectionalLightComponent)
        moon = by_label["MoonLight"].get_component_by_class(unreal.DirectionalLightComponent)
        sky_c = by_label["SkyLight"].get_component_by_class(unreal.SkyLightComponent)
        lamps = [a for a in eas.get_all_level_actors() if a.get_actor_label().startswith("Farm_Lantern_")]
        lamp_i = []
        for L in lamps:
            try:
                lamp_i.append(float(L.get_component_by_class(unreal.PointLightComponent).get_editor_property("intensity")))
            except Exception:
                pass
        samples[tag] = {
            "hour": hour,
            "sun": float(sun.get_editor_property("intensity")),
            "sun_prio": int(sun.get_editor_property("forward_shading_priority")),
            "moon": float(moon.get_editor_property("intensity")),
            "moon_prio": int(moon.get_editor_property("forward_shading_priority")),
            "sky": float(sky_c.get_editor_property("intensity")),
            "lamps_avg": (sum(lamp_i) / len(lamp_i)) if lamp_i else 0.0,
            "lamp_count": len(lamps),
        }
    # Leave editor preview at pleasant morning/day 10
    clock.apply_lighting(10.0)
    clock.set_editor_property("preview_hour", 10.0)
    REPORT["snapshot"] = samples
    REPORT["lamp_intensity_prop"] = float(clock.get_editor_property("lamp_intensity"))
    keys = clock.get_editor_property("light_keys")
    REPORT["light_key_hours"] = [float(k.hour) for k in keys]
    REPORT["light_key_noon_sun"] = next((float(k.sun) for k in keys if abs(float(k.hour) - 12) < 0.01), None)
    REPORT["light_key_night_moon"] = next((float(k.moon) for k in keys if abs(float(k.hour) - 21) < 0.01), None)

saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
packages = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
REPORT["level_saved"] = bool(saved)
REPORT["packages_saved"] = bool(packages)
