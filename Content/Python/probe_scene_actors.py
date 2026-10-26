import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
labels = []
for a in eas.get_all_level_actors():
    try:
        lab = a.get_actor_label()
        cls = a.get_class().get_name()
        loc = a.get_actor_location()
        labels.append((lab, cls, round(loc.x), round(loc.y), round(loc.z)))
    except Exception:
        pass
labels.sort(key=lambda t: t[0])
for t in labels:
    unreal.log("[PROBE] {} | {} | ({},{},{})".format(t[0], t[1], t[2], t[3], t[4]))
unreal.log("[PROBE] count={}".format(len(labels)))
