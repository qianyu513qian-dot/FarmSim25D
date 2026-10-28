# -*- coding: utf-8 -*-
"""Independent celestial day/night readability fix.
Root cause (OUR prior opt): moon MaxI=0.55 (~7% of sun=8) + SkyNight=0.5 on already-dark
RTC cubemap + lower_hemisphere_is_black → pitch-black night for stylized ortho farm.
Also FColor(R,G,B) was applied as BGRA so sun/moon tints were swapped.

Independent targets (stylized game-scale, NOT physical lux, NOT Codex lamps):
  sun day 8.0 warm; moon night 2.4 (~30% sun) cool; SkyNight 2.0 / SkyDay 1.8;
  lower hemisphere NOT black; moon pitch stays inverted; DayLength 75.
SURGICAL only. Never wipe graphs. Never touch PointLights.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

# Independent reasoned targets
SUN_MAX = 8.0
MOON_MAX = 2.4      # readable soft night; day still ~3.3x brighter
SKY_NIGHT = 2.0     # RTC night cubemap is dark — raise multiplier for fill
SKY_DAY = 1.8
FOG_DENSITY = 0.020
# Pitch: midnight sun below (+48) => moon above (-48) via existing * -1
SUN_MIDNIGHT_PITCH = 48.0
SUN_NOON_PITCH = -70.0

def log(m):
    unreal.log("[DN_SELF] " + str(m)); print("[DN_SELF] " + str(m))

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
    if not pin:
        log("no " + label); return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, value)); return True
    except Exception as e:
        log("fail {} {}".format(label, e)); return False

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def set_prop(comp, name, value):
    try:
        comp.set_editor_property(name, value)
        log("  {}={}".format(name, value)); return True
    except Exception as e:
        log("  skip {} ({})".format(name, e)); return False

def cool_moon_color():
    # FColor Python ctor is B,G,R,A — pass cool blue correctly
    return unreal.Color(255, 184, 140, 255)  # B=255 G=184 R=140 → RGB(140,184,255)

def warm_sun_color():
    return unreal.Color(185, 230, 255, 255)  # B=185 G=230 R=255 → RGB(255,230,185)

# ---------- BP MapRanges + MakeColor ----------
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

moon_pitch_neg = False
for n in ge.list_all_nodes():
    t = title(n)
    if "MakeRotator" not in t:
        continue
    pitch = find_pin(n, "Pitch", "Input")
    if not pitch:
        continue
    for lp in pitch.list_connected_pins():
        ot = title(lp.get_owning_node())
        if "*" in ot or "Multiply" in ot or "Negate" in ot or "float * float" in ot:
            moon_pitch_neg = True
            # ensure multiply B is -1 if it's a multiply
            bpin = find_pin(lp.get_owning_node(), "B", "Input")
            if bpin and ("*" in ot or "Multiply" in ot or "float * float" in ot):
                try:
                    bv = bpin.get_pin_value()
                    if abs(float(bv) + 1.0) > 0.05 and abs(float(bv) - 1.0) < 0.05:
                        set_val(bpin, "-1.0", "moonPitchMul")
                    elif abs(float(bv) + 1.0) > 0.05:
                        # if not already -1, force -1 for invert
                        set_val(bpin, "-1.0", "moonPitchMulForce")
                    else:
                        log("moon pitch mul already -1")
                except Exception as e:
                    log("moon mul check " + str(e))
log("moonPitchInvertWiring={}".format(moon_pitch_neg))

for n in ge.list_all_nodes():
    if "MapRange" not in title(n):
        continue
    oa = find_pin(n, "OutRangeA", "Input")
    ob = find_pin(n, "OutRangeB", "Input")
    ia = find_pin(n, "InRangeA", "Input")
    ib = find_pin(n, "InRangeB", "Input")
    try:
        oav, obv, iav, ibv = oa.get_pin_value(), ob.get_pin_value(), ia.get_pin_value(), ib.get_pin_value()
        foa, fob, fia = float(oav), float(obv), float(iav)
    except Exception:
        continue
    log("MapRange before InA={} InB={} OutA={} OutB={}".format(iav, ibv, oav, obv))

    # Sun intensity: OutB~8, InA negative-ish
    if abs(fob - 8.0) < 0.3 and fia < 0.05:
        set_val(oa, "0.0", "sunMinI")
        set_val(ob, str(SUN_MAX), "sunMaxI")
        set_val(ia, "-0.05", "sunInA")
        set_val(ib, "0.40", "sunInB")
        continue

    # Moon intensity: OutB was 0.55 (or similar small)
    if 0.3 <= fob <= 3.5 and fia > 0.05:
        set_val(oa, "0.0", "moonMinI")
        set_val(ob, str(MOON_MAX), "moonMaxI")
        set_val(ia, "0.20", "moonInA")   # begin rising at dusk
        set_val(ib, "-0.35", "moonInB")  # full by deep night
        continue

    # Pitch sun: OutA positive (below at midnight), OutB negative (noon)
    if foa >= 20.0 and fob <= -50.0:
        set_val(oa, str(SUN_MIDNIGHT_PITCH), "sunMidPitch")
        set_val(ob, str(SUN_NOON_PITCH), "sunNoonPitch")
        continue

    # Sky intensity: OutA night, OutB day
    if (0.3 <= foa <= 3.5) and (1.0 <= fob <= 3.5) and abs(fia + 1.0) < 0.05:
        set_val(oa, str(SKY_NIGHT), "skyNight")
        set_val(ob, str(SKY_DAY), "skyDay")
        continue

# MakeColor: cool moon / warm sun (LinearColor pins — RGBA, not FColor)
for n in ge.list_all_nodes():
    if "MakeColor" not in title(n) and "Make LinearColor" not in title(n):
        # also match "Make LinearColor"
        if "LinearColor" not in title(n) and "MakeColor" not in title(n):
            continue
    r = find_pin(n, "R", "Input") or find_pin(n, "Red", "Input")
    g = find_pin(n, "G", "Input") or find_pin(n, "Green", "Input")
    b = find_pin(n, "B", "Input") or find_pin(n, "Blue", "Input")
    if not r:
        continue
    try:
        rv = float(r.get_pin_value())
    except Exception:
        continue
    # Heuristic: cooler/darker R => moon; high R => sun
    if rv < 0.85:
        set_val(r, "0.55", "moonR")
        set_val(g, "0.70", "moonG")
        set_val(b, "1.0", "moonB")
    else:
        set_val(r, "1.0", "sunR")
        set_val(g, "0.90", "sunG")
        set_val(b, "0.72", "sunB")

try:
    bel.compile_blueprint(bp)
    log("compile ok status={}".format(getattr(bp, "status", "?")))
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

# ---------- Level celestial actors only (skip PointLight) ----------
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

for a in actors:
    cn = a.get_class().get_name()
    try: label = str(a.get_actor_label())
    except Exception: label = a.get_name()

    # NEVER touch point lights / lamps
    if cn == "PointLight" or "PointLight" in cn:
        log("skip lamp " + label)
        continue

    if "GridManager" in cn or "GridManager" in label:
        try:
            cur = a.get_editor_property("DayLengthSeconds")
            log("DayLengthSeconds={}".format(cur))
            if cur is None or float(cur) < 10:
                a.set_editor_property("DayLengthSeconds", 75.0)
                log("DayLengthSeconds->75")
        except Exception as e:
            log("DayLength " + str(e))

    if cn == "DirectionalLight":
        is_moon = ("Moon" in label) or ("FarmMoon" in [str(t) for t in (a.tags or [])])
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            log("celestial DL " + label + (" MOON" if is_moon else " SUN"))
            set_prop(c, "mobility", unreal.ComponentMobility.MOVABLE)
            set_prop(c, "atmosphere_sun_light", True)
            set_prop(c, "atmosphere_sun_light_index", 1 if is_moon else 0)
            # Both 0: brighter light drives forward main-light; avoids sun-prio=1 blocking night
            set_prop(c, "forward_shading_priority", 0)
            set_prop(c, "use_temperature", False)
            set_prop(c, "cast_shadows", True)
            if is_moon:
                set_prop(c, "intensity", MOON_MAX)
                set_prop(c, "light_color", cool_moon_color())
                set_prop(c, "shadow_amount", 0.65)
                set_prop(c, "indirect_lighting_intensity", 0.85)
                set_prop(c, "volumetric_scattering_intensity", 0.5)
                set_prop(c, "dynamic_shadow_distance_movable_light", 15000.0)
                set_prop(c, "light_source_angle", 1.0)  # softer moon shadows
            else:
                set_prop(c, "intensity", SUN_MAX)
                set_prop(c, "light_color", warm_sun_color())
                set_prop(c, "shadow_amount", 1.0)
                set_prop(c, "indirect_lighting_intensity", 1.0)
                set_prop(c, "volumetric_scattering_intensity", 1.0)
                set_prop(c, "dynamic_shadow_distance_movable_light", 25000.0)
                set_prop(c, "light_source_angle", 0.85)

    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            log("SkyLight celestial fill")
            set_prop(c, "mobility", unreal.ComponentMobility.MOVABLE)
            set_prop(c, "real_time_capture", True)
            # Critical for ortho farm: allow lower-hemisphere ambient so ground isn't crushed
            set_prop(c, "lower_hemisphere_is_black", False)
            set_prop(c, "intensity", SKY_DAY)
            set_prop(c, "cast_shadows", False)

    if cn == "ExponentialHeightFog":
        for c in a.get_components_by_class(unreal.ExponentialHeightFogComponent):
            log("Fog soften for night readability")
            set_prop(c, "fog_density", FOG_DENSITY)
            set_prop(c, "fog_height_falloff", 0.22)
            set_prop(c, "fog_max_opacity", 0.85)

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("level save " + str(e))

unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE moonMax={} skyN/D={}/{} sunMidPitch={} fog={} lampsUntouched".format(
    MOON_MAX, SKY_NIGHT, SKY_DAY, SUN_MIDNIGHT_PITCH, FOG_DENSITY))
