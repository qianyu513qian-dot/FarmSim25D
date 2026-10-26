# -*- coding: utf-8 -*-
"""Configure BP_PlotVisual StaticMeshComponent: Plane, no collision, attach root."""
import unreal

PATH = "/Game/Farm/Grid/BP_PlotVisual"
PLANE = "/Engine/BasicShapes/Plane"
MAT_TILLED = "/Game/Farm/Art/Mats/M_Tilled"

bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log("[VIZ_SMC] " + str(m))


def dump_sub(sub, bp):
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    log("handles=" + str(len(handles)))
    for i, h in enumerate(handles):
        data = None
        try:
            data = sub.k2_find_subobject_data_from_handle(h)
        except Exception as e:
            log("find data {}: {}".format(i, e))
        # Probe SubobjectDataBlueprintFunctionLibrary
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        obj = None
        for meth_name in (
            "get_object",
            "get_object_for_handle",
            "get_component_template",
            "get_data",
            "get_blueprint",
            "get_variable_name",
            "get_display_name",
            "is_component",
            "is_root_component",
            "is_instanced_component",
            "get_class",
        ):
            if hasattr(lib, meth_name):
                try:
                    fn = getattr(lib, meth_name)
                    # try with handle or data
                    for arg in (h, data):
                        try:
                            r = fn(arg)
                            log("  [{}] lib.{}({})={}".format(i, meth_name, type(arg).__name__, r))
                            if meth_name in ("get_object", "get_object_for_handle", "get_component_template") and r:
                                obj = r
                            break
                        except Exception:
                            pass
                except Exception as e:
                    log("  lib.{} err {}".format(meth_name, e))
        if obj:
            log("  [{}] OBJ class={} name={}".format(i, obj.get_class().get_name(), obj.get_name()))
            try:
                for p in ("static_mesh", "StaticMesh", "mobility", "Mobility"):
                    try:
                        log("    prop {}={}".format(p, obj.get_editor_property(p)))
                    except Exception:
                        pass
            except Exception:
                pass
    return handles


def main():
    log("=== START ===")
    bp = unreal.load_asset(PATH)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary

    # List lib methods
    for m in dir(lib):
        if not m.startswith("_"):
            if any(k in m.lower() for k in ("get", "set", "object", "component", "mesh", "name", "root", "attach")):
                log("lib." + m)

    for m in dir(sub):
        if not m.startswith("_"):
            if any(k in m.lower() for k in ("add", "attach", "rename", "mesh", "delete", "root", "handle", "object")):
                log("sub." + m)

    handles = dump_sub(sub, bp)

    plane = unreal.load_asset(PLANE)
    mat = unreal.load_asset(MAT_TILLED)

    # Find StaticMeshComponent template and set mesh
    for h in handles:
        try:
            obj = None
            if hasattr(lib, "get_object"):
                try:
                    obj = lib.get_object(h)
                except Exception:
                    data = sub.k2_find_subobject_data_from_handle(h)
                    obj = lib.get_object(data)
            if obj is None and hasattr(sub, "k2_find_subobject_data_from_handle"):
                data = sub.k2_find_subobject_data_from_handle(h)
                for attr in ("object", "component_template", "weak_object"):
                    if hasattr(data, attr):
                        log("data.{}={}".format(attr, getattr(data, attr)))
            if obj and "StaticMesh" in obj.get_class().get_name():
                log("FOUND SMC " + obj.get_name())
                try:
                    obj.set_editor_property("static_mesh", plane)
                    log("set static_mesh ok")
                except Exception as e:
                    log("set mesh: " + str(e))
                try:
                    obj.set_material(0, mat)
                    log("set_material ok")
                except Exception as e:
                    try:
                        obj.set_editor_property("override_materials", [mat])
                        log("override_materials ok")
                    except Exception as e2:
                        log("mat fail: {} / {}".format(e, e2))
                try:
                    obj.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
                    log("no collision")
                except Exception as e:
                    log("collision: " + str(e))
                try:
                    obj.set_editor_property("cast_shadow", False)
                except Exception:
                    pass
                try:
                    # Make it the scene root if possible
                    if hasattr(sub, "attach_subobject"):
                        log("has attach_subobject")
                    if hasattr(sub, "make_new_scene_root"):
                        log("has make_new_scene_root")
                except Exception:
                    pass
        except Exception as e:
            log("loop err: " + str(e))

    # Rename variable to Mesh if API exists
    try:
        for h in handles:
            data = sub.k2_find_subobject_data_from_handle(h)
            obj = None
            try:
                obj = lib.get_object(h)
            except Exception:
                try:
                    obj = lib.get_object(data)
                except Exception:
                    pass
            if obj and "StaticMesh" in obj.get_class().get_name():
                if hasattr(sub, "rename_subobject"):
                    try:
                        ok = sub.rename_subobject(h, unreal.Text("PlotMesh"))
                        log("rename -> " + str(ok))
                    except Exception as e:
                        log("rename: " + str(e))
                if hasattr(sub, "attach"):
                    log("sub.attach exists")
    except Exception as e:
        log("rename block: " + str(e))

    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)

    # Re-dump
    dump_sub(sub, bp)
    log("=== END ===")


if __name__ == "__main__":
    main()
