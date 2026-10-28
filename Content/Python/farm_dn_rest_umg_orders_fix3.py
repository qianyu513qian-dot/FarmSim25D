# -*- coding: utf-8 -*-
"""Fix EnsureOrderUI: Cast Create result to WBP before Set OrderListWidget."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
WBP="/Game/Farm/UI/WBP_RestOrderList"
REPORT={"steps":[]}

def log(m):
    unreal.log("[UMGFIX3] "+str(m)); print("[UMGFIX3] "+str(m)); REPORT["steps"].append(str(m))
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
    for name in ("ReturnValue","OrderListWidget"):
        p=find_pin(node,name,"Output")
        if p: return p
    for p in bel.list_all_pins(node):
        if "OUTPUT" in str(p.get_pin_direction()) and "Object" in str(p.get_pin_type_display_string()):
            n=str(p.get_pin_name()).lower()
            if n not in ("outputdelegate","then","else","castfailed"):
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
        except Exception as e: log(str(e)[:80]); return False
def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name: return n
    return None
def walk_then(start,max_d=30):
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
def status_of(bp):
    try: return str(bp.get_editor_property("status"))
    except Exception as e: return str(e)

mbp=unreal.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ens=find_custom(mge,"EnsureOrderUI")
chain=walk_then(ens,20)
log("ensure before: "+" -> ".join(title(n) for n in chain))

# Find Create Widget and Set OrderListWidget
create=None; set_w=None; add=None
for n in chain:
    t=title(n)
    if "Create" in t: create=n
    if t=="AddToViewport": add=n
    if "Set OrderListWidget" in t or t=="Set OrderListWidget": set_w=n
log("create={} add={} set={}".format(create is not None, add is not None, set_w is not None))

# Break set input and insert cast
if create and set_w:
    # break Create.ReturnValue -> Set.OrderListWidget and Add.self maybe ok as UserWidget
    # Insert cast between Add.then -> Set, and cast object from Create return
    cast=mge.create_node_from_name("Utilities|Casting|CastToWBP_RestOrderList", unreal.Vector2D(100,5400), [])
    if cast is None:
        # discover name
        ret=out_data(create)
        avail=mge.list_available_nodes([ret]) if ret else []
        name=None
        for a in avail:
            if "WBP_RestOrderList" in a and "Cast" in a:
                name=a; log("found cast name "+a); break
        if name:
            cast=mge.create_node_from_name(name, unreal.Vector2D(100,5400), [])
    log("cast="+str(cast))
    if cast:
        bel.set_node_pos(cast, pos(100,5400))
        # Rewire: Add.then -> Cast.execute -> Set.execute
        # Create.Return -> Cast.Object
        # Cast.As -> Set.OrderListWidget
        if add:
            then_add=find_pin(add,"then","Output")
            if then_add:
                # disconnect set from add
                for c in list(then_add.list_connected_pins() or []):
                    if c.get_owning_node()==set_w:
                        then_add.break_pin_links()  # careful - breaks all
                        break
            # reconnect properly
            if then_add:
                try: then_add.break_pin_links()
                except: pass
            connect(find_pin(add,"then","Output"), find_pin(cast,"execute","Input"),"add->cast")
            connect(find_pin(cast,"then","Output"), find_pin(set_w,"execute","Input"),"cast->set")
        connect(out_data(create), find_pin(cast,"Object","Input"),"create->castobj")
        # break existing set input links
        inp=find_pin(set_w,"OrderListWidget","Input")
        if inp:
            try: inp.break_pin_links()
            except: pass
        connect(out_data(cast), inp, "cast->setval")
        # Also ensure Add.self still from create
        connect(out_data(create), find_pin(add,"self","Input"),"create->addself")
        log("cast spliced")
    else:
        # Fallback: change OrderListWidget back to UserWidget
        p=unreal.EdGraphPinType()
        p.import_text('(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/UMG.UserWidget")')
        try:
            bel.change_member_variable_type(mbp,"OrderListWidget",p)
            log("fallback retype to UserWidget")
            # then need Cast before UpdateOrders instead
        except Exception as e:
            log("fallback "+str(e))

# Also verify WidgetType on Create
if create:
    setdef(find_pin(create,"WidgetType","Input"), "/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C")
    log("WidgetType set")

bel.compile_blueprint(mbp)
errs=[]
for n in (mge.list_nodes_with_errors() or []):
    try: msg=str(n.get_editor_property("error_msg"))[:160]
    except: msg=""
    errs.append({"t":title(n),"m":msg})
log("mgr status={} errs={}".format(status_of(mbp), errs))

# If still error on set, retype to UserWidget and cast in ApplyOrderUMG only
if errs or status_of(mbp)!="<BlueprintStatus.BS_UP_TO_DATE: 3>":
    # retype UserWidget
    p=unreal.EdGraphPinType()
    p.import_text('(PinCategory="object",PinSubCategory="",PinSubCategoryObject="/Script/UMG.UserWidget")')
    bel.change_member_variable_type(mbp,"OrderListWidget",p)
    log("retyped OrderListWidget back to UserWidget")
    # Refresh get/set nodes by recompile
    bel.compile_blueprint(mbp)
    mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
    # Rebuild Ensure simple without cast
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
        create=mge.add_call_function_node("/Script/UMG.WidgetBlueprintLibrary:Create"); bel.set_node_pos(create,pos(-400,5400))
        setdef(find_pin(create,"WidgetType","Input"), "/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C")
        connect(find_pin(br,"else","Output"), find_pin(create,"execute","Input"),"else->c")
        add=mge.add_call_function_node("/Script/UMG.UserWidget:AddToViewport"); bel.set_node_pos(add,pos(-50,5400))
        connect(find_pin(create,"then","Output"), find_pin(add,"execute","Input"),"c->a")
        connect(out_data(create), find_pin(add,"self","Input"),"a self")
        set_w=mge.add_set_member_variable_node("OrderListWidget"); bel.set_node_pos(set_w,pos(300,5400))
        connect(find_pin(add,"then","Output"), find_pin(set_w,"execute","Input"),"a->s")
        connect(out_data(create), find_pin(set_w,"OrderListWidget","Input"),"s val")
        log("ensure rebuilt UserWidget")
    # Rebuild Apply with CastToWBP before UpdateOrders
    apply=find_custom(mge,"ApplyOrderUMG")
    if apply:
        tp=find_pin(apply,"then","Output")
        if tp: tp.break_pin_links()
        get_w=mge.add_get_member_variable_node("OrderListWidget"); bel.set_node_pos(get_w,pos(-2700,6600))
        isv=mge.add_call_function_node("/Script/Engine.KismetSystemLibrary:IsValid"); bel.set_node_pos(isv,pos(-2450,6700))
        connect(out_data(get_w), find_pin(isv,"Object","Input"),"isv")
        br=mge.add_branch_node(); bel.set_node_pos(br,pos(-2200,6600))
        connect(find_pin(apply,"then","Output"), find_pin(br,"execute","Input"),"a->br")
        connect(out_data(isv), find_pin(br,"Condition","Input"),"isc")
        cast=mge.create_node_from_name("Utilities|Casting|CastToWBP_RestOrderList", unreal.Vector2D(-1900,6600), [])
        if cast is None:
            ret=out_data(get_w)
            avail=mge.list_available_nodes([ret]) if ret else []
            for a in avail:
                if "WBP_RestOrderList" in a and "Cast" in a:
                    cast=mge.create_node_from_name(a, unreal.Vector2D(-1900,6600), []); log("cast "+a); break
        if cast is None:
            log("NO WBP CAST"); 
        else:
            bel.set_node_pos(cast,pos(-1900,6600))
            connect(find_pin(br,"then","Output"), find_pin(cast,"execute","Input"),"br->cast")
            connect(out_data(get_w), find_pin(cast,"Object","Input"),"w->cast")
            get_l1=mge.add_get_member_variable_node("OrderLine1"); get_l2=mge.add_get_member_variable_node("OrderLine2")
            bel.set_node_pos(get_l1,pos(-1900,6780)); bel.set_node_pos(get_l2,pos(-1900,6880))
            bel.compile_blueprint(unreal.load_asset(WBP))
            bel.compile_blueprint(mbp)
            mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
            # re-find cast in apply chain
            apply=find_custom(mge,"ApplyOrderUMG")
            chain=walk_then(apply,15)
            cast=None; br=None
            for n in chain:
                if "Cast" in title(n) and "RestOrder" in title(n): cast=n
                if n.get_class().get_name()=="K2Node_IfThenElse" and br is None: br=n
            if cast is None:
                # find any CastToWBP
                for n in chain:
                    if "Cast" in title(n): cast=n; break
            call_upd=mge.add_call_function_node("/Game/Farm/UI/WBP_RestOrderList.WBP_RestOrderList_C:UpdateOrders")
            bel.set_node_pos(call_upd,pos(-1500,6600))
            if cast:
                connect(find_pin(cast,"then","Output"), find_pin(call_upd,"execute","Input"),"c->u")
                connect(out_data(cast), find_pin(call_upd,"self","Input"),"u self")
            get_l1=mge.add_get_member_variable_node("OrderLine1"); get_l2=mge.add_get_member_variable_node("OrderLine2")
            connect(out_data(get_l1), find_pin(call_upd,"Line1","Input"),"L1")
            connect(out_data(get_l2), find_pin(call_upd,"Line2","Input"),"L2")
            # visibility on UserWidget (OrderListWidget) without cast
            get_open=mge.add_get_member_variable_node("bIsOpenBusiness")
            ne1=mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
            ne2=mge.add_call_function_node("/Script/Engine.KismetStringLibrary:NotEqual_StrStr")
            connect(out_data(get_l1), find_pin(ne1,"A","Input"),"ne1"); setdef(find_pin(ne1,"B","Input"),"")
            connect(out_data(get_l2), find_pin(ne2,"A","Input"),"ne2"); setdef(find_pin(ne2,"B","Input"),"")
            or1=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
            or2=mge.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
            connect(out_data(get_open), find_pin(or1,"A","Input"),"o1a"); connect(out_data(ne1), find_pin(or1,"B","Input"),"o1b")
            connect(out_data(or1), find_pin(or2,"A","Input"),"o2a"); connect(out_data(ne2), find_pin(or2,"B","Input"),"o2b")
            brv=mge.add_branch_node(); bel.set_node_pos(brv,pos(-1100,6600))
            connect(find_pin(call_upd,"then","Output"), find_pin(brv,"execute","Input"),"u->v")
            connect(out_data(or2), find_pin(brv,"Condition","Input"),"vc")
            vs=mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
            vh=mge.add_call_function_node("/Script/UMG.Widget:SetVisibility")
            bel.set_node_pos(vs,pos(-800,6500)); bel.set_node_pos(vh,pos(-800,6750))
            get_w3=mge.add_get_member_variable_node("OrderListWidget")
            connect(out_data(get_w3), find_pin(vs,"self","Input"),"vss")
            connect(out_data(get_w3), find_pin(vh,"self","Input"),"vhs")
            setdef(find_pin(vs,"InVisibility","Input"),"Visible")
            setdef(find_pin(vh,"InVisibility","Input"),"Collapsed")
            connect(find_pin(brv,"then","Output"), find_pin(vs,"execute","Input"),"show")
            connect(find_pin(brv,"else","Output"), find_pin(vh,"execute","Input"),"hide")
            log("Apply rebuilt with cast")

# RefreshOrderUI Ensure->Apply
bel.compile_blueprint(mbp)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
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
        ens_call=call_ens
    call_app=mge.add_call_function_node("/Game/Farm/Restaurant/BP_RestaurantManager.BP_RestaurantManager_C:ApplyOrderUMG")
    bel.set_node_pos(call_app,pos(-2500,5700))
    connect(find_pin(ens_call,"then","Output"), find_pin(call_app,"execute","Input"),"e->a")

final={}
for path,key in ((WBP,"wbp"),(MGR,"mgr"),("/Game/Farm/Restaurant/BP_RestaurantTable","tbl")):
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
open(unreal.Paths.project_saved_dir()+"rest_umg_orders_fix3.json","w",encoding="utf-8").write(json.dumps(REPORT,ensure_ascii=False,indent=2))
print("DONE_FIX3")
