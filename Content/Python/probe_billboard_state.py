# -*- coding: utf-8 -*-
"""Probe Scene_* rotations, camera spring arm, prototyping actors."""
import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def log(m):
    unreal.log("[FIXPROBE] " + str(m))

# Scene actors sample
scene = []
proto = []
camera_bits = []
all_labs = []
for a in eas.get_all_level_actors():
    try:
        lab = a.get_actor_label()
        cls = a.get_class().get_name()
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        sc = a.get_actor_scale3d()
        all_labs.append(lab)
        if lab.startswith("Scene_"):
            scene.append((lab, cls, round(loc.x), round(loc.y), round(loc.z),
                          round(rot.pitch,1), round(rot.yaw,1), round(rot.roll,1),
                          round(sc.x,2), round(sc.y,2), round(sc.z,2)))
        # prototyping / gray box heuristics
        low = lab.lower()
        cname = cls.lower()
        mesh_name = ""
        try:
            if hasattr(a, "static_mesh_component") and a.static_mesh_component:
                m = a.static_mesh_component.static_mesh
                if m:
                    mesh_name = m.get_name()
        except Exception:
            pass
        if ("prototyp" in low or "prototyp" in mesh_name.lower()
            or mesh_name.startswith("SM_Ramp") or mesh_name.startswith("SM_Chamfer")
            or "Template" in lab or lab.startswith("Floor") or lab.startswith("Wall")
            or lab.startswith("Ramp") or "Cylinder" in mesh_name
            or "Cube" in mesh_name and not lab.startswith("Scene_")
            or "SM_" in mesh_name and "LevelPrototyping" in str(getattr(a.static_mesh_component.static_mesh, "get_path_name", lambda: "")())
            ):
            proto.append((lab, cls, mesh_name, round(loc.x), round(loc.y), round(loc.z)))
        # also catch by path
        try:
            if hasattr(a, "static_mesh_component") and a.static_mesh_component and a.static_mesh_component.static_mesh:
                p = a.static_mesh_component.static_mesh.get_path_name()
                if "LevelPrototyping" in p or "Prototype" in p:
                    if (lab, cls, mesh_name, round(loc.x), round(loc.y), round(loc.z)) not in proto:
                        proto.append((lab, cls, mesh_name + "|" + p, round(loc.x), round(loc.y), round(loc.z)))
        except Exception:
            pass
        # camera / character
        if "TopDown" in cls or "TopDown" in lab or "Camera" in cls or "Player" in lab:
            camera_bits.append((lab, cls, round(loc.x), round(loc.y), round(loc.z),
                                round(rot.pitch,1), round(rot.yaw,1), round(rot.roll,1)))
            # components
            try:
                for c in a.get_components_by_class(unreal.SceneComponent):
                    cn = c.get_name()
                    if "Spring" in cn or "Camera" in cn or "Arm" in cn:
                        try:
                            cr = c.get_relative_rotation()
                            cl = c.get_relative_location()
                            extra = ""
                            try:
                                if hasattr(c, "target_arm_length"):
                                    extra += " armLen=" + str(c.get_editor_property("target_arm_length"))
                            except Exception:
                                pass
                            try:
                                if hasattr(c, "ortho_width"):
                                    extra += " ortho=" + str(c.get_editor_property("ortho_width"))
                            except Exception:
                                pass
                            try:
                                if hasattr(c, "projection_mode"):
                                    extra += " proj=" + str(c.get_editor_property("projection_mode"))
                            except Exception:
                                pass
                            camera_bits.append(("  COMP "+cn, type(c).__name__, round(cl.x), round(cl.y), round(cl.z),
                                                round(cr.pitch,1), round(cr.yaw,1), round(cr.roll,1)))
                            if extra:
                                log("  " + cn + extra)
                        except Exception as e:
                            log("comp err " + str(e))
            except Exception as e:
                log("comps fail " + str(e))
    except Exception as e:
        log("actor err " + str(e))

log("=== SCENE sample (first 15) ===")
for t in sorted(scene)[:15]:
    log("{} rot=({},{},{}) scale=({},{},{}) loc=({},{},{})".format(
        t[0], t[5], t[6], t[7], t[8], t[9], t[10], t[2], t[3], t[4]))
log("scene_count=" + str(len(scene)))

log("=== PROTO / gray ===")
for t in proto:
    log("{} | {} | mesh={} @ ({},{},{})".format(t[0], t[1], t[2], t[3], t[4], t[5]))
log("proto_count=" + str(len(proto)))

log("=== CAMERA-ish ===")
for t in camera_bits:
    log(str(t))

# Blueprint defaults for TopDown character
for path in [
    "/Game/TopDown/Blueprints/BP_TopDownCharacter",
    "/Game/Variant_TopDown/Blueprints/BP_TopDownCharacter",
    "/Game/TopDownBP/Blueprints/TopDownCharacter",
    "/Game/Blueprints/BP_TopDownCharacter",
]:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        log("FOUND BP " + path)
        bp = unreal.EditorAssetLibrary.load_asset(path)
        try:
            cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(path)) if False else None
        except Exception:
            pass

# search assets
assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False)
hits = [a for a in assets if "TopDown" in a and ("Character" in a or "Controller" in a or "Camera" in a)]
log("=== TopDown assets ===")
for h in hits[:40]:
    log(h)

# also list all non-Scene actors briefly
log("=== ALL LABELS ===")
for lab in sorted(all_labs):
    if not lab.startswith("Scene_"):
        log("  " + lab)
