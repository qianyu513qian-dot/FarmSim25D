# -*- coding: utf-8 -*-
"""Add near-distance Chinese PrintString (Key=RestHint) to BP_RestDebugLabels Tick chain end."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
BP = "/Game/Farm/Restaurant/BP_RestDebugLabels"
R = {"steps": [], "errors": []}
PROPS = [
    ("OpenSign", "\u5f00\u4e1a\u724c", "OPEN", 1680.0, 500.0, 201.0, (0.0, 1.0, 1.0)),
    ("Stove", "\u7076\u53f0", "STOVE", 2080.0, 700.0, 173.0, (1.0, 0.55, 0.1)),
    ("Table1", "\u9910\u684c1", "T1", 1820.0, 300.0, 148.0, (1.0, 1.0, 0.15)),
    ("Table2", "\u9910\u684c2", "T2", 2080.0, 300.0, 148.0, (0.35, 1.0, 0.2)),
    ("Trash", "\u5783\u573e\u6876", "TRASH", 1780.0, 700.0, 160.0, (1.0, 0.2, 1.0)),
]

def log(m):
    unreal.log("[REST_NEAR] " + str(m)); R["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x),int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a,b,label=""):
    if a is None or b is None: log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

def setdef(pin,val):
    if not pin: return False
    try: pin.set_pin_value(str(val)); return True
    except Exception:
        try: pin.set_default_value(str(val)); return True
        except Exception as e: log(str(e)[:60]); return False

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

# Find last DrawDebugString then pin in tick chain (Trash)
last_ds = None
for n in ge.list_all_nodes():
    if bel.get_node_title(n) == "DrawDebugString":
        # check text contains TRASH
        tp = find_pin(n, "Text", "Input")
        try:
            v = tp.get_pin_value() if tp else ""
        except Exception:
            v = ""
        if v and "TRASH" in str(v):
            last_ds = n
if not last_ds:
    # fallback: any DrawDebugString with no then links
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "DrawDebugString":
            then = find_pin(n, "then", "Output")
            if then and len(list(then.list_connected_pins())) == 0:
                last_ds = n
if not last_ds:
    R["errors"].append("no last DrawDebugString"); 
    open(r"E:\UE\FarmSim25D\Saved\restaurant_near_hint.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
    print(json.dumps(R,ensure_ascii=False,indent=2))
    raise SystemExit(0)

prev = find_pin(last_ds, "then", "Output")
BASE_Y = 1200

pawn = ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
bel.set_node_pos(pawn, pos(50, BASE_Y))
setdef(find_pin(pawn, "PlayerIndex", "Input"), "0")
getloc = ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
if getloc is None:
    getloc = ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
bel.set_node_pos(getloc, pos(50, BASE_Y+100))
connect(out_data(pawn), find_pin(getloc, "self", "Input"), "pawn->loc")
player_loc = out_data(getloc)

for i,(key,cn,eng,x,y,z,rgb) in enumerate(PROPS):
    row = BASE_Y + i*150
    mv = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    bel.set_node_pos(mv, pos(300, row))
    setdef(find_pin(mv,"X","Input"), "{:.1f}".format(x))
    setdef(find_pin(mv,"Y","Input"), "{:.1f}".format(y))
    setdef(find_pin(mv,"Z","Input"), "{:.1f}".format(z))
    dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance")
    if dist is None:
        dist = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Distance")
    bel.set_node_pos(dist, pos(550, row))
    p1 = find_pin(dist,"V1","Input") or find_pin(dist,"A","Input")
    p2 = find_pin(dist,"V2","Input") or find_pin(dist,"B","Input")
    connect(player_loc, p1, "pl"+key)
    connect(out_data(mv), p2, "pr"+key)
    le = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble")
    if le is None:
        le = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    bel.set_node_pos(le, pos(800, row))
    connect(out_data(dist), find_pin(le,"A","Input"), "dA"+key)
    setdef(find_pin(le,"B","Input"), "250.0")
    # Branch via IfThenElse
    try:
        br = ge.add_node(unreal.K2Node_IfThenElse.static_class(), unreal.Vector2D(1000, row))
    except Exception as e:
        R["errors"].append("branch "+str(e)[:80]); continue
    bel.set_node_pos(br, pos(1000, row))
    connect(prev, find_pin(br,"execute","Input"), "ex"+key)
    connect(out_data(le), find_pin(br,"Condition","Input"), "cond"+key)
    pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    bel.set_node_pos(pr, pos(1300, row))
    setdef(find_pin(pr,"InString","Input"), "\u3010{}\u3011 {}  E=\u4e92\u52a8".format(cn, eng))
    setdef(find_pin(pr,"Key","Input"), "RestHint")
    setdef(find_pin(pr,"Duration","Input"), "0.12")
    connect(find_pin(br,"then","Output"), find_pin(pr,"execute","Input"), "tpr"+key)
    # continue via else so chain always progresses
    prev = find_pin(br, "else", "Output")

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(BP)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"]=True
except Exception:
    R["level_saved"]=False
R["ok"]=True
open(r"E:\UE\FarmSim25D\Saved\restaurant_near_hint.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps(R,ensure_ascii=False,indent=2))