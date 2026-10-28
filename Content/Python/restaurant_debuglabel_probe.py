# -*- coding: utf-8 -*-
"""Probe RestName_* visibility + Manager Tick graph."""
import unreal, json
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
R = {"names": {}, "mgr": {}, "errors": []}

for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not (lab.startswith("RestName_") or lab.startswith("RestLabel_") or lab.startswith("Restaurant_")):
        continue
    loc = a.get_actor_location()
    sc = a.get_actor_scale3d()
    info = {
        "cls": a.get_class().get_name(),
        "loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)],
        "scale": [round(sc.x,3), round(sc.y,3), round(sc.z,3)],
        "hidden_game": bool(a.is_hidden_ed() if hasattr(a, "is_hidden_ed") else False),
        "actor_hidden": None,
        "visible": None,
        "rot": [round(a.get_actor_rotation().pitch,1), round(a.get_actor_rotation().yaw,1), round(a.get_actor_rotation().roll,1)],
        "comps": [],
        "mats": [],
    }
    try:
        info["actor_hidden"] = a.b_hidden
    except Exception:
        try:
            info["actor_hidden"] = a.get_editor_property("b_hidden")
        except Exception as e:
            info["actor_hidden_err"] = str(e)[:80]
    try:
        smc = getattr(a, "static_mesh_component", None)
        if smc:
            info["visible"] = smc.is_visible()
            info["hidden_in_game"] = smc.get_editor_property("hidden_in_game") if hasattr(smc, "get_editor_property") else None
            try:
                info["hidden_in_game"] = smc.b_hidden_in_game
            except Exception:
                pass
            try:
                mesh = smc.static_mesh
                info["mesh"] = mesh.get_path_name() if mesh else None
            except Exception:
                pass
            try:
                mat = smc.get_material(0)
                if mat:
                    info["mats"].append(mat.get_path_name())
                    try:
                        info["blend"] = str(mat.get_editor_property("blend_mode"))
                    except Exception:
                        pass
                    try:
                        info["shading"] = str(mat.get_editor_property("shading_model"))
                    except Exception:
                        pass
                    try:
                        info["two_sided"] = bool(mat.get_editor_property("two_sided"))
                    except Exception:
                        pass
            except Exception as e:
                info["mat_err"] = str(e)[:100]
            try:
                bounds = smc.bounds
                info["box_extent"] = [round(bounds.box_extent.x,1), round(bounds.box_extent.y,1), round(bounds.box_extent.z,1)]
            except Exception:
                pass
    except Exception as e:
        info["smc_err"] = str(e)[:100]
    R["names"][lab] = info

# Manager BP tick
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
nodes = []
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if any(k in t for k in ("Tick", "BeginPlay", "DrawRest", "RestaurantTick", "PrintString", "SetTimer")) or c in ("K2Node_Event", "K2Node_CustomEvent"):
        pins = []
        for p in bel.list_all_pins(n):
            links = []
            try:
                for lp in p.get_linked_to():
                    own = lp.get_owning_node()
                    links.append(bel.get_node_title(own) + "." + str(lp.get_pin_name()))
            except Exception:
                pass
            if links or "then" in str(p.get_pin_name()).lower() or "execute" in str(p.get_pin_name()).lower():
                pins.append({"name": str(p.get_pin_name()), "dir": str(p.get_pin_direction()), "links": links[:6]})
        nodes.append({"title": t, "cls": c, "pins": pins[:12]})
R["mgr"]["interesting_nodes"] = nodes
R["mgr"]["vars"] = [str(v) for v in bel.list_member_variable_names(bp, False)]
out = r"E:\UE\FarmSim25D\Saved\restaurant_debuglabel_probe.json"
open(out, "w", encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print("WROTE", out, "names", len(R["names"]), "nodes", len(nodes))
