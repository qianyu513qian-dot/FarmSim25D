# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
bp = unreal.load_asset("/Game/Farm/Grid/BP_GridManager")

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    want = name_substr.lower().replace(" ", "")
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name()).lower().replace(" ", "")
        if want in pn:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

# Yaw
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "ApplyDayNightVisuals"))
for n in ge.list_all_nodes():
    if title(n) == "MakeRotator":
        yp = find_pin(n, "Yaw", "Input")
        cps = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in yp.list_connected_pins()]
        print("[FINAL] MakeRotator.Yaw <-", cps)
        unreal.log("[FINAL] MakeRotator.Yaw <- " + str(cps))
    if "*" in title(n):
        b = find_pin(n, "B", "Input")
        a = find_pin(n, "A", "Input")
        try: bv = b.get_pin_value() if b else None
        except: bv = None
        ac = [(title(c.get_owning_node()), str(c.get_pin_name())) for c in (a.list_connected_pins() if a else [])]
        if bv and "360" in str(bv):
            print("[FINAL] yaw mul A<-", ac, "B=", bv)
            unreal.log("[FINAL] yaw mul A<-{} B={}".format(ac, bv))
    if "MapRangeClamped" in title(n):
        oa = find_pin(n, "OutRangeA", "Input")
        ob = find_pin(n, "OutRangeB", "Input")
        try:
            oav = oa.get_pin_value() if oa else None
            obv = ob.get_pin_value() if ob else None
        except:
            oav = obv = None
        if str(oav) in ("35.0","35") or str(obv) in ("185.0","185"):
            print("[FINAL] WARN leftover arc", oav, obv)
            unreal.log("[FINAL] WARN leftover arc")

# AdvanceDayGrowth
ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "AdvanceDayGrowth"))
print("[FINAL] AdvanceDayGrowth nodes=", [title(n) for n in ge2.list_all_nodes()])
unreal.log("[FINAL] AdvanceDayGrowth nodes=" + str([title(n) for n in ge2.list_all_nodes()]))
for n in ge2.list_all_nodes():
    if "equal" in title(n).lower():
        print("[FINAL] Adv Equal.B=", find_pin(n, "B", "Input").get_pin_value())
        unreal.log("[FINAL] Adv Equal.B=" + str(find_pin(n, "B", "Input").get_pin_value()))
    if "Set Array" in title(n):
        print("[FINAL] Adv Set.Item=", find_pin(n, "Item", "Input").get_pin_value())
        unreal.log("[FINAL] Adv Set.Item=" + str(find_pin(n, "Item", "Input").get_pin_value()))
    if title(n) == "VisualizeCell":
        print("[FINAL] Adv Viz.State=", find_pin(n, "State", "Input").get_pin_value())
        unreal.log("[FINAL] Adv Viz.State=" + str(find_pin(n, "State", "Input").get_pin_value()))

# GrowCell
ge3 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge3.list_all_nodes():
    if "equal" in title(n).lower():
        print("[FINAL] Grow Equal.B=", find_pin(n, "B", "Input").get_pin_value())
        unreal.log("[FINAL] Grow Equal.B=" + str(find_pin(n, "B", "Input").get_pin_value()))
print("[FINAL] errors Adv=", len(ge2.list_nodes_with_errors()), "Grow=", len(ge3.list_nodes_with_errors()), "DN=", len(ge.list_nodes_with_errors()))
unreal.log("[FINAL] errors ok")
