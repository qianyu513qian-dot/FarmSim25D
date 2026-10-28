# -*- coding: utf-8 -*-
"""Fix empty DrawDebugString Text pins + verify MakeVector coords; append near Print without Branch."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
BP = "/Game/Farm/Restaurant/BP_RestDebugLabels"
R = {"steps": [], "errors": [], "fixed": []}
TEXTS = [
    (400, "OPEN \u5f00\u4e1a\u724c"),
    (540, "STOVE \u7076\u53f0"),
    (680, "T1 \u9910\u684c1"),
    (820, "T2 \u9910\u684c2"),
    (960, "TRASH \u5783\u573e\u6876"),
]
COORDS = [
    # y of sphere row -> (x,y,z) for center; string z+45
    (400, 1680.0, 500.0, 201.0),
    (540, 2080.0, 700.0, 173.0),
    (680, 1820.0, 300.0, 148.0),
    (820, 2080.0, 300.0, 148.0),
    (960, 1780.0, 700.0, 160.0),
]

def log(m):
    unreal.log("[REST_FIXTEXT] " + str(m)); R["steps"].append(str(m))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def setdef(pin, val):
    if not pin: return False
    for fn in ("set_pin_value",):
        try:
            getattr(pin, fn)(str(val))
            return True
        except Exception as e:
            R["errors"].append(str(e)[:80])
    try:
        pin.import_text(str(val)); return True
    except Exception:
        pass
    return False

def connect(a,b,label=""):
    if a is None or b is None: return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

def out_data(node):
    for name in ("ReturnValue","Return Value"):
        p=find_pin(node,name,"Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            if str(p.get_pin_name()).lower() not in ("outputdelegate","then","completed","loopbody"):
                return p
    return None

bp = unreal.EditorAssetLibrary.load_asset(BP)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))

# Map DrawDebugString by Y
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "DrawDebugString":
        continue
    np = bel.get_node_pos(n)
    text = None
    for ty, s in TEXTS:
        if abs(np.y - ty) < 20:
            text = s; break
    if not text:
        # fallback by order
        continue
    tp = find_pin(n, "Text", "Input")
    ok = setdef(tp, text)
    got = None
    try: got = tp.get_pin_value()
    except Exception: pass
    R["fixed"].append({"y": np.y, "set": ok, "got": got, "want": text})
    log("text y={} ok={} got={!r}".format(np.y, ok, got))

# Verify / fix MakeVector values linked to spheres at known Y
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "MakeVector":
        continue
    np = bel.get_node_pos(n)
    # sphere MakeVectors at row y; string ones at row+60
    for sy, x, y, z in COORDS:
        if abs(np.y - sy) < 15:
            setdef(find_pin(n,"X","Input"), "{:.1f}".format(x))
            setdef(find_pin(n,"Y","Input"), "{:.1f}".format(y))
            setdef(find_pin(n,"Z","Input"), "{:.1f}".format(z))
            R["fixed"].append({"mv_sphere": sy, "xyz": [x,y,z]})
        if abs(np.y - (sy+60)) < 15:
            setdef(find_pin(n,"X","Input"), "{:.1f}".format(x))
            setdef(find_pin(n,"Y","Input"), "{:.1f}".format(y))
            setdef(find_pin(n,"Z","Input"), "{:.1f}".format(z+45.0))
            R["fixed"].append({"mv_str": sy, "xyz": [x,y,z+45]})

# Also try setting Text via default_value property on pin
for n in ge.list_all_nodes():
    if bel.get_node_title(n) != "DrawDebugString":
        continue
    np = bel.get_node_pos(n)
    text=None
    for ty,s in TEXTS:
        if abs(np.y-ty)<20: text=s; break
    if not text: continue
    tp=find_pin(n,"Text","Input")
    if not tp: continue
    try:
        tp.set_editor_property("default_value", text)
    except Exception:
        pass
    # dump pin methods once
    if "pin_methods" not in R:
        R["pin_methods"]=[m for m in dir(tp) if "pin" in m.lower() or "value" in m.lower() or "text" in m.lower() or "default" in m.lower()]

# Near hint without Branch: always PrintString Key=RestHint with Chinese legend each tick (short duration) — noisy but OK for MVP
# Better: Print once-ish with Key. Append after last DrawDebugString then.
last=None
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="DrawDebugString":
        then=find_pin(n,"then","Output")
        if then and len(list(then.list_connected_pins()))==0:
            last=n
if last:
    # Get player location distance - without branch, print ALL names in one string with nearest
    # Simplest reliable Chinese: PrintString every tick Key=RestHintNear with legend
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, unreal.IntPoint(1200, 960))
    legend = "cyan=\u5f00\u4e1a\u724c orange=\u7076\u53f0 yellow=\u9910\u684c1 lime=\u9910\u684c2 magenta=\u5783\u573e\u6876 | cubes+OPEN/STOVE/T1/T2/TRASH"
    setdef(find_pin(pr,"InString","Input"), legend)
    setdef(find_pin(pr,"Key","Input"), "RestHint")
    setdef(find_pin(pr,"Duration","Input"), "0.0")
    # only show when near any prop - skip without branch; use screen message always is too noisy with Duration 0
    # Instead Duration 1 with Key means updates in place every tick - acceptable as HUD legend
    setdef(find_pin(pr,"Duration","Input"), "1.0")
    connect(find_pin(last,"then","Output"), find_pin(pr,"execute","Input"), "last->legend")
    R["legend"]=True

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(BP)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"]=True
except Exception:
    R["level_saved"]=False

# re-read texts
texts=[]
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="DrawDebugString":
        tp=find_pin(n,"Text","Input")
        try: v=tp.get_pin_value()
        except Exception: v=None
        texts.append({"y": bel.get_node_pos(n).y, "v": v})
R["texts_after"]=texts

# MakeVector check
mvs=[]
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="MakeVector":
        mvs.append({
            "y": bel.get_node_pos(n).y,
            "X": find_pin(n,"X","Input").get_pin_value() if find_pin(n,"X","Input") else None,
            "Y": find_pin(n,"Y","Input").get_pin_value() if find_pin(n,"Y","Input") else None,
            "Z": find_pin(n,"Z","Input").get_pin_value() if find_pin(n,"Z","Input") else None,
        })
R["mvs"]=mvs

open(r"E:\UE\FarmSim25D\Saved\restaurant_fixtext.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps({k:R[k] for k in ("fixed","texts_after","mvs","legend","level_saved","errors","pin_methods") if k in R}, ensure_ascii=False, indent=2))