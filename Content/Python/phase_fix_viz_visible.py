# -*- coding: utf-8 -*-
"""Fix PlotVisual visibility: raise Z, verify scale, ensure meshes/materials, add debug print."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"
PV_CLASS = "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C"

MESH = {
    "dry": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Dry",
    "wet": "/Game/Farm/VoxelMicroFarm/Models/Terrain/SM_VMF_Soil_Wet",
    "seed": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Seedling",
    "grow": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Growing",
    "mature": "/Game/Farm/VoxelMicroFarm/Models/Crops/SM_VMF_Crop_Tomato_Mature",
}


def log(m):
    unreal.log("[FIX_VIZ] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name() if a else None, b.get_pin_name() if b else None, ok))
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
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r} -> {!r}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


def fix_plotvisual_comps():
    bp = unreal.load_asset(PV)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    dry = unreal.load_asset(MESH["dry"])
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            vname = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            if not obj or "StaticMesh" not in obj.get_class().get_name():
                continue
            if vname == "PlotMesh":
                obj.set_editor_property("static_mesh", dry)
                obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 0.0))
                obj.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
                try:
                    obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
                try:
                    obj.set_editor_property("cast_shadow", False)
                except Exception:
                    pass
                try:
                    obj.set_editor_property("b_visible", True)
                except Exception:
                    pass
                log("PlotMesh configured dry=" + str(bool(dry)))
            elif vname == "CropMesh":
                obj.set_editor_property("static_mesh", None)
                obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 8.0))
                obj.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
                try:
                    obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
                try:
                    obj.set_editor_property("cast_shadow", False)
                except Exception:
                    pass
                log("CropMesh cleared default")
        except Exception as e:
            log("comp err " + str(e))
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile pv: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PV)
    return True


def fix_visualize_cell_transform():
    """Raise Z offset, force scale 0.01, ensure Scale pin wired, add PrintString on spawn."""
    bp = unreal.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))

    # Find MakeVectors: one with Z~3 (offset), one with 0.01 (scale)
    offset_mv = None
    scale_mv = None
    make_tf = None
    spawn = None
    g2w = None
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "Make Vector" or t == "MakeVector":
            zx = find_pin(n, "Z", "Input")
            xx = find_pin(n, "X", "Input")
            zv = pin_val(zx) if zx else ""
            xv = pin_val(xx) if xx else ""
            log("MakeVector X={} Z={}".format(xv, zv))
            if "0.01" in xv:
                scale_mv = n
            elif "3" in zv or zv in ("3.0", "3", "5.0", "5", "20.0", "25.0"):
                offset_mv = n
            elif zv in ("0.0", "0") and xv in ("0.0", "0"):
                # could be offset with Z to change
                if offset_mv is None:
                    offset_mv = n
        if "Make Transform" in t or t == "MakeTransform":
            make_tf = n
        if "SpawnActor" in t or "Spawn Actor" in t:
            spawn = n
        if t == "GridToWorld":
            g2w = n

    if offset_mv is None or scale_mv is None:
        # classify by connections
        for n in ge.list_all_nodes():
            t = bel.get_node_title(n)
            if "Make Vector" not in t and t != "MakeVector":
                continue
            rp = find_pin(n, "ReturnValue", "Output")
            if not rp:
                continue
            for cp in rp.list_connected_pins():
                own_t = bel.get_node_title(cp.get_owning_node())
                pn = str(cp.get_pin_name())
                if "Scale" in pn:
                    scale_mv = n
                if "vector + vector" in own_t.lower() or "Add_Vector" in own_t or "+" in own_t:
                    offset_mv = n

    log("offset_mv={} scale_mv={} make_tf={} spawn={}".format(
        bool(offset_mv), bool(scale_mv), bool(make_tf), bool(spawn)))

    # Raise Z to 25 so soil sits clearly above grass (grass Z=0.5, soil half-h~16 at 0.01)
    if offset_mv:
        set_val(find_pin(offset_mv, "X", "Input"), "0.0", "off.X")
        set_val(find_pin(offset_mv, "Y", "Input"), "0.0", "off.Y")
        set_val(find_pin(offset_mv, "Z", "Input"), "25.0", "off.Z")

    if scale_mv:
        set_val(find_pin(scale_mv, "X", "Input"), "0.01", "sc.X")
        set_val(find_pin(scale_mv, "Y", "Input"), "0.01", "sc.Y")
        set_val(find_pin(scale_mv, "Z", "Input"), "0.01", "sc.Z")

    # Ensure MakeTransform.Scale <- scale_mv
    if make_tf and scale_mv:
        sc_pin = find_pin(make_tf, "Scale", "Input")
        if sc_pin:
            try:
                sc_pin.break_pin_links(False)
            except Exception:
                try:
                    sc_pin.break_pin_links()
                except Exception as e:
                    log("break scale: " + str(e))
            connect(find_pin(scale_mv, "ReturnValue", "Output"), sc_pin, "sc->tf.Scale")
            log("MakeTransform.Scale now " + pin_val(sc_pin) + " conns=" + str(len(list(sc_pin.list_connected_pins()))))

    # Ensure Location still connected
    if make_tf:
        loc_pin = find_pin(make_tf, "Location", "Input")
        log("MakeTransform.Location conns=" + str(
            [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in (loc_pin.list_connected_pins() if loc_pin else [])]))

    # Add PrintString after spawn.then (before Array_Set) if not present
    has_print = False
    for n in ge.list_all_nodes():
        if "Print String" in bel.get_node_title(n) or "PrintString" in bel.get_node_title(n).replace(" ", ""):
            has_print = True
            break

    if spawn and not has_print:
        # Find Array_Set that follows spawn
        then_spawn = find_pin(spawn, "then", "Output")
        set_at = None
        if then_spawn:
            for cp in list(then_spawn.list_connected_pins()):
                if "Set Array" in bel.get_node_title(cp.get_owning_node()) or "Array_Set" in bel.get_node_title(cp.get_owning_node()):
                    set_at = cp.get_owning_node()
        if set_at and then_spawn:
            try:
                then_spawn.break_pin_links(False)
            except Exception:
                try:
                    then_spawn.break_pin_links()
                except Exception as e:
                    log("break spawn.then: " + str(e))

            pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
            bel.set_node_pos(pr, pos(3000, 300))
            set_val(find_pin(pr, "InString", "Input") or find_pin(pr, "In String", "Input"),
                    "VISUALIZE SPAWNED", "print")
            set_val(find_pin(pr, "Duration", "Input"), "3.0", "print.dur")
            # yellow
            try:
                set_val(find_pin(pr, "TextColor", "Input") or find_pin(pr, "Text Colour", "Input"),
                        "(R=1,G=1,B=0,A=1)", "print.col")
            except Exception:
                pass
            connect(then_spawn, find_pin(pr, "execute", "Input"), "spawn->print")
            connect(find_pin(pr, "then", "Output"), find_pin(set_at, "execute", "Input"), "print->set")
            log("added spawn PrintString")

    # Also print on ApplyState update path (existing valid)
    # Find first ApplyState's then -> Return; insert print
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "ApplyState":
            continue
        thenp = find_pin(n, "then", "Output")
        if not thenp:
            continue
        cps = list(thenp.list_connected_pins())
        if len(cps) == 1 and bel.get_node_title(cps[0].get_owning_node()) == "Return Node":
            # only add one update print
            already = False
            for n2 in ge.list_all_nodes():
                if "VISUALIZE UPDATE" in pin_val(find_pin(n2, "InString", "Input") or find_pin(n2, "In String", "Input") or type("x", (), {"get_pin_value": lambda s: ""})()):
                    already = True
            # simpler: check titles for second print with update text
            break  # skip for now to keep graph small

    try:
        bel.compile_blueprint(bp)
        log("VisualizeCell compile ok")
    except Exception as e:
        log("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(MGR)
    return True


def live_spawn_marker():
    """Editor-spawn a visible dry soil at (1850,1850,25) scale 0.01 for immediate visual check."""
    pv_cls = unreal.load_object(None, PV_CLASS)
    dry = unreal.load_asset(MESH["dry"])
    seed = unreal.load_asset(MESH["seed"])
    if not pv_cls:
        log("no pv class")
        return
    loc = unreal.Vector(1850.0, 1850.0, 25.0)
    try:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(pv_cls, loc, unreal.Rotator(0, 0, 0))
    except Exception as e:
        log("spawn fail " + str(e))
        return
    if not actor:
        log("spawn returned None")
        return
    actor.set_actor_scale3d(unreal.Vector(0.01, 0.01, 0.01))
    actor.set_actor_location(loc, False, True)
    actor.set_actor_label("DEBUG_PlotVisual_Test")
    comps = actor.get_components_by_class(unreal.StaticMeshComponent)
    log("spawned DEBUG actor comps=" + str(len(comps)))
    for c in comps:
        cn = c.get_name()
        if "PlotMesh" in cn:
            c.set_static_mesh(dry)
            c.set_hidden_in_game(False, False)
            c.set_visibility(True, False)
            log("PlotMesh set")
        elif "CropMesh" in cn:
            c.set_static_mesh(seed)
            c.set_hidden_in_game(False, False)
            c.set_visibility(True, False)
            log("CropMesh set")
    if comps and not any("PlotMesh" in c.get_name() for c in comps):
        comps[0].set_static_mesh(dry)
        comps[0].set_visibility(True, False)
        if len(comps) > 1:
            comps[1].set_static_mesh(seed)
            comps[1].set_visibility(True, False)
    try:
        origin, extent = actor.get_actor_bounds(False)
        log("DEBUG bounds origin={} extent={} loc={} scale={}".format(
            origin, extent, actor.get_actor_location(), actor.get_actor_scale3d()))
    except Exception as e:
        log("bounds " + str(e))


def check_materials():
    for key, path in MESH.items():
        a = unreal.load_asset(path)
        if not a:
            log("MISSING " + path)
            continue
        try:
            mats = a.get_editor_property("static_materials") if hasattr(a, "get_editor_property") else None
            # StaticMesh has get_materials or slots
            n = a.get_num_sections(0) if hasattr(a, "get_num_sections") else "?"
            log("mesh {} sections0={} path_ok".format(key, n))
        except Exception as e:
            log("mat check {}: {}".format(key, e))
        # try materials via EditorAssetLibrary
        try:
            mats = []
            for i in range(8):
                try:
                    m = a.get_material(i)
                    if m:
                        mats.append(m.get_name())
                except Exception:
                    break
            log("mesh {} mats={}".format(key, mats))
        except Exception as e:
            log("get_material {}: {}".format(key, e))


def main():
    log("=== START ===")
    check_materials()
    fix_plotvisual_comps()
    fix_visualize_cell_transform()
    live_spawn_marker()
    # Force save related
    unreal.EditorAssetLibrary.save_asset(PV)
    unreal.EditorAssetLibrary.save_asset(MGR)
    try:
        unreal.EditorAssetLibrary.save_directory("/Game/Farm/Grid")
    except Exception:
        pass
    log("=== END ===")


if __name__ == "__main__":
    main()
