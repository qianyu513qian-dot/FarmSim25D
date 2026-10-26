# -*- coding: utf-8 -*-
"""ONE clean -90 deg yaw rotation of VMF farm about center.
No grass fill, no water rebuild, no fence spawn. Preserves relative layout.
Assumes green VMF scene already rebuilt (phase_vmf_scene_build + holes2).
Camera/IMC/GridManager/VisualizeCell untouched.
"""
import unreal
import math

ANGLE_DEG = -90.0
CELL = 100.0

def log(m):
    unreal.log("[CLEANROT] " + str(m))
    print("[CLEANROT] " + str(m))

def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def rot_xy(x, y, deg, cx, cy):
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    dx, dy = x - cx, y - cy
    return cx + dx * c - dy * s, cy + dx * s + dy * c

def should_rotate(lab, cn):
    if lab.startswith("VMF_") or lab.startswith("Scene_"):
        return True
    if lab in ("PlayerStart", "FarmCollisionFloor"):
        return True
    if cn == "PlayerStart":
        return True
    return False

def hide_farmground():
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if "FarmGround" in lab or lab in ("GroundPlane",):
            try:
                a.set_actor_hidden_in_game(True)
                a.set_is_temporarily_hidden_in_editor(True)
                a.set_actor_location(unreal.Vector(-50000, -50000, -1000), False, True)
                try:
                    smc = a.static_mesh_component
                    if smc:
                        smc.set_visibility(False)
                        smc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                except Exception:
                    pass
                log("hid " + lab)
            except Exception as e:
                log("hide fail {}: {}".format(lab, e))

def main():
    hide_farmground()

    # Farm center from VMF AABB (fallback 1950,2000)
    xs, ys = [], []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab.startswith("VMF_"):
            loc = a.get_actor_location()
            xs.append(loc.x)
            ys.append(loc.y)
    if xs:
        CX = (min(xs) + max(xs)) * 0.5
        CY = (min(ys) + max(ys)) * 0.5
        log("center from AABB ({:.0f},{:.0f}) n={}".format(CX, CY, len(xs)))
    else:
        CX, CY = 1950.0, 2000.0
        log("WARN no VMF; fallback center")

    actors = []
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        cn = a.get_class().get_name()
        if should_rotate(lab, cn):
            actors.append(a)

    log("rotating {} actors by {} about ({:.0f},{:.0f})".format(
        len(actors), ANGLE_DEG, CX, CY))

    moved = 0
    nxs, nys = [], []
    for a in actors:
        lab = a.get_actor_label() or ""
        loc = a.get_actor_location()
        nx, ny = rot_xy(loc.x, loc.y, ANGLE_DEG, CX, CY)
        try:
            old_rot = a.get_actor_rotation()
            new_yaw = old_rot.yaw + ANGLE_DEG
            while new_yaw > 180.0:
                new_yaw -= 360.0
            while new_yaw < -180.0:
                new_yaw += 360.0
            a.set_actor_location(unreal.Vector(nx, ny, loc.z), False, True)
            a.set_actor_rotation(unreal.Rotator(old_rot.pitch, new_yaw, old_rot.roll), False)
            moved += 1
            nxs.append(nx)
            nys.append(ny)
        except Exception as e:
            log("fail {}: {}".format(lab, e))

    log("moved={}".format(moved))

    # PlayerStart: Z=100, keep rotated XY clamped into farm
    ps = None
    for a in eas().get_all_level_actors():
        lab = a.get_actor_label() or ""
        if lab == "PlayerStart" or a.get_class().get_name() == "PlayerStart":
            ps = a
            break
    if ps:
        loc = ps.get_actor_location()
        px = max(150.0, min(3850.0, loc.x))
        py = max(150.0, min(3850.0, loc.y))
        ps.set_actor_location(unreal.Vector(px, py, 100.0), False, True)
        log("PlayerStart ({:.0f},{:.0f},100) Grid=({},{})".format(
            px, py, int(px // CELL), int(py // CELL)))
    else:
        log("WARN no PlayerStart")

    # Recenter invisible collision floor to new AABB
    floor = None
    for a in eas().get_all_level_actors():
        if a.get_actor_label() == "FarmCollisionFloor":
            floor = a
            break
    if nxs:
        mid_x = (min(nxs) + max(nxs)) * 0.5
        mid_y = (min(nys) + max(nys)) * 0.5
        span_x = max(nxs) - min(nxs) + 200.0
        span_y = max(nys) - min(nys) + 200.0
    else:
        mid_x, mid_y, span_x, span_y = CX, CY, 4200.0, 4200.0
    sx = max(span_x, 4200.0) / 100.0
    sy = max(span_y, 4200.0) / 100.0
    if floor:
        floor.set_actor_location(unreal.Vector(mid_x, mid_y, 0.0), False, True)
        floor.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
        try:
            smc = floor.static_mesh_component
            if smc:
                smc.set_visibility(False)
                smc.set_hidden_in_game(True)
                smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        except Exception:
            pass
        log("FarmCollisionFloor ({:.0f},{:.0f}) scale=({:.1f},{:.1f})".format(
            mid_x, mid_y, sx, sy))
    else:
        try:
            plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane")
            floor = eas().spawn_actor_from_class(
                unreal.StaticMeshActor, unreal.Vector(mid_x, mid_y, 0.0), unreal.Rotator())
            floor.set_actor_label("FarmCollisionFloor")
            floor.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
            smc = floor.static_mesh_component
            smc.set_static_mesh(plane)
            smc.set_visibility(False)
            smc.set_hidden_in_game(True)
            smc.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            log("spawned FarmCollisionFloor")
        except Exception as e:
            log("floor spawn fail: " + str(e))

    # Composition report
    def centroid(pred):
        pts = []
        for a in eas().get_all_level_actors():
            if pred(a.get_actor_label() or ""):
                loc = a.get_actor_location()
                pts.append((loc.x, loc.y))
        if not pts:
            return None
        return (sum(p[0] for p in pts) / len(pts),
                sum(p[1] for p in pts) / len(pts), len(pts))

    h = centroid(lambda l: "FarmShed" in l)
    w = centroid(lambda l: l.startswith("VMF_Cliff_") or l == "VMF_Water_Left")
    t = centroid(lambda l: l.startswith("VMF_") and "Tree" in l)
    g = centroid(lambda l: l.startswith("VMF_Grass_"))
    s = centroid(lambda l: "Soil" in l or "Crop" in l)
    log("house={}".format(h))
    log("water/cliff={}".format(w))
    log("trees={}".format(t))
    log("grass={}".format(g))
    log("soil/crop={}".format(s))

    vmf = sum(1 for a in eas().get_all_level_actors()
              if (a.get_actor_label() or "").startswith("VMF_"))
    total = sum(1 for _ in eas().get_all_level_actors())
    log("VMF_*={} total_actors={}".format(vmf, total))

    # Screen scores for yaw=-45: su~(dx-dy), sr~(dx+dy)
    center = (CX, CY)
    def scr(p, name):
        if not p:
            return
        dx, dy = p[0] - center[0], p[1] - center[1]
        su = (dx - dy) / math.sqrt(2)
        sr = (dx + dy) / math.sqrt(2)
        log("{} screen_up={:.0f} screen_right={:.0f}".format(name, su, sr))
    scr(h, "house")
    scr(w, "water")
    scr(t, "trees")
    scr(s, "fields")

    try:
        els = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        log("save={}".format(els.save_current_level()))
    except Exception as e:
        log("save fail " + str(e))
    log("DONE angle={}".format(ANGLE_DEG))

main()
