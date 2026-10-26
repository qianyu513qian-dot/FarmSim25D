# -*- coding: utf-8 -*-
"""SURGICAL: moon Pitch = -sunPitch; bump moon/sky night intensity; reconnect Sky SetIntensity if missing.
FORBIDDEN: clear/rebuild ApplyDayNightVisuals."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[MOON_PITCH] " + str(m))
    print("[MOON_PITCH] " + str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok

def set_val(pin, value, label=""):
    if not pin:
        log("no " + label)
        return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, value))
        return True
    except Exception as e:
        log("set fail {} {}".format(label, e))
        return False

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def ret(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output")

bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

# Collect nodes
make_rots = []
map_ranges = []
set_intens = []
get_moon = None
get_sky = None
sky_map = None
branches = []
returns = []
for n in ge.list_all_nodes():
    t = title(n)
    if "MakeRotator" in t:
        make_rots.append(n)
    if "MapRange" in t:
        map_ranges.append(n)
    if "SetIntensity" in t:
        set_intens.append(n)
    if "Get MoonActor" in t or t == "Get MoonActor":
        get_moon = n
    if "Get SkyLightActor" in t:
        get_sky = n
    if t == "Branch":
        branches.append(n)
    if "Return" in t:
        returns.append(n)

log("MakeRotators={} MapRanges={} SetIntensity={}".format(len(make_rots), len(map_ranges), len(set_intens)))

# Identify pitch MapRange: OutRangeA=25 OutRangeB=-70
pitch_map = None
sun_i_map = None
moon_i_map = None
sky_i_map = None
for n in map_ranges:
    oa = find_pin(n, "OutRangeA", "Input")
    ob = find_pin(n, "OutRangeB", "Input")
    ia = find_pin(n, "InRangeA", "Input")
    try:
        oav = oa.get_pin_value() if oa else ""
        obv = ob.get_pin_value() if ob else ""
        iav = ia.get_pin_value() if ia else ""
    except Exception:
        oav = obv = iav = ""
    log("MapRange InA={} OutA={} OutB={}".format(iav, oav, obv))
    if "25" in str(oav) and "70" in str(obv):
        pitch_map = n
    elif str(oav).startswith("0") and "8" in str(obv):
        sun_i_map = n
    elif "2.5" in str(obv) or (str(oav).startswith("0") and "2" in str(obv) and "8" not in str(obv)):
        # moon intensity: OutB=2.5
        if "2.5" in str(obv) or ("0.15" in str(iav) or "0.15" in str(find_pin(n,"InRangeA","Input").get_pin_value() if find_pin(n,"InRangeA","Input") else "")):
            moon_i_map = n
        elif "0.6" in str(oav) or "1.2" in str(obv):
            sky_i_map = n
        else:
            moon_i_map = n
    elif "0.6" in str(oav) or "1.2" in str(obv):
        sky_i_map = n

log("pitch_map={} sun_i={} moon_i={} sky_i={}".format(bool(pitch_map), bool(sun_i_map), bool(moon_i_map), bool(sky_i_map)))

# Identify moon MakeRotator: its Yaw comes from +180 add node
moon_rot = None
sun_rot = None
for n in make_rots:
    yaw_pin = find_pin(n, "Yaw", "Input")
    links = list(yaw_pin.list_connected_pins()) if yaw_pin else []
    from_add180 = False
    for lp in links:
        ot = title(lp.get_owning_node())
        # float + float with B=180
        if "+" in ot or "Add" in ot or "float + float" in ot:
            from_add180 = True
        bp_pin = find_pin(lp.get_owning_node(), "B", "Input")
        try:
            if bp_pin and "180" in str(bp_pin.get_pin_value()):
                from_add180 = True
        except Exception:
            pass
    if from_add180:
        moon_rot = n
    else:
        sun_rot = n

# fallback: second MakeRotator is moon if first is sun
if not moon_rot and len(make_rots) >= 2:
    # check which SetActorRotation uses which
    sun_rot = make_rots[0]
    moon_rot = make_rots[1]
    log("fallback MakeRotators order sun=0 moon=1")
log("sun_rot={} moon_rot={}".format(bool(sun_rot), bool(moon_rot)))

# --- 1) Moon pitch = -sun pitch ---
if pitch_map and moon_rot:
    moon_pitch_pin = find_pin(moon_rot, "Pitch", "Input")
    # break existing pitch links into moon
    if moon_pitch_pin:
        for cp in list(moon_pitch_pin.list_connected_pins() or []):
            try:
                moon_pitch_pin.break_single_pin_link(cp)
                log("broke moon pitch from " + title(cp.get_owning_node()))
            except Exception as e:
                try:
                    moon_pitch_pin.break_pin_links(False)
                    log("broke all moon pitch links")
                    break
                except Exception as e2:
                    log("break fail " + str(e2))

    # Add Multiply_DoubleDouble: pitch * -1
    # Place near moon rotator
    try:
        mx = bel.get_node_pos(moon_rot).x - 280
        my = bel.get_node_pos(moon_rot).y + 40
    except Exception:
        mx, my = 1400, 400

    neg = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble")
    if not neg:
        neg = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Multiply_FloatFloat")
    bel.set_node_pos(neg, pos(mx, my))
    connect(ret(pitch_map), find_pin(neg, "A", "Input"), "pitch->negA")
    set_val(find_pin(neg, "B", "Input"), "-1.0", "neg*-1")
    connect(ret(neg), moon_pitch_pin, "neg->moonPitch")
    log("moon pitch inverted")
else:
    log("SKIP pitch invert missing nodes")

# --- 2) Bump moon night intensity 2.5 -> 5.0 ---
if moon_i_map:
    set_val(find_pin(moon_i_map, "OutRangeB", "Input"), "5.0", "moonMaxI")
else:
    # find by InRangeA=0.15
    for n in map_ranges:
        ia = find_pin(n, "InRangeA", "Input")
        try:
            if ia and "0.15" in str(ia.get_pin_value()):
                moon_i_map = n
                set_val(find_pin(n, "OutRangeB", "Input"), "5.0", "moonMaxI")
                break
        except Exception:
            pass

# --- 3) Bump sky night floor 0.6 -> 1.5 ---
if not sky_i_map:
    for n in map_ranges:
        oa = find_pin(n, "OutRangeA", "Input")
        try:
            if oa and "0.6" in str(oa.get_pin_value()):
                sky_i_map = n
                break
        except Exception:
            pass
if sky_i_map:
    set_val(find_pin(sky_i_map, "OutRangeA", "Input"), "1.5", "skyNight")
    set_val(find_pin(sky_i_map, "OutRangeB", "Input"), "2.0", "skyDay")

# --- 4) Reconnect SkyLight SetIntensity if Branch.then goes straight to Return ---
# Find sky branch: condition from SkyLight IsValid
sky_branch = None
for n in ge.list_all_nodes():
    if title(n) != "Branch":
        continue
    cond = find_pin(n, "Condition", "Input")
    for cp in list(cond.list_connected_pins() or []):
        # IsValid whose Object from SkyLightActor
        own = cp.get_owning_node()
        if "IsValid" in title(own):
            obj = find_pin(own, "Object", "Input")
            for op in list(obj.list_connected_pins() or []):
                if "Sky" in title(op.get_owning_node()):
                    sky_branch = n
                    break
    if sky_branch:
        break

log("sky_branch={}".format(bool(sky_branch)))

# Check if any SetIntensity already for sky
has_sky_set_i = False
for n in set_intens:
    sp = find_pin(n, "self", "Input")
    for cp in list(sp.list_connected_pins() or []):
        ot = title(cp.get_owning_node())
        if "Sky" in ot or "GetComponent" in ot:
            # check component class pin on GetComponentByClass
            pass
    # Check NewIntensity linked to sky map
    ip = find_pin(n, "NewIntensity", "Input")
    for cp in list(ip.list_connected_pins() or []):
        if sky_i_map and cp.get_owning_node() == sky_i_map:
            has_sky_set_i = True
            log("sky SetIntensity already linked to sky map")

if sky_branch and sky_i_map and get_sky and not has_sky_set_i:
    thenp = find_pin(sky_branch, "then", "Output")
    # What does then currently go to?
    then_targets = []
    for cp in list(thenp.list_connected_pins() or []):
        then_targets.append((title(cp.get_owning_node()), str(cp.get_pin_name())))
    log("sky then -> {}".format(then_targets))

    # If goes to Return only, insert SetIntensity
    only_return = all("Return" in t for t, _ in then_targets) if then_targets else True
    if only_return or not then_targets:
        # break then -> return
        for cp in list(thenp.list_connected_pins() or []):
            try:
                thenp.break_single_pin_link(cp)
            except Exception:
                try:
                    thenp.break_pin_links(False)
                except Exception:
                    pass

        get_sc = ge.add_call_function_node("/Script/Engine.Actor:GetComponentByClass")
        bel.set_node_pos(get_sc, pos(3800, 80))
        connect(find_pin(get_sky, "SkyLightActor", "Output") or find_pin(get_sky, "SkyLight", "Output"),
                find_pin(get_sc, "self", "Input"), "sky->getcomp")
        set_val(find_pin(get_sc, "ComponentClass", "Input"), "/Script/Engine.SkyLightComponent", "SkyComp")

        set_si = ge.add_call_function_node("/Script/Engine.SkyLightComponent:SetIntensity")
        bel.set_node_pos(set_si, pos(4100, 0))
        connect(thenp, find_pin(set_si, "execute", "Input"), "br->skyI")
        connect(ret(get_sc), find_pin(set_si, "self", "Input"), "sc->self")
        connect(ret(sky_i_map), find_pin(set_si, "NewIntensity", "Input"), "skyIval")

        # return after
        rn = None
        for n in returns:
            rn = n
            break
        if not rn:
            rn = ge.add_return_node()
            bel.set_node_pos(rn, pos(4400, 0))
        connect(find_pin(set_si, "then", "Output"), find_pin(rn, "execute", "Input"), "skyI->ret")
        log("wired SkyLight SetIntensity")
    else:
        log("sky then already has non-return targets; leave alone")
elif has_sky_set_i:
    log("sky intensity already ok")
else:
    log("skip sky rewire")

# Compile + save — do NOT open editor UI
try:
    bel.compile_blueprint(bp)
    log("compile ok status={}".format(getattr(bp, "status", "?")))
except Exception as e:
    log("compile " + str(e))

unreal.EditorAssetLibrary.save_asset(MGR)
log("saved BP")

# Also raise level moon default intensity for first frame
try:
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    tags = [str(t) for t in a.tags] if hasattr(a, "tags") else []
    label = ""
    try:
        label = str(a.get_actor_label())
    except Exception:
        pass
    name = a.get_name()
    if "Moon" in label or "FarmMoon" in tags or "Moon" in name:
        for c in a.get_components_by_class(unreal.LightComponentBase):
            try:
                c.set_editor_property("intensity", 5.0)
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                # ensure atmosphere index 1
                try:
                    c.set_editor_property("atmosphere_sun_light", True)
                    c.set_editor_property("atmosphere_sun_light_index", 1)
                except Exception:
                    pass
                log("level moon inten->5 label={} tags={}".format(label, tags))
            except Exception as e:
                log("moon edit " + str(e))
    if a.get_class().get_name() == "SkyLight":
        for c in a.get_components_by_class(unreal.LightComponentBase):
            try:
                c.set_editor_property("intensity", 1.5)
                try:
                    c.set_editor_property("real_time_capture", True)
                except Exception:
                    pass
                log("SkyLight inten->1.5")
            except Exception as e:
                log("sky edit " + str(e))

try:
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
except Exception:
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log("level saved2")
    except Exception as e:
        log("level save " + str(e))

# Verify moon pitch link
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
for n in ge.list_all_nodes():
    if "MakeRotator" not in title(n):
        continue
    pp = find_pin(n, "Pitch", "Input")
    links = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in (pp.list_connected_pins() or [])]
    yp = find_pin(n, "Yaw", "Input")
    ylinks = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in (yp.list_connected_pins() or [])]
    log("verify MakeRotator Pitch<-{} Yaw<-{}".format(links, ylinks))

log("DONE")
