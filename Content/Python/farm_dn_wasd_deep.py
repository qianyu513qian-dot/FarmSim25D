# -*- coding: utf-8 -*-
"""Deep dump MoveCharacter + IMC real keys + GetForward source."""
import unreal, json
from pathlib import Path

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
REPORT = {}

def pins(n):
    out=[]
    for p in bel.list_all_pins(n):
        try: val=p.get_pin_value()
        except: val=""
        links=[]
        for c in p.list_connected_pins():
            try: links.append(str(bel.get_node_title(c.get_owning_node()))+"."+str(c.get_pin_name()))
            except: links.append("?")
        out.append({"name":str(p.get_pin_name()),"dir":str(p.get_pin_direction()),"val":str(val)[:100],"links":links})
    return out

bp=unreal.load_asset(CHAR)
names=[str(x) for x in bel.list_graph_names(bp)]
REPORT["graphs"]=names

# Dump MoveCharacter graph fully
for gname in names:
    if "MoveCharacter" not in gname and gname != "MoveCharacter":
        continue
    ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,gname))
    nodes=[]
    for n in ge.list_all_nodes():
        nodes.append({"title":str(bel.get_node_title(n)),"class":n.get_class().get_name(),"pins":pins(n)})
    REPORT["MoveCharacter"]=nodes

# Also EventGraph GetForward/GetRight ownership + BreakVector2D
ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,"EventGraph"))
ev=[]
for n in ge.list_all_nodes():
    t=str(bel.get_node_title(n))
    if any(s in t for s in ("GetForward","GetRight","BreakVector","Get Camera","Camera","SpringArm","GetControl","GetActor","MakeRotator","Get Rotation","Component")):
        ev.append({"title":t,"class":n.get_class().get_name(),"pins":pins(n)})
REPORT["event_vecs"]=ev

# IMC keys via export_text on each mapping or FKey fields
imc=unreal.load_asset(IMC)
rows=[]
for m in imc.get_editor_property("mappings"):
    row={"action": m.get_editor_property("action").get_name() if m.get_editor_property("action") else "?"}
    key=m.get_editor_property("key")
    # try many accessors
    info={}
    for attr in ("key_name","KeyName","get_display_name","get_fkey","fkey"):
        try:
            v=getattr(key, attr)
            info[attr]=str(v() if callable(v) else v)
        except Exception as e:
            info[attr]="err:"+str(e)[:40]
    try:
        info["export"]=key.export_text()
    except Exception as e:
        info["export"]="err:"+str(e)[:60]
    try:
        info["str"]=str(key)
    except Exception:
        pass
    # UObject reflection on mapping
    try:
        info["mapping_export"]=m.export_text()
    except Exception as e:
        info["mapping_export"]=str(e)[:80]
    for pn in dir(key):
        if "key" in pn.lower() or "name" in pn.lower() or "display" in pn.lower():
            try:
                v=getattr(key,pn)
                if not pn.startswith("_"):
                    info["d_"+pn]=str(v() if callable(v) else v)[:80]
            except Exception:
                pass
    row["key_info"]=info
    mods=[]
    for md in (m.get_editor_property("modifiers") or []):
        mods.append(md.get_class().get_name())
    row["mods"]=mods
    rows.append(row)
REPORT["imc"]=rows

# Controller IMC assignment on BP_TopDownController
ctrl=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownController")
if not ctrl:
    ctrl=unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownPlayerController")
REPORT["controller_asset"]=str(ctrl.get_path_name()) if ctrl else None
if ctrl:
    cdo=unreal.get_default_object(ctrl.generated_class())
    for p in ("default_mapping_contexts","DefaultMappingContexts","input_mapping_context","mapping_context"):
        try:
            REPORT["ctrl_"+p]=str(cdo.get_editor_property(p))
        except Exception:
            pass
    # variables
    try:
        for vn in bel.list_member_variable_names(ctrl):
            if "map" in str(vn).lower() or "imc" in str(vn).lower() or "input" in str(vn).lower():
                try:
                    REPORT["ctrl_var_"+str(vn)]=str(cdo.get_editor_property(str(vn)))
                except Exception as e:
                    REPORT["ctrl_var_"+str(vn)]="err "+str(e)[:60]
    except Exception as e:
        REPORT["ctrl_vars_err"]=str(e)

path=Path(unreal.Paths.project_saved_dir())/"DayNight"/"wasd_deep.json"
path.write_text(json.dumps(REPORT,default=str,indent=2),encoding="utf-8")
REPORT={"file":str(path),"graphs":REPORT["graphs"],"move_node_count":len(REPORT.get("MoveCharacter") or []),"imc_count":len(rows),"controller":REPORT.get("controller_asset")}
