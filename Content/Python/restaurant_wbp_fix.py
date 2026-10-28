# -*- coding: utf-8 -*-
"""Fix WBP_RestOrderList: rename TxtTitle back to TxtMoney so FarmHUD EventGraph compiles."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
PATH = "/Game/Farm/UI/WBP_RestOrderList"
BUB = "/Game/Farm/UI/WBP_RestOrderBubble"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"
TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
R = {"steps": []}

def log(m):
    unreal.log("[WBPFIX3] " + str(m)); print("[WBPFIX3] " + str(m)); R["steps"].append(str(m))

def status_of(bp):
    try:
        return str(bp.get_editor_property("status"))
    except Exception as e:
        return str(e)

wbp = unreal.load_asset(PATH)
R["status_before"] = status_of(wbp)

# Find TxtTitle and rename to TxtMoney
renamed = False
for o in unreal.ObjectIterator(unreal.Widget):
    pn = o.get_path_name()
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." not in pn:
        continue
    name = o.get_name()
    if name == "TxtTitle":
        try:
            o.rename("TxtMoney")
            log("renamed TxtTitle -> TxtMoney via rename()")
            renamed = True
        except Exception as e:
            log("rename() failed: " + str(e))
            # try SubobjectDataSubsystem or set_editor_property
            try:
                # WidgetBlueprintEditorUtils style - force name via Package rename
                ok = unreal.EditorAssetLibrary.rename_asset  # wrong
            except Exception:
                pass
            try:
                # BlueprintEditorLibrary has no rename widget; use Object.rename with flags
                import unreal as u
                # Some UE builds: o.rename(new_name, outer)
                o.rename("TxtMoney", o.get_outer())
                log("renamed with outer")
                renamed = True
            except Exception as e2:
                log("rename2 failed: " + str(e2))

# Verify widgets after rename
widgets = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets[o.get_name()] = o.get_class().get_name()
R["widgets_after_rename"] = widgets
log("widgets=" + str(widgets))

if "TxtMoney" not in widgets:
    # Fallback: create a new TxtMoney TextBlock under HUDLayout and leave TxtTitle
    log("TxtMoney still missing — creating new TextBlock TxtMoney")
    tree = unreal.load_object(wbp, "WidgetTree")
    layout = None
    for o in unreal.ObjectIterator(unreal.VerticalBox):
        if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree.HUDLayout" in o.get_path_name():
            layout = o
            break
    tb = unreal.new_object(unreal.TextBlock, tree, "TxtMoney")
    try:
        tb.set_text("\u8ba2\u5355")
    except Exception:
        try:
            tb.set_editor_property("text", "\u8ba2\u5355")
        except Exception as e:
            log("set text " + str(e))
    if layout:
        try:
            layout.add_child_to_vertical_box(tb)
            log("added TxtMoney to HUDLayout")
        except Exception as e:
            log("add child " + str(e))
    # collapse it if title already exists — EventGraph only needs the var for SetText
    try:
        # keep visible as title substitute if TxtTitle exists collapsed farm texts
        pass
    except Exception:
        pass
    renamed = True

# Also check: if both TxtTitle and TxtMoney exist after create, fine.
# Compile
bel.compile_blueprint(wbp)
R["status_after_compile1"] = status_of(wbp)
log("status after compile1=" + R["status_after_compile1"])

# If still error, strip broken Get TxtMoney nodes instead
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(wbp))
err_nodes = list(ge.list_nodes_with_errors() or [])
R["err_after1"] = []
for n in err_nodes:
    t = str(bel.get_node_title(n))
    msg = None
    try:
        msg = str(n.get_editor_property("error_msg"))[:200]
    except Exception:
        pass
    R["err_after1"].append({"title": t, "msg": msg})
    log("still err: {} | {}".format(t, msg))

if err_nodes:
    # Surgical: replace Get TxtMoney with Get TxtTitle if TxtTitle exists, else remove SetText chain for money
    kill = []
    for n in list(ge.list_all_nodes()):
        if n.get_class().get_name() != "K2Node_VariableGet":
            continue
        if "TxtMoney" not in str(bel.get_node_title(n)):
            continue
        # Find consumers of the output pin
        outp = None
        for p in bel.list_all_pins(n):
            if "OUTPUT" in str(p.get_pin_direction()):
                outp = p
                break
        consumers = list(outp.list_connected_pins() or []) if outp else []
        # If TxtTitle exists, add Get TxtTitle and reconnect
        if "TxtTitle" in widgets or any(o.get_name()=="TxtTitle" for o in unreal.ObjectIterator(unreal.Widget) if "WBP_RestOrderList" in o.get_path_name()):
            try:
                neu = ge.add_variable_get_node("TxtTitle")
            except Exception as e:
                log("add_variable_get_node " + str(e))
                neu = None
            if neu is None:
                # try create member reference differently
                try:
                    neu = ge.add_node_to_graph  # won't work
                except Exception:
                    pass
            if neu is not None:
                new_out = None
                for p in bel.list_all_pins(neu):
                    if "OUTPUT" in str(p.get_pin_direction()):
                        new_out = p
                        break
                if outp:
                    outp.break_pin_links()
                for c in consumers:
                    if new_out:
                        new_out.try_create_connection(c)
                        log("rewired consumer to TxtTitle")
                kill.append(n)
            else:
                # Just remove the Get and break links — disconnect SetText target
                if outp:
                    outp.break_pin_links()
                kill.append(n)
                log("broke links on Get TxtMoney (no TxtTitle get)")
        else:
            if outp:
                outp.break_pin_links()
            kill.append(n)
            log("removing Get TxtMoney")
    if kill:
        ge.remove_nodes(kill)
        log("removed {} broken nodes".format(len(kill)))
    bel.compile_blueprint(wbp)
    R["status_after_compile2"] = status_of(wbp)
    err2 = []
    for n in (ge.list_nodes_with_errors() or []):
        err2.append(str(bel.get_node_title(n)))
    R["err_after2"] = err2
    log("status2={} err={}".format(R["status_after_compile2"], err2))

# Final widgets
widgets2 = {}
for o in unreal.ObjectIterator(unreal.Widget):
    if "WBP_RestOrderList.WBP_RestOrderList:WidgetTree." in o.get_path_name():
        widgets2[o.get_name()] = o.get_class().get_name()
R["widgets_final"] = widgets2

# Save and compile related
eas.save_asset(PATH)
for p in (BUB, MGR, TBL, GUEST):
    bp = unreal.load_asset(p)
    bel.compile_blueprint(bp)
    eas.save_asset(p)
    R[p] = status_of(bp)
    log("{} status={}".format(p, R[p]))

# Final status list
for p in (PATH, BUB, MGR, TBL, GUEST):
    bp = unreal.load_asset(p)
    st = status_of(bp)
    # list_nodes_with_errors
    try:
        ge2 = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
        errs = [str(bel.get_node_title(n)) for n in (ge2.list_nodes_with_errors() or [])]
    except Exception as e:
        errs = ["ge:" + str(e)[:80]]
    R.setdefault("final", {})[p] = {"status": st, "errs": errs}
    log("FINAL {} {} errs={}".format(p, st, errs))

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

out = unreal.Paths.project_saved_dir() + "WBP_RestOrder_fix_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("WROTE " + out)
