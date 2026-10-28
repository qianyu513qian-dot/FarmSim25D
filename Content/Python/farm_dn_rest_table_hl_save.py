import unreal, json
REPORT={}
# save current level
try:
    ok = unreal.EditorLoadingAndSavingUtils.save_current_level()
    REPORT["save_current_level"]=str(ok)
except Exception as e:
    REPORT["save_current_level_err"]=str(e)[:120]
try:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    REPORT["save_dirty"]="ok"
except Exception as e:
    REPORT["save_dirty_err"]=str(e)[:120]
# verify tags still present
actor_sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
tags={}
for a in actor_sub.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab in ("Restaurant_Table1","Restaurant_Table2","RestMark_Table1","RestMark_Table2"):
        tags[lab]=[str(t) for t in (a.tags or [])]
REPORT["tags"]=tags
open(r"E:\UE\FarmSim25D\Saved\restaurant_table_hl_save.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False))