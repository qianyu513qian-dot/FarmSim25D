# -*- coding: utf-8 -*-
"""Trace data deps of live AddMovementInput nodes on MoveCharacter exec path."""
import unreal, json
from pathlib import Path
bel=unreal.BlueprintEditorLibrary
bp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,"MoveCharacter"))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(n, name, direction=None):
    for p in bel.list_all_pins(n):
        if name.lower() in str(p.get_pin_name()).lower().replace(" ",""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

nodes=list(ge.list_all_nodes())
entry=next(n for n in nodes if n.get_class().get_name()=="K2Node_FunctionEntry" or title(n)=="MoveCharacter")
# exec BFS collect AMI on path
seen=set(); q=[]; live=[]
for p in bel.list_all_pins(entry):
    if str(p.get_pin_name())=="then":
        for c in p.list_connected_pins(): q.append(c.get_owning_node())
while q:
    n=q.pop(0)
    if id(n) in seen: continue
    seen.add(id(n))
    if "AddMovementInput" in title(n):
        live.append(n)
    for p in bel.list_all_pins(n):
        if "OUTPUT" in str(p.get_pin_direction()):
            pn=str(p.get_pin_name()).lower()
            if pn in ("then","true","false","else","completed") or "then" in pn:
                for c in p.list_connected_pins():
                    q.append(c.get_owning_node())

def trace_back(pin, depth=0, visited=None):
    if visited is None: visited=set()
    if not pin or depth>12: return []
    rows=[]
    for c in pin.list_connected_pins():
        on=c.get_owning_node()
        if id(on) in visited: continue
        visited.add(id(on))
        t=title(on)
        row={"depth":depth,"title":t,"pin":str(c.get_pin_name())}
        if "MakeRotator" in t:
            w={}
            for p in bel.list_all_pins(on):
                links=[title(x.get_owning_node())+"."+str(x.get_pin_name()) for x in p.list_connected_pins()]
                if links or str(p.get_pin_name()) in ("Pitch","Yaw","Roll"):
                    w[str(p.get_pin_name())]=links
            row["make"]=w
        rows.append(row)
        # continue into inputs of this node
        for p in bel.list_all_pins(on):
            if "INPUT" in str(p.get_pin_direction()):
                rows.extend(trace_back(p, depth+1, visited))
    return rows

REPORT={"live_ami_count":len(live),"traces":[]}
for ami in live:
    tr={"scale_links":[], "dir_trace":[]}
    sp=find_pin(ami,"ScaleValue","Input")
    if sp:
        tr["scale_links"]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in sp.list_connected_pins()]
        try: tr["scale_default"]=sp.get_pin_value()
        except: pass
    wp=find_pin(ami,"WorldDirection","Input")
    if wp:
        tr["dir_trace"]=trace_back(wp)
    REPORT["traces"].append(tr)

# Also Branch condition
branch=next((n for n in nodes if title(n)=="Branch" and id(n) in seen), None)
if branch:
    cond=find_pin(branch,"Condition","Input")
    REPORT["branch_cond"]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in cond.list_connected_pins()] if cond else None
    for p in bel.list_all_pins(branch):
        if "OUTPUT" in str(p.get_pin_direction()):
            REPORT["branch_"+str(p.get_pin_name())]=[title(c.get_owning_node()) for c in p.list_connected_pins()]

# Set FacingDirection
face=next((n for n in nodes if "Facing" in title(n) and id(n) in seen), None)
if face:
    REPORT["facing_title"]=title(face)
    REPORT["facing_pins"]={str(p.get_pin_name()):[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()] for p in bel.list_all_pins(face)}

path=Path(unreal.Paths.project_saved_dir())/"DayNight"/"wasd_live.json"
path.write_text(json.dumps(REPORT,default=str,indent=2),encoding="utf-8")
REPORT={"file":str(path),"live":len(live)}
