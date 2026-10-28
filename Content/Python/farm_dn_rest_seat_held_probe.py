# -*- coding: utf-8 -*-
"""Probe RestChair actors + SpawnGuestVisual spawn transform pins."""
import unreal, json
REPORT = {}
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
bel = unreal.BlueprintEditorLibrary
actors = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        actors.append({
            "label": lab,
            "class": a.get_class().get_name(),
            "loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)],
            "yaw": round(rot.yaw,1),
            "scale": [round(a.get_actor_scale3d().x,4), round(a.get_actor_scale3d().y,4), round(a.get_actor_scale3d().z,4)],
        })
REPORT["actors"] = sorted(actors, key=lambda x: x["label"])

# Dump SpawnGuestVisual graph nodes of interest
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def pin_def(p):
    if not p: return None
    for fn in ("get_default_as_string", "get_default_value", "get_pin_value"):
        if hasattr(p, fn):
            try: return str(getattr(p, fn)())
            except Exception: pass
    return None

spawn = find_custom(tge, "SpawnGuestVisual")
nodes = []
if spawn:
    thenp = find_pin(spawn, "then", "Output")
    q = [c.get_owning_node() for c in (thenp.list_connected_pins() if thenp else [])]
    seen=set()
    while q:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        info={"title": title(cur), "class": cur.get_class().get_name(), "defs": {}}
        for p in bel.list_all_pins(cur):
            pn=str(p.get_pin_name())
            if "INPUT" in str(p.get_pin_direction()):
                d=pin_def(p)
                if d and d not in ("", "None", "DefaultValue"):
                    info["defs"][pn]=d[:80]
        nodes.append(info)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
REPORT["spawn_chain"]=nodes

# Guest BP mesh offset
GUEST="/Game/Farm/Restaurant/BP_RestGuest"
gbp=unreal.load_asset(GUEST)
sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib=unreal.SubobjectDataBlueprintFunctionLibrary
ginfo=[]
for h in list(sub.k2_gather_subobject_data_for_blueprint(gbp) or []):
    data=sub.k2_find_subobject_data_from_handle(h)
    try:
        name=str(lib.get_variable_name(data) or "")
        obj=lib.get_associated_object(data) if hasattr(lib,"get_associated_object") else lib.get_object(data)
        entry={"name":name,"class": obj.get_class().get_name() if obj else None}
        if obj and hasattr(obj, "get_editor_property"):
            try: entry["rel"]=str(obj.get_editor_property("relative_location"))
            except Exception: pass
            try: entry["rel_rot"]=str(obj.get_editor_property("relative_rotation"))
            except Exception: pass
        ginfo.append(entry)
    except Exception as e:
        ginfo.append({"err":str(e)})
REPORT["guest_subs"]=ginfo

# Manager vars related to held
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
mbp=unreal.load_asset(MGR)
REPORT["mgr_vars"]=[str(n) for n in bel.list_member_variable_names(mbp, False)]
REPORT["table_vars"]=[str(n) for n in bel.list_member_variable_names(tbp, False)]

# VMF small props
props=[]
for p in unreal.EditorAssetLibrary.list_assets("/Game/Farm/VoxelMicroFarm/Models/Props", recursive=True) or []:
    pl=p.lower()
    if any(k in pl for k in ("crate","bowl","plate","bucket","basket","pot","mug","cup","food","apple","tomato")):
        props.append(p.split(".")[0])
REPORT["vmf_props"]=props[:40]

out=unreal.Paths.project_saved_dir()+"rest_seat_held_probe.json"
open(out,"w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(out)
print(json.dumps({k:REPORT[k] if k!='spawn_chain' else REPORT[k][:15] for k in REPORT}, ensure_ascii=False)[:6000])
