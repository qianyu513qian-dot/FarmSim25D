# -*- coding: utf-8 -*-
"""Surgical fix: disconnect broken SkyLight SetIntensity; pass-through return."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_SKY] " + str(m))
    print("[FIX_SKY] " + str(m))


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


def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))

# Dump errors
errs = list(ge.list_nodes_with_errors())
log("errors before={}".format(len(errs)))
for e in errs:
    log("  ERR node={} class={}".format(title(e), e.get_class().get_name()))
    for p in bel.list_all_pins(e):
        try:
            v = p.get_pin_value()
        except Exception:
            v = "?"
        log("    pin {}={} dir={}".format(p.get_pin_name(), v, p.get_pin_direction()))

# Find sky branch: Branch whose Condition comes from SkyLightActor IsValid,
# or whose then goes to SetIntensity with SkyLightComponent
br_sk = None
set_sk_i = None
rets = []
for n in ge.list_all_nodes():
    t = title(n)
    cls = n.get_class().get_name()
    if cls == "K2Node_FunctionResult":
        rets.append(n)
    if cls == "K2Node_IfThenElse" or "Branch" in t:
        # check if then links to SetIntensity that has error or sky
        thenp = find_pin(n, "then", "Output")
        links = list(thenp.list_connected_pins() or []) if thenp else []
        if links:
            nxt = links[0].get_owning_node()
            nt = title(nxt)
            if "SetIntensity" in nt or "Set Intensity" in nt:
                # check self type / error
                self_pin = find_pin(nxt, "self", "Input")
                linked = list(self_pin.list_connected_pins() or []) if self_pin else []
                # Prefer the last SetIntensity (sky is after moon)
                # Identify by GetComponentByClass with SkyLightComponent nearby
                br_sk = n
                set_sk_i = nxt

# Better: find GetComponentByClass with SkyLightComponent class pin
sky_comp_get = None
for n in ge.list_all_nodes():
    if "GetComponentByClass" in title(n).replace(" ", "") or title(n) == "Get Component by Class":
        cp = find_pin(n, "ComponentClass", "Input")
        try:
            v = cp.get_pin_value() if cp else ""
        except Exception:
            v = ""
        if "SkyLight" in str(v):
            sky_comp_get = n
            log("found sky GetComponentByClass")

# Find SetIntensity whose self is unconnected or errored — likely sky
for n in ge.list_all_nodes():
    if "SetIntensity" not in title(n) and "Set Intensity" not in title(n):
        continue
    self_pin = find_pin(n, "self", "Input")
    links = list(self_pin.list_connected_pins() or []) if self_pin else []
    if not links:
        set_sk_i = n
        log("found SetIntensity with no self: " + title(n))
        # find branch feeding it
        exec_in = find_pin(n, "execute", "Input")
        for cp in list(exec_in.list_connected_pins() or []):
            br_sk = cp.get_owning_node()
            log("  fed by " + title(br_sk))

if br_sk and set_sk_i:
    thenp = find_pin(br_sk, "then", "Output")
    try:
        thenp.break_pin_links(False)
    except Exception:
        try:
            thenp.break_pin_links()
        except Exception as e:
            log("break " + str(e))

    # Prefer existing return that set_sk_i then went to
    then_out = find_pin(set_sk_i, "then", "Output")
    target = None
    if then_out:
        for cp in list(then_out.list_connected_pins() or []):
            target = cp.get_owning_node()
    if not target:
        target = rets[0] if rets else ge.add_return_node()
        if target not in rets:
            bel.set_node_pos(target, pos(5400, 0))

    connect(thenp, find_pin(target, "execute", "Input"), "sky then->ret")

    # Remove broken SetIntensity and unused sky GetComponent if desired
    kill = [set_sk_i]
    # Also remove sky intensity MapRange if only used by set_sk_i — optional leave
    if sky_comp_get:
        # only remove if unused after
        kill.append(sky_comp_get)
    try:
        ge.remove_nodes(kill)
        log("removed broken sky nodes={}".format(len(kill)))
    except Exception as e:
        log("rm " + str(e))
else:
    log("could not locate sky SetIntensity branch; dumping SetIntensity nodes")
    for n in ge.list_all_nodes():
        if "SetIntensity" in title(n) or "Set Intensity" in title(n):
            log("  SI " + title(n))
            for p in bel.list_all_pins(n):
                try:
                    v = p.get_pin_value()
                except Exception:
                    v = "?"
                cps = []
                for c in list(p.list_connected_pins() or []):
                    cps.append(title(c.get_owning_node()) + "." + str(c.get_pin_name()))
                log("    {}={!r} -> {}".format(p.get_pin_name(), v, cps))

errs2 = list(ge.list_nodes_with_errors())
log("errors after={}".format(len(errs2)))
for e in errs2:
    log("  ERR " + title(e))

# Count remaining SetIntensity / SetRotation
si = sum(1 for n in ge.list_all_nodes() if "SetIntensity" in title(n) or "Set Intensity" in title(n))
sr = sum(1 for n in ge.list_all_nodes() if "Set Actor Rotation" in title(n) or "SetActorRotation" in title(n).replace(" ", ""))
log("SetIntensity={} SetRotation={}".format(si, sr))

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
log("DONE")
