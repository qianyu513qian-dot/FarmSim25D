# -*- coding: utf-8 -*-
"""Replace broken RestLabel_* TextRender (Tt sprites) with texture nameplate planes showing Chinese."""
import unreal
import json
import os

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {"steps": [], "errors": [], "destroyed": [], "spawned": [], "assets": []}

PNG_DIR = r"E:\\UE\\FarmSim25D\\Saved\\RestLabels"
ASSET_DIR = "/Game/Farm/Restaurant/Labels"
PLANE = "/Engine/BasicShapes/Plane"

TARGETS = {
    "OpenSign": "Restaurant_OpenSign",
    "Stove": "Restaurant_Stove",
    "Table1": "Restaurant_Table1",
    "Table2": "Restaurant_Table2",
    "Trash": "Restaurant_Trash",
}
CN = {
    "OpenSign": "\u5f00\u4e1a\u724c",
    "Stove": "\u7076\u53f0",
    "Table1": "\u9910\u684c1",
    "Table2": "\u9910\u684c2",
    "Trash": "\u5783\u573e\u6876",
}
Z_OFF = 150.0
# Plane 100x100 -> wide short plate
SCALE = (2.6, 0.65, 1.0)
# Camera approx direction FROM label TO camera under iso (matches prior TextRender facing)
TOWARD_CAM = unreal.Vector(-0.542, 0.542, 0.643)

def log(m):
    unreal.log("[REST_TEXLABEL] " + str(m))
    REPORT["steps"].append(str(m))

def ensure_dir(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)

def destroy_old():
    n = 0
    for a in list(eas.get_all_level_actors()):
        lab = a.get_actor_label() or ""
        if lab.startswith("RestLabel_") or lab.startswith("RestName_"):
            REPORT["destroyed"].append(lab)
            eas.destroy_actor(a)
            n += 1
    log("destroyed_old={}".format(n))

def face_rot_for_plane():
    # Align Plane +Z (normal) toward camera
    try:
        r = unreal.MathLibrary.make_rot_from_z(TOWARD_CAM)
        return r
    except Exception:
        pass
    # Fallback: standing billboard facing NW-ish (scene style + yaw tweak)
    r = unreal.Rotator()
    r.pitch = 0.0
    r.yaw = 135.0
    r.roll = 90.0
    return r

def import_png(key):
    src = os.path.join(PNG_DIR, "T_RestLabel_{}.png".format(key))
    if not os.path.isfile(src):
        REPORT["errors"].append("missing png " + src)
        return None
    ensure_dir(ASSET_DIR)
    dest_name = "T_RestLabel_" + key
    dest_path = ASSET_DIR + "/" + dest_name
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = ASSET_DIR
    task.destination_name = dest_name
    task.replace_existing = True
    task.automated = True
    task.save = True
    tools.import_asset_tasks([task])
    if not unreal.EditorAssetLibrary.does_asset_exist(dest_path):
        REPORT["errors"].append("import fail " + key)
        return None
    tex = unreal.EditorAssetLibrary.load_asset(dest_path)
    for prop, val in (
        ("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI),
        ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
    ):
        try:
            tex.set_editor_property(prop, val)
        except Exception:
            pass
    try:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(dest_path)
    REPORT["assets"].append(dest_path)
    log("imported " + dest_path)
    return tex

def create_masked_mat(key, texture):
    mat_name = "M_RestLabel_" + key
    path = ASSET_DIR + "/" + mat_name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        try:
            unreal.EditorAssetLibrary.delete_asset(path)
        except Exception as e:
            log("del mat " + str(e))
    factory = unreal.MaterialFactoryNew()
    mat = tools.create_asset(mat_name, ASSET_DIR, unreal.Material, factory)
    if not mat:
        REPORT["errors"].append("mat create fail " + key)
        return None
    try:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception:
        pass
    try:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    except Exception:
        pass
    try:
        mat.set_editor_property("two_sided", True)
    except Exception:
        pass
    try:
        mel.delete_all_material_expressions(mat)
    except Exception:
        pass
    tex_coord = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -600, 0)
    tex_sample = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -350, 0)
    try:
        tex_sample.set_editor_property("texture", texture)
    except Exception:
        tex_sample.texture = texture
    mel.connect_material_expressions(tex_coord, "", tex_sample, "UVs")
    mel.connect_material_property(tex_sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(tex_sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    try:
        mel.recompile_material(mat)
    except Exception as e:
        log("recompile " + str(e))
    unreal.EditorAssetLibrary.save_asset(path)
    REPORT["assets"].append(path)
    log("mat " + path)
    return mat

def spawn_nameplate(key, target_actor, mat, face):
    tloc = target_actor.get_actor_location()
    loc = unreal.Vector(tloc.x, tloc.y, tloc.z + Z_OFF)
    label = "RestName_" + key
    mesh = unreal.EditorAssetLibrary.load_asset(PLANE)
    if not mesh:
        REPORT["errors"].append("no plane mesh")
        return None
    actor = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, face)
    if not actor:
        REPORT["errors"].append("spawn fail " + label)
        return None
    actor.set_actor_label(label)
    try:
        actor.set_folder_path("Restaurant/Labels")
    except Exception:
        pass
    actor.set_actor_scale3d(unreal.Vector(SCALE[0], SCALE[1], SCALE[2]))
    smc = actor.static_mesh_component
    smc.set_editor_property("static_mesh", mesh)
    if mat:
        smc.set_material(0, mat)
    try:
        smc.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    try:
        smc.set_editor_property("cast_shadow", False)
    except Exception:
        pass
    try:
        actor.set_actor_hidden_in_game(False)
        smc.set_visibility(True, True)
        smc.set_hidden_in_game(False)
    except Exception:
        pass
    actor.set_actor_location(loc, False, True)
    actor.set_actor_rotation(face, True)
    # Verify normal ~ toward cam
    try:
        up = actor.get_actor_up_vector()  # Plane normal is actor up after rot_from_z
        dot = up.x * TOWARD_CAM.x + up.y * TOWARD_CAM.y + up.z * TOWARD_CAM.z
    except Exception:
        up = None
        dot = None
    REPORT["spawned"].append({
        "label": label,
        "cn": CN[key],
        "loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)],
        "rot": [round(face.pitch,1), round(face.yaw,1), round(face.roll,1)],
        "dot_up_cam": (round(dot,3) if dot is not None else None),
        "target": target_actor.get_actor_label(),
    })
    log("spawned {} '{}' @{} rot=({},{},{}) dot={}".format(
        label, CN[key], REPORT["spawned"][-1]["loc"],
        round(face.pitch,1), round(face.yaw,1), round(face.roll,1),
        REPORT["spawned"][-1]["dot_up_cam"]))
    return actor

log("start")
destroy_old()
actors = {(a.get_actor_label() or ""): a for a in eas.get_all_level_actors()}
face = face_rot_for_plane()
log("face_rot p={} y={} r={}".format(round(face.pitch,1), round(face.yaw,1), round(face.roll,1)))

for key in TARGETS:
    tgt = actors.get(TARGETS[key])
    if not tgt:
        REPORT["errors"].append("missing target " + TARGETS[key])
        continue
    tex = import_png(key)
    if not tex:
        continue
    mat = create_masked_mat(key, tex)
    if not mat:
        continue
    spawn_nameplate(key, tgt, mat, face)

ok = False
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    ok = True
except Exception:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        ok = True
    except Exception as e:
        REPORT["errors"].append("save level " + str(e))
REPORT["level_saved"] = ok
try:
    unreal.EditorAssetLibrary.save_directory(ASSET_DIR, only_if_is_dirty=False, recursive=True)
except Exception:
    pass
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_invalidate_viewports()
except Exception:
    pass

log("DONE spawned={} errors={}".format(len(REPORT["spawned"]), REPORT["errors"]))
outp = r"E:\\UE\\FarmSim25D\\Saved\\restaurant_texlabels.json"
open(outp, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
