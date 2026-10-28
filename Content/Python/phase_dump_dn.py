# -*- coding: utf-8 -*-
"""Dump current sun/moon/sky level + ApplyDayNightVisuals MapRanges (read-only)."""
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

for a in actors:
    cn = a.get_class().get_name()
    label = ""
    try: label = str(a.get_actor_label())
    except Exception: pass
    if cn not in ("DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud"):
        continue
    log("ACTOR {} class={}".format(label, cn))
    if cn == "DirectionalLight":
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            props = [
                "intensity", "light_color", "temperature", "use_temperature",
                "atmosphere_sun_light", "atmosphere_sun_light_index",
                "forward_shading_priority", "mobility", "cast_shadows",
                "indirect_lighting_intensity", "volumetric_scattering_intensity",
                "dynamic_shadow_distance_movable_light", "shadow_amount",
            ]
            for pn in props:
                try:
                    log("  {}.{}={}".format(label, pn, c.get_editor_property(pn)))
                except Exception as e:
                    log("  {}.{} ERR {}".format(label, pn, e))
            try:
                r = a.get_actor_rotation()
                log("  {}.rot P={} Y={} R={}".format(label, r.pitch, r.yaw, r.roll))
            except Exception as e:
                log("  rot err " + str(e))
    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            for pn in ("intensity", "mobility", "real_time_capture", "source_type",
                       "lower_hemisphere_is_black", "cast_shadows"):
                try:
                    log("  Sky.{}={}".format(pn, c.get_editor_property(pn)))
                except Exception as e:
                    try:
                        # older name
                        if pn == "lower_hemisphere_is_black":
                            log("  Sky.lower_hemisphere_is_solid_color={}".format(
                                c.get_editor_property("lower_hemisphere_is_solid_color")))
                        else:
                            log("  Sky.{} ERR {}".format(pn, e))
                    except Exception as e2:
                        log("  Sky.{} ERR2 {}".format(pn, e2))
    if cn == "SkyAtmosphere":
        log("  SkyAtmosphere OK")
    if cn == "ExponentialHeightFog":
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            for pn in ("fog_density", "fog_height_falloff", "fog_inscattering_color", "volumetric_fog"):
                try: log("  Fog.{}={}".format(pn, c.get_editor_property(pn)))
                except Exception as e: log("  Fog.{} ERR {}".format(pn, e))

bp = unreal.load_asset(MGR)
# vars on CDO
try:
    cdo = unreal.get_default_object(bp.generated_class())
    for vn in ("DayLengthSeconds", "TimeOfDay", "SunActor", "MoonActor", "SkyLightActor"):
        try:
            log("BP.{}={}".format(vn, cdo.get_editor_property(vn) if hasattr(cdo, "get_editor_property") else "?"))
        except Exception:
            pass
    # blueprint variables via reflection
    for v in bel.get_blueprint_variable_list(bp) if hasattr(bel, "get_blueprint_variable_list") else []:
        log("var " + str(v))
except Exception as e:
    log("cdo " + str(e))

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
log("--- ApplyDayNightVisuals MapRange/MakeColor/Negate ---")
for n in ge.list_all_nodes():
    t = title(n)
    if "MapRange" in t:
        ia = find_pin(n, "InRangeA", "Input"); ib = find_pin(n, "InRangeB", "Input")
        oa = find_pin(n, "OutRangeA", "Input"); ob = find_pin(n, "OutRangeB", "Input")
        try:
            log("MapRange InA={} InB={} OutA={} OutB={}".format(
                ia.get_pin_value(), ib.get_pin_value(), oa.get_pin_value(), ob.get_pin_value()))
        except Exception as e:
            log("MapRange read err " + str(e))
    if "MakeColor" in t or "Make Linear Color" in t:
        r = find_pin(n, "R", "Input"); g = find_pin(n, "G", "Input"); b = find_pin(n, "B", "Input")
        try:
            log("MakeColor R={} G={} B={}".format(r.get_pin_value(), g.get_pin_value(), b.get_pin_value()))
        except Exception:
            pass
    if "Negate" in t or "Multiply" in t:
        log("node " + t)

log("DONE dump")
