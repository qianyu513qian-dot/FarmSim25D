# -*- coding: utf-8 -*-
"""Deep probe Manager BeginPlay/Tick links + test DrawDebugString CJK once in editor."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
R = {"beginplay": None, "tick": None, "customs": [], "draw_test": {}, "errors": []}

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

def pin_info(p):
    links = []
    try:
        for lp in p.get_linked_to():
            own = lp.get_owning_node()
            links.append({"to_title": bel.get_node_title(own), "to_pin": str(lp.get_pin_name()), "to_cls": own.get_class().get_name()})
    except Exception as e:
        links.append({"err": str(e)[:120]})
    dv = None
    try:
        dv = p.get_default_as_string()
    except Exception:
        try:
            dv = p.get_default_value()
        except Exception:
            pass
    return {"name": str(p.get_pin_name()), "dir": str(p.get_pin_direction()), "type": str(p.get_pin_type_display_string()), "default": dv, "links": links}

for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    c = n.get_class().get_name()
    if c == "K2Node_Event" and ("BeginPlay" in t or "Tick" in t):
        info = {"title": t, "cls": c, "pins": [pin_info(p) for p in bel.list_all_pins(n)]}
        if "BeginPlay" in t:
            R["beginplay"] = info
        if "Tick" in t:
            R["tick"] = info
    if c == "K2Node_CustomEvent":
        R["customs"].append(t)

# Also dump ALL nodes with any exec links
linked = []
for n in ge.list_all_nodes():
    for p in bel.list_all_pins(n):
        try:
            lt = p.get_linked_to()
        except Exception:
            lt = []
        if lt and ("exec" in str(p.get_pin_type_display_string()).lower() or str(p.get_pin_name()).lower() in ("then","execute","completed","loopbody","entry_point")):
            linked.append({"from": bel.get_node_title(n)+"."+str(p.get_pin_name()), "to": [bel.get_node_title(x.get_owning_node())+"."+str(x.get_pin_name()) for x in lt]})
R["exec_links_sample"] = linked[:60]
R["exec_links_count"] = len(linked)

# One-shot DrawDebugString CJK in editor world
world = None
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
except Exception:
    pass
try:
    if world is None:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
except Exception as e:
    R["errors"].append("world "+str(e))

if world:
    loc = unreal.Vector(1680, 500, 250)
    try:
        unreal.SystemLibrary.draw_debug_string(world, loc, "TEST开业牌 OPEN", unreal.LinearColor(0,1,1,1), 30.0)
        R["draw_test"]["string"] = "ok"
    except Exception as e:
        R["draw_test"]["string_err"] = str(e)
        # try KismetSystemLibrary
        try:
            unreal.KismetSystemLibrary.draw_debug_string(world, loc, "TEST开业牌 OPEN", unreal.LinearColor(0,1,1,1), 30.0)
            R["draw_test"]["string"] = "ok_kismet"
        except Exception as e2:
            R["draw_test"]["string_err2"] = str(e2)
    try:
        unreal.SystemLibrary.draw_debug_sphere(world, loc, 40.0, 12, unreal.LinearColor(0,1,1,1), 30.0, 3.0)
        R["draw_test"]["sphere"] = "ok"
    except Exception as e:
        R["draw_test"]["sphere_err"] = str(e)
        try:
            unreal.KismetSystemLibrary.draw_debug_sphere(world, loc, 40.0, 12, unreal.LinearColor(0,1,1,1), 30.0, 3.0)
            R["draw_test"]["sphere"] = "ok_kismet"
        except Exception as e2:
            R["draw_test"]["sphere_err2"] = str(e2)

# Material opacity probe - sample texture size
for key in ["OpenSign","Stove"]:
    path = "/Game/Farm/Restaurant/Labels/T_RestLabel_" + key
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        tex = unreal.EditorAssetLibrary.load_asset(path)
        info = {"path": path, "cls": tex.get_class().get_name()}
        for prop in ("size_x","size_y","imported_size_x","imported_size_y","compression_settings","lod_group","srgb"):
            try:
                info[prop] = str(tex.get_editor_property(prop))
            except Exception:
                pass
        R.setdefault("textures", {})[key] = info
    matp = "/Game/Farm/Restaurant/Labels/M_RestLabel_" + key
    if unreal.EditorAssetLibrary.does_asset_exist(matp):
        mat = unreal.EditorAssetLibrary.load_asset(matp)
        minfo = {"path": matp}
        for prop in ("blend_mode","shading_model","two_sided","opacity_mask_clip_value","material_domain"):
            try:
                minfo[prop] = str(mat.get_editor_property(prop))
            except Exception:
                pass
        # expressions?
        try:
            exprs = unreal.MaterialEditingLibrary.get_expressions(mat) if hasattr(unreal.MaterialEditingLibrary, "get_expressions") else []
            minfo["expr_count"] = len(exprs) if exprs else 0
        except Exception as e:
            minfo["expr_err"] = str(e)[:80]
        R.setdefault("materials", {})[key] = minfo

out = r"E:\UE\FarmSim25D\Saved\restaurant_debuglabel_probe2.json"
open(out,"w",encoding="utf-8").write(json.dumps(R, ensure_ascii=False, indent=2))
print(json.dumps({k:R[k] for k in ("beginplay","tick","customs","draw_test","exec_links_count","textures","materials","errors")}, ensure_ascii=False, indent=2))
print("exec_sample", json.dumps(R["exec_links_sample"][:15], ensure_ascii=False))
