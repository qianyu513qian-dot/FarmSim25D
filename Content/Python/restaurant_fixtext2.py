# -*- coding: utf-8 -*-
"""Exact-match Text pin fix for DrawDebugString; restore TextLocation MakeVector links."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
BP = "/Game/Farm/Restaurant/BP_RestDebugLabels"
R = {"steps": [], "fixed": [], "errors": []}
TEXTS_BY_Y = {
    400: "OPEN \u5f00\u4e1a\u724c",
    540: "STOVE \u7076\u53f0",
    680: "T1 \u9910\u684c1",
    820: "T2 \u9910\u684c2",
    960: "TRASH \u5783\u573e\u6876",
}
COORDS = {
    400: (1680.0, 500.0, 201.0),
    540: (2080.0, 700.0, 173.0),
    680: (1820.0, 300.0, 148.0),
    820: (2080.0, 300.0, 148.0),
    960: (1780.0, 700.0, 160.0),
}

def log(m):
    unreal.log("[REST_FIXTEXT2] " + str(m)); R["steps"].append(str(m))

def exact_pin(node, name, direction=None):
    name = name.lower()
    for p in bel.list_all_pins(node):
        if str(p.get_pin_name()).lower() == name:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def out_data(node):
    p = exact_pin(node, "ReturnValue", "Output")
    if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate","then","completed","loopbody"):
                return p
    return None

bp = unreal.EditorAssetLibrary.load_asset(BP)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Index MakeVectors by Y
mvs = {}
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "MakeVector":
        mvs[bel.get_node_pos(n).y] = n

for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "DrawDebugString":
        continue
    y = bel.get_node_pos(n).y
    text = None
    for ty, s in TEXTS_BY_Y.items():
        if abs(y - ty) < 20:
            text = s; break
    if not text:
        continue
    tp = exact_pin(n, "Text", "Input")
    if not tp:
        R["errors"].append("no Text pin at y="+str(y)); continue
    # list exact pin names once
    if "pin_names" not in R:
        R["pin_names"] = [str(p.get_pin_name()) for p in bel.list_all_pins(n)]
    tp.set_pin_value(text)
    got = tp.get_pin_value()
    R["fixed"].append({"y": y, "got": got, "want": text, "ok": got == text or (got and text.split()[0] in got)})
    log("Text y={} got={!r}".format(y, got))

    # Restore TextLocation connection to MakeVector at y+60
    tloc = exact_pin(n, "TextLocation", "Input")
    if tloc:
        try:
            tloc.break_pin_links()
        except Exception:
            pass
        mv = None
        for my, mn in mvs.items():
            if abs(my - (y + 60)) < 15:
                mv = mn; break
        if mv:
            ok = out_data(mv).try_create_connection(tloc)
            log("relink TextLocation y={} {}".format(y, ok))
        else:
            # set vector default from coords
            base = None
            for ty, c in COORDS.items():
                if abs(y - ty) < 20:
                    base = c; break
            if base:
                tloc.set_pin_value("{}, {}, {}".format(base[0], base[1], base[2]+45))
                log("TextLocation literal y={}".format(y))

# Also ensure DrawDebugSphere Center still linked
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "DrawDebugSphere":
        continue
    y = bel.get_node_pos(n).y
    center = exact_pin(n, "Center", "Input")
    if not center: continue
    links = list(center.list_connected_pins())
    if links:
        continue
    mv = mvs.get(y) or None
    if not mv:
        for my, mn in mvs.items():
            if abs(my - y) < 15:
                mv = mn; break
    if mv:
        ok = out_data(mv).try_create_connection(center)
        log("relink Center y={} {}".format(y, ok))

# Fix legend PrintString InString (exact)
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "PrintString":
        continue
    keyp = exact_pin(n, "Key", "Input")
    try:
        kv = keyp.get_pin_value() if keyp else ""
    except Exception:
        kv = ""
    if kv == "RestHint":
        insp = exact_pin(n, "InString", "Input")
        legend = "cyan=\u5f00\u4e1a\u724c orange=\u7076\u53f0 yellow=\u9910\u684c1 lime=\u9910\u684c2 magenta=\u5783\u573e\u6876 | OPEN/STOVE/T1/T2/TRASH"
        insp.set_pin_value(legend)
        R["legend_set"] = insp.get_pin_value()
    if kv == "RestLabelsBoot":
        insp = exact_pin(n, "InString", "Input")
        # leave as is / reaffirm
        pass

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(BP)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"] = True
except Exception:
    R["level_saved"] = False

# verify
ver=[]
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="DrawDebugString":
        tp=exact_pin(n,"Text","Input")
        tloc=exact_pin(n,"TextLocation","Input")
        ver.append({
            "y": bel.get_node_pos(n).y,
            "text": tp.get_pin_value() if tp else None,
            "tloc_links": [bel.get_node_title(c.get_owning_node()) for c in tloc.list_connected_pins()] if tloc else [],
        })
R["verify"]=ver
open(r"E:\UE\FarmSim25D\Saved\restaurant_fixtext2.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps(R, ensure_ascii=False, indent=2))