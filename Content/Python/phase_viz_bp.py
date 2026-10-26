# -*- coding: utf-8 -*-
"""Create BP_PlotVisual actor with Plane SMC. No GridManager graph edits. No open_editor."""
import unreal

DIR = "/Game/Farm/Grid"
PATH = DIR + "/BP_PlotVisual"
PLANE = "/Engine/BasicShapes/Plane"
MATS = {
    1: "/Game/Farm/Art/Mats/M_Tilled",
    2: "/Game/Farm/Art/Mats/M_Planted",
    3: "/Game/Farm/Art/Mats/M_Watered",
    4: "/Game/Farm/Art/Mats/M_Ready",
}

bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log("[VIZ_BP] " + str(m))


def ensure_dir():
    if not unreal.EditorAssetLibrary.does_directory_exist("/Game/Farm"):
        unreal.EditorAssetLibrary.make_directory("/Game/Farm")
    if not unreal.EditorAssetLibrary.does_directory_exist(DIR):
        unreal.EditorAssetLibrary.make_directory(DIR)


def create_bp():
    if unreal.EditorAssetLibrary.does_asset_exist(PATH):
        log("exists, load")
        return unreal.load_asset(PATH)
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.Actor)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BP_PlotVisual", DIR, unreal.Blueprint, factory
    )
    log("created " + str(bp))
    unreal.EditorAssetLibrary.save_asset(PATH)
    return unreal.load_asset(PATH)


def add_plane_component(bp):
    """Try SubobjectDataSubsystem / SCS to add StaticMeshComponent with Plane."""
    plane = unreal.load_asset(PLANE)
    # Probe APIs
    for name in ("SubobjectDataSubsystem", "SubobjectDataBlueprintFunctionLibrary", "EditorActorSubsystem"):
        log("has {} = {}".format(name, hasattr(unreal, name)))

    # Method A: SimpleConstructionScript
    try:
        scs = bp.simple_construction_script
        log("scs=" + str(scs))
        if scs:
            for m in dir(scs):
                if "add" in m.lower() or "create" in m.lower() or "node" in m.lower():
                    if not m.startswith("_"):
                        log("scs." + m)
            root = None
            try:
                root = scs.get_default_scene_root_node()
                log("root=" + str(root))
            except Exception as e:
                log("get root: " + str(e))
            try:
                nodes = scs.get_all_nodes()
                log("scs nodes=" + str(len(nodes)))
                for n in nodes:
                    log("  scsnode " + str(n) + " " + str(getattr(n, "component_class", None)))
            except Exception as e:
                log("get_all_nodes: " + str(e))
    except Exception as e:
        log("scs fail: " + str(e))

    # Method B: SubobjectDataSubsystem (UE5)
    try:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        log("subsys=" + str(sub))
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        log("handles count=" + str(len(handles)))
        for h in handles:
            try:
                log("  handle " + str(h))
            except Exception:
                pass
        # Try add
        params = unreal.AddNewSubobjectParams()
        params.set_editor_property("parent_handle", handles[0] if handles else unreal.SubobjectDataHandle())
        params.set_editor_property("new_class", unreal.StaticMeshComponent)
        # blueprint context
        try:
            params.set_editor_property("blueprint_context", bp)
        except Exception as e:
            log("bp context prop: " + str(e))
        result = sub.add_new_subobject(params)
        log("add_new_subobject result=" + str(result))
        # Refresh
        handles2 = sub.k2_gather_subobject_data_for_blueprint(bp)
        log("handles after=" + str(len(handles2)))
        for h in handles2:
            data = sub.k2_find_subobject_data_from_handle(h)
            try:
                obj = sub.get_object_for_handle(h) if hasattr(sub, "get_object_for_handle") else None
                log("  after obj=" + str(obj))
            except Exception as e:
                log("  get obj: " + str(e))
            try:
                # Try set mesh on template
                tmpl = None
                for meth in ("get_data", "get_object", "get_component_template"):
                    if hasattr(data, meth):
                        log("data." + meth)
                log("data=" + str(data) + " type=" + str(type(data)))
            except Exception as e:
                log("data inspect: " + str(e))
    except Exception as e:
        log("SubobjectDataSubsystem fail: " + str(e))
        import traceback
        log(traceback.format_exc())

    return bp


def add_mat_vars(bp):
    """Soft refs / object refs for materials as member vars for ApplyState."""
    for name, path in [
        ("MatTilled", MATS[1]),
        ("MatPlanted", MATS[2]),
        ("MatWatered", MATS[3]),
        ("MatReady", MATS[4]),
    ]:
        pin = unreal.EdGraphPinType()
        # object ref to MaterialInterface
        pin.import_text(
            '(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/Engine.MaterialInterface")'
        )
        try:
            ok = bel.add_member_variable(bp, name, pin)
            log("add var {} -> {}".format(name, ok))
        except Exception as e:
            log("add var {} fail: {}".format(name, e))

    # Try set defaults on CDO after compile
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log("compile: " + str(e))
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        for prop, path in [
            ("mat_tilled", MATS[1]),
            ("MatTilled", MATS[1]),
            ("mat_planted", MATS[2]),
            ("MatPlanted", MATS[2]),
            ("mat_watered", MATS[3]),
            ("MatWatered", MATS[3]),
            ("mat_ready", MATS[4]),
            ("MatReady", MATS[4]),
        ]:
            mat = unreal.load_asset(path)
            try:
                cdo.set_editor_property(prop, mat)
                log("CDO set {} ok".format(prop))
            except Exception:
                pass
    except Exception as e:
        log("CDO: " + str(e))


def main():
    log("=== START ===")
    ensure_dir()
    bp = create_bp()
    add_plane_component(bp)
    add_mat_vars(bp)
    try:
        bel.compile_blueprint(bp)
        log("compile ok")
    except Exception as e:
        log("compile: " + str(e))
    unreal.EditorAssetLibrary.save_asset(PATH)
    log("=== END ===")


if __name__ == "__main__":
    main()
