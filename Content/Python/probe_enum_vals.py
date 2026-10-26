# -*- coding: utf-8 -*-
import unreal
ude = unreal.load_asset("/Game/Farm/Grid/E_PlotState")
# Try Kismet Enum / Blueprint libraries
for libname in ("UserDefinedEnumEditorLibrary", "EnumEditorLibrary", "UserDefinedEnumLibrary", "KismetEnumLibrary"):
    if hasattr(unreal, libname):
        unreal.log("[E] has "+libname+" dir="+str([x for x in dir(getattr(unreal,libname)) if not x.startswith("_")])[:500])

# Dump via AssetExport / Text
try:
    # Names are FName list on UEnum
    # In UE5 python: unreal.EnumBase doesn't wrap UDE well
    # Try get_editor_property with every possible name
    for p in ("EnumDisplayNameFn","EnumDisplayNameMap","DisplayNameMap","Names","Enums","EnumNames","Entries"):
        try:
            unreal.log("[E] prop {}={}".format(p, ude.get_editor_property(p)))
        except Exception as ex:
            pass
except Exception as e:
    unreal.log(str(e))

# Use unreal.EditorAssetLibrary.save + read generated header? 
# Alternative: create temp BP variable of enum type and list pin enum values
bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
bel = unreal.BlueprintEditorLibrary
# list member vars and their pin types
try:
    names = bel.list_member_variable_names(bp)
    unreal.log("[E] members="+str(list(names)[:40]))
except Exception as e:
    unreal.log("[E] members err "+str(e))

# TillCell Equal B default
tg = bel.find_graph(bp, "TillCell")
ge = unreal.BlueprintGraphEditor.get_graph_editor(tg)
for n in ge.list_all_nodes():
    if "Promotable" in n.get_class().get_name() or "Equal" in n.get_class().get_name().lower():
        for p in bel.list_all_pins(n):
            unreal.log("[E] eq pin {} val={!r} type={}".format(p.get_pin_name(), p.get_pin_value(), p.get_pin_type_display_string()))

# PlantCell Item values
for fn in ("PlantCell","WaterCell","GrowCell","HarvestCell"):
    g = bel.find_graph(bp, fn)
    if not g: continue
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    for n in ge.list_all_nodes():
        if "Array" in n.get_class().get_name() or "equal" in n.get_class().get_name().lower() or "Promotable" in n.get_class().get_name():
            for p in bel.list_all_pins(n):
                pn=str(p.get_pin_name())
                try: val=p.get_pin_value()
                except: val=""
                if val not in ("", None) and pn in ("Item","B","A","NewItem","Index","State"):
                    unreal.log("[E] {} node={} {}={!r}".format(fn, n.get_class().get_name(), pn, val))

# VisualizeCell ApplyState switch
vg = bel.find_graph(bp, "VisualizeCell")
ge = unreal.BlueprintGraphEditor.get_graph_editor(vg)
for n in ge.list_all_nodes():
    try: t=str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
    except: t=n.get_class().get_name()
    if "Switch" in t or "Equal" in t.lower() or "State" in t or "Enum" in t:
        vals=[]
        for p in bel.list_all_pins(n):
            try: vals.append("{}={!r}".format(p.get_pin_name(), p.get_pin_value()))
            except: pass
        unreal.log("[E] Viz "+t+" "+str(vals[:10]))

unreal.log("[E] DONE")
