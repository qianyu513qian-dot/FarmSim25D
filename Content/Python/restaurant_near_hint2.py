# -*- coding: utf-8 -*-
"""Near Chinese hint via Branch create_node_from_name on BP_RestDebugLabels."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
BP = "/Game/Farm/Restaurant/BP_RestDebugLabels"
R = {"steps": [], "errors": []}
PROPS = [
    ("OpenSign", "\u5f00\u4e1a\u724c", "OPEN", 1680.0, 500.0, 201.0),
    ("Stove", "\u7076\u53f0", "STOVE", 2080.0, 700.0, 173.0),
    ("Table1", "\u9910\u684c1", "T1", 1820.0, 300.0, 148.0),
    ("Table2", "\u9910\u684c2", "T2", 2080.0, 300.0, 148.0),
    ("Trash", "\u5783\u573e\u6876", "TRASH", 1780.0, 700.0, 160.0),
]

def log(m):
    unreal.log("[REST_NEAR2] " + str(m)); R["steps"].append(str(m))

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
        except Exception: return False

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

# Purge prior near-hint orphans at y>=1100 (GetPlayerPawn / Distance / LessEqual / MakeVector extras)
kill=[]
for n in ge.list_all_nodes():
    t=bel.get_node_title(n)
    try:
        np=bel.get_node_pos(n)
    except Exception:
        np=None
    if np and np.y >= 1100:
        if t in ("GetPlayerPawn","Get Actor Location","K2_GetActorLocation","GetActorLocation","Vector_Distance","Distance","Less Equal","LessEqual","MakeVector","PrintString","Branch"):
            kill.append(n)
if kill:
    for n in kill:
        for p in bel.list_all_pins(n):
            try: p.break_pin_links()
            except Exception: pass
    ge.remove_nodes(kill)
    log("purged orphans {}".format(len(kill)))

# Find last DrawDebugString with TRASH or dangling then
last_ds=None
for n in ge.list_all_nodes():
    if bel.get_node_title(n)!="DrawDebugString": continue
    tp=find_pin(n,"Text","Input")
    try: v=tp.get_pin_value() if tp else ""
    except Exception: v=""
    if v and "TRASH" in str(v):
        last_ds=n; break
if not last_ds:
    R["errors"].append("no TRASH DrawDebugString")
else:
    prev=find_pin(last_ds,"then","Output")
    BASE_Y=1300
    pawn=ge.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerPawn")
    bel.set_node_pos(pawn, pos(40, BASE_Y))
    setdef(find_pin(pawn,"PlayerIndex","Input"),"0")
    getloc=ge.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
    if getloc is None:
        getloc=ge.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
    bel.set_node_pos(getloc, pos(40, BASE_Y+90))
    connect(out_data(pawn), find_pin(getloc,"self","Input"), "pawn->loc")
    player_loc=out_data(getloc)

    for i,(key,cn,eng,x,y,z) in enumerate(PROPS):
        row=BASE_Y + i*160
        mv=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
        bel.set_node_pos(mv, pos(280, row))
        setdef(find_pin(mv,"X","Input"),"{:.1f}".format(x))
        setdef(find_pin(mv,"Y","Input"),"{:.1f}".format(y))
        setdef(find_pin(mv,"Z","Input"),"{:.1f}".format(z))
        dist=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Vector_Distance")
        if dist is None:
            dist=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:Distance")
        bel.set_node_pos(dist, pos(520, row))
        p1=find_pin(dist,"V1","Input") or find_pin(dist,"A","Input")
        p2=find_pin(dist,"V2","Input") or find_pin(dist,"B","Input")
        connect(player_loc,p1,"pl"+key)
        connect(out_data(mv),p2,"pr"+key)
        le=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble")
        if le is None:
            le=ge.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
        bel.set_node_pos(le, pos(760, row))
        connect(out_data(dist), find_pin(le,"A","Input"), "dA"+key)
        setdef(find_pin(le,"B","Input"),"250.0")

        br=None
        for name in ("Flow Control|Branch","Branch"):
            try:
                br=ge.create_node_from_name(name, unreal.Vector2D(1000, row), [])
                if br: break
            except Exception as e:
                log("br try "+name+" "+str(e)[:50])
        if not br:
            R["errors"].append("no branch "+key); continue
        bel.set_node_pos(br, pos(1000, row))
        connect(prev, find_pin(br,"execute","Input"), "ex"+key)
        connect(out_data(le), find_pin(br,"Condition","Input"), "cond"+key)
        prn=ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(prn, pos(1300, row))
        setdef(find_pin(prn,"InString","Input"), "\u3010{}\u3011 {}  E=\u4e92\u52a8".format(cn, eng))
        setdef(find_pin(prn,"Key","Input"), "RestHint")
        setdef(find_pin(prn,"Duration","Input"), "0.12")
        true_pin = find_pin(br,"then","Output") or find_pin(br,"True","Output")
        connect(true_pin, find_pin(prn,"execute","Input"), "tpr"+key)
        prev = find_pin(br,"else","Output") or find_pin(br,"False","Output")

bel.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(BP)
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    R["level_saved"]=True
except Exception:
    R["level_saved"]=False
open(r"E:\UE\FarmSim25D\Saved\restaurant_near_hint2.json","w",encoding="utf-8").write(json.dumps(R,ensure_ascii=False,indent=2))
print(json.dumps(R,ensure_ascii=False,indent=2))