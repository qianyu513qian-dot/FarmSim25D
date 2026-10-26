# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
ENUM = "/Game/Farm/Grid/E_PlotState"
bp = unreal.load_asset(MGR)
unreal.log("funcs=" + str([str(f.name) for f in bel.list_functions(bp)]))
unreal.log("graphs=" + str([str(n) for n in bel.list_graph_names(bp)]))
e = unreal.load_asset(ENUM)
if e:
    try:
        names = e.get_editor_property("names")
        unreal.log("enum names prop=" + str(names))
    except Exception as ex:
        unreal.log_warning(str(ex))
    try:
        # UE enum
        for i in range(0, 16):
            try:
                n = unreal.DataTableFunctionLibrary.get_data_table_column_as_string  # noop
            except Exception:
                pass
        # display names via export
        unreal.log("enum=" + str(e) + " " + e.get_name())
        unreal.log("export=" + e.get_path_name())
    except Exception as ex:
        unreal.log_warning(str(ex))
# UserDefinedEnum
try:
    ude = unreal.UserDefinedEnum.cast(e) if e else None
    unreal.log("ude=" + str(ude))
    if ude:
        unreal.log("num=" + str(ude.get_editor_property("num_enums") if hasattr(ude, "get_editor_property") else "?"))
except Exception as ex:
    unreal.log_warning("ude: " + str(ex))
# list entries
try:
    entries = e.get_editor_property("Names")
    unreal.log("Names=" + str(entries))
except Exception as ex:
    unreal.log_warning("Names: " + str(ex))
