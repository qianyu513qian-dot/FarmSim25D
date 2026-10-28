# -*- coding: utf-8 -*-
import unreal, json, inspect
R = {"string_sigs": [], "sphere_ok": False, "pin_api": [], "errors": []}
# Probe SystemLibrary draw_debug_string
fn = unreal.SystemLibrary.draw_debug_string
R["string_doc"] = str(getattr(fn, "__doc__", ""))[:500]
# Try common UE5 signatures: (world, loc, text, test_base_actor, color, duration)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
loc = unreal.Vector(1680, 500, 260)
color = unreal.LinearColor(0, 1, 1, 1)
# variants
variants = [
    ("w_loc_text_actor_color_dur", lambda: unreal.SystemLibrary.draw_debug_string(world, loc, "OPEN开业牌", None, color, 25.0)),
    ("w_loc_text_color_dur", lambda: unreal.SystemLibrary.draw_debug_string(world, loc, "OPEN开业牌", color, 25.0)),
    ("kwargs", lambda: unreal.SystemLibrary.draw_debug_string(world_context_object=world, text_location=loc, text="OPEN开业牌", test_base_actor=None, text_color=color, duration=25.0)),
]
for name, fnc in variants:
    try:
        fnc()
        R["string_sigs"].append({"name": name, "ok": True})
        break
    except Exception as e:
        R["string_sigs"].append({"name": name, "ok": False, "err": str(e)[:220]})

# Also draw spheres for all 5 so user can see NOW in editor viewport even without PIE
pts = [
    (1680,500,200, unreal.LinearColor(0,1,1,1), "OPEN"),
    (2080,700,180, unreal.LinearColor(1,0.5,0,1), "STOVE"),
    (1820,300,150, unreal.LinearColor(1,1,0,1), "T1"),
    (2080,300,150, unreal.LinearColor(0.4,1,0.2,1), "T2"),
    (1780,700,160, unreal.LinearColor(1,0,1,1), "TRASH"),
]
for x,y,z,c,n in pts:
    try:
        unreal.SystemLibrary.draw_debug_sphere(world, unreal.Vector(x,y,z), 35.0, 12, c, 60.0, 4.0)
        # try string kwargs style
        try:
            unreal.SystemLibrary.draw_debug_string(world_context_object=world, text_location=unreal.Vector(x,y,z+40), text=n, test_base_actor=None, text_color=c, duration=60.0)
        except Exception:
            pass
    except Exception as e:
        R["errors"].append(n+":"+str(e)[:100])
R["spheres_drawn"] = len(pts)

# Pin API
bel = unreal.BlueprintEditorLibrary
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
for n in ge.list_all_nodes():
    if "BeginPlay" in bel.get_node_title(n):
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "then":
                R["pin_api"] = [m for m in dir(p) if not m.startswith("_")]
                for meth in ("get_linked_to","linked_to","get_linked_pins","get_destination_pins","has_any_connections","break_all_pin_links","break_pin_links","try_create_connection"):
                    if hasattr(p, meth):
                        R.setdefault("pin_has", {})[meth] = True
                        try:
                            if meth in ("get_linked_to","get_linked_pins","get_destination_pins"):
                                R["pin_call_"+meth] = str(getattr(p, meth)())[:200]
                            elif meth == "linked_to":
                                R["pin_call_linked_to"] = str(getattr(p, meth))[:200]
                            elif meth == "has_any_connections":
                                R["pin_has_conn"] = p.has_any_connections()
                        except Exception as e:
                            R["pin_call_"+meth] = "ERR "+str(e)[:120]
                break
        break

open(r"E:\UE\FarmSim25D\Saved\restaurant_debuglabel_probe3.json","w",encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps(R, ensure_ascii=False, indent=2))
