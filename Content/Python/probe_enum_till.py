# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
TAG="[PROBE_ENUM]"
def log(m):
    unreal.log(TAG+" "+str(m)); print(TAG+" "+str(m))

# Enum
ude = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/E_PlotState")
log("ude="+str(ude)+" cls="+ude.get_class().get_name())
# UserDefinedEnum API
try:
    n = ude.get_editor_property("NumEnums")
    log("NumEnums="+str(n))
except Exception as e:
    log("NumEnums err "+str(e))
try:
    names = ude.get_editor_property("Names")
    log("Names="+str(names))
except Exception as e:
    log("Names err "+str(e))
# try EnumEditorUtils / AssetEditor
try:
    for i in range(12):
        try:
            dn = unreal.UserDefinedEnum.get_display_name_text_by_index(ude, i) if hasattr(unreal.UserDefinedEnum, "get_display_name_text_by_index") else None
        except: dn=None
        try:
            # C++ UUserDefinedEnum::GetDisplayNameTextByIndex via python
            t = ude.get_display_name_text_by_index(i)
            log("idx{} display={}".format(i, t))
        except Exception as e:
            try:
                # alternate
                pass
            except: pass
            if i==0: log("get_display fail "+str(e))
except Exception as e:
    log("loop "+str(e))

# Dump via export text
try:
    log("export="+unreal.EditorAssetLibrary.duplicate_asset.__doc__[:20])
except: pass

# Use AssetRegistry / object flags
try:
    obj = unreal.load_asset("/Game/Farm/Grid/E_PlotState")
    # iterate Python attrs
    attrs = [a for a in dir(obj) if not a.startswith("_")]
    log("attrs sample="+str(attrs[:40]))
    for meth in ("get_display_name_text_by_index","get_name_by_value","get_value_by_name","get_enum_entries","get_enums"):
        if hasattr(obj, meth):
            log("HAS "+meth)
except Exception as e:
    log("dir "+str(e))

# Try unreal.Enum
try:
    # Generated enum path
    ecls = unreal.load_object(None, "/Game/Farm/Grid/E_PlotState.E_PlotState")
    log("ecls="+str(ecls))
except Exception as e:
    log("ecls "+str(e))

# BP_GridManager graphs / functions
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
log("bp="+str(bp))
try:
    graphs = bel.get_all_graphs(bp) if hasattr(bel, "get_all_graphs") else []
    log("graphs via get_all_graphs="+str([g.get_name() for g in graphs] if graphs else graphs))
except Exception as e:
    log("get_all_graphs "+str(e))

# list function graphs by known names
for fn in ("TillCell","PlantCell","WaterCell","GrowCell","HarvestCell","BeginPlay","IsValidCell","WorldToGrid","GridToWorld","GetPlotState","SetPlotState","InitBlockedCells","VisualizeCell","HideGrassAt","ShowGrassAt"):
    g = bel.find_graph(bp, fn)
    log("graph {} = {}".format(fn, g.get_name() if g else None))

# EventGraph BeginPlay - dump nodes with Blocked/PlotStates
eg = bel.find_graph(bp, "EventGraph")
if eg:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
    nodes = ge.list_all_nodes()
    log("EG nodes={}".format(len(nodes)))
    for n in nodes:
        title = ""
        try: title = n.get_node_title(unreal.NodeTitleType.FULL_TITLE)
        except:
            try: title = str(n.get_class().get_name())
            except: title = "?"
        ts = str(title)
        if any(k in ts for k in ("BeginPlay","PlotState","Blocked","Resize","Init","Till","Empty","Set Array")):
            log("EG node: "+ts)

# TillCell dump
tg = bel.find_graph(bp, "TillCell")
if tg:
    ge = unreal.BlueprintGraphEditor.get_graph_editor(tg)
    for n in ge.list_all_nodes():
        try: title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except: title = n.get_class().get_name()
        pins_info = []
        for p in bel.list_all_pins(n):
            try:
                val = p.get_default_as_string() if hasattr(p,"get_default_as_string") else p.get_pin_value()
            except:
                try: val = p.get_pin_value()
                except: val = ""
            if val not in (None, "", "None"):
                pins_info.append("{}={}".format(p.get_pin_name(), val))
        log("TillCell node: {} | {}".format(title, pins_info[:6]))

# Grid manager instance props
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if "GridManager" in (a.get_actor_label() or "") or "GridManager" in a.get_class().get_name():
        for pname in ("CellSize","GridWidth","GridHeight","GridOrigin"):
            try: log("GM.{}={}".format(pname, a.get_editor_property(pname)))
            except Exception as e: log("GM.{} {}".format(pname,e))
        try:
            ps = a.get_editor_property("PlotStates")
            log("PlotStates type={} len={}".format(type(ps).__name__, len(ps) if ps is not None else None))
            if ps is not None and len(ps)>0:
                log("PlotStates[0]={}".format(ps[0]))
        except Exception as e:
            log("PS "+str(e))

# Water plane scale
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab == "VMF_Water_Left":
        loc=a.get_actor_location(); sc=a.get_actor_scale3d(); rot=a.get_actor_rotation()
        o,e = a.get_actor_bounds(False)
        log("Water loc={} scale={} rot={} origin={} extent={}".format(loc, sc, rot, o, e))

# Missing grass under soil?
grass=set(); soil=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_Grass_") and "Clump" not in lab:
        parts=lab.split("_")
        try: grass.add((int(parts[-2]), int(parts[-1])))
        except: pass
    if lab.startswith("VMF_Soil_"):
        parts=lab.split("_")
        try: soil.append((int(parts[-2]), int(parts[-1])))
        except: pass
miss=[c for c in soil if c not in grass]
log("soil={} grass_under_soil_missing={}/{} {}".format(len(soil), len(miss), len(soil), miss[:30]))

# Path cell set from labels
path_cells=[]; bridge_cells=[]; cliff_cells=[]; yard_cells=[]
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    parts=lab.split("_")
    try:
        c=(int(parts[-2]), int(parts[-1]))
    except:
        continue
    if lab.startswith("VMF_Path"):
        path_cells.append(c)
    elif lab.startswith("VMF_Bridge"):
        bridge_cells.append(c)
    elif lab.startswith("VMF_Cliff_"):
        cliff_cells.append(c)
    elif lab.startswith("VMF_Yard_"):
        yard_cells.append(c)
log("path_cells={} uniq={}".format(len(path_cells), len(set(path_cells))))
log("bridge_cells={} uniq={}".format(len(bridge_cells), len(set(bridge_cells))))
log("cliff_cells={} uniq={}".format(len(cliff_cells), len(set(cliff_cells))))
log("yard_cells={} uniq={}".format(len(yard_cells), len(set(yard_cells))))
log("DONE")
