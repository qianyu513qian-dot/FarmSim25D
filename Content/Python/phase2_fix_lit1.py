# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
bp = unreal.EditorAssetLibrary.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
# Force LitTilled = 1 (Tilled index)
ge.set_local_variable_default_value("LitTilled", "1")
unreal.log("LitTilled=" + str(ge.get_local_variable_default_value("LitTilled")))
ge.set_local_variable_default_value("LitEmpty", "0")
unreal.log("LitEmpty=" + str(ge.get_local_variable_default_value("LitEmpty")))
bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(MGR)