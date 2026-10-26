# -*- coding: utf-8 -*-
"""
phase_sun_moon_dual.py
Rebuild FarmSim25D day/night to Epic dual DirectionalLight pattern:
  Sun AtmosphereSunLightIndex=0, Moon=1, opposite yaw, elev crossfade.
Keeps TimeOfDay/CurrentDay/AdvanceDayGrowth clock. No Day Sequence plugin.
Does NOT touch AdvanceDayGrowth, GrowCell, IMC, grid, BlockedIndices, airwalls.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

# Intensity / pitch tunables (Epic-style elev crossfade)
SUN_I_IN_A = -0.15
SUN_I_IN_B = 0.4
SUN_I_OUT_A = 0.0
SUN_I_OUT_B = 8.0
MOON_I_IN_A = 0.15   # reverse: day off
MOON_I_IN_B = -0.4
MOON_I_OUT_A = 0.0
MOON_I_OUT_B = 2.5
PITCH_IN_A = -1.0
PITCH_IN_B = 1.0
PITCH_OUT_A = 25.0   # midnight: sun below horizon
PITCH_OUT_B = -70.0  # noon: high
SKY_I_OUT_A = 0.6
SKY_I_OUT_B = 1.2
SUN_RGB = (1.00, 0.94, 0.78)
MOON_RGB = (0.55, 0.65, 0.95)
TAG_SUN = "FarmSun"
TAG_MOON = "FarmMoon"


def log(m):
    unreal.log("[SUNMOON] " + str(m))
    print("[SUNMOON] " + str(m))


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


def ret(node):
    return find_pin(node, "ReturnValue", "Output") or find_pin(node, "Return", "Output")


def call(ge, path, x, y):
    n = ge.add_call_function_node(path)
    if n:
        bel.set_node_pos(n, pos(x, y))
    else:
        log("FAIL " + path)
    return n


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


def clear_fn(ge):
    entry = None
    kill = []
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_FunctionEntry":
            entry = n
        else:
            kill.append(n)
    if kill:
        ge.remove_nodes(kill)
        log("cleared {} nodes".format(len(kill)))
    return entry


def make_pin(text):
    p = unreal.EdGraphPinType()
    p.import_text(text)
    return p


def var_names(bp):
    return [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]


def get_level_actors():
    try:
        return list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    except Exception:
        return list(unreal.EditorLevelLibrary.get_all_level_actors())


def set_actor_tags(actor, tag_names):
    try:
        arr = unreal.Array(unreal.Name)
        for t in tag_names:
            arr.append(unreal.Name(t))
        actor.set_editor_property("tags", arr)
        log("tags {} -> {}".format(actor.get_actor_label(), tag_names))
        return True
    except Exception as e:
        log("tags fail {} {}".format(actor.get_name(), e))
        return False


def save_level():
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved")
        return True
    except Exception as e:
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
            log("level saved2")
            return True
        except Exception as e2:
            log("level save fail {} / {}".format(e, e2))
            return False


def compile_save(bp):
    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile " + str(e))
    ok = unreal.EditorAssetLibrary.save_asset(MGR)
    log("save MGR={}".format(ok))
    return ok


# ---------------------------------------------------------------------------
# Level: ensure Moon DirectionalLight + tags + atmosphere indices
# ---------------------------------------------------------------------------
def setup_level_lights():
    log("=== setup level lights ===")
    actors = get_level_actors()
    sun = None
    moon = None
    sky = None
    sky_atmo = None
    for a in actors:
        cn = a.get_class().get_name()
        label = a.get_actor_label() if hasattr(a, "get_actor_label") else a.get_name()
        if cn == "DirectionalLight":
            if "moon" in label.lower() or a.get_name().lower().startswith("moon"):
                moon = a
            else:
                # Prefer existing non-moon; if multiple, last non-moon wins then first kept
                if sun is None:
                    sun = a
                else:
                    # If we already have a sun and this isn't moon-named, check idx
                    try:
                        comps = a.get_components_by_class(unreal.DirectionalLightComponent)
                        idx = comps[0].get_editor_property("atmosphere_sun_light_index") if comps else 0
                        if int(idx) == 1:
                            moon = a
                        else:
                            sun = a
                    except Exception:
                        sun = a
        elif cn == "SkyLight":
            sky = a
        elif cn == "SkyAtmosphere":
            sky_atmo = a

    if sky_atmo is None:
        try:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            sky_atmo = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
            sky_atmo.set_actor_label("SkyAtmosphere")
            log("spawned SkyAtmosphere")
        except Exception as e:
            log("SkyAtmosphere spawn fail " + str(e))
    else:
        log("SkyAtmosphere ok " + sky_atmo.get_name())

    if sun is None:
        try:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 200))
            log("spawned Sun DirectionalLight")
        except Exception as e:
            log("sun spawn fail " + str(e))
            return False

    try:
        sun.set_actor_label("SunLight")
    except Exception:
        pass
    set_actor_tags(sun, [TAG_SUN])
    try:
        for c in sun.get_components_by_class(unreal.DirectionalLightComponent):
            c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            c.set_editor_property("atmosphere_sun_light", True)
            c.set_editor_property("atmosphere_sun_light_index", 0)
            c.set_editor_property("cast_shadows", True)
            # warm default; runtime overwrites
            try:
                c.set_editor_property("light_color", unreal.Color(255, 240, 199, 255))
            except Exception:
                pass
            log("Sun configured inten={} idx={}".format(
                c.get_editor_property("intensity"),
                c.get_editor_property("atmosphere_sun_light_index")))
    except Exception as e:
        log("sun cfg " + str(e))

    if moon is None:
        try:
            eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            moon = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 200))
            log("spawned MoonLight")
        except Exception as e:
            log("moon spawn fail " + str(e))
            return False
    try:
        moon.set_actor_label("MoonLight")
    except Exception:
        pass
    set_actor_tags(moon, [TAG_MOON])
    try:
        for c in moon.get_components_by_class(unreal.DirectionalLightComponent):
            c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
            c.set_editor_property("atmosphere_sun_light", True)
            c.set_editor_property("atmosphere_sun_light_index", 1)
            c.set_editor_property("cast_shadows", True)
            c.set_editor_property("intensity", 0.0)
            try:
                c.set_editor_property("light_color", unreal.Color(140, 166, 242, 255))
            except Exception:
                pass
            log("Moon configured inten={} idx={}".format(
                c.get_editor_property("intensity"),
                c.get_editor_property("atmosphere_sun_light_index")))
    except Exception as e:
        log("moon cfg " + str(e))

    if sky:
        try:
            for c in sky.get_components_by_class(unreal.SkyLightComponent):
                c.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
                try:
                    c.set_editor_property("real_time_capture", True)
                except Exception as e:
                    log("rtc " + str(e))
                log("SkyLight rtc={} inten={}".format(
                    c.get_editor_property("real_time_capture"),
                    c.get_editor_property("intensity")))
        except Exception as e:
            log("sky cfg " + str(e))

    save_level()
    return True


# ---------------------------------------------------------------------------
# BP var MoonActor
# ---------------------------------------------------------------------------
def ensure_moon_var(bp):
    names = var_names(bp)
    if "MoonActor" in names:
        log("MoonActor var exists")
        return True
    pin = '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.Actor")'
    ok = bel.add_member_variable(bp, "MoonActor", make_pin(pin))
    log("add MoonActor -> {}".format(ok))
    return ok


# ---------------------------------------------------------------------------
# Rebuild ApplyDayNightVisuals (dual light)
# ---------------------------------------------------------------------------
def rebuild_apply_day_night(bp):
    log("=== rebuild ApplyDayNightVisuals (sun+moon) ===")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    entry = clear_fn(ge)
    if not entry:
        for n in ge.list_all_nodes():
            if n.get_class().get_name() == "K2Node_FunctionEntry":
                entry = n
    bel.set_node_pos(entry, pos(0, 0))

    get_tod = ge.add_get_member_variable_node("TimeOfDay")
    bel.set_node_pos(get_tod, pos(0, 200))

    # elev = Sin((TOD - 0.25) * 2PI)
    sub = call(ge, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 260, 200)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(sub, "A", "Input"), "tod-")
    set_val(find_pin(sub, "B", "Input"), "0.25", "0.25")

    mul = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 520, 200)
    connect(ret(sub), find_pin(mul, "A", "Input"), "*2pi")
    set_val(find_pin(mul, "B", "Input"), "6.283185", "2pi")

    sinn = call(ge, "/Script/Engine.KismetMathLibrary:Sin", 780, 200)
    connect(ret(mul), find_pin(sinn, "A", "Input"), "sin")

    # SunIntensity
    sun_i = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1100, 40)
    connect(ret(sinn), find_pin(sun_i, "Value", "Input"), "elev->SunI")
    set_val(find_pin(sun_i, "InRangeA", "Input"), str(SUN_I_IN_A), "sInA")
    set_val(find_pin(sun_i, "InRangeB", "Input"), str(SUN_I_IN_B), "sInB")
    set_val(find_pin(sun_i, "OutRangeA", "Input"), str(SUN_I_OUT_A), "sOutA")
    set_val(find_pin(sun_i, "OutRangeB", "Input"), str(SUN_I_OUT_B), "sOutB")

    # MoonIntensity (reverse elev)
    moon_i = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1100, 220)
    connect(ret(sinn), find_pin(moon_i, "Value", "Input"), "elev->MoonI")
    set_val(find_pin(moon_i, "InRangeA", "Input"), str(MOON_I_IN_A), "mInA")
    set_val(find_pin(moon_i, "InRangeB", "Input"), str(MOON_I_IN_B), "mInB")
    set_val(find_pin(moon_i, "OutRangeA", "Input"), str(MOON_I_OUT_A), "mOutA")
    set_val(find_pin(moon_i, "OutRangeB", "Input"), str(MOON_I_OUT_B), "mOutB")

    # Pitch from elev
    pitch = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 1100, 400)
    connect(ret(sinn), find_pin(pitch, "Value", "Input"), "elev->P")
    set_val(find_pin(pitch, "InRangeA", "Input"), str(PITCH_IN_A), "pInA")
    set_val(find_pin(pitch, "InRangeB", "Input"), str(PITCH_IN_B), "pInB")
    set_val(find_pin(pitch, "OutRangeA", "Input"), str(PITCH_OUT_A), "pOutA")
    set_val(find_pin(pitch, "OutRangeB", "Input"), str(PITCH_OUT_B), "pOutB")

    # Yaw = TOD * 360 continuous
    yaw = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 520, 420)
    connect(find_pin(get_tod, "TimeOfDay", "Output"), find_pin(yaw, "A", "Input"), "tod*yaw")
    set_val(find_pin(yaw, "B", "Input"), "360.0", "yaw360")

    # Moon yaw = sun yaw + 180
    yaw_m = call(ge, "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", 780, 520)
    connect(ret(yaw), find_pin(yaw_m, "A", "Input"), "yaw+")
    set_val(find_pin(yaw_m, "B", "Input"), "180.0", "+180")

    # Colors
    sun_col = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1100, 580)
    set_val(find_pin(sun_col, "R", "Input"), str(SUN_RGB[0]), "sR")
    set_val(find_pin(sun_col, "G", "Input"), str(SUN_RGB[1]), "sG")
    set_val(find_pin(sun_col, "B", "Input"), str(SUN_RGB[2]), "sB")
    set_val(find_pin(sun_col, "A", "Input"), "1.0", "sA")

    moon_col = call(ge, "/Script/Engine.KismetMathLibrary:MakeColor", 1100, 740)
    set_val(find_pin(moon_col, "R", "Input"), str(MOON_RGB[0]), "mR")
    set_val(find_pin(moon_col, "G", "Input"), str(MOON_RGB[1]), "mG")
    set_val(find_pin(moon_col, "B", "Input"), str(MOON_RGB[2]), "mB")
    set_val(find_pin(moon_col, "A", "Input"), "1.0", "mA")

    make_sun_rot = call(ge, "/Script/Engine.KismetMathLibrary:MakeRotator", 1450, 200)
    connect(ret(pitch), find_pin(make_sun_rot, "Pitch", "Input"), "sPitch")
    connect(ret(yaw), find_pin(make_sun_rot, "Yaw", "Input"), "sYaw")
    set_val(find_pin(make_sun_rot, "Roll", "Input"), "0.0", "sRoll")

    make_moon_rot = call(ge, "/Script/Engine.KismetMathLibrary:MakeRotator", 1450, 420)
    connect(ret(pitch), find_pin(make_moon_rot, "Pitch", "Input"), "mPitch")
    connect(ret(yaw_m), find_pin(make_moon_rot, "Yaw", "Input"), "mYaw")
    set_val(find_pin(make_moon_rot, "Roll", "Input"), "0.0", "mRoll")

    # ---- Sun path ----
    get_sun = ge.add_get_member_variable_node("SunActor")
    bel.set_node_pos(get_sun, pos(1450, 40))
    isv_s = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 1680, 40)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(isv_s, "Object", "Input"), "sun valid")

    br_s = ge.add_branch_node()
    bel.set_node_pos(br_s, pos(1920, 0))
    connect(find_pin(entry, "then", "Output"), find_pin(br_s, "execute", "Input"), "e->brS")
    connect(ret(isv_s), find_pin(br_s, "Condition", "Input"), "condS")

    set_s_rot = call(ge, "/Script/Engine.Actor:K2_SetActorRotation", 2180, 0)
    connect(find_pin(br_s, "then", "Output"), find_pin(set_s_rot, "execute", "Input"), "brS->rot")
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(set_s_rot, "self", "Input"), "sunself")
    connect(ret(make_sun_rot), find_pin(set_s_rot, "NewRotation", "Input"), "sNewRot")
    set_val(find_pin(set_s_rot, "bTeleportPhysics", "Input"), "true", "sTele")

    get_s_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 2180, 200)
    connect(find_pin(get_sun, "SunActor", "Output"), find_pin(get_s_comp, "self", "Input"), "suncomp")
    set_val(find_pin(get_s_comp, "ComponentClass", "Input"), "/Script/Engine.DirectionalLightComponent", "sDL")

    set_s_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 2520, 0)
    connect(find_pin(set_s_rot, "then", "Output"), find_pin(set_s_i, "execute", "Input"), "sRot->I")
    connect(ret(get_s_comp), find_pin(set_s_i, "self", "Input"), "sCompI")
    connect(ret(sun_i), find_pin(set_s_i, "NewIntensity", "Input"), "sIval")

    set_s_c = call(ge, "/Script/Engine.LightComponent:SetLightColor", 2820, 0)
    connect(find_pin(set_s_i, "then", "Output"), find_pin(set_s_c, "execute", "Input"), "sI->C")
    connect(ret(get_s_comp), find_pin(set_s_c, "self", "Input"), "sCompC")
    connect(ret(sun_col), find_pin(set_s_c, "NewLightColor", "Input"), "sCval")

    # Merge sun then/else into moon branch
    # ---- Moon path ----
    get_moon = ge.add_get_member_variable_node("MoonActor")
    bel.set_node_pos(get_moon, pos(2820, 280))
    isv_m = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 3050, 280)
    connect(find_pin(get_moon, "MoonActor", "Output"), find_pin(isv_m, "Object", "Input"), "moon valid")

    br_m = ge.add_branch_node()
    bel.set_node_pos(br_m, pos(3280, 0))
    # from sun color then OR sun else
    connect(find_pin(set_s_c, "then", "Output"), find_pin(br_m, "execute", "Input"), "sC->brM")
    # also wire sun else into br_m — need a second path; use Sequence or wire else too
    # K2 Branch only one exec in — use intermediate: wire else also to br_m by connecting both
    # UE pins allow multiple incoming? Usually one. Use a Sequence node after entry... simpler:
    # Wire sun-else separately with a dummy pass-through: both connect to br_m execute (multi-in often works in UE BP)
    connect(find_pin(br_s, "else", "Output"), find_pin(br_m, "execute", "Input"), "sElse->brM")
    connect(ret(isv_m), find_pin(br_m, "Condition", "Input"), "condM")

    set_m_rot = call(ge, "/Script/Engine.Actor:K2_SetActorRotation", 3540, 0)
    connect(find_pin(br_m, "then", "Output"), find_pin(set_m_rot, "execute", "Input"), "brM->rot")
    connect(find_pin(get_moon, "MoonActor", "Output"), find_pin(set_m_rot, "self", "Input"), "moonself")
    connect(ret(make_moon_rot), find_pin(set_m_rot, "NewRotation", "Input"), "mNewRot")
    set_val(find_pin(set_m_rot, "bTeleportPhysics", "Input"), "true", "mTele")

    get_m_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 3540, 220)
    connect(find_pin(get_moon, "MoonActor", "Output"), find_pin(get_m_comp, "self", "Input"), "mooncomp")
    set_val(find_pin(get_m_comp, "ComponentClass", "Input"), "/Script/Engine.DirectionalLightComponent", "mDL")

    set_m_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 3880, 0)
    connect(find_pin(set_m_rot, "then", "Output"), find_pin(set_m_i, "execute", "Input"), "mRot->I")
    connect(ret(get_m_comp), find_pin(set_m_i, "self", "Input"), "mCompI")
    connect(ret(moon_i), find_pin(set_m_i, "NewIntensity", "Input"), "mIval")

    set_m_c = call(ge, "/Script/Engine.LightComponent:SetLightColor", 4180, 0)
    connect(find_pin(set_m_i, "then", "Output"), find_pin(set_m_c, "execute", "Input"), "mI->C")
    connect(ret(get_m_comp), find_pin(set_m_c, "self", "Input"), "mCompC")
    connect(ret(moon_col), find_pin(set_m_c, "NewLightColor", "Input"), "mCval")

    # ---- Sky path (mild) ----
    sky_i = call(ge, "/Script/Engine.KismetMathLibrary:MapRangeClamped", 3880, 400)
    connect(ret(sinn), find_pin(sky_i, "Value", "Input"), "elev->Sky")
    set_val(find_pin(sky_i, "InRangeA", "Input"), "-1.0", "skInA")
    set_val(find_pin(sky_i, "InRangeB", "Input"), "1.0", "skInB")
    set_val(find_pin(sky_i, "OutRangeA", "Input"), str(SKY_I_OUT_A), "skOutA")
    set_val(find_pin(sky_i, "OutRangeB", "Input"), str(SKY_I_OUT_B), "skOutB")

    get_sky = ge.add_get_member_variable_node("SkyLightActor")
    bel.set_node_pos(get_sky, pos(4180, 280))
    isv_sk = call(ge, "/Script/Engine.KismetSystemLibrary:IsValid", 4400, 280)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(isv_sk, "Object", "Input"), "sky valid")

    br_sk = ge.add_branch_node()
    bel.set_node_pos(br_sk, pos(4620, 0))
    connect(find_pin(set_m_c, "then", "Output"), find_pin(br_sk, "execute", "Input"), "mC->brSk")
    connect(find_pin(br_m, "else", "Output"), find_pin(br_sk, "execute", "Input"), "mElse->brSk")
    connect(ret(isv_sk), find_pin(br_sk, "Condition", "Input"), "condSk")

    get_sk_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 4860, 120)
    connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(get_sk_comp, "self", "Input"), "skycomp")
    set_val(find_pin(get_sk_comp, "ComponentClass", "Input"), "/Script/Engine.SkyLightComponent", "SkyComp")

    # Prefer LightComponentBase SetIntensity (works for SkyLightComponent)
    set_sk_i = call(ge, "/Script/Engine.LightComponentBase:SetIntensity", 5120, 0)
    if not set_sk_i:
        set_sk_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 5120, 0)
    connect(find_pin(br_sk, "then", "Output"), find_pin(set_sk_i, "execute", "Input"), "brSk->sI")
    connect(ret(get_sk_comp), find_pin(set_sk_i, "self", "Input"), "skCompI")
    connect(ret(sky_i), find_pin(set_sk_i, "NewIntensity", "Input"), "skIval")

    ret_ok = ge.add_return_node()
    bel.set_node_pos(ret_ok, pos(5400, 0))
    connect(find_pin(set_sk_i, "then", "Output"), find_pin(ret_ok, "execute", "Input"), "ok")

    ret_nosky = ge.add_return_node()
    bel.set_node_pos(ret_nosky, pos(4860, 280))
    connect(find_pin(br_sk, "else", "Output"), find_pin(ret_nosky, "execute", "Input"), "nosky")

    errs = ge.list_nodes_with_errors()
    log("ApplyDayNightVisuals errors={}".format(len(errs)))
    for e in errs:
        log("  err " + title(e))
    return len(errs) == 0


# ---------------------------------------------------------------------------
# BeginPlay: assign Sun/Moon by tag
# ---------------------------------------------------------------------------
def wire_beginplay_moon(bp):
    log("=== wire BeginPlay sun/moon tags ===")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

    # Idempotent: if Set MoonActor exists, skip
    if any(title(n) == "Set MoonActor" for n in ge.list_all_nodes()):
        log("Set MoonActor already present — skip rewire")
        return True

    # Find existing Set SunActor and its GetAllActorsOfClass DirectionalLight
    set_sun = None
    set_sky = None
    get_dl = None
    for n in ge.list_all_nodes():
        t = title(n)
        if t == "Set SunActor":
            set_sun = n
        elif t == "Set SkyLightActor":
            set_sky = n
        elif "GetAllActorsOfClass" in t.replace(" ", "") or t == "Get All Actors Of Class":
            pin = find_pin(n, "ActorClass", "Input")
            try:
                v = pin.get_pin_value() if pin else ""
            except Exception:
                v = ""
            if "DirectionalLight" in str(v):
                get_dl = n

    if not set_sun:
        log("NO Set SunActor — cannot wire")
        return False

    # Replace DirectionalLight GetAllActorsOfClass with GetAllActorsWithTag FarmSun
    if get_dl:
        # Find Array_Get connected to OutActors
        out_actors = find_pin(get_dl, "OutActors", "Output")
        arr_get = None
        if out_actors:
            for cp in list(out_actors.list_connected_pins() or []):
                arr_get = cp.get_owning_node()
                break
        exec_in = find_pin(get_dl, "execute", "Input")
        prev = None
        if exec_in:
            for cp in list(exec_in.list_connected_pins() or []):
                prev = cp.get_owning_node()
                break
        then_out = find_pin(get_dl, "then", "Output")
        next_n = None
        if then_out:
            for cp in list(then_out.list_connected_pins() or []):
                next_n = cp.get_owning_node()
                break

        bx, by = 400, -450
        try:
            # place near old
            pass
        except Exception:
            pass
        # Use positions relative
        get_tag = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsWithTag", bx, by)
        if not get_tag:
            log("FAIL GetAllActorsWithTag")
            return False
        set_val(find_pin(get_tag, "Tag", "Input"), TAG_SUN, "FarmSun")

        # reconnect prev -> get_tag -> set_sun (via new Array_Get)
        if prev:
            prev_then = find_pin(prev, "then", "Output") or find_pin(prev, "Completed", "Output")
            if prev_then:
                try:
                    prev_then.break_pin_links(False)
                except Exception:
                    try:
                        prev_then.break_pin_links()
                    except Exception:
                        pass
                connect(prev_then, find_pin(get_tag, "execute", "Input"), "prev->tagSun")

        arr_sun = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx + 300, by)
        connect(find_pin(get_tag, "OutActors", "Output"), find_pin(arr_sun, "TargetArray", "Input"), "sunArr")
        set_val(find_pin(arr_sun, "Index", "Input"), "0", "sun0")

        # rewire Set SunActor item from new Array_Get
        sun_pin = find_pin(set_sun, "SunActor", "Input")
        if sun_pin:
            try:
                sun_pin.break_pin_links(False)
            except Exception:
                try:
                    sun_pin.break_pin_links()
                except Exception:
                    pass
        connect(find_pin(arr_sun, "Item", "Output"), sun_pin, "tagItem->Sun")

        # exec get_tag -> set_sun
        set_sun_exec = find_pin(set_sun, "execute", "Input")
        if set_sun_exec:
            try:
                set_sun_exec.break_pin_links(False)
            except Exception:
                try:
                    set_sun_exec.break_pin_links()
                except Exception:
                    pass
        connect(find_pin(get_tag, "then", "Output"), set_sun_exec, "tag->SetSun")

        # remove old get_dl and its Array_Get if unused
        kill = []
        if get_dl:
            kill.append(get_dl)
        if arr_get and arr_get is not arr_sun:
            # only remove if no longer linked meaningfully
            kill.append(arr_get)
        if kill:
            try:
                ge.remove_nodes(kill)
                log("removed old DL GetAllActors nodes={}".format(len(kill)))
            except Exception as e:
                log("rm old " + str(e))
    else:
        log("no DirectionalLight GetAllActors — will still add moon")

    # Insert Moon assignment after Set SkyLightActor, before whatever follows
    if not set_sky:
        # fall back: after Set SunActor
        set_sky = set_sun
        log("no Set SkyLightActor; chaining moon after Set SunActor")

    sky_then = find_pin(set_sky, "then", "Output")
    after = None
    if sky_then:
        links = list(sky_then.list_connected_pins() or [])
        if links:
            after = links[0].get_owning_node()
        try:
            sky_then.break_pin_links(False)
        except Exception:
            try:
                sky_then.break_pin_links()
            except Exception:
                pass

    bx2, by2 = 1450, -650
    get_moon_tag = call(ge, "/Script/Engine.GameplayStatics:GetAllActorsWithTag", bx2, by2)
    set_val(find_pin(get_moon_tag, "Tag", "Input"), TAG_MOON, "FarmMoon")
    connect(sky_then, find_pin(get_moon_tag, "execute", "Input"), "sky->moonTag")

    arr_moon = call(ge, "/Script/Engine.KismetArrayLibrary:Array_Get", bx2 + 300, by2)
    connect(find_pin(get_moon_tag, "OutActors", "Output"), find_pin(arr_moon, "TargetArray", "Input"), "moonArr")
    set_val(find_pin(arr_moon, "Index", "Input"), "0", "moon0")

    set_moon = ge.add_set_member_variable_node("MoonActor")
    bel.set_node_pos(set_moon, pos(bx2 + 580, by2))
    connect(find_pin(get_moon_tag, "then", "Output"), find_pin(set_moon, "execute", "Input"), "->SetMoon")
    connect(find_pin(arr_moon, "Item", "Output"), find_pin(set_moon, "MoonActor", "Input"), "moonItem")

    if after:
        connect(find_pin(set_moon, "then", "Output"), find_pin(after, "execute", "Input"), "moon->after")
        log("moon chained before " + title(after))
    else:
        log("moon at end of chain (no after)")

    return True


def verify(bp):
    log("=== verify ===")
    names = var_names(bp)
    log("MoonActor var=" + str("MoonActor" in names))

    actors = get_level_actors()
    for a in actors:
        if a.get_class().get_name() != "DirectionalLight":
            continue
        label = a.get_actor_label()
        try:
            tags = [str(t) for t in a.get_editor_property("tags")]
        except Exception:
            tags = []
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            log("VERIFY light label={} tags={} idx={} atm={} inten={}".format(
                label, tags,
                c.get_editor_property("atmosphere_sun_light_index"),
                c.get_editor_property("atmosphere_sun_light"),
                c.get_editor_property("intensity")))

    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
    set_i = 0
    set_rot = 0
    has_360 = False
    has_180 = False
    moon_get = False
    for n in ge.list_all_nodes():
        t = title(n)
        if "SetIntensity" in t or "Set Intensity" in t:
            set_i += 1
        if "Set Actor Rotation" in t or "SetActorRotation" in t.replace(" ", ""):
            set_rot += 1
        if "MoonActor" in t:
            moon_get = True
        for p in bel.list_all_pins(n):
            try:
                v = str(p.get_pin_value())
            except Exception:
                v = ""
            if v in ("360.0", "360"):
                has_360 = True
            if v in ("180.0", "180"):
                has_180 = True
    log("VERIFY Apply SetIntensity={} SetRotation={} yaw360={} yaw+180={} MoonActorNode={}".format(
        set_i, set_rot, has_360, has_180, moon_get))
    errs = ge.list_nodes_with_errors()
    log("VERIFY Apply errors={}".format(len(errs)))

    ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    has_set_moon = any(title(n) == "Set MoonActor" for n in ge2.list_all_nodes())
    log("VERIFY Set MoonActor in EG={}".format(has_set_moon))
    return set_i >= 2 and has_360 and moon_get and has_set_moon


def main():
    log("START dual sun/moon")
    bp = unreal.load_asset(MGR)
    if not bp:
        log("NO BP_GridManager")
        return

    if not setup_level_lights():
        log("ABORT level lights")
        return

    ensure_moon_var(bp)
    compile_save(bp)

    ok_apply = rebuild_apply_day_night(bp)
    compile_save(bp)
    if not ok_apply:
        log("WARN ApplyDayNightVisuals had errors — check graph")

    ok_wire = wire_beginplay_moon(bp)
    compile_save(bp)
    save_level()

    ok_v = verify(bp)
    log("DONE apply_ok={} wire_ok={} verify={}".format(ok_apply, ok_wire, ok_v))
    log("FORMULAS: elev=Sin((TOD-0.25)*2PI); "
        "SunI=Map(elev,{},{},{},{}); MoonI=Map(elev,{},{},{},{}); "
        "Pitch=Map(elev,-1,1,{},{}); Yaw=TOD*360; MoonYaw=Yaw+180".format(
            SUN_I_IN_A, SUN_I_IN_B, SUN_I_OUT_A, SUN_I_OUT_B,
            MOON_I_IN_A, MOON_I_IN_B, MOON_I_OUT_A, MOON_I_OUT_B,
            PITCH_OUT_A, PITCH_OUT_B))


if __name__ == "__main__":
    main()
