# -*- coding: utf-8 -*-
"""Place Farm_Shop (AFarmSeedShop) near farmhouse/path. Idempotent."""
import unreal, json, math

REPORT = {"ok": False, "steps": [], "placed": None, "errors": []}
OUT = r"E:\UE\FarmSim25D\Saved\shop_place.json"
# Near farmhouse (home ~1950,3400) / bed ~1880,3320 — path side
LOC = unreal.Vector(2050.0, 3280.0, 2.0)
LABEL = "Farm_Shop"

def log(m):
    REPORT["steps"].append(str(m))
    unreal.log("[shop_place] " + str(m))

def main():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Remove old Farm_Shop actors
    removed = 0
    for a in list(eas.get_all_level_actors()):
        lab = a.get_actor_label() or ""
        cls = a.get_class().get_name() if a.get_class() else ""
        tags = [str(t) for t in (a.tags or [])]
        if lab == LABEL or "FarmSeedShop" in cls or "Farm_Shop" in tags or "FarmShop" in tags:
            # keep only our C++ class if already correct? delete all labeled Farm_Shop to re-place
            if lab == LABEL or "FarmSeedShop" in cls:
                try:
                    eas.destroy_actor(a)
                    removed += 1
                except Exception as e:
                    REPORT["errors"].append("destroy " + str(e))
    log("removed=" + str(removed))

    cls = unreal.load_class(None, "/Script/FarmSim25D.FarmSeedShop")
    if not cls:
        # try alternate
        try:
            cls = unreal.FarmSeedShop.static_class()
        except Exception:
            cls = None
    if not cls:
        REPORT["errors"].append("FarmSeedShop class not loaded — compile C++ first")
        open(OUT, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
        print(json.dumps(REPORT, ensure_ascii=False, indent=2))
        return REPORT

    actor = eas.spawn_actor_from_class(cls, LOC, unreal.Rotator(0, 0, 0))
    if not actor:
        REPORT["errors"].append("spawn failed")
        open(OUT, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
        print(json.dumps(REPORT, ensure_ascii=False, indent=2))
        return REPORT

    try:
        actor.set_actor_label(LABEL)
    except Exception:
        pass
    try:
        tags = list(actor.tags or [])
        for t in ("FarmShop", "Farm_Shop"):
            n = unreal.Name(t)
            if n not in tags:
                tags.append(n)
        actor.set_editor_property("tags", tags)
    except Exception as e:
        log("tag warn " + str(e))

    # Visible label mark (debug text actor optional) — scale mesh a bit
    try:
        actor.set_actor_scale3d(unreal.Vector(1.2, 1.2, 1.2))
    except Exception:
        pass

    loc = actor.get_actor_location()
    REPORT["placed"] = {
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_name(),
        "x": round(loc.x), "y": round(loc.y), "z": round(loc.z),
        "tags": [str(t) for t in (actor.tags or [])],
    }
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved")
    except Exception as e:
        REPORT["errors"].append("save " + str(e))

    REPORT["ok"] = True
    open(OUT, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
    print(json.dumps(REPORT, ensure_ascii=False, indent=2))
    return REPORT

main()
