# -*- coding: utf-8 -*-
"""Knife3: ensure vars + TableId on instances + TrySeat init patience/price/dish."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
R = {"steps": []}

def log(m):
    unreal.log("[K3V] " + str(m)); R["steps"].append(str(m))

def ensure_var(bp, name, type_name):
    names = [str(n) for n in bel.list_member_variable_names(bp, False)]
    t = bel.get_basic_type_by_name(type_name)
    if name not in names:
        bel.add_member_variable(bp, name, t)
        log("add " + bp.get_name() + "." + name)
    else:
        try:
            bel.change_member_variable_type(bp, name, t)
        except Exception:
            pass
    return True

# ---- Table vars ----
tbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
for n, ty in [
    ("TableId", "int"),
    ("bOccupied", "bool"),
    ("CurrentOrder", "string"),
    ("CurrentDishId", "int"),
    ("bHasOrder", "bool"),
    ("bOrderPending", "bool"),  # needs cooking / not yet served
    ("bEating", "bool"),
    ("PatienceLeft", "real"),
    ("EatLeft", "real"),
    ("OrderPrice", "real"),
]:
    ensure_var(tbp, n, ty)

# ---- Stove vars ----
sbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
for n, ty in [
    ("bCooking", "bool"),
    ("bCookReady", "bool"),
    ("CookingDishId", "int"),
    ("CookingTableId", "int"),
    ("CookTimeLeft", "real"),
    ("CookingOrder", "string"),
]:
    ensure_var(sbp, n, ty)

# ---- Manager vars ----
mbp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
for n, ty in [
    ("HeldDishId", "int"),
    ("HeldTableId", "int"),
    ("HeldOrder", "string"),
    ("RestaurantMoney", "real"),
    ("bIsOpenBusiness", "bool"),
]:
    ensure_var(mbp, n, ty)

# set TableId on level instances
for a in eas.get_all_level_actors():
    lab = a.get_actor_label()
    if lab == "Restaurant_Table1":
        try:
            a.set_editor_property("table_id", 1)
            log("Table1 id=1")
        except Exception as e:
            # try generated name
            try:
                a.set_editor_property("TableId", 1); log("Table1 TableId=1")
            except Exception as e2:
                log("Table1 fail " + str(e)[:60] + " / " + str(e2)[:60])
    if lab == "Restaurant_Table2":
        try:
            a.set_editor_property("table_id", 2); log("Table2 id=2")
        except Exception:
            try:
                a.set_editor_property("TableId", 2); log("Table2 TableId=2")
            except Exception as e:
                log("Table2 fail " + str(e)[:80])

bel.compile_blueprint(tbp)
bel.compile_blueprint(sbp)
bel.compile_blueprint(mbp)
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/BP_RestaurantStove")
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
R["statuses"] = {
    "table": str(tbp.get_editor_property("status")),
    "stove": str(sbp.get_editor_property("status")),
    "mgr": str(mbp.get_editor_property("status")),
}
open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_vars.json","w",encoding="utf-8").write(json.dumps(R, indent=2))
print(json.dumps(R, indent=2, ensure_ascii=False))