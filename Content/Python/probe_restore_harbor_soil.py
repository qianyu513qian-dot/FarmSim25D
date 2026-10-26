# -*- coding: utf-8 -*-
"""Probe leftover soil/crop/cliff/yard and missing pier/fence actors."""
import unreal
from collections import Counter, defaultdict

TAG = "[RESTORE_PROBE]"

def log(m):
    unreal.log(TAG + " " + str(m))
    print(TAG + " " + str(m))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
KW = ("Soil", "Hoe", "Till", "Crop", "Fence", "Gate", "Dock", "Pier", "Harbor",
      "Path", "Deck", "Bridge", "Water", "AirWall", "Cliff", "Yard", "Shore",
      "Untilled", "Dry", "Wet", "Rail", "Post", "Plot")

prefix_counts = Counter()
kw_hits = defaultdict(list)
mesh_samples = []
brownish = []  # actors whose mesh path contains Soil
all_labels = []

for a in eas.get_all_level_actors():
    try:
        lab = a.get_actor_label() or ""
    except Exception:
        continue
    all_labels.append(lab)
    pref = lab.split("_")[0] if lab else "?"
    if lab.startswith("VMF_"):
        parts = lab.split("_")
        pref = "VMF_" + (parts[1] if len(parts) > 1 else "")
    elif lab.startswith("AirWall"):
        pref = "AirWall"
    elif lab.startswith("Scene_"):
        pref = "Scene_"
    prefix_counts[pref] += 1

    low = lab.lower()
    matched = False
    for k in KW:
        if k.lower() in low:
            kw_hits[k].append(lab)
            matched = True

    # mesh path
    mesh_path = None
    try:
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        for c in comps:
            try:
                sm = c.get_editor_property("static_mesh")
                if sm:
                    mesh_path = sm.get_path_name()
                    break
            except Exception:
                pass
    except Exception:
        pass

    if mesh_path and ("Soil" in mesh_path or "soil" in mesh_path):
        loc = a.get_actor_location()
        brownish.append((lab, mesh_path, round(loc.x), round(loc.y), round(loc.z)))

    if matched or (mesh_path and "Soil" in (mesh_path or "")):
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        hid = False
        try:
            hid = a.is_hidden_ed() or a.b_hidden_ed_temporary or a.is_actor_being_destroyed()
        except Exception:
            pass
        try:
            ingame_hid = a.is_hidden()
        except Exception:
            try:
                ingame_hid = a.get_editor_property("b_hidden")
            except Exception:
                ingame_hid = "?"
        mesh_samples.append((lab, mesh_path, round(loc.x), round(loc.y), round(loc.z),
                             round(sc.x, 4), hid, ingame_hid))

log("total_actors={}".format(len(all_labels)))
log("=== prefix counts (top) ===")
for p, n in prefix_counts.most_common(40):
    log("  {} = {}".format(p, n))

log("=== keyword hits ===")
for k in KW:
    labs = kw_hits.get(k, [])
    if not labs:
        continue
    labs_s = sorted(set(labs))
    log("{} n={} sample={}".format(k, len(labs_s), labs_s[:15]))

log("=== mesh contains Soil (brownish) n={} ===".format(len(brownish)))
for t in sorted(brownish, key=lambda x: (x[2], x[3]))[:60]:
    log("BROWN {} mesh={} loc=({},{},{})".format(t[0], t[1].split(".")[-1] if t[1] else None, t[2], t[3], t[4]))
if len(brownish) > 60:
    log("... +{} more brownish".format(len(brownish) - 60))

# specific pier/fence expected labels
expect = []
for tag in ("Mid", "South"):
    for cx in range(2, 17):
        expect.append("VMF_Bridge{}RailN_{}".format(tag, cx))
        expect.append("VMF_Bridge{}RailS_{}".format(tag, cx))
    expect.append("VMF_Bridge{}PostN".format(tag))
    expect.append("VMF_Bridge{}PostS".format(tag))
label_set = set(all_labels)
missing_rails = [e for e in expect if e not in label_set]
present_rails = [e for e in expect if e in label_set]
bridge_decks = sorted(l for l in all_labels if "Bridge" in l and "Rail" not in l and "Post" not in l)
fence_all = sorted(l for l in all_labels if "Fence" in l)
log("bridge_decks n={} sample={}".format(len(bridge_decks), bridge_decks[:20]))
log("fence_all n={} sample={}".format(len(fence_all), fence_all[:30]))
log("pier_rails_posts present={} missing={}".format(len(present_rails), len(missing_rails)))
log("missing sample={}".format(missing_rails[:20]))

# water edge browns: low X or high X?
if brownish:
    xs = [t[2] for t in brownish]
    ys = [t[3] for t in brownish]
    log("brown X range {}..{} Y range {}..{}".format(min(xs), max(xs), min(ys), max(ys)))

# AirWall visibility check
air = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("AirWall"):
        continue
    loc = a.get_actor_location()
    vis = True
    try:
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        for c in comps:
            try:
                vis = c.is_visible()
            except Exception:
                try:
                    vis = c.get_editor_property("b_visible")
                except Exception:
                    pass
            break
    except Exception:
        pass
    try:
        hid = a.b_hidden
    except Exception:
        hid = "?"
    air.append((lab, round(loc.x), round(loc.y), round(loc.z), vis, hid))
log("AirWall n={} sample_vis={}".format(len(air), air[:5]))
visible_air = [t for t in air if t[4] is True]
log("AirWall visible_mesh n={}".format(len(visible_air)))

log("=== done ===")
