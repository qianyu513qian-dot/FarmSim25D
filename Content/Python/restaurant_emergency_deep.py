# -*- coding: utf-8 -*-
"""Deeper label census: soil/water/cliff/yard; character IA chain; spring arm."""
import unreal, json
from collections import Counter
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel=unreal.BlueprintEditorLibrary
pref=Counter()
examples={}
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or a.get_name()
    # prefix before last _digits
    key=lab
    if lab.startswith("VMF_"):
        parts=lab.split("_")
        key="_".join(parts[:2]) if len(parts)>=2 else lab
        # more specific
        for p in ("VMF_Grass","VMF_Path","VMF_Soil","VMF_Water","VMF_Cliff","VMF_Bridge","VMF_Tree","VMF_Crop","VMF_House","VMF_Well","VMF_Chicken","VMF_Scarecrow","VMF_Shipping","VMF_Fence"):
            if lab.startswith(p) or p.replace("VMF_","") in lab and lab.startswith("VMF_"):
                pass
    # bucket by startswith buckets
    bucket="other"
    for b in ("VMF_Grass","VMF_Path","VMF_PathV","VMF_PathJunc","VMF_Soil","VMF_Water","VMF_Cliff","VMF_Bridge","VMF_Tree","VMF_Crop","VMF_Nature","VMF_House","VMF_Well","VMF_Chicken","VMF_Scarecrow","VMF_Shipping","Restaurant","RestChair","Farm_","AirWall","FarmCollision","PlayerStart","FarmClock","BP_Grid","GridManager"):
        if lab.startswith(b) or b in lab:
            bucket=b; break
    pref[bucket]+=1
    if bucket not in examples:
        examples[bucket]=lab

# soil-like any
soilish=[]
waterish=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    low=lab.lower()
    if any(k in low for k in ("soil","till","plot","hoe","crop","field")):
        soilish.append(lab)
    if any(k in low for k in ("water","river","lake","pond")):
        waterish.append(lab)

# character spring arm + IA
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
arm=None
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(cbp):
    data=sds.k2_find_subobject_data_from_handle(h)
    obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
    if obj and "SpringArm" in obj.get_class().get_name():
        r=obj.get_editor_property("relative_rotation")
        arm={"pitch":r.pitch,"yaw":r.yaw,"arm":obj.get_editor_property("target_arm_length")}

cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
chain=[]
for n in cge.list_all_nodes():
    if "IA_Interact" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name())=="Started":
                q=[cp.get_owning_node() for cp in p.list_connected_pins()]; seen=set()
                while q and len(chain)<20:
                    x=q.pop(0)
                    if id(x) in seen: continue
                    seen.add(id(x)); chain.append(bel.get_node_title(x))
                    for pp in bel.list_all_pins(x):
                        if "output" in str(pp.get_pin_direction()).lower():
                            for cp in pp.list_connected_pins(): q.append(cp.get_owning_node())

rep={"buckets":dict(pref),"examples":examples,"soilish_n":len(soilish),"soilish_sample":soilish[:40],"waterish_n":len(waterish),"waterish_sample":waterish[:20],"spring_arm":arm,"ia_chain":chain}
open(r"E:\UE\FarmSim25D\Saved\restaurant_emergency_deep.json","w",encoding="utf-8").write(json.dumps(rep,ensure_ascii=False,indent=2))
print(json.dumps(rep,ensure_ascii=False,indent=2))
