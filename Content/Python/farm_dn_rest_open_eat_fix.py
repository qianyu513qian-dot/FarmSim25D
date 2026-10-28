# -*- coding: utf-8 -*-
"""Fix missing string defaults on eating UI + verify gdm data links. OpenEatUI_v1b."""
import unreal, json
REPORT={"steps":[],"errors":[],"ok":[]}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary

def log(m):
    unreal.log("[OpenEatFix] "+str(m)); print("[OpenEatFix] "+str(m)); REPORT["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

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
    for fn in ("set_pin_value","set_default_value"):
        if hasattr(pin, fn):
            try:
                getattr(pin, fn)(str(val)); return True
            except Exception as e:
                log(fn+" fail "+str(e)[:60])
    return False

def pin_val(p):
    if not p: return None
    for fn in ("get_pin_value","get_default_as_string","get_default_value"):
        if hasattr(p,fn):
            try: return str(getattr(p,fn)())
            except: pass
    return None

def walk_then(start, max_d=80):
    thenp=find_pin(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else","Completed","LoopBody"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return seen

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok

# ---- Manager: verify GetDisplayMinutes linked ----
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tick=find_custom(mge,"RestaurantTick")
gdm=None; get0=None
for n in walk_then(tick,100):
    if title(n)=="Get":
        get0=n
    # pure nodes not in walk — search all nodes near gao
for n in mge.list_all_nodes():
    if "GetDisplayMinutes" in title(n):
        sp=find_pin(n,"self","Input")
        links=[title(c.get_owning_node()) for c in (sp.list_connected_pins() or [])] if sp else []
        if links:
            REPORT.setdefault("gdm_linked",[]).append(links)
            gdm=n
        else:
            REPORT.setdefault("gdm_unlinked",[]).append(True)

# Find Get (Array_Get) that is in tick chain after our GAO
for n in walk_then(tick,100):
    if title(n)=="Get" or title(n)=="Array_Get" or "Get" == title(n):
        # check if TargetArray from GetAllActorsOfClass with FarmClock
        pass

# Find the Array Get whose array comes from FarmClock GAO
for n in mge.list_all_nodes():
    if title(n) in ("Get","Array_Get") or n.get_class().get_name()=="K2Node_GetArrayItem":
        tp=find_pin(n,"TargetArray","Input") or find_pin(n,"Array","Input") or find_pin(n,"Target Array","Input")
        if not tp: continue
        srcs=[c.get_owning_node() for c in (tp.list_connected_pins() or [])]
        for s in srcs:
            if title(s)=="GetAllActorsOfClass":
                cp=find_pin(s,"ActorClass","Input")
                cv=pin_val(cp) or ""
                if "FarmClock" in cv:
                    item=find_pin(n,"Item","Output") or find_pin(n,"ReturnValue","Output")
                    # find GetDisplayMinutes with empty self and connect
                    for g in mge.list_all_nodes():
                        if "GetDisplayMinutes" not in title(g): continue
                        sp=find_pin(g,"self","Input")
                        if sp and not list(sp.list_connected_pins() or []):
                            connect(item, sp, "fix item->gdm")
                            REPORT["ok"].append("fixed_gdm_self")
                        elif sp and list(sp.list_connected_pins() or []):
                            REPORT["ok"].append("gdm_self_ok")
                            log("gdm self already "+title(list(sp.list_connected_pins())[0].get_owning_node()))

# Verify RestOpenHint text via get_pin_value
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    if pin_val(find_pin(n,"Key","Input"))=="RestOpenHint":
        REPORT["hint_text"]=pin_val(find_pin(n,"InString","Input"))
        log("hint text="+str(REPORT["hint_text"]))

# ---- Table: fix eating string defaults ----
tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))
rb=find_custom(tge,"RefreshTableBubble")
chain=walk_then(rb,40)

# Find eating DrawDebugString (green color)
for n in chain:
    if title(n)!="DrawDebugString": continue
    tc=pin_val(find_pin(n,"TextColor","Input")) or ""
    if "0.950000" in tc or "0.95" in tc:
        tp=find_pin(n,"Text","Input")
        log("dds_eat Text before="+str(pin_val(tp)))
        # Try multiple set methods + MakeLiteralString feed
        ok=setdef(tp, "用餐中")
        log("setdef Text ok="+str(ok)+" after="+str(pin_val(tp)))
        if not pin_val(tp) or pin_val(tp) in ("","Hello"):
            lit=tge.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralString")
            if lit:
                bel.set_node_pos(lit, unreal.IntPoint(1200, 40))
                vp=find_pin(lit,"Value","Input") or find_pin(lit,"InString","Input")
                setdef(vp, "用餐中")
                # also try set on Value
                try:
                    if vp: vp.set_pin_value("用餐中")
                except Exception: pass
                out=find_pin(lit,"ReturnValue","Output")
                if tp:
                    try: tp.break_pin_links()
                    except Exception: pass
                connect(out, tp, "lit->dds Text")
                log("lit Value after="+str(pin_val(vp)))
                REPORT["ok"].append("dds_text_literal")

# Fix Concat/Append defaults used by eating print (green PrintString Duration 0.15)
eat_print=None
for n in chain:
    if title(n)!="PrintString": continue
    if pin_val(find_pin(n,"Duration","Input"))=="0.15":
        eat_print=n; break

if eat_print:
    # Walk data back from InString and Key
    def walk_data(node, depth=8):
        out=[]; seen=set(); q=[(node,0)]
        while q:
            cur,d=q.pop(0)
            if id(cur) in seen or d>depth: continue
            seen.add(id(cur)); out.append(cur)
            for p in bel.list_all_pins(cur):
                if "INPUT" not in str(p.get_pin_direction()): continue
                for c in p.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
        return out
    nodes=walk_data(eat_print, 10)
    REPORT["eat_data"]=[title(n) for n in nodes]
    for n in nodes:
        t=title(n)
        if t in ("Append",) or "Concat" in t:
            pins_info={}
            for p in bel.list_all_pins(n):
                pins_info[str(p.get_pin_name())]={"val":pin_val(p),"links":[title(c.get_owning_node()) for c in (p.list_connected_pins() or [])]}
            log("concat "+t+" "+str(pins_info))
            # Determine role by what ReturnValue connects to
            rv=find_pin(n,"ReturnValue","Output")
            targets=[]
            if rv:
                for c in rv.list_connected_pins() or []:
                    targets.append(title(c.get_owning_node())+"."+str(c.get_pin_name()))
            A=find_pin(n,"A","Input"); B=find_pin(n,"B","Input")
            # Key builder: RestOrder + id  (Return goes to String To Name)
            if any("String To Name" in x or "Conv_StringToName" in x or "To Name" in x for x in targets):
                setdef(A, "RestOrder"); log("set RestOrder -> "+str(pin_val(A)))
            # 桌 + id
            elif pin_val(A) in ("","Hello",None) and not list((A.list_connected_pins() if A else []) or []):
                # if A has no links, it's a literal side
                # Heuristic: if B linked to To String (Integer) and A empty -> could be RestOrder or 桌
                B_links=[title(c.get_owning_node()) for c in (B.list_connected_pins() or [])] if B else []
                if any("To String" in x or "Conv_Int" in x for x in B_links):
                    # distinguish by whether Return goes to another Append.A (桌) or to StringToName (RestOrder)
                    if any(".A" in x and ("Append" in x or "Concat" in x) for x in targets):
                        setdef(A, "桌"); log("set 桌 -> "+str(pin_val(A)))
                    else:
                        setdef(A, "RestOrder"); log("set RestOrder2 -> "+str(pin_val(A)))
            # id +  用餐中  (A linked from Append, B literal)
            if B and not list(B.list_connected_pins() or []):
                if pin_val(B) in ("","Hello",None):
                    # if A linked from Append/Concat, this is the suffix
                    A_links=[title(c.get_owning_node()) for c in (A.list_connected_pins() or [])] if A else []
                    if any("Append" in x or "Concat" in x for x in A_links):
                        setdef(B, " 用餐中"); log("set 用餐中 -> "+str(pin_val(B)))
                    elif not A_links and pin_val(A)=="RestOrder":
                        pass  # B should be id from ToString — should be linked
                    elif not A_links and pin_val(A)=="桌":
                        pass

bel.compile_blueprint(mbp); eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
bel.compile_blueprint(tbp); eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantTable")

# Re-read eating strings
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")))
rb=find_custom(tge,"RefreshTableBubble")
final=[]
for n in walk_then(rb,40):
    if title(n)=="DrawDebugString":
        final.append({"dds":pin_val(find_pin(n,"Text","Input")),"color":pin_val(find_pin(n,"TextColor","Input"))})
    if title(n) in ("Append",) or "Concat" in title(n):
        final.append({"concat":title(n),"A":pin_val(find_pin(n,"A","Input")),"B":pin_val(find_pin(n,"B","Input")),
                      "A_links":[title(c.get_owning_node()) for c in ((find_pin(n,"A","Input").list_connected_pins() or []) if find_pin(n,"A","Input") else [])],
                      "B_links":[title(c.get_owning_node()) for c in ((find_pin(n,"B","Input").list_connected_pins() or []) if find_pin(n,"B","Input") else [])],
                      "rv_to":[title(c.get_owning_node()) for c in ((find_pin(n,"ReturnValue","Output").list_connected_pins() or []) if find_pin(n,"ReturnValue","Output") else [])]})
REPORT["final"]=final
try:
    REPORT["tbl_errs"]=[title(n) for n in (tge.list_nodes_with_errors() or [])]
    REPORT["mgr_errs"]=[title(n) for n in (unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager"))).list_nodes_with_errors() or [])]
except Exception as e:
    REPORT["err"]=str(e)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_open_eat_fix.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps({"ok":REPORT.get("ok"),"hint":REPORT.get("hint_text"),"final":final,"errs":REPORT.get("tbl_errs")},ensure_ascii=False)[:4000])
