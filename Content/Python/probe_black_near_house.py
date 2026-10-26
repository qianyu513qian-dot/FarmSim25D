# -*- coding: utf-8 -*-
"""Probe Scene_* near house + materials/meshes that could be black."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorAssetLibrary)
eas_act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[BLKPROBE] " + str(m))

# House region approx: cells 9-17, 19-26 -> world 900-1700, 1900-2600
HOUSE_X0, HOUSE_X1 = 700.0, 2000.0
HOUSE_Y0, HOUSE_Y1 = 1700.0, 2900.0

log("=== Scene_* + nearby actors ===")
rows = []
for a in eas_act.get_all_level_actors():
    try:
        lab = a.get_actor_label()
        cn = a.get_class().get_name()
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        rr = a.get_actor_rotation()
        hidden = False
        try:
            hidden = a.is_hidden_ed() or bool(a.get_editor_property("b_hidden"))
        except Exception:
            try:
                hidden = a.actor_is_temporarily_hidden_in_editor()
            except Exception:
                pass
        try:
            hg = a.b_hidden
        except Exception:
            hg = "?"
        near = (HOUSE_X0 <= loc.x <= HOUSE_X1 and HOUSE_Y0 <= loc.y <= HOUSE_Y1)
        is_scene = lab.startswith("Scene_")
        is_suspect = any(k in lab or k in cn or k in a.get_name() for k in (
            "House", "Terrace", "Cliff", "Fence", "Cube", "Prototype", "Floor", "Stairs", "Path"
        ))
        if not (is_scene or near or is_suspect):
            continue
        mats = []
        mesh_name = ""
        try:
            smc = a.static_mesh_component
            if smc:
                m = smc.static_mesh
                mesh_name = m.get_name() if m else "None"
                for i in range(4):
                    try:
                        mat = smc.get_material(i)
                        if mat:
                            mats.append(mat.get_path_name())
                    except Exception:
                        break
                try:
                    vis = smc.is_visible()
                except Exception:
                    vis = "?"
                try:
                    cast_shadow = smc.get_editor_property("cast_shadow")
                except Exception:
                    cast_shadow = "?"
            else:
                vis = "no-smc"
                cast_shadow = "?"
        except Exception as e:
            mats = ["err:"+str(e)]
            vis = "?"
            cast_shadow = "?"
        rows.append((lab, cn, loc, sc, rr, mats, mesh_name, hidden, hg, vis, near))
    except Exception as e:
        log("actor err " + str(e))

rows.sort(key=lambda t: (t[0],))
for lab, cn, loc, sc, rr, mats, mesh_name, hidden, hg, vis, near in rows:
    log("{} | {} | loc=({},{},{}) sc=({},{},{}) rot=({},{},{}) mesh={} mats={} hidEd={} bHid={} vis={} nearHouse={}".format(
        lab, cn,
        round(loc.x), round(loc.y), round(loc.z),
        round(sc.x, 2), round(sc.y, 2), round(sc.z, 2),
        round(rr.pitch, 1), round(rr.yaw, 1), round(rr.roll, 1),
        mesh_name, mats, hidden, hg, vis, near))

log("=== Key materials ===")
for path in [
    "/Game/Farm/Art/Mats/M_House",
    "/Game/Farm/Art/Mats/M_Terrace",
    "/Game/Farm/Art/Mats/M_Cliff",
    "/Game/Farm/Art/Mats/M_Fence",
    "/Game/Farm/Art/Mats/M_FenceDetail",
    "/Game/Farm/Art/Mats/M_Stairs",
    "/Game/Farm/Art/Mats/M_Dirt",
    "/Game/Farm/Art/T_House",
    "/Game/Farm/Art/T_TerraceTop",
    "/Game/Farm/Art/T_CliffS",
    "/Game/Farm/Art/T_FenceH",
]:
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    if not exists:
        log("MISSING " + path)
        continue
    asset = unreal.EditorAssetLibrary.load_asset(path)
    cn = asset.get_class().get_name()
    extra = ""
    if "Material" in cn and "Instance" not in cn:
        try:
            blend = asset.get_editor_property("blend_mode")
            shade = asset.get_editor_property("shading_model")
            two = asset.get_editor_property("two_sided")
            extra = " blend={} shade={} twoSided={}".format(blend, shade, two)
        except Exception as e:
            extra = " matprop-err " + str(e)
    if "Texture" in cn:
        try:
            sz = (asset.blueprint_get_size_x(), asset.blueprint_get_size_y())
        except Exception:
            try:
                sz = (asset.get_editor_property("source_size_x") if False else "?")
            except Exception:
                sz = "?"
        try:
            comp = asset.get_editor_property("compression_settings")
            has_alpha = not bool(asset.get_editor_property("compression_no_alpha"))
            filt = asset.get_editor_property("filter")
            extra = " size={} comp={} noAlphaInvertedHasA?={} filt={}".format(sz, comp, has_alpha, filt)
        except Exception as e:
            extra = " tex " + str(e)
    log("OK {} ({}){}".format(path, cn, extra))

log("=== DONE ===")
