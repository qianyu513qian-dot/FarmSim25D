import unreal
def log(m):
    print("[w]", m); unreal.log("[w] "+m)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
names = {}
water = []
cliff = []
bridge = []
grass = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or a.get_name()
    loc = a.get_actor_location()
    if not (lab.startswith("VMF_") or lab.startswith("Scene_")):
        continue
    prefix = lab.split("_")[1] if "_" in lab else lab
    names[prefix] = names.get(prefix, 0) + 1
    low = lab.lower()
    if "water" in low or "pond" in low or "lake" in low:
        water.append((lab, loc.x, loc.y))
    if "cliff" in low or "bank" in low:
        cliff.append((lab, loc.x, loc.y))
    if "bridge" in low or "pier" in low or "plank" in low:
        bridge.append((lab, loc.x, loc.y))
    if "Grass" in lab and "Clump" not in lab:
        grass += 1
log("prefixes " + str(sorted(names.items(), key=lambda x:-x[1])[:25]))
log("water n={} sample={}".format(len(water), water[:5]))
log("cliff n={} sample={}".format(len(cliff), cliff[:5]))
log("bridge n={} sample={}".format(len(bridge), bridge[:8]))
log("grass_tiles~{}".format(grass))
if water:
    xs=[w[1] for w in water]; ys=[w[2] for w in water]
    log("water xy {:.0f}..{:.0f} , {:.0f}..{:.0f}".format(min(xs),max(xs),min(ys),max(ys)))
if cliff:
    xs=[w[1] for w in cliff]
    log("cliff x {:.0f}..{:.0f}".format(min(xs),max(xs)))
