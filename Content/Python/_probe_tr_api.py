# -*- coding: utf-8 -*-
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
la = None
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "") == "RestLabel_OpenSign":
        la = a
        break
tr = la.get_component_by_class(unreal.TextRenderComponent)
names = [n for n in dir(tr) if not n.startswith("_") and ("rot" in n.lower() or "forward" in n.lower() or "world" in n.lower() or "relative" in n.lower() or "visib" in n.lower() or "hidden" in n.lower() or "text" in n.lower() or "font" in n.lower() or "size" in n.lower())]
print(json.dumps({"tr_class": tr.get_class().get_name(), "methods": names, "actor_rot": [la.get_actor_rotation().pitch, la.get_actor_rotation().yaw, la.get_actor_rotation().roll]}, indent=2))
