# -*- coding: utf-8 -*-
import unreal
bel = unreal.BlueprintEditorLibrary
TAG="[PROBE_EG]"
def log(m):
    unreal.log(TAG+" "+str(m)); print(TAG+" "+str(m))

bp = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Grid/BP_GridManager")
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
for n in ge.list_all_nodes():
    try: title = str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
    except: title = n.get_class().get_name()
    pins=[]
    for p in bel.list_all_pins(n):
        try: val=p.get_pin_value()
        except:
            try: val=p.get_default_as_string()
            except: val=""
        linked=[]
        try:
            for lp in p.get_linked_to():
                linked.append(str(lp.get_owning_node().get_class().get_name())+":"+str(lp.get_pin_name()))
        except: pass
        pins.append("{} dir={} val={!r} links={}".format(p.get_pin_name(), p.get_pin_direction(), val, linked[:3]))
    log("NODE {} cls={}".format(title, n.get_class().get_name()))
    for pi in pins:
        log("  "+pi)

# Enum via asset data / package export
ude = unreal.load_asset("/Game/Farm/Grid/E_PlotState")
# Try call_method
for meth in ("GetNumEnums","GetDisplayNameTextByIndex","GetNameStringByIndex","GetNameByValue"):
    try:
        r = ude.call_method(meth, (0,) if "Index" in meth or "Value" in meth else ())
        log("call {} -> {}".format(meth, r))
    except Exception as e:
        log("call {} err {}".format(meth, e))

# Try reading .uasset as text? no
# Use EnumAsset or AssetTools
try:
    # DisplayNameMap might be map property with different casing
    for prop in ude.get_editor_property.__doc__:
        pass
except: pass

# Dump via unreal.EditorAssetLibrary.find_asset_data
ad = unreal.EditorAssetLibrary.find_asset_data("/Game/Farm/Grid/E_PlotState")
log("asset_data="+str(ad))
try:
    log("tags="+str(ad.get_tag_value_names() if hasattr(ad,"get_tag_value_names") else "n/a"))
except Exception as e:
    log("tags err "+str(e))

# Check CDO default PlotStates and enum var type
try:
    gc = bp.generated_class()
    cdo = unreal.get_default_object(gc)
    log("CDO="+str(cdo))
    for pname in ("PlotStates","CellSize","GridWidth","GridHeight","LitTilled","LitEmpty","LitPlanted","LitWatered","LitGrown","LitBlocked"):
        try:
            v = cdo.get_editor_property(pname)
            log("CDO.{}={}".format(pname, v if pname!="PlotStates" else ("len="+str(len(v) if v else 0))))
        except Exception as e:
            log("CDO.{} missing {}".format(pname, e))
except Exception as e:
    log("CDO err "+str(e))

# VisualizeCell State pin values / ApplyState
vg = bel.find_graph(bp, "VisualizeCell")
if vg:
    vge = unreal.BlueprintGraphEditor.get_graph_editor(vg)
    for n in vge.list_all_nodes():
        try: title=str(n.get_node_title(unreal.NodeTitleType.FULL_TITLE))
        except: title=n.get_class().get_name()
        if any(k in title for k in ("Switch","Equal","State","Enum","Branch","Item","Lit")):
            vals=[]
            for p in bel.list_all_pins(n):
                try: vals.append("{}={!r}".format(p.get_pin_name(), p.get_pin_value()))
                except: pass
            log("Viz "+title+" "+str(vals[:8]))

# How was enum created - check file
log("enum path="+ude.get_path_name())
log("DONE")
