# -*- coding: utf-8 -*-
"""Fix DrawDebugString Text pin exactly (not TextLocation). OpenEatUI_v1c."""
import unreal, json
REPORT={"steps":[],"ok":[],"errors":[]}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

def log(m):
    unreal.log("[OpenEatFix2] "+str(m)); print("[OpenEatFix2] "+str(m)); REPORT["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def exact_pin(node, name, direction=None):
    if not node: return None
    name_l=name.lower()
    for p in bel.list_all_pins(node):
        if str(p.get_pin_name()).lower()==name_l:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def find_pin_substr(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def pin_val(p):
    if not p: return None
    for fn in ("get_pin_value","get_default_as_string","get_default_value"):
        if hasattr(p,fn):
            try: return str(getattr(p,fn)())
            except: pass
    return None

def setdef(pin, val):
    if not pin: return False
    for fn in ("set_pin_value","set_default_value"):
        if hasattr(pin,fn):
            try:
                getattr(pin,fn)(str(val)); return True
            except Exception as e:
                log(fn+" "+str(e)[:60])
    return False

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); REPORT["errors"].append("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok))
    if not ok: REPORT["errors"].append("fail "+label)
    return ok

def walk_then(start, max_d=80):
    thenp=exact_pin(start,"then","Output") or find_pin_substr(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=exact_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return seen

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
rb=find_custom(tge,"RefreshTableBubble")
chain=walk_then(rb,40)

target=None
for n in chain:
    if title(n)!="DrawDebugString": continue
    tc=pin_val(exact_pin(n,"TextColor","Input")) or ""
    if "0.95" in tc or "0.950000" in tc:
        target=n; break

if not target:
    REPORT["errors"].append("no green dds")
else:
    text_pin=exact_pin(target,"Text","Input")
    loc_pin=exact_pin(target,"TextLocation","Input")
    log("Text pin="+str(text_pin)+" val="+str(pin_val(text_pin)))
    log("Loc pin val="+str(pin_val(loc_pin))+" links="+str([title(c.get_owning_node()) for c in (loc_pin.list_connected_pins() or [])] if loc_pin else []))

    # Break any wrong links on Text
    if text_pin:
        try: text_pin.break_pin_links()
        except Exception: pass
        ok=setdef(text_pin, "用餐中")
        log("setdef exact Text ok={} val={}".format(ok, pin_val(text_pin)))

    # If still empty/wrong, feed MakeLiteralString
    cur=pin_val(text_pin) or ""
    if "用餐" not in cur:
        lit=tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralString")
        bel.set_node_pos(lit, unreal.IntPoint(1250, -40))
        vp=exact_pin(lit,"Value","Input")
        setdef(vp, "用餐中")
        log("lit Value="+str(pin_val(vp)))
        # dump lit pins
        for p in bel.list_all_pins(lit):
            log("litpin {} type={} val={}".format(p.get_pin_name(), p.get_pin_type_display_string(), pin_val(p)))
        out=exact_pin(lit,"ReturnValue","Output")
        connect(out, text_pin, "lit->Text")
        REPORT["ok"].append("literal_text")
    else:
        REPORT["ok"].append("text_default_ok")

    # Ensure TextLocation still linked to vector+vector (don't break)
    if loc_pin and not list(loc_pin.list_connected_pins() or []):
        # re-link from original white DDS
        for n in chain:
            if title(n)!="DrawDebugString" or n is target: continue
            old_loc=exact_pin(n,"TextLocation","Input")
            for c in (old_loc.list_connected_pins() or []) if old_loc else []:
                connect(c, loc_pin, "restore loc")
                break

bel.compile_blueprint(tbp)
eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")

# verify
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")))
rb=find_custom(tge,"RefreshTableBubble")
ver=[]
for n in walk_then(rb,40):
    if title(n)=="DrawDebugString":
        ver.append({
            "Text": pin_val(exact_pin(n,"Text","Input")),
            "Text_links":[title(c.get_owning_node()) for c in ((exact_pin(n,"Text","Input").list_connected_pins() or []) if exact_pin(n,"Text","Input") else [])],
            "Color": pin_val(exact_pin(n,"TextColor","Input")),
            "Loc_links":[title(c.get_owning_node()) for c in ((exact_pin(n,"TextLocation","Input").list_connected_pins() or []) if exact_pin(n,"TextLocation","Input") else [])],
        })
REPORT["verify"]=ver
try:
    REPORT["errs"]=[title(n) for n in (tge.list_nodes_with_errors() or [])]
except Exception:
    REPORT["errs"]=[]

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_open_eat_fix2.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:3500])
