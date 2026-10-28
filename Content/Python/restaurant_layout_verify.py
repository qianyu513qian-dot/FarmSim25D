# -*- coding: utf-8 -*-
import unreal, json, math
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {"furniture": {}, "labels": {}, "interact_labels": {}, "pairwise": [], "ok": True}
actors = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith(("Restaurant_", "RestChair_", "RestLabel_")):
        loc = a.get_actor_location()
        actors[lab] = a
        if lab.startswith("RestLabel_"):
            tr = a.get_component_by_class(unreal.TextRenderComponent)
            info = {"loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)]}
            if tr:
                t = str(tr.get_editor_property("text"))
                info["text"] = t
                info["cps"] = [hex(ord(c)) for c in t]
                f = tr.get_editor_property("font")
                info["font"] = f.get_path_name() if f else None
                info["world_size"] = float(tr.get_editor_property("world_size"))
            out["labels"][lab] = info
        else:
            out["furniture"][lab] = [round(loc.x,1), round(loc.y,1), round(loc.z,1)]
            for k in ("InteractLabel", "interact_label"):
                try:
                    out["interact_labels"][lab] = str(a.get_editor_property(k))
                    break
                except Exception:
                    pass

# pairwise distances among interactables
keys = ["Restaurant_OpenSign","Restaurant_Table1","Restaurant_Table2","Restaurant_Stove","Restaurant_Trash"]
for i,a in enumerate(keys):
    for b in keys[i+1:]:
        if a not in actors or b not in actors: continue
        la, lb = actors[a].get_actor_location(), actors[b].get_actor_location()
        d = math.sqrt((la.x-lb.x)**2 + (la.y-lb.y)**2)
        out["pairwise"].append({"a": a, "b": b, "dist2d": round(d,1), "both_in_200_if_at_a": d < 200})

# expected cps
expect = {
    "RestLabel_OpenSign": ["0x5f00","0x4e1a","0x724c"],
    "RestLabel_Stove": ["0x7076","0x53f0"],
    "RestLabel_Table1": ["0x9910","0x684c","0x31"],
    "RestLabel_Table2": ["0x9910","0x684c","0x32"],
    "RestLabel_Trash": ["0x5783","0x573e","0x6876"],
}
for k, cps in expect.items():
    got = out["labels"].get(k, {}).get("cps")
    if got != cps:
        out["ok"] = False
        out.setdefault("mismatches", []).append({k: {"got": got, "want": cps}})

open(r"E:\UE\FarmSim25D\Saved\restaurant_layout_verify.json","w",encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(out, ensure_ascii=False, indent=2))