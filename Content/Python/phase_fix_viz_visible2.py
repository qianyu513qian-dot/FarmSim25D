# -*- coding: utf-8 -*-
"""Check root scale, material, and strengthen VisualizeCell post-spawn visibility."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"


def log(m):
    unreal.log("[FIX_VIZ2] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}]: {}".format(label, ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
        return True
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))
        return False


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


# --- Inspect BP_PlotVisual root / comps ---
bp = unreal.load_asset(PV)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sub.k2_gather_subobject_data_for_blueprint(bp):
    data = sub.k2_find_subobject_data_from_handle(h)
    try:
        vname = str(lib.get_variable_name(data) or "")
        obj = lib.get_object(data)
        if not obj:
            continue
        cls = obj.get_class().get_name()
        if "Scene" in cls or "StaticMesh" in cls:
            try:
                sc = obj.get_editor_property("relative_scale3d")
                loc = obj.get_editor_property("relative_location")
            except Exception:
                sc = loc = None
            abs_s = None
            try:
                abs_s = obj.get_editor_property("absolute_scale")
            except Exception:
                pass
            sm = None
            try:
                sm = obj.get_editor_property("static_mesh")
            except Exception:
                pass
            log("COMP {} class={} scale={} loc={} abs_scale={} mesh={}".format(
                vname, cls, sc, loc, abs_s, sm.get_name() if sm else None))
    except Exception as e:
        log("insp " + str(e))

# Material
mat = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Palette")
if not mat:
    # search
    assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/VoxelMicroFarm", recursive=True)
    mats = [a for a in assets if "Palette" in a or "M_VMF" in a]
    log("Palette load failed; candidates=" + str(mats[:20]))
else:
    log("M_VMF_Palette OK " + str(mat))

# Check DEBUG actor still in level
try:
    actors = unreal.EditorActorSubsystem().get_all_level_actors()
except Exception:
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    try:
        lab = a.get_actor_label()
    except Exception:
        lab = a.get_name()
    if "DEBUG_Plot" in str(lab) or "PlotVisual" in str(lab):
        try:
            origin, extent = a.get_actor_bounds(False)
            log("LEVEL {} loc={} scale={} bounds_ext={}".format(
                lab, a.get_actor_location(), a.get_actor_scale3d(), extent))
            for c in a.get_components_by_class(unreal.StaticMeshComponent):
                log("  {} mesh={} vis={}".format(
                    c.get_name(),
                    c.static_mesh.get_path_name() if c.static_mesh else None,
                    c.is_visible() if hasattr(c, "is_visible") else "?"))
        except Exception as e:
            log("actor read " + str(e))

# --- Strengthen VisualizeCell: after ApplyState on spawn path, also SetActorHiddenInGame(false) + SetActorScale3D ---
gbp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "VisualizeCell"))

# Find spawn-path ApplyState (the one after second Cast)
apply_nodes = []
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "ApplyState":
        apply_nodes.append(n)
log("ApplyState count=" + str(len(apply_nodes)))

# Find spawn ReturnValue pin for scale set target
spawn = None
for n in ge.list_all_nodes():
    if "SpawnActor" in bel.get_node_title(n):
        spawn = n
        break

# Change TransformScaleMethod to OverrideRootScale so spawn scale is absolute 0.01
if spawn:
    p = find_pin(spawn, "TransformScaleMethod", "Input")
    if p:
        # Try enum values
        for cand in ("OverrideRootScale", "Override", "GiveOverride", "MultiplyWithRoot"):
            try:
                p.set_pin_value(cand)
                log("TransformScaleMethod -> " + pin_val(p))
                if "Override" in pin_val(p):
                    break
            except Exception as e:
                log("try {}: {}".format(cand, e))

# Insert after spawn-path ApplyState: SetActorScale3D(0.01) + SetActorHiddenInGame(false)
# Identify spawn-path ApplyState: its self comes from cast whose Object comes from Spawn ReturnValue
spawn_apply = None
spawn_cast = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "Cast To BP_PlotVisual" in t:
        obj_pin = find_pin(n, "Object", "Input")
        if obj_pin:
            for cp in obj_pin.list_connected_pins():
                if "SpawnActor" in bel.get_node_title(cp.get_owning_node()):
                    spawn_cast = n
for n in apply_nodes:
    self_pin = find_pin(n, "self", "Input")
    if self_pin and spawn_cast:
        for cp in self_pin.list_connected_pins():
            if cp.get_owning_node() == spawn_cast:
                spawn_apply = n
log("spawn_cast={} spawn_apply={}".format(bool(spawn_cast), bool(spawn_apply)))

if spawn_apply and spawn:
    then_ap = find_pin(spawn_apply, "then", "Output")
    ret = None
    if then_ap:
        for cp in list(then_ap.list_connected_pins()):
            if bel.get_node_title(cp.get_owning_node()) == "Return Node":
                ret = cp.get_owning_node()
    # Also check if we already added SetActorScale3D
    has_scale_set = False
    for n in ge.list_all_nodes():
        if "SetActorScale3D" in bel.get_node_title(n).replace(" ", "") or "Set Actor Scale" in bel.get_node_title(n):
            has_scale_set = True
    if ret and then_ap and not has_scale_set:
        try:
            then_ap.break_pin_links(False)
        except Exception:
            try:
                then_ap.break_pin_links()
            except Exception as e:
                log("break apply.then " + str(e))

        # SetActorHiddenInGame false
        hid = ge.add_call_function_node("/Script/Engine.Actor:SetActorHiddenInGame")
        bel.set_node_pos(hid, pos(4100, 420))
        connect(then_ap, find_pin(hid, "execute", "Input"), "ap->hid")
        connect(find_pin(spawn, "ReturnValue", "Output"), find_pin(hid, "self", "Input"), "spawn->hid.self")
        set_val(find_pin(hid, "bNewHidden", "Input") or find_pin(hid, "NewHidden", "Input"), "false", "hid")

        # SetActorScale3D 0.01
        ssc = ge.add_call_function_node("/Script/Engine.Actor:SetActorScale3D")
        bel.set_node_pos(ssc, pos(4400, 420))
        connect(find_pin(hid, "then", "Output"), find_pin(ssc, "execute", "Input"), "hid->scale")
        connect(find_pin(spawn, "ReturnValue", "Output"), find_pin(ssc, "self", "Input"), "spawn->scale.self")
        # NewScaleXYZ or Scale pin
        sp = (find_pin(ssc, "NewScale3D", "Input") or find_pin(ssc, "Scale", "Input")
              or find_pin(ssc, "NewScale", "Input") or find_pin(ssc, "New Scale 3D", "Input"))
        if sp:
            # Need a MakeVector 0.01
            mv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
            bel.set_node_pos(mv, pos(4200, 560))
            set_val(find_pin(mv, "X", "Input"), "0.01", "fixsc.X")
            set_val(find_pin(mv, "Y", "Input"), "0.01", "fixsc.Y")
            set_val(find_pin(mv, "Z", "Input"), "0.01", "fixsc.Z")
            connect(find_pin(mv, "ReturnValue", "Output"), sp, "mv->NewScale")
        else:
            log("NO scale pin on SetActorScale3D; pins=" + str([str(p.get_pin_name()) for p in bel.list_all_pins(ssc)]))

        connect(find_pin(ssc, "then", "Output"), find_pin(ret, "execute", "Input"), "scale->ret")
        log("inserted Hidden+Scale after spawn ApplyState")

# Also bump existing-path: after update ApplyState, SetActorHiddenInGame false
# (in case actor was hidden)

try:
    bel.compile_blueprint(gbp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)
unreal.EditorAssetLibrary.save_asset(PV)

# Rebuild ApplyState to also SetVisibility(true) on shown meshes
# Safer: patch each SetHiddenInGame(false) path - already there.
# Instead ensure Empty clears mesh via SetStaticMesh null properly.

# Verify grass vs soil size
grass = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Ground_Grass")
soil = unreal.load_asset("/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry")
for name, a in (("grass", grass), ("soil", soil)):
    if a:
        b = a.get_bounds()
        log("{} extent={} origin={}".format(name, b.box_extent, b.origin))

log("=== DONE ===")
