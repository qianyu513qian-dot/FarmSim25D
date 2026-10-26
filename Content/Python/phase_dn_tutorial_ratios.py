# -*- coding: utf-8 -*-
"""Retune day/night to tutorial ratios (rays-unreal / Cosindra / Epic dual-light).
Moon = ~5% of sun (readable farm night), NOT equal to sun.
Sky night dark; Sky Atmosphere + RTC already expected.
SURGICAL pin value edits only."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

# Tutorial: sun outdoor ~3-10; moon 1-5% of sun. Farm playable night ~8% -> ~0.65
SUN_MAX = 8.0
MOON_MAX = 0.65   # ~8% of sun — was wrongly 5~10
SKY_NIGHT = 0.45
SKY_DAY = 1.6
# Pitch: midnight sun below (+40), noon overhead (-70); moon = -pitch => midnight ~-40
SUN_MID_PITCH = 40.0
SUN_NOON_PITCH = -70.0

def log(m):
    unreal.log("[DN_TUNE] " + str(m)); print("[DN_TUNE] " + str(m))

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

bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

for n in ge.list_all_nodes():
    if "MapRange" not in title(n):
        continue
    oa = find_pin(n, "OutRangeA", "Input")
    ob = find_pin(n, "OutRangeB", "Input")
    ia = find_pin(n, "InRangeA", "Input")
    ib = find_pin(n, "InRangeB", "Input")
    try:
        oav, obv, iav = oa.get_pin_value(), ob.get_pin_value(), ia.get_pin_value()
    except Exception:
        continue
    log("before MapRange InA={} OutA={} OutB={}".format(iav, oav, obv))

    # Sun intensity: InA=-0.15 OutB=8
    if "-0.15" in str(iav) and ("8" in str(obv) or "8.0" in str(obv)):
        set_val(oa, "0.0", "sunMinI")
        set_val(ob, str(SUN_MAX), "sunMaxI")
        set_val(ia, "-0.1", "sunInA")
        set_val(ib, "0.35", "sunInB")
    # Moon intensity: was InA 0.25 OutB 10
    elif ("0.15" in str(iav) or "0.25" in str(iav)) and float(str(obv) or "0") >= 2.0:
        set_val(oa, "0.0", "moonMinI")
        set_val(ob, str(MOON_MAX), "moonMaxI")
        set_val(ia, "0.2", "moonInA")   # off when day elev high
        set_val(ib, "-0.35", "moonInB") # full at night
    # Pitch
    elif ("25" in str(oav) or "55" in str(oav) or "40" in str(oav)) and "70" in str(obv):
        set_val(oa, str(SUN_MID_PITCH), "sunMidPitch")
        set_val(ob, str(SUN_NOON_PITCH), "sunNoonPitch")
    # Sky
    elif float(str(oav) or "0") >= 0.5:
        set_val(oa, str(SKY_NIGHT), "skyNight")
        set_val(ob, str(SKY_DAY), "skyDay")

# Force moon MakeColor cool (find MakeColor with R~0.55 or second MakeColor)
colors = [n for n in ge.list_all_nodes() if "MakeColor" in title(n)]
log("MakeColor count={}".format(len(colors)))
for n in colors:
    r = find_pin(n, "R", "Input")
    try:
        rv = float(r.get_pin_value()) if r else 1
    except Exception:
        rv = 1
    if rv < 0.8:  # cool moon color
        set_val(r, "0.55", "moonR")
        set_val(find_pin(n, "G", "Input"), "0.65", "moonG")
        set_val(find_pin(n, "B", "Input"), "0.95", "moonB")
    else:  # warm sun
        set_val(r, "1.0", "sunR")
        set_val(find_pin(n, "G", "Input"), "0.94", "sunG")
        set_val(find_pin(n, "B", "Input"), "0.78", "sunB")

try:
    bel.compile_blueprint(bp)
    log("compile {}".format(getattr(bp, "status", "?")))
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

# Level defaults matching tutorial night ratios
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

for a in actors:
    cn = a.get_class().get_name()
    label = ""
    try: label = str(a.get_actor_label())
    except Exception: pass
    tags = [str(t) for t in (a.tags or [])]
    if cn == "DirectionalLight":
        is_moon = ("Moon" in label) or ("FarmMoon" in tags)
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            try:
                c.set_editor_property("forward_shading_priority", 0)
                c.set_editor_property("atmosphere_sun_light", True)
                c.set_editor_property("atmosphere_sun_light_index", 1 if is_moon else 0)
                c.set_editor_property("intensity", MOON_MAX if is_moon else SUN_MAX)
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                log("DL {} moon={} I={}".format(label, is_moon, MOON_MAX if is_moon else SUN_MAX))
            except Exception as e:
                log("dl err " + str(e))
    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.LightComponentBase):
            try:
                c.set_editor_property("intensity", SKY_NIGHT)
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                try: c.set_editor_property("real_time_capture", True)
                except Exception: pass
                log("Sky I={}".format(SKY_NIGHT))
            except Exception as e:
                log("sky " + str(e))
    if cn == "SkyAtmosphere":
        log("SkyAtmosphere present OK")

# Ensure SkyAtmosphere exists
has_atm = any(a.get_class().get_name() == "SkyAtmosphere" for a in actors)
if not has_atm:
    try:
        loc = unreal.Vector(0, 0, 0)
        atm = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyAtmosphere, loc)
        log("spawned SkyAtmosphere {}".format(atm))
    except Exception as e:
        try:
            subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            atm = subsystem.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0,0,0))
            log("spawned SkyAtmosphere2 {}".format(atm))
        except Exception as e2:
            log("no atm spawn " + str(e2))

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("save " + str(e))

# Verify
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
for n in ge.list_all_nodes():
    if "MapRange" in title(n):
        oa = find_pin(n, "OutRangeA", "Input"); ob = find_pin(n, "OutRangeB", "Input")
        ia = find_pin(n, "InRangeA", "Input")
        try:
            log("verify InA={} OutA={} OutB={}".format(ia.get_pin_value(), oa.get_pin_value(), ob.get_pin_value()))
        except Exception:
            pass
log("DONE tutorial ratios sun={} moon={} skyN={}".format(SUN_MAX, MOON_MAX, SKY_NIGHT))
