# -*- coding: utf-8 -*-
"""SURGICAL sun/moon look polish. No graph wipe. Level light props + mild MapRange dusk soften + DayLength check."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

# Keep tutorial ratios; soften dusk handoff slightly
SUN_MAX = 8.0
MOON_MAX = 0.55   # ~7% sun — night readable, not day-bright
SKY_NIGHT = 0.5
SKY_DAY = 1.7

def log(m):
    unreal.log("[DN_OPT] " + str(m)); print("[DN_OPT] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node: return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def set_val(pin, value, label=""):
    if not pin: log("no "+label); return False
    try:
        pin.set_pin_value(str(value)); log("set {}={!r}".format(label, value)); return True
    except Exception as e:
        log("fail {} {}".format(label, e)); return False

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def set_prop(comp, name, value):
    try:
        comp.set_editor_property(name, value)
        log("  {}={}".format(name, value))
        return True
    except Exception as e:
        log("  skip {} ({})".format(name, e))
        return False

bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

# Mild retune MapRanges by fingerprint
for n in ge.list_all_nodes():
    if "MapRange" not in title(n):
        continue
    oa = find_pin(n, "OutRangeA", "Input")
    ob = find_pin(n, "OutRangeB", "Input")
    ia = find_pin(n, "InRangeA", "Input")
    ib = find_pin(n, "InRangeB", "Input")
    try:
        oav, obv, iav, ibv = oa.get_pin_value(), ob.get_pin_value(), ia.get_pin_value(), ib.get_pin_value()
    except Exception:
        continue
    # Sun intensity OutB~8
    try:
        if abs(float(obv) - 8.0) < 0.2 or abs(float(obv) - SUN_MAX) < 0.2:
            if float(iav) < 0:
                set_val(oa, "0.0", "sunMinI")
                set_val(ob, str(SUN_MAX), "sunMaxI")
                set_val(ia, "-0.08", "sunInA")
                set_val(ib, "0.42", "sunInB")  # linger into dusk
                continue
    except Exception:
        pass
    # Moon intensity OutB~0.65
    try:
        if 0.4 <= float(obv) <= 1.5 and float(iav) > 0:
            set_val(oa, "0.0", "moonMinI")
            set_val(ob, str(MOON_MAX), "moonMaxI")
            set_val(ia, "0.18", "moonInA")
            set_val(ib, "-0.4", "moonInB")
            continue
    except Exception:
        pass
    # Sky
    try:
        if abs(float(oav) - 0.45) < 0.15 or abs(float(obv) - 1.6) < 0.2:
            set_val(oa, str(SKY_NIGHT), "skyNight")
            set_val(ob, str(SKY_DAY), "skyDay")
            continue
    except Exception:
        pass

# Colors: warm sun / cool moon (keep)
for n in ge.list_all_nodes():
    if "MakeColor" not in title(n):
        continue
    r = find_pin(n, "R", "Input")
    try:
        rv = float(r.get_pin_value()) if r else 1
    except Exception:
        rv = 1
    if rv < 0.8:
        set_val(r, "0.62", "moonR")
        set_val(find_pin(n, "G", "Input"), "0.72", "moonG")
        set_val(find_pin(n, "B", "Input"), "1.0", "moonB")
    else:
        set_val(r, "1.0", "sunR")
        set_val(find_pin(n, "G", "Input"), "0.92", "sunG")
        set_val(find_pin(n, "B", "Input"), "0.75", "sunB")

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

# Level actors polish
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

# Fix DayLengthSeconds on placed GridManager
for a in actors:
    cn = a.get_class().get_name()
    label = ""
    try: label = str(a.get_actor_label())
    except Exception: pass

    if "GridManager" in cn or "GridManager" in label or "BP_GridManager" in cn:
        for prop in ("DayLengthSeconds", "day_length_seconds"):
            try:
                cur = a.get_editor_property("DayLengthSeconds")
                log("GridManager DayLengthSeconds was {}".format(cur))
                if cur is None or float(cur) < 10:
                    a.set_editor_property("DayLengthSeconds", 75.0)
                    log("set DayLengthSeconds=75")
                break
            except Exception as e:
                log("DayLength try {} -> {}".format(prop, e))

    if cn == "DirectionalLight":
        is_moon = ("Moon" in label)
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            log("polish " + label)
            set_prop(c, "mobility", unreal.ComponentMobility.MOVABLE)
            set_prop(c, "atmosphere_sun_light", True)
            set_prop(c, "atmosphere_sun_light_index", 1 if is_moon else 0)
            set_prop(c, "forward_shading_priority", 0 if is_moon else 1)
            set_prop(c, "use_temperature", False)  # BP SetLightColor owns tint
            set_prop(c, "cast_shadows", True)
            if is_moon:
                set_prop(c, "intensity", MOON_MAX)
                set_prop(c, "light_color", unreal.Color(158, 184, 255, 255))
                set_prop(c, "shadow_amount", 0.55)
                set_prop(c, "dynamic_shadow_distance_movable_light", 12000.0)
                set_prop(c, "indirect_lighting_intensity", 0.6)
                set_prop(c, "volumetric_scattering_intensity", 0.4)
                # smaller disk for moon if available
                for pn, pv in (("light_source_angle", 0.5), ("source_angle", 0.5)):
                    set_prop(c, pn, pv)
            else:
                set_prop(c, "intensity", SUN_MAX)
                set_prop(c, "light_color", unreal.Color(255, 235, 191, 255))
                set_prop(c, "shadow_amount", 1.0)
                set_prop(c, "dynamic_shadow_distance_movable_light", 25000.0)
                set_prop(c, "indirect_lighting_intensity", 1.0)
                set_prop(c, "volumetric_scattering_intensity", 1.0)
                for pn, pv in (("light_source_angle", 0.8), ("source_angle", 0.8)):
                    set_prop(c, pn, pv)

    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            log("polish SkyLight")
            set_prop(c, "mobility", unreal.ComponentMobility.MOVABLE)
            set_prop(c, "real_time_capture", True)
            set_prop(c, "lower_hemisphere_is_black", True)
            set_prop(c, "intensity", SKY_DAY)
            set_prop(c, "cast_shadows", False)  # avoid double AO wash on farm

    if cn == "ExponentialHeightFog":
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            log("polish Fog")
            # slightly clearer farm day, keep some depth
            set_prop(c, "fog_density", 0.028)
            set_prop(c, "fog_height_falloff", 0.25)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("save " + str(e))

unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE sunFSP=1 moonFSP=0 moonI={} sunI={} skyD/N={}/{}".format(MOON_MAX, SUN_MAX, SKY_DAY, SKY_NIGHT))
