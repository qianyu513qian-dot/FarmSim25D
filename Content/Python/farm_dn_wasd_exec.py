# -*- coding: utf-8 -*-
"""Trace MoveCharacter exec chain from entry; list GetComponentByClass class pins."""
import unreal, json
from pathlib import Path
bel=unreal.BlueprintEditorLibrary
bp=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,"MoveCharacter"))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

nodes=list(ge.list_all_nodes())
# Find entry
entry=None
for n in nodes:
    t=title(n)
    if "MoveCharacter"==t or n.get_class().get_name() in ("K2Node_FunctionEntry","K2Node_CustomEvent"):
        entry=n
        if "Entry" in n.get_class().get_name() or t=="MoveCharacter":
            break
REPORT={"entry_class": entry.get_class().get_name() if entry else None, "entry_title": title(entry) if entry else None}

# BFS exec
chain=[]
seen=set()
q=[]
if entry:
    for p in bel.list_all_pins(entry):
        if "then" in str(p.get_pin_name()).lower() or str(p.get_pin_direction()).endswith("OUTPUT: 1"):
            if "Axis" in str(p.get_pin_name()): continue
            for c in p.list_connected_pins():
                q.append(c.get_owning_node())
while q:
    n=q.pop(0)
    if id(n) in seen: continue
    seen.add(id(n))
    row={"title":title(n),"class":n.get_class().get_name()}
    # note MakeRotator wiring
    if "MakeRotator" in row["title"]:
        wiring={}
        for p in bel.list_all_pins(n):
            pn=str(p.get_pin_name())
            links=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
            if links or pn in ("Pitch","Yaw","Roll"):
                try: val=p.get_pin_value()
                except: val=""
                wiring[pn]={"val":str(val),"links":links,"dir":str(p.get_pin_direction())}
        row["wiring"]=wiring
    if "GetComponentByClass" in row["title"] or "Component Class" in str([str(p.get_pin_name()) for p in bel.list_all_pins(n)]):
        for p in bel.list_all_pins(n):
            if "Class" in str(p.get_pin_name()) or "Component" in str(p.get_pin_name()):
                try: row[str(p.get_pin_name())]=p.get_pin_value()
                except: pass
                row[str(p.get_pin_name())+"_links"]=[title(c.get_owning_node()) for c in p.list_connected_pins()]
    if "BreakRotator" in row["title"]:
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) in ("Pitch","Yaw","Roll","InRot"):
                row[str(p.get_pin_name())]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
    chain.append(row)
    # follow then/execute outputs
    for p in bel.list_all_pins(n):
        pn=str(p.get_pin_name()).lower()
        if pn in ("then","execute","true","false","else","completed") or pn.startswith("then"):
            if "INPUT" in str(p.get_pin_direction()) and pn=="execute":
                continue
            if "OUTPUT" in str(p.get_pin_direction()) or pn in ("then","true","false","else"):
                for c in p.list_connected_pins():
                    if id(c.get_owning_node()) not in seen:
                        q.append(c.get_owning_node())
        # also Branch then pins
        if pn in ("then","true","false","else") and "OUTPUT" in str(p.get_pin_direction()):
            for c in p.list_connected_pins():
                q.append(c.get_owning_node())

REPORT["exec_chain"]=chain

# All MakeRotators in graph regardless of exec
makes=[]
for n in nodes:
    if "MakeRotator" not in title(n): continue
    w={}
    for p in bel.list_all_pins(n):
        pn=str(p.get_pin_name())
        links=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
        try: val=p.get_pin_value()
        except: val=""
        if links or pn in ("Pitch","Yaw","Roll","ReturnValue"):
            w[pn]={"val":str(val),"links":links}
    makes.append(w)
REPORT["all_makerotators"]=makes

# GetComponentByClass targets
comps=[]
for n in nodes:
    if "GetComponentByClass" not in title(n): continue
    row={"title":title(n)}
    for p in bel.list_all_pins(n):
        try: row[str(p.get_pin_name())]=p.get_pin_value()
        except: row[str(p.get_pin_name())]="?"
        row[str(p.get_pin_name())+"_L"]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
    comps.append(row)
REPORT["get_comp"]=comps

# Function entry Axis pins destinations
if entry:
    ax={}
    for p in bel.list_all_pins(entry):
        ax[str(p.get_pin_name())]=[title(c.get_owning_node())+"."+str(c.get_pin_name()) for c in p.list_connected_pins()]
    REPORT["entry_pins"]=ax

path=Path(unreal.Paths.project_saved_dir())/"DayNight"/"wasd_exec.json"
path.write_text(json.dumps(REPORT,default=str,indent=2),encoding="utf-8")
REPORT={"file":str(path),"chain_len":len(chain),"makes":len(makes),"entry":REPORT.get("entry_title")}
