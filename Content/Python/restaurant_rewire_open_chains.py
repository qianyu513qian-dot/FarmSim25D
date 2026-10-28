# -*- coding: utf-8 -*-
"""Restore open/close then-chains after ApplySign calls."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
MGR="/Game/Farm/Restaurant/BP_RestaurantManager"
R={"steps":[],"errors":[]}
def log(m):
    unreal.log("[REWIRE] "+str(m)); print("[REWIRE] "+str(m)); R["steps"].append(str(m))
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
def connect(a,b,label=""):
    if a is None or b is None:
        log("skip "+label); R["errors"].append(label); return False
    ok=a.try_create_connection(b); log("conn[{}] {}".format(label,ok))
    if not ok: R["errors"].append("fail "+label)
    return ok
def pin_text(n):
    inp=find_pin(n,"InString","Input")
    return (inp.get_pin_value() if inp else "") or ""

mbp=eas.load_asset(MGR)
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))

# Find targets
open_print=None
close_print=None
auto_print=None
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    v=pin_text(n)
    if "OPEN for business" in v: open_print=n
    elif "CLOSED (early)" in v: close_print=n
    elif "AUTO CLOSE" in v: auto_print=n

# Set GuestTimer that currently has no execute preds and leads to open print
guest_timer_open=None
for n in mge.list_all_nodes():
    if title(n)!="Set GuestTimer": continue
    ep=find_pin(n,"execute","Input")
    preds=list(ep.list_connected_pins() if ep else [])
    thenp=find_pin(n,"then","Output")
    succs=[c.get_owning_node() for c in (thenp.list_connected_pins() if thenp else [])]
    if not preds and any(s is open_print or (title(s)=="PrintString" and "OPEN" in pin_text(s)) for s in succs):
        guest_timer_open=n
        break
    # also: succs is open_print
    if not preds:
        for s in succs:
            if s is open_print:
                guest_timer_open=n

log("open_print="+str(open_print is not None)+" close="+str(close_print is not None)+" auto="+str(auto_print is not None)+" timer="+str(guest_timer_open is not None))

# Classify Set bIsOpenBusiness by walking backwards a bit - use node Y position or following context
# Get all Set + their ApplySign call
sets=[]
for n in mge.list_all_nodes():
    if title(n)!="Set bIsOpenBusiness": continue
    val=find_pin(n,"bIsOpenBusiness","Input")
    v=(val.get_pin_value() if val else "") or ""
    thenp=find_pin(n,"then","Output")
    apply=None
    if thenp:
        for c in thenp.list_connected_pins() or []:
            own=c.get_owning_node()
            if "ApplySign" in title(own):
                apply=own
    # predecessors
    ep=find_pin(n,"execute","Input")
    preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
    sets.append({"node":n,"val":v,"apply":apply,"preds":preds})
    log("Set val="+v+" preds="+str(preds)+" apply="+title(apply) if apply else "Set val="+v+" no apply")

# Heuristic:
# - true Set -> ApplySignOpen -> Set GuestTimer (open)
# - false Set with ClearGuests orphan close_print -> early close (from HandlePlayerE)
# - false Set with auto_print -> auto close from tick
# Distinguish two false sets by looking at what Branch feeds them / nearby GetDisplayMinutes

# For false sets: look at exec predecessor chain for "1380" or close vs open toggle
def upstream_titles(node, depth=8):
    out=[]; cur=node; seen=set()
    for _ in range(depth):
        ep=find_pin(cur,"execute","Input")
        if not ep: break
        preds=list(ep.list_connected_pins() or [])
        if not preds: break
        cur=preds[0].get_owning_node()
        if id(cur) in seen: break
        seen.add(id(cur)); out.append(title(cur))
        # also check data for literals on sibling? 
    return out

# Also scan for Integer >= 1380 near each set via shared branch
# Simpler approach: 
# ApplySignOpen (only one) -> guest_timer_open
# For ApplySignClosed calls that have empty then:
#   find close_print and auto_print orphans
#   Match by Y position proximity

def node_y(n):
    try:
        return int(bel.get_node_pos(n).y)
    except Exception:
        try:
            return int(n.node_pos_y)
        except Exception:
            return 0

# ApplySignOpen
for s in sets:
    if str(s["val"]).lower() in ("true","1") and s["apply"]:
        ap=s["apply"]
        thenp=find_pin(ap,"then","Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            if guest_timer_open:
                connect(thenp, find_pin(guest_timer_open,"execute","Input"), "Open->GuestTimer")
            elif open_print:
                connect(thenp, find_pin(open_print,"execute","Input"), "Open->Print")

# ApplySignClosed ones - sort by y
closed_applies=[]
for s in sets:
    if str(s["val"]).lower() in ("false","0") and s["apply"]:
        closed_applies.append((node_y(s["node"]), s))
closed_applies.sort(key=lambda x: x[0])

# Orphan prints
# close_print and auto_print
# Typically early close is in HandlePlayerE (lower/negative y ~ -150), auto at ~1550
# From first probe: false y=-150 early, false y=1550 auto, true y=120 open

if close_print and auto_print and len(closed_applies)>=2:
    # assign lower y -> early close, higher y -> auto
    (y0,s0),(y1,s1)=closed_applies[0], closed_applies[1]
    # if y0 < y1: s0 early, s1 auto — but -150 < 1550 so early first
    mapping=[(s0, close_print, "early"), (s1, auto_print, "auto")]
    # verify: if y ordering wrong, check upstream for GetDisplayMinutes near auto
    for s, pr, kind in mapping:
        ap=s["apply"]
        thenp=find_pin(ap,"then","Output")
        if thenp and not list(thenp.list_connected_pins() or []):
            connect(thenp, find_pin(pr,"execute","Input"), kind+"->Print")
            log("linked "+kind)
elif len(closed_applies)==1:
    s=closed_applies[0][1]
    ap=s["apply"]
    thenp=find_pin(ap,"then","Output")
    # prefer close_print if orphan
    target=close_print or auto_print
    if thenp and target and not list(thenp.list_connected_pins() or []):
        connect(thenp, find_pin(target,"execute","Input"), "closed->print")
else:
    # fallback: match by y distance to prints
    for y,s in closed_applies:
        ap=s["apply"]
        thenp=find_pin(ap,"then","Output")
        if not thenp or list(thenp.list_connected_pins() or []): continue
        # pick nearest orphan print by y
        cands=[]
        if close_print:
            ep=find_pin(close_print,"execute","Input")
            if ep and not list(ep.list_connected_pins() or []):
                cands.append((abs(node_y(close_print)-y), close_print, "early"))
        if auto_print:
            ep=find_pin(auto_print,"execute","Input")
            if ep and not list(ep.list_connected_pins() or []):
                cands.append((abs(node_y(auto_print)-y), auto_print, "auto"))
        if cands:
            cands.sort()
            _,pr,kind=cands[0]
            connect(thenp, find_pin(pr,"execute","Input"), kind+"->Print y")

# BeginPlay ApplySignClosed should not need further chain (just visual)

bel.compile_blueprint(mbp)
eas.save_asset(MGR)

# Verify
def check():
    out=[]
    for n in mge.list_all_nodes():
        if title(n)!="Set bIsOpenBusiness": continue
        val=find_pin(n,"bIsOpenBusiness","Input")
        v=val.get_pin_value() if val else "?"
        thenp=find_pin(n,"then","Output")
        chain=[]
        cur=n
        for _ in range(6):
            tp=find_pin(cur,"then","Output")
            if not tp or not tp.list_connected_pins(): break
            cur=tp.list_connected_pins()[0].get_owning_node()
            chain.append(title(cur))
        out.append({"val":v,"chain":chain})
    return out
R["after"]=check()
log("after="+str(R["after"]))

# Check orphans gone
orph=[]
for n in mge.list_all_nodes():
    if title(n)!="PrintString": continue
    v=pin_text(n)
    if "CLOSED (early)" in v or "AUTO CLOSE" in v or "OPEN for business" in v:
        ep=find_pin(n,"execute","Input")
        if not list(ep.list_connected_pins() if ep else []):
            orph.append(v[:60])
R["orphans_left"]=orph
log("orphans_left="+str(orph))

# GuestTimer open preds
for n in mge.list_all_nodes():
    if n is guest_timer_open or (title(n)=="Set GuestTimer"):
        ep=find_pin(n,"execute","Input")
        preds=[title(c.get_owning_node()) for c in (ep.list_connected_pins() if ep else [])]
        if "ApplySignOpen" in preds or (guest_timer_open and n is guest_timer_open):
            log("timer preds="+str(preds))

try: unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
except Exception: pass
out=unreal.Paths.project_saved_dir()+"restaurant_rewire_open.json"
with open(out,"w",encoding="utf-8") as f: json.dump(R,f,indent=2,ensure_ascii=False)
log("DONE err="+str(R["errors"]))
