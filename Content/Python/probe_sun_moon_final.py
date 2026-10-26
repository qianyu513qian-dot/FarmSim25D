# -*- coding: utf-8 -*-
"""Final verify dual sun/moon day-night."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[VERIFY_SM] " + str(m))
    print("[VERIFY_SM] " + str(m))


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


bp = unreal.load_asset(MGR)
names = [str(n).split(".")[-1] for n in bel.list_member_variable_names(bp)]
log("MoonActor=" + str("MoonActor" in names))

try:
    actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
except Exception:
    actors = list(unreal.EditorLevelLibrary.get_all_level_actors())

for a in actors:
    cn = a.get_class().get_name()
    if cn not in ("DirectionalLight", "SkyLight", "SkyAtmosphere"):
        continue
    label = a.get_actor_label()
    try:
        tags = [str(t) for t in a.get_editor_property("tags")]
    except Exception:
        tags = []
    log("ACTOR {} label={} tags={}".format(cn, label, tags))
    if cn == "DirectionalLight":
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            log("  idx={} atm={} inten={} mob={}".format(
                c.get_editor_property("atmosphere_sun_light_index"),
                c.get_editor_property("atmosphere_sun_light"),
                c.get_editor_property("intensity"),
                c.get_editor_property("mobility")))
    if cn == "SkyLight":
        for c in a.get_components_by_class(unreal.SkyLightComponent):
            log("  rtc={} inten={}".format(
                c.get_editor_property("real_time_capture"),
                c.get_editor_property("intensity")))

ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
si = sr = 0
vals = []
for n in ge.list_all_nodes():
    t = title(n)
    if "SetIntensity" in t or "Set Intensity" in t:
        si += 1
    if "Set Actor Rotation" in t:
        sr += 1
    if "MapRangeClamped" in t or "Map Range" in t:
        row = {}
        for p in bel.list_all_pins(n):
            try:
                row[str(p.get_pin_name())] = p.get_pin_value()
            except Exception:
                pass
        vals.append(row)
    for p in bel.list_all_pins(n):
        try:
            v = str(p.get_pin_value())
        except Exception:
            v = ""
        if v in ("360.0", "180.0", "2.5", "8.0", "-0.15", "0.15", "-0.4", "25.0", "-70.0"):
            vals.append("{}:{}={}".format(t, p.get_pin_name(), v))
log("Apply SetIntensity={} SetRotation={} errors={}".format(
    si, sr, len(ge.list_nodes_with_errors())))
log("key vals sample=" + str(vals[:20]))

ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for n in ge2.list_all_nodes():
    t = title(n)
    if t in ("Set MoonActor", "Set SunActor", "Set SkyLightActor") or "GetAllActorsWithTag" in t.replace(" ", "") or "Get All Actors with Tag" in t:
        pins = []
        for p in bel.list_all_pins(n):
            try:
                v = p.get_pin_value()
            except Exception:
                v = ""
            if str(v):
                pins.append("{}={!r}".format(p.get_pin_name(), v))
        log("EG {} {}".format(t, pins))

# Ensure AdvanceDayGrowth / GrowCell untouched (just count nodes)
for gname in ("AdvanceDayGrowth", "GrowCell"):
    g = bel.find_graph(bp, gname)
    if g:
        ge3 = unreal.BlueprintGraphEditor.get_graph_editor(g)
        log("{} nodes={} errors={}".format(gname, len(list(ge3.list_all_nodes())), len(ge3.list_nodes_with_errors())))

log("DONE OK")
