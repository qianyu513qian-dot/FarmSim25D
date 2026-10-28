# -*- coding: utf-8 -*-
"""Probe pay amounts, BeginEatOnlyIfId*, DestroyGuestVisual, open/close print strings."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
R={}

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

def pin_val(p):
    if not p: return None
    for fn in ("get_default_as_string","get_default_value"):
        if hasattr(p,fn):
            try:
                v=getattr(p,fn)()
                if v is not None and str(v)!="": return str(v)
            except: pass
    try: return str(p.default_value)
    except: return None

def find_custom(ge,name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name()=="K2Node_CustomEvent" and title(n)==name:
            return n
    return None

def walk(start,limit=25):
    chain=[]; seen=set(); q=[start]
    while q and len(chain)<limit:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); chain.append(title(cur))
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    return chain

mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
tbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
tge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(tbp))

# OnGuestPaid: find Set RestaurantMoney A/B values
for evn in ("OnGuestPaidSalad","OnGuestPaidStew"):
    ev=find_custom(mge,evn)
    info={"chain":walk(ev)}
    for n in mge.list_all_nodes():
        if title(n)!="Set RestaurantMoney": continue
        # is it reachable from this event? rough: check nearby Y
        # just dump all Set RestaurantMoney with input pin links
    # walk nodes from event and find set money
    cur=ev; seen=set(); nodes=[]
    q=[ev]
    while q:
        cur=q.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur)); nodes.append(cur)
        for pn in ("then","else"):
            tp=find_pin(cur,pn,"Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    q.append(c.get_owning_node())
    for n in nodes:
        if title(n)=="Set RestaurantMoney":
            # find add node feeding it
            vp=find_pin(n,"RestaurantMoney","Input")
            info["money_links"]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in (vp.list_connected_pins() or [])] if vp else []
            for c in (vp.list_connected_pins() or []) if vp else []:
                addn=c.get_owning_node()
                info["add_title"]=title(addn)
                for pin in ("A","B"):
                    pp=find_pin(addn,pin,"Input")
                    info["add_"+pin]=pin_val(pp)
                    info["add_"+pin+"_links"]=[title(x.get_owning_node()) for x in (pp.list_connected_pins() or [])] if pp else []
        if title(n)=="PrintString":
            info["print"]=pin_val(find_pin(n,"InString","Input"))
            info["print_key"]=pin_val(find_pin(n,"Key","Input"))
    R[evn]=info

# BeginEatOnlyIfId1/2 chains on table
for name in ("BeginEatOnlyIfId1","BeginEatOnlyIfId2","DestroyGuestVisual","SpawnGuestVisual","ClearGuests"):
    # table or mgr
    for label,ge in (("tbl",tge),("mgr",mge)):
        ev=find_custom(ge,name)
        if ev:
            R[label+"_"+name]=walk(ev)

# PrintStrings near close
prints=[]
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    s=pin_val(find_pin(n,"InString","Input")) or ""
    k=pin_val(find_pin(n,"Key","Input")) or ""
    if any(x in s for x in ("CLOSE","Closed","CLOSED","Open","OPEN","PAY","打烊","营收","开业")) or any(x in k for x in ("Rest","Pay","Close","Open")):
        prints.append({"s":s,"k":k})
R["prints"]=prints

# BeginEat terminal then pin free?
be=find_custom(tge,"BeginEat")
R["BeginEat_chain"]=walk(be)
# last node then links
cur=be; last=be; seen=set()
while cur and id(cur) not in seen:
    seen.add(id(cur)); last=cur
    tp=find_pin(cur,"then","Output")
    if not tp or not tp.list_connected_pins(): break
    cur=tp.list_connected_pins()[0].get_owning_node()
R["BeginEat_last"]=title(last)
R["BeginEat_last_then"]=bool(find_pin(last,"then","Output") and find_pin(last,"then","Output").list_connected_pins())

cs=find_custom(tge,"ClearSeat")
cur=cs; last=cs; seen=set()
while cur and id(cur) not in seen:
    seen.add(id(cur)); last=cur
    tp=find_pin(cur,"then","Output")
    if not tp or not tp.list_connected_pins(): break
    cur=tp.list_connected_pins()[0].get_owning_node()
R["ClearSeat_last"]=title(last)
R["ClearSeat_chain"]=walk(cs)

# ClearGuests mgr
cg=find_custom(mge,"ClearGuests")
R["ClearGuests"]=walk(cg) if cg else None

# open set true prints
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    then=find_pin(n,"then","Output")
    nxt=[title(c.get_owning_node()) for c in (then.list_connected_pins() or [])] if then else []
    R.setdefault("open_sets",[]).append(nxt)

open(r"E:\UE\FarmSim25D\Saved\rest_dish_dayend_probe2.json","w",encoding="utf-8").write(json.dumps(R,indent=2,ensure_ascii=False,default=str))
print(json.dumps(R,indent=2,ensure_ascii=False,default=str)[:10000])
