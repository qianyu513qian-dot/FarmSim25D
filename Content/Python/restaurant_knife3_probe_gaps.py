# -*- coding: utf-8 -*-
import unreal, json
bel = unreal.BlueprintEditorLibrary

def find_pin(node, substr, direction=None):
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def pin_links(p):
    if not p: return -1
    try: return len(list(p.list_connected_pins()))
    except: return -1

def pin_val(p):
    if not p: return ""
    try: return str(p.get_pin_value())
    except: return ""

R = {}
for path, key in [
    ("/Game/Farm/Restaurant/BP_RestaurantStove", "stove"),
    ("/Game/Farm/Restaurant/BP_RestaurantManager", "manager"),
    ("/Game/Farm/Restaurant/BP_RestaurantTable", "table"),
]:
    bp = unreal.EditorAssetLibrary.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    info = {"customs": [], "dangling_then": [], "prints": [], "tick_notes": [], "status": str(bp.get_editor_property("status")), "errors": []}
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        c = n.get_class().get_name()
        try:
            em = n.get_editor_property("error_msg")
            if em and str(em).strip():
                info["errors"].append(t + ": " + str(em)[:180])
        except: pass
        if c == "K2Node_CustomEvent":
            info["customs"].append(t)
        if t == "Print String":
            info["prints"].append(pin_val(find_pin(n, "InString", "Input"))[:80])
        # dangling then on GetAll / Branch / Print / CustomEvent
        if c in ("K2Node_CallFunction", "K2Node_IfThenElse", "K2Node_CustomEvent", "K2Node_Event", "K2Node_MacroInstance"):
            then = find_pin(n, "then", "Output") or find_pin(n, "LoopBody", "Output") or find_pin(n, "else", "Output")
            # check multiple
            for pname in ("then", "else", "LoopBody", "Completed"):
                p = find_pin(n, pname, "Output")
                if p and pin_links(p) == 0:
                    # only report interesting
                    if "Get All" in t or c in ("K2Node_IfThenElse", "K2Node_CustomEvent") or "ForEach" in t or t == "Print String":
                        cls = ""
                        if "Get All" in t:
                            cls = pin_val(find_pin(n, "ActorClass", "Input") or find_pin(n, "Class", "Input"))[-40:]
                        info["dangling_then"].append({"title": t, "pin": pname, "y": int(bel.get_node_pos(n).y), "x": int(bel.get_node_pos(n).x), "cls": cls})
        if c == "K2Node_Event" and "Tick" in t:
            then = find_pin(n, "then", "Output")
            info["tick_notes"].append({"linked": pin_links(then)})
    # unique dangling limited
    info["dangling_then"] = info["dangling_then"][:40]
    info["customs"] = sorted(set(info["customs"]))
    R[key] = info

open(r"E:\UE\FarmSim25D\Saved\restaurant_knife3_gaps.json","w",encoding="utf-8").write(json.dumps(R, indent=2, ensure_ascii=False))
print(json.dumps(R, indent=2, ensure_ascii=False)[:12000])