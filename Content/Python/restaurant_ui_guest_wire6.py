# -*- coding: utf-8 -*-
"""Fix K2_SetTimer defaults; set TintIndex on spawn via GuestMesh ApplyTint path; verify WBP/OrderBubble."""
import unreal, json

bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary

TBL = "/Game/Farm/Restaurant/BP_RestaurantTable"
GUEST = "/Game/Farm/Restaurant/BP_RestGuest"
MGR = "/Game/Farm/Restaurant/BP_RestaurantManager"

R = {"steps": []}

def log(m):
    unreal.log("[UI_W6] " + str(m)); print("[UI_W6] " + str(m)); R["steps"].append(str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def title(n):
    try: return str(bel.get_node_title(n))
    except Exception: return n.get_class().get_name()

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def find_event(ge, name_substr):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_Event" and name_substr in title(n):
            return n
    return None

def walk_then(start, max_d=40):
    thenp = find_pin(start, "then", "Output")
    queue = [(c.get_owning_node(), 0) for c in (thenp.list_connected_pins() if thenp else [])]
    seen = []; ids = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in ids or d > max_d: continue
        ids.add(id(cur)); seen.append(cur)
        for pn in ("then", "else", "Completed", "LoopBody"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in tp.list_connected_pins() or []:
                    queue.append((c.get_owning_node(), d + 1))
    return seen

def pin_default(pin):
    if not pin: return None
    for fn in ("get_default_as_string", "get_default_value"):
        if hasattr(pin, fn):
            try: return str(getattr(pin, fn)())
            except Exception: pass
    return "?"

def setdef(pin, val):
    if not pin: return False
    # Try BlueprintEditorLibrary helpers
    for fn_name in ("set_pin_default_value", "set_node_pin_default"):
        if hasattr(bel, fn_name):
            try:
                getattr(bel, fn_name)(pin, str(val)); return True
            except Exception as e:
                log(fn_name + " " + str(e)[:60])
    for fn in ("set_pin_value", "set_default_value", "set_default_as_string"):
        if hasattr(pin, fn):
            try:
                getattr(pin, fn)(str(val)); return True
            except Exception as e:
                log(fn + " " + str(e)[:60])
    # autograph
    try:
        pin.make_link_to  # exists?
    except Exception:
        pass
    try:
        unreal.BlueprintEditorLibrary  # 
        # EdGraphSchema
        schema = unreal.EdGraphSchema_K2()
        if hasattr(schema, "try_set_default_value"):
            schema.try_set_default_value(pin, str(val), True); return True
    except Exception as e:
        log("schema " + str(e)[:80])
    return False

# Probe pin set APIs
tbp = unreal.load_asset(TBL)
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(tbp, "EventGraph"))
apis = [a for a in dir(tge) if "default" in a.lower() or "pin" in a.lower()]
log("ge pin apis: " + str(apis))
bel_apis = [a for a in dir(bel) if "default" in a.lower() or "pin" in a.lower()]
log("bel pin apis: " + str(bel_apis))

# Find SetTimer node and fix
for n in tge.list_all_nodes():
    if "SetTimer" in title(n) or title(n) == "Set Timer by Function Name":
        log("Found timer: " + title(n))
        for p in bel.list_all_pins(n):
            log("  before {} = {}".format(p.get_pin_name(), repr(pin_default(p))))
        # Try ge method
        for pname, val in (("FunctionName", "RefreshTableBubble"), ("Time", "0.2"), ("bLooping", "true")):
            p = find_pin(n, pname, "Input")
            if p is None: continue
            ok = False
            if hasattr(tge, "set_pin_default_value"):
                try:
                    tge.set_pin_default_value(p, str(val)); ok = True
                except Exception as e:
                    log("ge.set_pin_default_value " + str(e)[:80])
            if not ok and hasattr(tge, "set_node_pin_default_value"):
                try:
                    tge.set_node_pin_default_value(n, pname, str(val)); ok = True
                except Exception as e:
                    log("ge.set_node_pin " + str(e)[:80])
            if not ok:
                ok = setdef(p, val)
            log("  set {} -> {} ok={} now={}".format(pname, val, ok, repr(pin_default(p))))

# Also fix ApplyTint to use GuestMesh instead of GetComponentByClass for reliability
gbp = unreal.load_asset(GUEST)
gge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(gbp, "EventGraph"))
at = find_custom(gge, "ApplyTint")
# Find SetMaterial nodes and ensure self comes from GuestMesh
get_mesh = None
for n in gge.list_all_nodes():
    if title(n) == "Get GuestMesh":
        get_mesh = n; break
if get_mesh is None:
    get_mesh = gge.add_get_member_variable_node("GuestMesh")
    bel.set_node_pos(get_mesh, pos(-700, 550))

if at:
    for n in walk_then(at, 20):
        if title(n) == "SetMaterial":
            sp = find_pin(n, "self", "Input")
            if sp:
                # break and reconnect to GuestMesh
                try: sp.break_pin_links()
                except Exception: pass
                outp = find_pin(get_mesh, "GuestMesh", "Output") or list(bel.list_all_pins(get_mesh))[0]
                ok = outp.try_create_connection(sp) if outp else False
                log("SetMaterial <- GuestMesh " + str(ok))
            # ElementIndex
            ep = find_pin(n, "ElementIndex", "Input") or find_pin(n, "Index", "Input")
            if ep and hasattr(tge, "set_pin_default_value"):
                pass
            setdef(ep, "1")
            log("ElementIndex now=" + repr(pin_default(ep)))
            mp = find_pin(n, "Material", "Input")
            log("Material now=" + repr(pin_default(mp)))

# Verify GetAllActors ActorClass on Manager via OutActors type (already typed)
mbp = unreal.load_asset(MGR)
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(mbp, "EventGraph"))
for n in mge.list_all_nodes():
    if "GetAllActorsOfClass" in title(n):
        cp = find_pin(n, "ActorClass", "Input")
        log("GetAllActors ActorClass=" + repr(pin_default(cp)))
        # force set via ge
        path = unreal.load_asset(TBL).generated_class().get_path_name()
        if hasattr(mge, "set_pin_default_value"):
            try:
                mge.set_pin_default_value(cp, path); log("ge set ActorClass OK")
            except Exception as e:
                log("ge set ActorClass " + str(e)[:80])
        setdef(cp, path)
        log("ActorClass after=" + repr(pin_default(cp)))
        for p in bel.list_all_pins(n):
            if "OutActors" in str(p.get_pin_name()):
                log("OutActors type=" + str(p.get_pin_type_display_string()))

# OrderBubble component check on Table CDO
tbp = unreal.load_asset(TBL)
# defaults
try:
    cdo = unreal.get_default_object(tbp.generated_class())
    log("Table CDO=" + str(cdo))
except Exception as e:
    log("cdo " + str(e))

# WBP structure
for wpath in ("/Game/Farm/UI/WBP_RestOrderList", "/Game/Farm/UI/WBP_RestOrderBubble"):
    w = unreal.load_asset(wpath)
    log("WBP " + wpath + " " + str(w))
    try:
        # WidgetTree
        wt = w.widget_tree if hasattr(w, "widget_tree") else None
        log("  widget_tree=" + str(wt))
    except Exception as e:
        log("  " + str(e))

bel.compile_blueprint(tbp); eas.save_asset(TBL)
bel.compile_blueprint(gbp); eas.save_asset(GUEST)
bel.compile_blueprint(mbp); eas.save_asset(MGR)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

for path, key in ((TBL, "table"), (MGR, "mgr"), (GUEST, "guest")):
    bp = unreal.load_asset(path)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
    errs = [title(n) for n in (ge.list_nodes_with_errors() or [])]
    R[key + "_err"] = errs
    log("{} err={}".format(key, errs))

# Re-read timer
tge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(unreal.load_asset(TBL), "EventGraph"))
for n in tge.list_all_nodes():
    if "Timer" in title(n):
        for p in bel.list_all_pins(n):
            if "INPUT" in str(p.get_pin_direction()):
                log("timer final {}={}".format(p.get_pin_name(), repr(pin_default(p))))

out = unreal.Paths.project_saved_dir() + "RestaurantUI_wire6_report.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2)
log("ALL_DONE " + out)
