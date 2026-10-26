# -*- coding: utf-8 -*-
import unreal, os, time

TAG = "[FORCE_RES] "
def log(m):
    s = TAG + str(m)
    unreal.log(s)
    print(s)

CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA_MAP = {
    "E": "/Game/TopDown/Input/Actions/IA_Interact",
    "F": "/Game/TopDown/Input/Actions/IA_Plant",
    "R": "/Game/TopDown/Input/Actions/IA_Water",
    "G": "/Game/TopDown/Input/Actions/IA_Grow",
    "H": "/Game/TopDown/Input/Actions/IA_Harvest",
}

imc = unreal.EditorAssetLibrary.load_asset(IMC)
for key_name, ia_path in IA_MAP.items():
    ia = unreal.EditorAssetLibrary.load_asset(ia_path)
    k = unreal.Key()
    k.import_text(key_name)
    try:
        imc.unmap_all_keys_from_action(ia)
    except Exception:
        pass
    imc.map_key(ia, k)

try:
    imc.modify()
except Exception as e:
    log("imc.modify " + str(e))

ok_imc = unreal.EditorAssetLibrary.save_asset(IMC, only_if_is_dirty=False)
log("save_imc only_if_is_dirty=False -> " + str(ok_imc))

try:
    okd = unreal.EditorAssetLibrary.save_directory("/Game/TopDown/Input", True, True)
    log("save_input_dir " + str(okd))
except Exception as e:
    log("save_input_dir " + str(e))

try:
    okp = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("save_dirty " + str(okp))
except Exception as e:
    log("save_dirty " + str(e))

txt = imc.get_editor_property("default_key_mappings").export_text()
imc_final = {
    "E": ("Key=E" in txt) and ("IA_Interact" in txt),
    "F": ("Key=F" in txt) and ("IA_Plant" in txt),
    "R": ("Key=R" in txt) and ("IA_Water" in txt),
    "G": ("Key=G" in txt) and ("IA_Grow" in txt),
    "H": ("Key=H" in txt) and ("IA_Harvest" in txt),
    "WASD": all(("Key=" + k) in txt for k in "WASD"),
}
log("IMC " + str(imc_final))

bp = unreal.EditorAssetLibrary.load_asset(CHAR)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    obj = lib.get_object_for_blueprint(lib.get_data(h), bp)
    if not obj:
        continue
    cname = obj.get_class().get_name()
    if "SpringArm" in cname:
        r = obj.get_editor_property("relative_rotation")
        arm = obj.get_editor_property("target_arm_length")
        log("SpringArm p={:.0f} y={:.0f} arm={}".format(r.pitch, r.yaw, arm))
    if cname == "CameraComponent":
        try:
            log("ortho=" + str(obj.get_editor_property("ortho_width")))
        except Exception:
            pass

try:
    bp.modify()
except Exception:
    pass
log("save_char " + str(unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)))

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
log("save_level " + str(les.save_current_level()))
try:
    log("save_ext " + str(unreal.EditorAssetLibrary.save_directory("/Game/__ExternalActors__/TopDown/Lvl_TopDown", True, True)))
except Exception as e:
    log("save_ext " + str(e))

paths = [
    r"E:\UE\FarmSim25D\Content\TopDown\Lvl_TopDown.umap",
    r"E:\UE\FarmSim25D\Content\TopDown\Blueprints\BP_TopDownCharacter.uasset",
    r"E:\UE\FarmSim25D\Content\TopDown\Input\IMC_Default.uasset",
    r"E:\UE\FarmSim25D\Content\Farm\Grid\BP_GridManager.uasset",
]
for p in paths:
    if os.path.exists(p):
        ts = os.path.getmtime(p)
        log("mtime {} = {}".format(os.path.basename(p), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))))
    else:
        log("MISSING " + p)
log("DONE")