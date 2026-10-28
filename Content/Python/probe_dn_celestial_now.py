# -*- coding: utf-8 -*-
"""Dump current day/night celestial state. Do NOT touch PointLights."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[DN_DUMP] " + str(m)); print("[DN_DUMP] " + str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    if not node: return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

log("=== LEVEL ACTORS (celestial + note lamps) ===")
point_n = 0
for a in actors:
    cn = a.get_class().get_name()
    try: label = str(a.get_actor_label())
    except Exception: label = a.get_name()
    tags = []
    try: tags = [str(t) for t in (a.tags or [])]
    except Exception: pass

    if cn == "DirectionalLight":
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            props = {}
            for pn in ("intensity","atmosphere_sun_light","atmosphere_sun_light_index",
                       "forward_shading_priority","cast_shadows","use_temperature",
                       "mobility","shadow_amount","indirect_lighting_intensity",
                       "light_source_angle","source_angle","dynamic_shadow_distance_movable_light"):
                try: props[pn] = c.get_editor_property(pn)
                except Exception: pass
            try:
                col = c.get_editor_property("light_color")
                props["light_color"] = (col.r, col.g, col.b, col.a) if hasattr(col,"r") else str(col)
            except Exception: pass
            try:
                rot = a.get_actor_rotation()
                props["rot"] = (rot.pitch, rot.yaw, rot.roll)
            except Exception: pass
            log("DL {} tags={} props={}".format(label, tags, props))

    elif cn == "SkyLight":
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            props = {}
            for pn in ("intensity","real_time_capture","lower_hemisphere_is_black","mobility","cast_shadows"):
                try: props[pn] = c.get_editor_property(pn)
                except Exception: pass
            log("SkyLight {} props={}".format(label, props))

    elif cn == "SkyAtmosphere":
        log("SkyAtmosphere {}".format(label))

    elif cn == "ExponentialHeightFog":
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            props = {}
            for pn in ("fog_density","fog_height_falloff","fog_inscattering_color","fog_max_opacity"):
                try: props[pn] = c.get_editor_property(pn)
                except Exception: pass
            log("Fog {} props={}".format(label, props))

    elif "VolumetricCloud" in cn:
        log("VolumetricCloud {}".format(label))

    elif "SkySphere" in label or "SkySphere" in cn or "SM_SkySphere" in label:
        log("SkySphere {} cn={}".format(label, cn))

    elif cn == "PointLight" or "PointLight" in cn:
        point_n += 1
        # note only, do not dump details for cloning
        log("PointLight NOTE-ONLY label={} (untouched)".format(label))

    elif "GridManager" in cn or "GridManager" in label:
        props = {}
        for pn in ("DayLengthSeconds","TimeOfDay","SunActor","MoonActor","SkyLightActor","day_length_seconds"):
            try: props[pn] = a.get_editor_property(pn)
            except Exception:
                try: props[pn] = a.get_editor_property(pn)  # noop
                except Exception: pass
        # try common names
        for pn in ("DayLengthSeconds","TimeOfDay"):
            try: props[pn] = a.get_editor_property(pn)
            except Exception as e: props[pn+"_err"] = str(e)
        log("GridManager {} props={}".format(label, props))

log("PointLight count (Codex lamps, leave alone)={}".format(point_n))

# BP CDO DayLength
bp = unreal.load_asset(MGR)
try:
    cdo = unreal.get_default_object(bp.generated_class())
    for pn in ("DayLengthSeconds","TimeOfDay"):
        try:
            log("CDO {}={}".format(pn, cdo.get_editor_property(pn)))
        except Exception as e:
            log("CDO {} err {}".format(pn, e))
except Exception as e:
    log("CDO fail "+str(e))

# ApplyDayNightVisuals MapRanges + MakeRotators
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
log("=== ApplyDayNightVisuals nodes ===")
for n in ge.list_all_nodes():
    t = title(n)
    if "MapRange" in t:
        vals = {}
        for pn in ("Value","InRangeA","InRangeB","OutRangeA","OutRangeB"):
            p = find_pin(n, pn, "Input")
            try: vals[pn] = p.get_pin_value() if p else None
            except Exception: vals[pn] = "?"
        log("MapRange {}".format(vals))
    elif "MakeRotator" in t:
        vals = {}
        for pn in ("Pitch","Yaw","Roll"):
            p = find_pin(n, pn, "Input")
            links = []
            try:
                if p:
                    links = [title(lp.get_owning_node()) for lp in p.list_connected_pins()]
                    vals[pn] = "links="+str(links)+" def="+str(p.get_pin_value())
            except Exception as e:
                vals[pn] = str(e)
        log("MakeRotator {}".format(vals))
    elif "SetIntensity" in t or "SetLightColor" in t or "SetActorRotation" in t:
        log("op {}".format(t))
    elif "Negate" in t or "Multiply" in t or float.__name__ in t:
        pass
    elif "Get Moon" in t or "Get Sun" in t or "Get Sky" in t or "Get Time" in t:
        log("get {}".format(t))

log("DONE dump")
