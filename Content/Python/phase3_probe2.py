# -*- coding: utf-8 -*-
"""Deeper probe: enum names, LitTilled, StateTilled CDO, Set Item wiring."""
import unreal

bel = unreal.BlueprintEditorLibrary
ENUM = "/Game/Farm/Grid/E_PlotState"
MGR = "/Game/Farm/Grid/BP_GridManager"


def main():
    unreal.log("=== phase3_probe2 start ===")
    en = unreal.EditorAssetLibrary.load_asset(ENUM)

    # UserDefinedEnum internals via export / properties
    for prop in ("Names", "DisplayNameMap", "EnumDisplayNameMap", "Enums"):
        try:
            v = en.get_editor_property(prop)
            unreal.log("prop {} = {}".format(prop, v))
        except Exception as ex:
            unreal.log_warning("prop {}: {}".format(prop, ex))

    # Try blueprint editor library enum helpers
    for meth in dir(bel):
        if "enum" in meth.lower():
            unreal.log("bel." + meth)

    # unreal.EnumEditorLibrary or similar
    for name in dir(unreal):
        if "enum" in name.lower() and ("Editor" in name or "UserDefined" in name or "Library" in name):
            unreal.log("unreal." + name)

    # Text dump of asset
    try:
        txt = unreal.EditorAssetLibrary.export_text(en) if hasattr(unreal.EditorAssetLibrary, "export_text") else None
        unreal.log("export_text=" + str(txt)[:2000] if txt else "no export_text")
    except Exception as ex:
        unreal.log_warning("export: " + str(ex))

    # Try get_display_name / get_name_string_by_index via Enum base
    try:
        # In UE5 python, UserDefinedEnum may support:
        # - get_enumerator_name_as_string? 
        for i in range(6):
            try:
                dn = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)  # noop
            except Exception:
                pass
            for meth_name in ("get_display_name_text_by_index", "get_name_string_by_index",
                              "get_name_by_index", "get_enumerator_user_friendly_name",
                              "get_enum_name_by_value", "get_name_by_value"):
                if hasattr(en, meth_name):
                    try:
                        unreal.log("{}({})={}".format(meth_name, i, getattr(en, meth_name)(i)))
                    except Exception as ex:
                        unreal.log_warning("{}({}): {}".format(meth_name, i, ex))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # List all non-dunder methods on enum
    methods = [m for m in dir(en) if not m.startswith("_") and ("get" in m.lower() or "enum" in m.lower() or "name" in m.lower())]
    unreal.log("enum methods: " + str(methods))

    # Try Enum as UEnum via cast to unreal.Enum
    try:
        # load as Enum
        e2 = unreal.load_object(None, "/Script/CoreUObject.Enum'/Game/Farm/Grid/E_PlotState.E_PlotState'")
        unreal.log("e2=" + str(e2))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # CDO StateTilled / StateEmpty
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    gen = unreal.load_object(None, "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C")
    cdo = unreal.get_default_object(gen)
    for prop in ("StateTilled", "StateEmpty", "StatePlanted"):
        try:
            unreal.log("CDO.{}={}".format(prop, cdo.get_editor_property(prop)))
        except Exception as ex:
            unreal.log_warning("CDO.{}: {}".format(prop, ex))

    # TillCell locals
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    try:
        unreal.log("locals=" + str([str(x) for x in ge.list_local_variable_names()]))
        for name in ge.list_local_variable_names():
            sn = str(name)
            try:
                unreal.log("{} type={} def={}".format(
                    sn, ge.get_local_variable_type(sn), ge.get_local_variable_default_value(sn)))
            except Exception as ex:
                unreal.log_warning(sn + ": " + str(ex))
    except Exception as ex:
        unreal.log_warning("locals: " + str(ex))

    # Trace Set Array Item connections
    for n in ge.list_all_nodes():
        if "Set Array" in bel.get_node_title(n):
            for p in bel.list_all_pins(n):
                if str(p.get_pin_name()) == "Item":
                    for cp in list(p.list_connected_pins()):
                        on = cp.get_owning_node()
                        unreal.log("Set.Item <- {}.{} title={}".format(
                            bel.get_node_title(on), cp.get_pin_name(), bel.get_node_title(on)))

    # How to add enum entry?
    for name in dir(unreal):
        if "UserDefinedEnum" in name:
            unreal.log("found " + name)
            cls = getattr(unreal, name)
            for m in dir(cls):
                if "add" in m.lower() or "insert" in m.lower() or "enum" in m.lower():
                    if not m.startswith("_"):
                        unreal.log("  " + name + "." + m)

    unreal.log("=== phase3_probe2 done ===")


if __name__ == "__main__":
    main()
