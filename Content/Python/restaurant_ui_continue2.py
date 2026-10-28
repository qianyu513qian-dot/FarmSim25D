# -*- coding: utf-8 -*-
"""Dup FarmHUD via AssetTools; probe mesh; check slot layout API on existing HUD."""
import unreal

def log(m):
    unreal.log("[UI_C2] " + str(m))
    print("[UI_C2] " + str(m))

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

src = "/Game/Farm/UI/WBP_FarmHUD"
dst_dir = "/Game/Farm/UI"
dst_name = "WBP_RestOrderList"
dst = dst_dir + "/" + dst_name
if eas.does_asset_exist(dst):
    eas.delete_asset(dst)

# Try AssetTools duplicate
try:
    # duplicate_asset(asset_name, package_path, original)
    out = tools.duplicate_asset(dst_name, dst_dir, unreal.load_asset(src))
    log("tools.duplicate=" + str(out))
except Exception as e:
    log("tools.dup " + str(e))
    try:
        out = eas.duplicate_asset(src, dst)
        log("eas.dup2=" + str(out))
    except Exception as e2:
        log("eas.dup2 " + str(e2))

log("exist=" + str(eas.does_asset_exist(dst)))

# Canvas slot props on FarmHUD
canvas = None
for o in unreal.ObjectIterator(unreal.CanvasPanel):
    if "WBP_FarmHUD.WBP_FarmHUD:WidgetTree.HUDCanvas" in o.get_path_name():
        canvas = o
        break
log("canvas=" + str(canvas))
if canvas:
    # get child slots
    try:
        slots = canvas.get_slots()
        log("get_slots=" + str(slots) + " len=" + str(len(list(slots or []))))
        for s in list(slots or [])[:3]:
            log(" slot class=" + s.get_class().get_name() + " dirs=" + str([x for x in dir(s) if not x.startswith('_')][:40]))
            for prop in ("layout_data", "LayoutData", "bAutoSize", "auto_size", "z_order", "ZOrder"):
                try:
                    log("  {}={}".format(prop, s.get_editor_property(prop)))
                except Exception as e:
                    pass
            try:
                ld = s.get_editor_property("layout_data")
                log("  layout_data type=" + str(type(ld)) + " " + str([x for x in dir(ld) if not x.startswith('_')]))
                try:
                    log("  ld export=" + ld.export_text()[:400])
                except Exception as e:
                    log("  ld exp " + str(e))
            except Exception as e:
                log("  ld " + str(e))
    except Exception as e:
        log("slots " + str(e))

# TextBlock font on FarmHUD TxtMoney
for o in unreal.ObjectIterator(unreal.TextBlock):
    if "WBP_FarmHUD.WBP_FarmHUD:WidgetTree.TxtMoney" in o.get_path_name():
        fi = o.get_editor_property("font")
        log("TxtMoney font export=" + fi.export_text()[:500])
        log("TxtMoney text=" + str(o.get_text() if hasattr(o,"get_text") else o.get_editor_property("text")))
        break

# Character skeletal mesh
for o in unreal.ObjectIterator(unreal.SkeletalMeshComponent):
    pn = o.get_path_name()
    if "BP_TopDownCharacter" in pn and "Default__" not in pn and "SKEL_" not in pn:
        if "GEN_VARIABLE" in pn or pn.endswith("Mesh") or ".Mesh" in pn:
            log("SKC " + pn)
            for prop in ("skeletal_mesh_asset", "SkeletalMeshAsset"):
                try:
                    v = o.get_editor_property(prop)
                    log("  {}={}".format(prop, v.get_path_name() if v else None))
                    if v:
                        try:
                            mats = v.materials
                        except Exception:
                            mats = None
                        try:
                            mats = v.get_editor_property("materials")
                        except Exception:
                            pass
                        log("  materials=" + str(mats))
                        if mats:
                            for i, m in enumerate(list(mats)[:8]):
                                try:
                                    mi = m.get_editor_property("material_interface") if hasattr(m,"get_editor_property") else m
                                    log("   [{}] {}".format(i, mi.get_path_name() if hasattr(mi,"get_path_name") else mi))
                                except Exception as e:
                                    log("   [{}] {}".format(i, m))
                except Exception as e:
                    log("  {} {}".format(prop, e))

# Patience defaults - scan Set PatienceLeft pin defaults
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
for n in ge.list_all_nodes():
    if str(bel.get_node_title(n)) != "Set PatienceLeft":
        continue
    for p in bel.list_all_pins(n):
        pn = str(p.get_pin_name())
        if pn == "PatienceLeft":
            try:
                log("SetPatience pin connected={} val={!r}".format(bool(p.list_connected_pins()), p.get_default_value() if hasattr(p,"get_default_value") else p.get_pin_value()))
            except Exception as e:
                try:
                    log("SetPatience val={!r}".format(p.get_pin_value()))
                except Exception as e2:
                    log("SetPatience " + str(e2))

# How is FarmHUD created on character?
cbp = unreal.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(cbp, "EventGraph"))
for n in cge.list_all_nodes():
    t = str(bel.get_node_title(n))
    c = n.get_class().get_name()
    if "Create" in t or "Viewport" in t or "FarmHUD" in t or "Widget" in c or "CreateWidget" in c:
        log("CharHUD node: {} | {}".format(t, c))

log("DONE_C2")
