# -*- coding: utf-8 -*-
"""Probe current Restaurant actor locs + BP components for labels."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
out = {"actors": [], "bps": {}}

for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        loc = a.get_actor_location()
        sc = a.get_actor_scale3d()
        tags = []
        try:
            tags = [str(t) for t in (a.get_editor_property("tags") or [])]
        except Exception:
            pass
        il = None
        for k in ("InteractLabel", "interact_label", "InteractLabel_"):
            try:
                il = a.get_editor_property(k)
                break
            except Exception:
                pass
        comps = []
        for c in a.get_components_by_class(unreal.ActorComponent):
            cn = c.get_class().get_name()
            if "Text" in cn or "Widget" in cn or "Billboard" in cn or "Mesh" in cn:
                comps.append({"name": c.get_name(), "class": cn})
        out["actors"].append({
            "label": lab, "class": a.get_class().get_name(),
            "loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)],
            "scale": [round(sc.x,4), round(sc.y,4), round(sc.z,4)],
            "tags": tags, "InteractLabel": str(il) if il is not None else None,
            "comps": comps,
        })

DIR = "/Game/Farm/Restaurant"
for name in ("BP_RestaurantInteractable", "BP_RestaurantTable", "BP_RestaurantStove",
             "BP_RestaurantTrash", "BP_RestaurantOpenSign", "BP_RestaurantManager"):
    path = DIR + "/" + name
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        out["bps"][name] = "MISSING"
        continue
    bp = unreal.EditorAssetLibrary.load_asset(path)
    info = {"path": path, "parent": None, "vars": [], "scs": []}
    try:
        info["parent"] = str(bp.parent_class)
    except Exception:
        pass
    try:
        for v in bel.get_introduced_variables(bp) or []:
            info["vars"].append(str(v))
    except Exception as e:
        info["vars_err"] = str(e)
    # SCS components
    try:
        scs = bp.simple_construction_script
        if scs:
            for n in scs.get_all_nodes():
                info["scs"].append({"name": n.get_variable_name() if hasattr(n, "get_variable_name") else str(n),
                                    "class": n.get_class().get_name()})
    except Exception as e:
        info["scs_err"] = str(e)
    # try component templates via generated class CDO
    try:
        cls = bp.generated_class()
        if cls:
            cdo = unreal.get_default_object(cls)
            for c in cdo.get_components_by_class(unreal.ActorComponent):
                info.setdefault("cdo_comps", []).append({"name": c.get_name(), "class": c.get_class().get_name()})
    except Exception as e:
        info["cdo_err"] = str(e)
    out["bps"][name] = info

path = r"E:\UE\FarmSim25D\Saved\restaurant_layout_probe.json"
open(path, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(out, ensure_ascii=False, indent=2))
