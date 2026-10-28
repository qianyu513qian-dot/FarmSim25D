# -*- coding: utf-8 -*-
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
R = {"marks": [], "mats": [], "furniture": []}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("RestMark_"):
        a.set_actor_scale3d(unreal.Vector(0.55, 0.55, 0.55))
        loc = a.get_actor_location()
        smc = a.static_mesh_component
        mat = smc.get_material(0)
        info = {"lab": lab, "loc": [round(loc.x,1),round(loc.y,1),round(loc.z,1)], "scale": 0.55,
                "visible": smc.is_visible(), "mat": mat.get_path_name() if mat else None}
        if mat:
            try:
                info["blend"] = str(mat.get_editor_property("blend_mode"))
                info["shading"] = str(mat.get_editor_property("shading_model"))
            except Exception: pass
            try:
                exprs = unreal.MaterialEditingLibrary.get_expressions(mat) if hasattr(unreal.MaterialEditingLibrary,"get_expressions") else None
                info["expr_count"] = len(exprs) if exprs is not None else "?"
            except Exception as e:
                info["expr_err"] = str(e)[:60]
        R["marks"].append(info)
    if lab.startswith("Restaurant_") and lab != "Restaurant_Manager":
        loc=a.get_actor_location()
        R["furniture"].append({"lab":lab,"loc":[round(loc.x,1),round(loc.y,1),round(loc.z,1)]})
    if lab == "RestDebugLabels":
        R["debug_actor"] = a.get_class().get_name()
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"]=True
except Exception:
    R["level_saved"]=False
# invalidate
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception: pass
open(r"E:\UE\FarmSim25D\Saved\restaurant_labels_final.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps(R,ensure_ascii=False,indent=2))