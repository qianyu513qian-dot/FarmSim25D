# -*- coding: utf-8 -*-
"""Fix night black: priority by brightness + higher moon elevation + stronger night fill.
SURGICAL only — no graph wipe."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[NIGHT_FIX] " + str(m)); print("[NIGHT_FIX] " + str(m))

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
        log("set fail {} {}".format(label, e)); return False

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

# ---- Level: both ForwardShadingPriority=0 (brightness picks main light) ----
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()

for a in actors:
    if a.get_class().get_name() != "DirectionalLight":
        continue
    label = ""
    try: label = str(a.get_actor_label())
    except Exception: pass
    tags = [str(t) for t in (a.tags or [])]
    for c in a.get_components_by_class(unreal.DirectionalLightComponent):
        try:
            c.set_editor_property("forward_shading_priority", 0)
        except Exception:
            pass
        is_moon = ("Moon" in label) or ("FarmMoon" in tags)
        try:
            if is_moon:
                c.set_editor_property("intensity", 8.0)
                # Cast shadows on for moon so it feels like real light
                try: c.set_editor_property("cast_shadows", True)
                except Exception: pass
            log("prio0 {} inten~ moon={} tags={}".format(label, is_moon, tags))
        except Exception as e:
            log("dl " + str(e))
    if a.get_class().get_name() == "SkyLight" or "SkyLight" in a.get_class().get_name():
        pass

for a in actors:
    if a.get_class().get_name() != "SkyLight":
        continue
    for c in a.get_components_by_class(unreal.LightComponentBase):
        try:
            c.set_editor_property("intensity", 2.5)
            try: c.set_editor_property("real_time_capture", True)
            except Exception: pass
            log("SkyLight inten->2.5 RTC")
        except Exception as e:
            log("sky " + str(e))

# ---- BP: bump moon intensity map + sky night map; raise moon pitch via negate source ----
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

# Find MapRanges by OutRange values
for n in ge.list_all_nodes():
    if "MapRange" not in title(n):
        continue
    oa = find_pin(n, "OutRangeA", "Input")
    ob = find_pin(n, "OutRangeB", "Input")
    ia = find_pin(n, "InRangeA", "Input")
    try:
        oav, obv, iav = oa.get_pin_value(), ob.get_pin_value(), ia.get_pin_value()
    except Exception:
        continue
    log("MapRange InA={} OutA={} OutB={}".format(iav, oav, obv))
    # Moon intensity: InA=0.15 OutB was 5.0
    if "0.15" in str(iav) and ("2.5" in str(obv) or "5" in str(obv) or "5.0" in str(obv)):
        set_val(ob, "10.0", "moonMaxI")
        # Soften so moon starts earlier at dusk
        set_val(find_pin(n, "InRangeA", "Input"), "0.25", "moonInA")
        set_val(find_pin(n, "InRangeB", "Input"), "-0.2", "moonInB")
    # Sky: OutA night
    if "1.5" in str(oav) or "0.6" in str(oav):
        set_val(oa, "3.0", "skyNight")
        set_val(ob, "2.2", "skyDay")
    # Pitch map sun: OutA=25 OutB=-70 — change midnight sun deeper below, and
    # moon uses -pitch so midnight moon becomes higher: if sun midnight=+40, moon=-40
    if "25" in str(oav) and "70" in str(obv):
        set_val(oa, "55.0", "sunMidPitchBelow")  # deeper below => -pitch moon higher (~-55)
        set_val(ob, "-70.0", "sunNoon")

try:
    bel.compile_blueprint(bp)
    log("compile {}".format(getattr(bp, "status", "?")))
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

# Optional: PostProcess auto-exposure floor so night isn't crushed
pp_n = 0
for a in actors:
    cn = a.get_class().get_name()
    if "PostProcess" not in cn:
        continue
    try:
        # Try raise min brightness / EV
        settings = a.get_editor_property("settings") if hasattr(a, "get_editor_property") else None
        log("found PP " + a.get_name())
        pp_n += 1
    except Exception as e:
        log("pp " + str(e))
if pp_n == 0:
    log("no PostProcessVolume in level (skip EV)")

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("lvl " + str(e))

log("DONE")
