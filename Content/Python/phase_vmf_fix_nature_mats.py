# -*- coding: utf-8 -*-
"""Fix VMF Expansion02 Nature meshes: wrong M_VMF_Palette -> M_VMF_Expansion02_Nature.
Also refresh materials on placed level actors. Does not thrash the editor.
"""
import unreal

def log(m):
    unreal.log("[VMF_MAT] " + str(m))
    print("[VMF_MAT] " + str(m))

NATURE_MAT = "/Game/Farm/VoxelMicroFarm/Materials/M_VMF_Expansion02_Nature"
NATURE_FOLDER = "/Game/Farm/VoxelMicroFarm/Models/Expansion02/Nature"

mat = unreal.EditorAssetLibrary.load_asset(NATURE_MAT)
if not mat:
    log("MISSING nature mat")
    raise SystemExit(1)

def apply_to_mesh(mesh):
    if not mesh:
        return False
    try:
        slots = mesh.static_materials
        if slots is None or len(slots) == 0:
            return False
        # rebuild slot list with new material
        new_slots = []
        for i, slot in enumerate(slots):
            ns = unreal.StaticMaterial()
            # copy existing fields where possible
            try:
                ns.set_editor_property("material_interface", mat if i == 0 else slot.material_interface)
            except Exception:
                ns.material_interface = mat if i == 0 else slot.material_interface
            try:
                ns.set_editor_property("material_slot_name", slot.material_slot_name)
            except Exception:
                pass
            try:
                ns.set_editor_property("imported_material_slot_name", slot.imported_material_slot_name)
            except Exception:
                pass
            new_slots.append(ns)
        mesh.set_editor_property("static_materials", new_slots)
        return True
    except Exception as e:
        log("apply fail {}: {}".format(mesh.get_name(), e))
        try:
            unreal.EditorStaticMeshLibrary.set_material(mesh, 0, mat)
            return True
        except Exception as e2:
            log("set_material fail " + str(e2))
            return False

assets = unreal.EditorAssetLibrary.list_assets(NATURE_FOLDER, recursive=True)
fixed = 0
for a in assets:
    path = a.split(".")[0]
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        continue
    old = None
    try:
        old = mesh.static_materials[0].material_interface
    except Exception:
        pass
    if old and old.get_name() == "M_VMF_Expansion02_Nature":
        log("already OK " + mesh.get_name())
        continue
    if apply_to_mesh(mesh):
        unreal.EditorAssetLibrary.save_asset(path)
        fixed += 1
        log("fixed mesh {} was={}".format(mesh.get_name(), old.get_name() if old else None))

# Also fix any other Expansion02 meshes that wrongly got Palette but need Nature-related
# Actor instance overrides
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()
actor_fixed = 0
for a in actors:
    lab = a.get_actor_label() or ""
    if not lab.startswith("VMF_"):
        continue
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.static_mesh
        if not sm:
            continue
        sp = sm.get_path_name()
        if "/Expansion02/Nature/" not in sp:
            continue
        n = c.get_num_materials()
        for i in range(n):
            cur = c.get_material(i)
            if cur and cur.get_name() == "M_VMF_Expansion02_Nature":
                continue
            c.set_material(i, mat)
            actor_fixed += 1
        # clear override to use mesh default if possible
        try:
            c.empty_override_materials()
            # re-push so instance uses fixed mesh mat
            c.set_material(0, mat)
        except Exception:
            pass

log("meshes_fixed={} actor_slots_touched={}".format(fixed, actor_fixed))

# verify
for name in ("SM_VMF_Nature_Tree_Tall", "SM_VMF_Nature_Tree_Broadleaf", "SM_VMF_Nature_Rock_Large"):
    p = NATURE_FOLDER + "/" + name
    mesh = unreal.EditorAssetLibrary.load_asset(p)
    mi = mesh.static_materials[0].material_interface if mesh else None
    log("VERIFY {} -> {}".format(name, mi.get_name() if mi else None))

# save current level
try:
    unreal.EditorLevelLibrary.save_current_level()
    log("level saved")
except Exception as e:
    log("level save " + str(e))

log("=== DONE MAT FIX ===")
