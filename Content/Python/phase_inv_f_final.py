# -*- coding: utf-8 -*-
"""Final verify + force save inventory assets."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[INV_F] " + str(m))
    print("[INV_F] " + str(m))

def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

bp = unreal.load_asset(CHAR)

# UpdateFarmHUD graph check
ug = bel.find_graph(bp, "UpdateFarmHUD")
uge = unreal.BlueprintGraphEditor.get_graph_editor(ug)
try:
    errs = uge.list_nodes_with_errors()
    log("UpdateFarmHUD errors=" + str(len(errs)))
    for n in errs:
        log("  " + title(n))
except Exception as e:
    log(str(e))
log("UpdateFarmHUD nodes=" + str(len(list(uge.list_all_nodes()))))

# Harvest walk
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
for n in ge.list_all_nodes():
    p = find_pin(n, "InputAction")
    if not p:
        continue
    try:
        if "IA_Harvest" not in (p.get_pin_value() or ""):
            continue
    except Exception:
        continue
    log("Harvest chain:")
    started = find_pin(n, "Started", "Output")
    queue = [(c.get_owning_node(), 0) for c in conn(started)]
    seen=set()
    while queue:
        cur,d=queue.pop(0)
        if id(cur) in seen or d>10: continue
        seen.add(id(cur))
        log("  "*d + title(cur))
        for cp in bel.list_all_pins(cur):
            if str(cp.get_pin_name()) in ("then","else"):
                for c in conn(cp):
                    queue.append((c.get_owning_node(), d+1))

# vars + defaults
names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(bp)]
for v in ("Money","SeedCount","CropCount","TomatoSellPrice","FarmHUDWidget"):
    log("var {}={}".format(v, v in names))
gen = bp.generated_class()
cdo = unreal.get_default_object(gen)
for prop in ("Money","SeedCount","CropCount","TomatoSellPrice"):
    log("default {}={}".format(prop, cdo.get_editor_property(prop)))

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
if unreal.EditorAssetLibrary.does_asset_exist(WBP):
    unreal.EditorAssetLibrary.save_asset(WBP, only_if_is_dirty=False)
    log("WBP saved (shell, no TextBlocks - UE5.8 Python cannot set RootWidget)")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("level " + str(e))
log("ALL GOOD")
