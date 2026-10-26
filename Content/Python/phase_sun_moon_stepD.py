# -*- coding: utf-8 -*-
"""
Step D surgical: Fix moon pitch (negate sun pitch), moon cool MakeColor,
re-append SkyLight SetIntensity. NEVER clear ApplyDayNightVisuals.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[SMD] " + str(m))
    print("[SMD] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()


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


def connected(pin):
    if not pin:
        return []
    try:
        return list(pin.list_connected_pins() or [])
    except Exception:
        return []


def break_links(pin, label=""):
    if not pin:
        log("no pin " + label)
        return
    try:
        pin.break_pin_links(False)
        log("broke " + label)
    except Exception:
        try:
            pin.break_pin_links()
            log("broke2 " + label)
        except Exception as e:
            log("break fail {}: {}".format(label, e))


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
        log("FAIL add " + path)
    return n


def node_pos(n):
    try:
        p = bel.get_node_pos(n)
        return p.x, p.y
    except Exception:
        return 0, 0


def main():
    log("Step D START")
    bp = unreal.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

    # Identify nodes by position / links
    sun_rot_make = moon_rot_make = None
    sun_set_color = moon_set_color = None
    sun_si = moon_si = None
    pitch_map = None  # MapRange OutA=25 OutB=-70
    sun_i_map = moon_i_map = sky_i_map = None
    moon_make_color = sun_make_color = None
    sky_branch = None
    get_sky = None
    rets = []

    for n in ge.list_all_nodes():
        t = title(n)
        x, y = node_pos(n)
        cls = n.get_class().get_name()
        if cls == "K2Node_FunctionResult":
            rets.append(n)
        if t == "MakeRotator":
            if y >= 350:
                moon_rot_make = n
            else:
                sun_rot_make = n
        if t == "SetLightColor":
            if x >= 4000:
                moon_set_color = n
            else:
                sun_set_color = n
        if t == "SetIntensity":
            if x >= 3500:
                moon_si = n
            else:
                sun_si = n
        if t == "MapRangeClamped":
            ina = find_pin(n, "InRangeA", "Input")
            outa = find_pin(n, "OutRangeA", "Input")
            outb = find_pin(n, "OutRangeB", "Input")
            try:
                oa = outa.get_pin_value() if outa else ""
                ob = outb.get_pin_value() if outb else ""
                ia = ina.get_pin_value() if ina else ""
            except Exception:
                oa = ob = ia = ""
            if oa in ("25.0", "25") and ob in ("-70.0", "-70"):
                pitch_map = n
            elif oa in ("0.0", "0") and ob in ("8.0", "8") and ia in ("-0.15",):
                sun_i_map = n
            elif oa in ("0.0", "0") and ob in ("2.5",) and ("0.15" in str(ia) or ia == "0.15"):
                moon_i_map = n
            elif oa in ("0.6", "0.60") and ob in ("1.2", "1.20"):
                sky_i_map = n
            log("MapRange x={} oa={} ob={} ia={}".format(x, oa, ob, ia))
        if t == "MakeColor":
            # identify by who consumes ReturnValue
            rv = ret(n)
            for cp in connected(rv):
                own = title(cp.get_owning_node())
                if own == "SetLightColor":
                    ox, oy = node_pos(cp.get_owning_node())
                    if ox >= 4000:
                        moon_make_color = n
                    else:
                        sun_make_color = n
        if t == "Get SkyLightActor":
            get_sky = n
        if cls == "K2Node_IfThenElse":
            # sky branch is last in exec (x~4620)
            if x >= 4500:
                sky_branch = n

    log("sun_rot={} moon_rot={} pitch_map={} sun_i={} moon_i={} sky_i={}".format(
        bool(sun_rot_make), bool(moon_rot_make), bool(pitch_map),
        bool(sun_i_map), bool(moon_i_map), bool(sky_i_map)))
    log("sun_color_node={} moon_color_node={} sky_br={} get_sky={}".format(
        bool(sun_make_color), bool(moon_make_color), bool(sky_branch), bool(get_sky)))

    # --- D1: moon pitch = -sun_pitch ---
    if moon_rot_make and pitch_map:
        pitch_pin = find_pin(moon_rot_make, "Pitch", "Input")
        break_links(pitch_pin, "moon.Pitch")
        neg = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble", 1320, 500)
        if not neg:
            # fallback float*
            neg = call(ge, "/Script/Engine.KismetMathLibrary:Multiply_FloatFloat", 1320, 500)
        connect(ret(pitch_map), find_pin(neg, "A", "Input"), "pitch->negA")
        set_val(find_pin(neg, "B", "Input"), "-1.0", "neg*-1")
        connect(ret(neg), pitch_pin, "neg->moonPitch")
        log("moon pitch negated")
    else:
        log("SKIP moon pitch — missing nodes")

    # --- D2: moon MakeColor cool ---
    if moon_make_color:
        set_val(find_pin(moon_make_color, "R", "Input"), "0.55", "moonR")
        set_val(find_pin(moon_make_color, "G", "Input"), "0.65", "moonG")
        set_val(find_pin(moon_make_color, "B", "Input"), "0.95", "moonB")
        set_val(find_pin(moon_make_color, "A", "Input"), "1.0", "moonA")
    else:
        log("WARN no moon MakeColor — will leave level color")

    # --- D3: ensure sun intensity night floor 0 ---
    if sun_i_map:
        set_val(find_pin(sun_i_map, "OutRangeA", "Input"), "0.0", "sunOutA")
        set_val(find_pin(sun_i_map, "OutRangeB", "Input"), "8.0", "sunOutB")

    # --- D4: bump moon intensity slightly ---
    if moon_i_map:
        set_val(find_pin(moon_i_map, "OutRangeA", "Input"), "0.0", "moonOutA")
        set_val(find_pin(moon_i_map, "OutRangeB", "Input"), "2.8", "moonOutB")

    # --- D5: re-append SkyLight SetIntensity on sky branch ---
    if sky_branch and get_sky and sky_i_map:
        thenp = find_pin(sky_branch, "then", "Output")
        elsep = find_pin(sky_branch, "else", "Output")
        # remember current return targets
        then_targets = [cp.get_owning_node() for cp in connected(thenp)]
        else_targets = [cp.get_owning_node() for cp in connected(elsep)]
        ret_node = None
        for t in then_targets + else_targets + rets:
            if t and t.get_class().get_name() == "K2Node_FunctionResult":
                ret_node = t
                break
        if not ret_node:
            ret_node = ge.add_return_node()
            bel.set_node_pos(ret_node, pos(5400, 0))

        break_links(thenp, "sky.then")
        # keep else -> return
        if not connected(elsep):
            connect(elsep, find_pin(ret_node, "execute", "Input"), "sky.else->ret")

        get_comp = call(ge, "/Script/Engine.Actor:GetComponentByClass", 4800, 200)
        connect(find_pin(get_sky, "SkyLightActor", "Output"), find_pin(get_comp, "self", "Input"), "sky->comp")
        set_val(find_pin(get_comp, "ComponentClass", "Input"),
                "/Script/Engine.SkyLightComponent", "SkyLightComp")

        set_i = call(ge, "/Script/Engine.LightComponent:SetIntensity", 5100, 0)
        # SkyLightComponent inherits LightComponent SetIntensity
        connect(thenp, find_pin(set_i, "execute", "Input"), "sky.then->SI")
        connect(ret(get_comp), find_pin(set_i, "self", "Input"), "comp->SI")
        connect(ret(sky_i_map), find_pin(set_i, "NewIntensity", "Input"), "skyI->SI")
        connect(find_pin(set_i, "then", "Output"), find_pin(ret_node, "execute", "Input"), "SI->ret")
        log("sky SetIntensity appended")
    else:
        log("SKIP sky SI — sky_branch={} get_sky={} sky_i_map={}".format(
            bool(sky_branch), bool(get_sky), bool(sky_i_map)))

    errs = list(ge.list_nodes_with_errors())
    log("errors={}".format(len(errs)))
    for e in errs:
        log("  ERR " + title(e))
        for p in bel.list_all_pins(e):
            try:
                v = p.get_pin_value()
            except Exception:
                v = "?"
            cps = ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in connected(p)]
            if cps or (v not in (None, "", "0.0", "0", "false", "true")):
                log("    {}={!r} links={}".format(p.get_pin_name(), v, cps))

    if errs:
        log("STOP: graph has errors — not compiling away; report")
        # still try compile to surface messages
        try:
            bel.compile_blueprint(bp)
        except Exception as e:
            log("compile " + str(e))
        return

    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile " + str(e))

    saved = unreal.EditorAssetLibrary.save_asset(MGR)
    log("save={}".format(saved))

    # Verify moon pitch link
    if moon_rot_make:
        pp = find_pin(moon_rot_make, "Pitch", "Input")
        log("moon Pitch links={}".format(
            ["{}.{}".format(title(c.get_owning_node()), c.get_pin_name()) for c in connected(pp)]))
    log("Step D DONE")


if __name__ == "__main__":
    main()
