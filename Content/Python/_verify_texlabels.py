# -*- coding: utf-8 -*-
import unreal, json
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
labs=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("RestLabel_") or lab.startswith("RestName_") or lab.startswith("Restaurant_"):
        loc=a.get_actor_location()
        mats=[]
        try:
            smc=getattr(a,"static_mesh_component",None)
            if smc:
                m=smc.get_material(0)
                mats.append(m.get_path_name() if m else None)
        except Exception:
            pass
        labs.append({"label":lab,"cls":a.get_class().get_name(),"loc":[round(loc.x,1),round(loc.y,1),round(loc.z,1)],"mat":mats})
print(json.dumps(labs,ensure_ascii=False,indent=2))
open(r"E:\\UE\\FarmSim25D\\Saved\\restaurant_label_verify.json","w",encoding="utf-8").write(json.dumps(labs,ensure_ascii=False,indent=2))
