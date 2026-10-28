# -*- coding: utf-8 -*-
"""Duplicate FarmHUD as order list base; inspect player mesh for guests."""
import unreal

def log(m):
    unreal.log("[UI_CONT] " + str(m))
    print("[UI_CONT] " + str(m))

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

# 1) List FarmHUD tree widgets via ObjectIterator
log("=== FarmHUD tree ===")
for o in unreal.ObjectIterator(unreal.Widget):
    pn = o.get_path_name()
    if "/Game/Farm/UI/WBP_FarmHUD.WBP_FarmHUD:WidgetTree." in pn:
        log("  " + o.get_name() + " " + o.get_class().get_name())

# 2) Duplicate FarmHUD -> WBP_RestOrderList (replace empty one)
src = "/Game/Farm/UI/WBP_FarmHUD"
dst_dir = "/Game/Farm/UI"
dst_name = "WBP_RestOrderList"
dst = dst_dir + "/" + dst_name
# delete empty shells
for p in (dst, "/Game/Farm/UI/WBP_RestOrderList_TMP", "/Game/Farm/UI/WBP_RestProbeRoot"):
    if eas.does_asset_exist(p):
        eas.delete_asset(p)
        log("deleted " + p)

ok = eas.duplicate_asset(dst_name, dst_dir, src)
log("duplicate=" + str(ok) + " exist=" + str(eas.does_asset_exist(dst)))

# 3) Inspect duplicated tree
log("=== Dup tree ===")
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    pn = o.get_path_name()
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in pn:
        widgets[o.get_name()] = o
        log("  " + o.get_name() + " " + o.get_class().get_name())

# 4) Player character mesh
char = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
handles = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(char)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
log("=== Char subobjects ===")
for i, h in enumerate(list(handles or [])):
    data = sub.k2_find_subobject_data_from_handle(h)
    ex = data.export_text()
    log("  [{}] {}".format(i, ex[:220].replace("\n"," ")))

# Mesh asset path from CDO
gen = char.generated_class()
cdo = unreal.get_default_object(gen)
try:
    mesh = cdo.get_editor_property("mesh")
    log("mesh comp=" + str(mesh))
    if mesh:
        sm = mesh.get_editor_property("skeletal_mesh") if hasattr(mesh, "get_editor_property") else None
        try:
            sm = mesh.get_editor_property("skeletal_mesh_asset")
        except Exception:
            try:
                sm = mesh.get_editor_property("SkeletalMesh")
            except Exception:
                sm = None
        log("skeletal=" + str(sm))
        if sm:
            log("skel path=" + sm.get_path_name())
            mats = sm.get_editor_property("materials") if False else None
except Exception as e:
    log("mesh err " + str(e))

# Find skeletal mesh via iterator on char package
for o in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    if "BP_TopDownCharacter" in o.get_path_name() and "GEN_VARIABLE" in o.get_path_name():
        log("SKC " + o.get_path_name())
        for prop in ("skeletal_mesh_asset", "SkeletalMeshAsset", "skeletal_mesh", "SkeletalMesh"):
            try:
                v = o.get_editor_property(prop)
                log("  {}={}".format(prop, v.get_path_name() if v else None))
            except Exception as e:
                pass
        try:
            mats = o.get_editor_property("override_materials")
            log("  override_materials=" + str(mats))
        except Exception as e:
            log("  mats " + str(e))

# Materials on common mannequin
for path in (
    "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
    "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
    "/Engine/EngineMeshes/SkeletalCube",
):
    log("mesh exist {} = {}".format(path, eas.does_asset_exist(path)))

# Search skeletal meshes in project
ar = unreal.AssetRegistryHelpers.get_asset_registry()
skels = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "SkeletalMesh"), True)
farmish = []
for a in list(skels or []):
    pn = str(a.package_name)
    if any(k in pn for k in ("Mannequin", "Manny", "Quinn", "TopDown", "Character", "Farm", "Hero")):
        farmish.append(pn + "/" + str(a.asset_name))
log("skel candidates=" + str(farmish[:30]))

# Table TrySeat - find Print after seat to know where to hook
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
# Find TrySeat and follow then chain briefly
tryseat = None
for n in ge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent" and str(bel.get_node_title(n))=="TrySeat":
        tryseat = n
        break
log("TrySeat=" + str(tryseat))

# Patience max from Set PatienceLeft pin defaults near TrySeat
for n in ge.list_all_nodes():
    if str(bel.get_node_title(n)) == "Set PatienceLeft":
        for p in bel.list_all_pins(n):
            if "PatienceLeft" in str(p.get_pin_name()) and "INPUT" in str(p.get_pin_direction()):
                try:
                    log("PatienceLeft set val=" + str(p.get_pin_value()) + " / def=" + str(getattr(p,"get_default_value",lambda:None)()))
                except Exception as e:
                    log("pl " + str(e))

log("DONE_CONT")
