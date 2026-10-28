# -*- coding: utf-8 -*-
"""Make TxtLine1/2 Blueprint variables; refresh OrderListWidget gets; compile clean."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
WBP="/Game/Farm/UI/WBP_RestOrderList"
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
TBL="/Game/Farm/Restaurant/BP_RestaurantTable"
REPORT={"steps":[]}

def log(m):
    unreal.log("[UMGFIX2] "+str(m)); print("[UMGFIX2] "+str(m)); REPORT["steps"].append(str(m))

def pos(x,y): return unreal.IntPoint(int(x),int(y))
def title(n):
    try: return str(bel.get_node_title(n))
    except: return "?"
def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None
def out_data(node):
    if not node: return None
    for name in ("ReturnValue","TxtTitle","TxtLine1","TxtLine2","OrderListWidget","OrderLine1","OrderLine2","Line1","Line2"):
        p=find_pin(node,name,"Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "exec" not in str(p.get_pin_type_display_string()).lower():
            n=str(p.get_pin_name()).lower()
            if n not in ("outputdelegate","then","else","completed","loopbody","castfailed"):
                return p
    return None
def connect(a,b,label=""):
    if a is None or b is None: log("skip "+label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok)); return ok
def setdef(pin,val):
    if not pin: return False
    try: pin.set_pin_value(str(val)); return True
    except:
        try: pin.set_default_value(str(val)); return True
        except Exception as e: log("setdef "+str(e)[:80]); return False
def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name: return n
    return None
def status_of(bp):
    try: return str(bp.get_editor_property("status"))
    except Exception as e: return str(e)

wbp=unreal.load_asset(WBP)
widgets={}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()]=o
        # Try bIsVariable
        for prop in ("is_variable","b_is_variable","IsVariable"):
            try:
                o.set_editor_property(prop, True)
                log("set {} True on {}".format(prop, o.get_name()))
            except Exception:
                pass

# Also via WidgetBlueprintLibrary / editor
try:
    # UE5: WidgetBlueprintEditorUtils
    log("widget names="+str(sorted(widgets.keys())))
except Exception:
    pass

# Inspect property names on TextBlock
tb=widgets.get("TxtLine1")
if tb:
    props=[p for p in dir(tb) if "var" in p.lower() or "Variable" in p]
    log("tb dir var="+str(props[:40]))
    # export text?
    try:
        log("export="+tb.export_text()[:300])
    except Exception as e:
        log("export "+str(e)[:80])

# Try SubobjectData / BlueprintEditorLibrary mark as variable
# Common approach in UE Python: widget.bIsVariable via set_editor_property('bIsVariable')
for name in ("TxtTitle","TxtLine1","TxtLine2"):
    w=widgets.get(name)
    if not w: continue
    for prop,val in (("bIsVariable",True),("is_variable",True)):
        try:
            w.set_editor_property(prop, val)
            log("OK {} {}={}".format(name,prop,val))
        except Exception as e:
            log("{} {} fail {}".format(name,prop,str(e)[:60]))

bel.compile_blueprint(wbp)
log("compile after bIsVariable="+status_of(wbp))

# List member vars on WBP
try:
    names=[str(n) for n in bel.list_member_variable_names(wbp, False)]
    log("wbp vars="+str(names))
except Exception as e:
    log("vars "+str(e))

# Rebuild UpdateOrders after variables exist
try:
    if bel.find_graph(wbp,"UpdateOrders"):
        bel.remove_function_graph(wbp,"UpdateOrders")
except Exception:
    pass
bel.compile_blueprint(wbp)
bel.add_function_graph(wbp,"UpdateOrders")
uge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(wbp,"UpdateOrders"))
entry=None
for n in list(uge.list_all_nodes()):
    if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n
    else: pass
# clear non-entry
to_del=[n for n in uge.list_all_nodes() if n.get_class().get_name()!="K2Node_FunctionEntry"]
if to_del: uge.remove_nodes(to_del)
for n in uge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n
str_pin=bel.get_basic_type_by_name("string")
if find_pin(entry,"Line1","Output") is None: uge.add_graph_input_parameter("Line1", str_pin)
if find_pin(entry,"Line2","Output") is None: uge.add_graph_input_parameter("Line2", str_pin)
for n in uge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n
bel.set_node_pos(entry,pos(0,0))

gets={}
for name,y in (("TxtTitle",-60),("TxtLine1",80),("TxtLine2",220)):
    g=uge.add_get_member_variable_node(name)
    bel.set_node_pos(g,pos(250,y))
    pins=[(str(p.get_pin_name()),str(p.get_pin_type_display_string())) for p in bel.list_all_pins(g)]
    log("get {} pins={}".format(name,pins))
    gets[name]=g

# If TxtLine1 still empty pins, use GetWidgetFromName instead inside UpdateOrders (self UserWidget)
if not bel.list_all_pins(gets["TxtLine1"]):
    log("FALLBACK GetWidgetFromName path")
    # Remove broken gets
    uge.remove_nodes([gets["TxtLine1"], gets["TxtLine2"]])
    # GetWidgetFromName on self
    # Actually on UserWidget function graph, Self is available via Self node
    selfn = None
    # add Self reference - often K2Node_Self via create?
    # Use call GetWidgetFromName with name TxtLine1
    # Path might be WidgetBlueprintLibrary
    for path in (
        "/Script/UMG.UserWidget:GetWidgetFromName",
        "/Script/UMG.WidgetBlueprintLibrary:GetWidgetFromName",
    ):
        n=uge.add_call_function_node(path)
        log("try {} -> {}".format(path,n))
        if n:
            for p in bel.list_all_pins(n):
                log("  pin {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
            uge.remove_nodes([n])

# Alternative: rename TxtSeeds -> already variable, use those as lines!
# TxtSeeds and TxtHarvest are original FarmHUD variables and Get works.
# Map: use TxtSeeds as Line1 display, TxtHarvest as Line2, TxtTitle as title.
# Uncollapse them and hide TxtLine1/2 visual duplicates OR set text on TxtSeeds/Harvest.

# Check Get TxtSeeds
gs=uge.add_get_member_variable_node("TxtSeeds")
gh=uge.add_get_member_variable_node("TxtHarvest")
log("TxtSeeds pins="+str([(str(p.get_pin_name()),str(p.get_pin_type_display_string())) for p in bel.list_all_pins(gs)]))
log("TxtHarvest pins="+str([(str(p.get_pin_name()),str(p.get_pin_type_display_string())) for p in bel.list_all_pins(gh)]))

# Strategy: UpdateOrders sets TxtTitle, TxtSeeds (as line1), TxtHarvest (as line2)
# Show those widgets, hide TxtLine1/2 if present
for name in ("TxtSeeds","TxtHarvest","TxtTitle"):
    w=widgets.get(name)
    if w:
        try: w.set_editor_property("visibility", unreal.SlateVisibility.VISIBLE)
        except Exception: pass
for name in ("TxtLine1","TxtOrder1","TxtLine2","TxtOrder2"):
    w=widgets.get(name)
    if w:
        try: w.set_editor_property("visibility", unreal.SlateVisibility.COLLAPSED)
        except Exception: pass

# Rebuild UpdateOrders body using TxtTitle / TxtSeeds / TxtHarvest
to_del=[n for n in uge.list_all_nodes() if n.get_class().get_name()!="K2Node_FunctionEntry"]
if to_del: uge.remove_nodes(to_del)
for n in uge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n
if find_pin(entry,"Line1","Output") is None: uge.add_graph_input_parameter("Line1", str_pin)
if find_pin(entry,"Line2","Output") is None: uge.add_graph_input_parameter("Line2", str_pin)
for n in uge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_FunctionEntry": entry=n

get_title=uge.add_get_member_variable_node("TxtTitle")
get_l1=uge.add_get_member_variable_node("TxtSeeds")
get_l2=uge.add_get_member_variable_node("TxtHarvest")
bel.set_node_pos(get_title,pos(250,-60)); bel.set_node_pos(get_l1,pos(250,80)); bel.set_node_pos(get_l2,pos(250,220))

conv_t=uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText"); bel.set_node_pos(conv_t,pos(520,-40))
setdef(find_pin(conv_t,"InString","Input"),"\u8ba2\u5355")
conv1=uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText"); bel.set_node_pos(conv1,pos(520,80))
connect(find_pin(entry,"Line1","Output"), find_pin(conv1,"InString","Input"),"L1")
conv2=uge.add_call_function_node("/Script/Engine.KismetTextLibrary:Conv_StringToText"); bel.set_node_pos(conv2,pos(520,220))
connect(find_pin(entry,"Line2","Output"), find_pin(conv2,"InString","Input"),"L2")

set_t=uge.add_call_function_node("/Script/UMG.TextBlock:SetText"); bel.set_node_pos(set_t,pos(820,-60))
set_1=uge.add_call_function_node("/Script/UMG.TextBlock:SetText"); bel.set_node_pos(set_1,pos(820,80))
set_2=uge.add_call_function_node("/Script/UMG.TextBlock:SetText"); bel.set_node_pos(set_2,pos(820,220))
connect(find_pin(entry,"then","Output"), find_pin(set_t,"execute","Input"),"e")
connect(out_data(get_title), find_pin(set_t,"self","Input"),"ts")
connect(out_data(conv_t), find_pin(set_t,"InText","Input"),"tt")
connect(find_pin(set_t,"then","Output"), find_pin(set_1,"execute","Input"),"t1")
connect(out_data(get_l1), find_pin(set_1,"self","Input"),"1s")
connect(out_data(conv1), find_pin(set_1,"InText","Input"),"1t")
connect(find_pin(set_1,"then","Output"), find_pin(set_2,"execute","Input"),"12")
connect(out_data(get_l2), find_pin(set_2,"self","Input"),"2s")
connect(out_data(conv2), find_pin(set_2,"InText","Input"),"2t")

# vis empty lines
eq1=uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr"); bel.set_node_pos(eq1,pos(1100,80))
connect(find_pin(entry,"Line1","Output"), find_pin(eq1,"A","Input"),"e1"); setdef(find_pin(eq1,"B","Input"),"")
br1=uge.add_branch_node(); bel.set_node_pos(br1,pos(1350,80))
connect(find_pin(set_2,"then","Output"), find_pin(br1,"execute","Input"),"s2br")
connect(out_data(eq1), find_pin(br1,"Condition","Input"),"c1")
h1=uge.add_call_function_node("/Script/UMG.Widget:SetVisibility"); s1=uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(h1,pos(1600,20)); bel.set_node_pos(s1,pos(1600,140))
connect(out_data(get_l1), find_pin(h1,"self","Input"),"h1s"); connect(out_data(get_l1), find_pin(s1,"self","Input"),"s1s")
setdef(find_pin(h1,"InVisibility","Input"),"Collapsed"); setdef(find_pin(s1,"InVisibility","Input"),"Visible")
connect(find_pin(br1,"then","Output"), find_pin(h1,"execute","Input"),"hide1")
connect(find_pin(br1,"else","Output"), find_pin(s1,"execute","Input"),"show1")

eq2=uge.add_call_function_node("/Script/Engine.KismetStringLibrary:EqualEqual_StrStr"); bel.set_node_pos(eq2,pos(1850,200))
connect(find_pin(entry,"Line2","Output"), find_pin(eq2,"A","Input"),"e2"); setdef(find_pin(eq2,"B","Input"),"")
br2=uge.add_branch_node(); bel.set_node_pos(br2,pos(2100,200))
connect(find_pin(h1,"then","Output"), find_pin(br2,"execute","Input"),"h->br2")
connect(find_pin(s1,"then","Output"), find_pin(br2,"execute","Input"),"s->br2")
connect(out_data(eq2), find_pin(br2,"Condition","Input"),"c2")
h2=uge.add_call_function_node("/Script/UMG.Widget:SetVisibility"); s2=uge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(h2,pos(2350,140)); bel.set_node_pos(s2,pos(2350,260))
connect(out_data(get_l2), find_pin(h2,"self","Input"),"h2s"); connect(out_data(get_l2), find_pin(s2,"self","Input"),"s2s")
setdef(find_pin(h2,"InVisibility","Input"),"Collapsed"); setdef(find_pin(s2,"InVisibility","Input"),"Visible")
connect(find_pin(br2,"then","Output"), find_pin(h2,"execute","Input"),"hide2")
connect(find_pin(br2,"else","Output"), find_pin(s2,"execute","Input"),"show2")

# Rename display: set TxtSeeds/Harvest default empty, title 订单 — already
# Also set CJK font on TxtSeeds/Harvest/Title
font=unreal.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
for name in ("TxtTitle","TxtSeeds","TxtHarvest"):
    tb=widgets.get(name)
    if not tb: continue
    try:
        if name=="TxtTitle": tb.set_text("\u8ba2\u5355")
        else: tb.set_text("")
        fi=tb.get_editor_property("font"); fi.set_editor_property("size", 22.0 if name=="TxtTitle" else 18.0)
        if font: fi.set_editor_property("font_object", font)
        tb.set_editor_property("font", fi)
    except Exception as e: log(str(e)[:80])

bel.compile_blueprint(wbp)
werrs=[title(n) for n in (uge.list_nodes_with_errors() or [])]
log("WBP UpdateOrders status={} errs={}".format(status_of(wbp), werrs))
eas.save_asset(WBP)

# Fix Manager: recreate Get OrderListWidget nodes by refreshing EnsureOrderUI + ApplyOrderUMG
mbp=unreal.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Replace broken Get OrderListWidget: find all VariableGet with OrderListWidget and refresh
# Easiest: break and rebuild EnsureOrderUI Set + ApplyOrderUMG gets
# List errs
errs=[]
for n in (mge.list_nodes_with_errors() or []):
    errs.append(title(n)+"|"+str(n.get_editor_property("error_msg") if hasattr(n,"get_editor_property") else "")[:100])
log("mgr errs before="+str(errs))

# Force refresh variable gets: remove Get OrderListWidget error nodes and re-add in Ensure/Apply
# Find EnsureOrderUI chain Create Widget -> Set OrderListWidget
ens=find_custom(mge,"EnsureOrderUI")
# Find Set OrderListWidget in ensure chain and Get OrderListWidget IsValid
from_nodes=[]
def walk(start,max_d=40):
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

# Kill ALL Get OrderListWidget / Set OrderListWidget nodes that error, then rewire Ensure + Apply
kill=[]
for n in list(mge.list_all_nodes()):
    if "OrderListWidget" in title(n) and n.get_class().get_name() in ("K2Node_VariableGet","K2Node_VariableSet"):
        # check error
        try:
            em=str(n.get_editor_property("error_msg") or "")
        except Exception:
            em=""
        if em or True:
            # break links then remove — we'll rebuild critical paths
            for p in bel.list_all_pins(n):
                try: p.break_pin_links()
                except Exception: pass
            kill.append(n)
if kill:
    mge.remove_nodes(kill)
    log("removed OrderListWidget get/set count="+str(len(kill)))

bel.compile_blueprint(mbp)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Rebuild EnsureOrderUI completely (keep event)
ens=find_custom(mge,"EnsureOrderUI")
if ens:
    tp=find_pin(ens,"then","Output")
    if tp: tp.break_pin_links()
    get_w=mge.add_get_member_variable_node("OrderListWidget"); bel.set_node_pos(get_w,pos(-1200,5300))
    isv=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid"); bel.set_node_pos(isv,pos(-950,5380))
    connect(out_data(get_w), find_pin(isv,"Object","Input"),"isv")
    br=mge.add_branch_node(); bel.set_node_pos(br,pos(-700,5300))
    connect(find_pin(ens,"then","Output"), find_pin(br,"execute","Input"),"e->br")
    connect(out_data(isv), find_pin(br,"Condition","Input"),"isc")
    # else create
    create=mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
    if create is None:
        create=mge.add_call_function_node("/Script/UMG.Blueprint|/Script/UMG.WidgetBlueprintLibrary:Create")
    # Try Create Widget
    if create is None or "Create" not in title(create):
        # use previous path from ensure - Create Widget node
        create=mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create")
    bel.set_node_pos(create,pos(-400,5400))
    # dump pins
    if create:
        for p in bel.list_all_pins(create):
            log("create pin {} {}".format(p.get_pin_name(), p.get_pin_type_display_string()))
        setdef(find_pin(create,"Class","Input") or find_pin(create,"WidgetType","Input"),
               "/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C")
        connect(find_pin(br,"else","Output"), find_pin(create,"execute","Input"),"else->create")
        add=mge.add_call_function_node("/Script/UMG.UserWidget:AddToViewport"); bel.set_node_pos(add,pos(-50,5400))
        connect(find_pin(create,"then","Output"), find_pin(add,"execute","Input"),"c->add")
        connect(out_data(create), find_pin(add,"self","Input"),"add self")
        set_w=mge.add_set_member_variable_node("OrderListWidget"); bel.set_node_pos(set_w,pos(300,5400))
        connect(find_pin(add,"then","Output"), find_pin(set_w,"execute","Input"),"add->set")
        connect(out_data(create), find_pin(set_w,"OrderListWidget","Input"),"set val")
        log("EnsureOrderUI rebuilt")
    else:
        log("CREATE WIDGET FAILED")

# Rebuild ApplyOrderUMG
apply=find_custom(mge,"ApplyOrderUMG")
if apply is None:
    apply=mge.add_custom_event_node("ApplyOrderUMG"); bel.set_node_pos(apply,pos(-3000,6600))
tp=find_pin(apply,"then","Output")
if tp: tp.break_pin_links()
# purge old apply chain orphans loosely — skip
get_w=mge.add_get_member_variable_node("OrderListWidget"); bel.set_node_pos(get_w,pos(-2700,6600))
isv=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid"); bel.set_node_pos(isv,pos(-2450,6700))
connect(out_data(get_w), find_pin(isv,"Object","Input"),"aisv")
br=mge.add_branch_node(); bel.set_node_pos(br,pos(-2200,6600))
connect(find_pin(apply,"then","Output"), find_pin(br,"execute","Input"),"a->br")
connect(out_data(isv), find_pin(br,"Condition","Input"),"aisc")
get_l1=mge.add_get_member_variable_node("OrderLine1"); get_l2=mge.add_get_member_variable_node("OrderLine2")
bel.set_node_pos(get_l1,pos(-2200,6780)); bel.set_node_pos(get_l2,pos(-2200,6880))
bel.compile_blueprint(wbp); bel.compile_blueprint(mbp)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
apply=find_custom(mge,"ApplyOrderUMG")
# walk to find branch
def walk_then(start,max_d=20):
    thenp=find_pin(start,"then","Output")
    q=[(c.get_owning_node(),0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen=[]; ids=set()
    while q:
        cur,d=q.pop(0)
        if id(cur) in ids or d>max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append((c.get_owning_node(),d+1))
    return seen
chain=walk_then(apply,10)
br=None
for n in chain:
    if n.get_class().get_name()=="K2Node_IfThenElse": br=n; break
get_l1=mge.add_get_member_variable_node("OrderLine1"); get_l2=mge.add_get_member_variable_node("OrderLine2")
get_w2=mge.add_get_member_variable_node("OrderListWidget")
bel.set_node_pos(get_l1,pos(-2000,6780)); bel.set_node_pos(get_l2,pos(-2000,6880)); bel.set_node_pos(get_w2,pos(-2000,6500))
call_upd=mge.add_call_function_node("/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C:UpdateOrders")
bel.set_node_pos(call_upd,pos(-1600,6600))
if br:
    connect(find_pin(br,"then","Output"), find_pin(call_upd,"execute","Input"),"br->upd")
connect(out_data(get_w2), find_pin(call_upd,"self","Input"),"uself")
connect(out_data(get_l1), find_pin(call_upd,"Line1","Input"),"uL1")
connect(out_data(get_l2), find_pin(call_upd,"Line2","Input"),"uL2")

get_open=mge.add_get_member_variable_node("bIsOpenBusiness"); bel.set_node_pos(get_open,pos(-1600,7050))
ne1=mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
ne2=mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
bel.set_node_pos(ne1,pos(-1300,7120)); bel.set_node_pos(ne2,pos(-1300,7220))
connect(out_data(get_l1), find_pin(ne1,"A","Input"),"ne1"); setdef(find_pin(ne1,"B","Input"),"")
connect(out_data(get_l2), find_pin(ne2,"A","Input"),"ne2"); setdef(find_pin(ne2,"B","Input"),"")
or1=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
or2=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
bel.set_node_pos(or1,pos(-1000,7080)); bel.set_node_pos(or2,pos(-750,7080))
connect(out_data(get_open), find_pin(or1,"A","Input"),"o1a"); connect(out_data(ne1), find_pin(or1,"B","Input"),"o1b")
connect(out_data(or1), find_pin(or2,"A","Input"),"o2a"); connect(out_data(ne2), find_pin(or2,"B","Input"),"o2b")
brv=mge.add_branch_node(); bel.set_node_pos(brv,pos(-500,6600))
connect(find_pin(call_upd,"then","Output"), find_pin(brv,"execute","Input"),"u->v")
connect(out_data(or2), find_pin(brv,"Condition","Input"),"vc")
vs=mge.add_call_function_node("/Script/UMG.Widget:SetVisibility"); vh=mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
bel.set_node_pos(vs,pos(-200,6500)); bel.set_node_pos(vh,pos(-200,6750))
get_w3=mge.add_get_member_variable_node("OrderListWidget"); bel.set_node_pos(get_w3,pos(-500,6500))
connect(out_data(get_w3), find_pin(vs,"self","Input"),"vss"); connect(out_data(get_w3), find_pin(vh,"self","Input"),"vhs")
setdef(find_pin(vs,"InVisibility","Input"),"Visible"); setdef(find_pin(vh,"InVisibility","Input"),"Collapsed")
connect(find_pin(brv,"then","Output"), find_pin(vs,"execute","Input"),"show")
connect(find_pin(brv,"else","Output"), find_pin(vh,"execute","Input"),"hide")
# debug off path - no print unless flag: skip print for cleanliness

# RefreshOrderUI Ensure->Apply
ref=find_custom(mge,"RefreshOrderUI")
if ref:
    tp=find_pin(ref,"then","Output")
    if tp: tp.break_pin_links()
    call_ens=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
    bel.set_node_pos(call_ens,pos(-2900,5700))
    connect(find_pin(ref,"then","Output"), find_pin(call_ens,"execute","Input"),"r->e")
    bel.compile_blueprint(mbp)
    mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
    ref=find_custom(mge,"RefreshOrderUI")
    chain=walk_then(ref,5)
    ens_call=None
    for n in chain:
        if title(n)=="EnsureOrderUI": ens_call=n; break
    if ens_call is None:
        ens_call=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:EnsureOrderUI")
        connect(find_pin(ref,"then","Output"), find_pin(ens_call,"execute","Input"),"r->e2")
    call_app=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplyOrderUMG")
    bel.set_node_pos(call_app,pos(-2500,5700))
    connect(find_pin(ens_call,"then","Output"), find_pin(call_app,"execute","Input"),"e->a")

final={}
for path,key in ((WBP,"wbp"),(MGR,"mgr"),(TBL,"tbl")):
    bp=unreal.load_asset(path); bel.compile_blueprint(bp)
    ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    errs=[]
    for n in (ge.list_nodes_with_errors() or []):
        try: msg=str(n.get_editor_property("error_msg"))[:160]
        except: msg=""
        errs.append({"t":title(n),"m":msg})
    for fname in ("UpdateOrders","SetOrderLine"):
        g=bel.find_graph(bp,fname)
        if g:
            fge=unreal.BlueprintGraphEditor.get_graph_editor(g)
            for n in (fge.list_nodes_with_errors() or []):
                errs.append({"t":fname+":"+title(n),"m":""})
    final[key]={"status":status_of(bp),"errs":errs}
    log("FINAL {} {} {}".format(key,final[key]["status"],errs))
    eas.save_asset(path)

mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(unreal.load_asset(MGR)))
for name,key in (("RefreshOrderUI","refresh"),("ApplyOrderUMG","apply"),("EnsureOrderUI","ensure")):
    ev=find_custom(mge,name)
    REPORT[key]=[title(n) for n in walk_then(ev,30)] if ev else []
    log(key+": "+" -> ".join(REPORT[key][:25]))
REPORT["final"]=final
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
open(unreal.Paths.project_saved_dir()+"rest_umg_orders_fix2.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print("DONE_FIX2")
