# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
TAG="[VERIFY_ZONES]"
def log(m):
    unreal.log(TAG+" "+str(m)); print(TAG+" "+str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
soil=crop=air=grass_restored=0
sample_air=None
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Soil_"): soil+=1
    if lab.startswith("VMF_Crop"): crop+=1
    if lab.startswith("AirWall_Water_"):
        air+=1
        if sample_air is None:
            sample_air=a
    if lab.startswith("VMF_Grass_12_20") or lab.startswith("VMF_Grass_8_24") or lab.startswith("VMF_Grass_14_26"):
        grass_restored+=1
        log("grass ok {} loc={} sc={}".format(lab, a.get_actor_location(), a.get_actor_scale3d()))

log("counts soil={} crop={} airwalls={} grass_samples={}".format(soil, crop, air, grass_restored))
if sample_air:
    smc=sample_air.static_mesh_component
    log("airwall sample {} hidden_game={} coll_actor={} mesh={} scale={}".format(
        sample_air.get_actor_label(),
        sample_air.is_hidden_ed() if hasattr(sample_air,"is_hidden_ed") else "?",
        sample_air.get_actor_enable_collision() if hasattr(sample_air,"get_actor_enable_collision") else "?",
        smc.get_editor_property("static_mesh") if smc else None,
        sample_air.get_actor_scale3d()))
    try:
        log("airwall coll_enabled={}".format(smc.get_editor_property("collision_enabled")))
    except Exception as e:
        log("coll prop "+str(e))
    try:
        log("airwall profile={}".format(smc.get_editor_property("collision_profile_name")))
    except Exception as e:
        try:
            log("airwall CollisionProfileName={}".format(smc.get_editor_property("CollisionProfileName")))
        except Exception as e2:
            log("profile "+str(e2))
    try:
        log("hidden_in_game={}".format(sample_air.is_actor_hidden_in_game() if hasattr(sample_air,"is_actor_hidden_in_game") else sample_air.get_editor_property("bHidden")))
    except Exception as e:
        log("hid "+str(e))

bp=unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
cdo=unreal.get_default_object(bp.generated_class())
bi=cdo.get_editor_property("BlockedIndices")
log("BlockedIndices n={}".format(len(bi) if bi else 0))
# spot checks
checks=[("path17,16",16*40+17,True),("path18,20",20*40+18,True),
        ("bridge3,18",18*40+3,True),("water0,10",10*40+0,True),
        ("grass23,16",16*40+23,False),("grass25,15",15*40+25,False),
        ("old_soil12,20",20*40+12,False)]
bil=list(bi) if bi else []
bset=set(bil)
for name,flat,expect in checks:
    got=flat in bset
    log("check {} flat={} blocked={} expect={} OK={}".format(name,flat,got,expect,got==expect))

# TillCell structure
g=bel.find_graph(bp,"TillCell")
ge=unreal.BlueprintGraphEditor.get_graph_editor(g)
has_contains=False
has_mul=False
for n in ge.list_all_nodes():
    if find_pin:=None:
        pass
    if n.get_class().get_name()=="K2Node_CallArrayFunction":
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name())=="ItemToFind":
                has_contains=True
    if n.get_class().get_name()=="K2Node_PromotableOperator":
        has_mul=True
log("TillCell has_contains={} has_promotable_ops={}".format(has_contains, has_mul))

# BeginPlay linked?
eg=bel.find_graph(bp,"EventGraph")
ege=unreal.BlueprintGraphEditor.get_graph_editor(eg)
begin=ege.find_event_node("ReceiveBeginPlay")
then=None
for p in bel.list_all_pins(begin):
    if str(p.get_pin_name()).lower()=="then":
        then=p
log("BeginPlay then pin exists={}".format(then is not None))
# compile status
try:
    bel.compile_blueprint(bp)
    log("compile clean")
except Exception as e:
    log("compile "+str(e))

# Force another save
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)
    log("resave ok")
except Exception as e:
    log("resave "+str(e))
log("DONE")
