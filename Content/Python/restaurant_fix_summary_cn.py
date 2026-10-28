# -*- coding: utf-8 -*-
"""Fix PrintDayEndSummary Chinese literals via unicode escapes."""
import unreal, json
bel = unreal.BlueprintEditorLibrary
eas = unreal.EditorAssetLibrary
R = {"steps": [], "ok": []}

def log(m):
    unreal.log("[SUMFIX] " + str(m)); print("[SUMFIX] " + str(m)); R["steps"].append(str(m))

def title(n):
    try: return str(bel.get_node_title(n))
    except: return n.get_class().get_name()

def find_pin(node, substr, direction=None):
    if not node: return None
    substr = substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def find_custom(ge, name):
    for n in ge.list_all_nodes():
        if n.get_class().get_name() == "K2Node_CustomEvent" and title(n) == name:
            return n
    return None

def setdef(pin, val):
    if not pin: return False
    try:
        pin.set_pin_value(str(val)); return True
    except Exception:
        try:
            pin.set_default_value(str(val)); return True
        except Exception as e:
            log("setdef " + str(e)[:60]); return False

mbp = eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
mge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
ev = find_custom(mge, "PrintDayEndSummary")

# Collect Append nodes reachable from PrintDayEndSummary
seen = set(); q = [ev]; nodes = []
while q:
    cur = q.pop(0)
    if not cur or id(cur) in seen: continue
    seen.add(id(cur)); nodes.append(cur)
    for p in bel.list_all_pins(cur):
        for c in (p.list_connected_pins() or []):
            q.append(c.get_owning_node())

# Desired literals (unicode escapes):
# prefix: 打烊 | 今日餐厅营收 $
PREFIX = "\u6253\u70c8 | \u4eca\u65e5\u9910\u5385\u8425\u6536 $"
# mid:  | 服务 
MID = " | \u670d\u52a1 "
# suffix:  桌
SUFFIX = " \u684c"

# Walk append chain: identify by structure
# First Append (A=prefix literal, B=ToString float)
# Then Append (A=prev, B=mid literal)
# Then Append (A=prev, B=ToString int)
# Then Append (A=prev, B=suffix)

fixed = 0
for n in nodes:
    if "Append" not in title(n) and "Concat" not in title(n):
        continue
    ap = find_pin(n, "A", "Input")
    bp = find_pin(n, "B", "Input")
    a_links = (ap.list_connected_pins() or []) if ap else []
    b_links = (bp.list_connected_pins() or []) if bp else []
    # Case 1: A is literal (no links), B linked to To String Float -> PREFIX
    if not a_links and b_links and "To String" in title(b_links[0].get_owning_node()) and "Float" in title(b_links[0].get_owning_node()) or (not a_links and b_links and "Float" in title(b_links[0].get_owning_node())):
        setdef(ap, PREFIX); fixed += 1; log("set PREFIX"); R["ok"].append("PREFIX")
        continue
    # Case 2: B is literal-ish with mid, A linked
    if a_links and not b_links:
        # Check current B value length / content heuristically via neighbors
        # Look at what B currently is - if mid-like (has | ) or suffix-like
        try:
            bv = str(bp.get_pin_value()) if hasattr(bp, "get_pin_value") else ""
        except:
            bv = ""
        # Mid contains pipe+spaces pattern typically " | "
        # Suffix is short
        # Also check next: if ReturnValue feeds Append whose B is ToString Int -> this is MID
        rv = find_pin(n, "ReturnValue", "Output")
        nexts = [c.get_owning_node() for c in (rv.list_connected_pins() or [])] if rv else []
        is_before_count = False
        for nx in nexts:
            if "Append" in title(nx) or "Concat" in title(nx):
                nbp = find_pin(nx, "B", "Input")
                nbl = (nbp.list_connected_pins() or []) if nbp else []
                if nbl and "Integer" in title(nbl[0].get_owning_node()):
                    is_before_count = True
        # If B has no links and Return feeds PrintString -> SUFFIX
        feeds_print = any(title(nx) == "PrintString" for nx in nexts)
        if is_before_count:
            setdef(bp, MID); fixed += 1; log("set MID"); R["ok"].append("MID")
        elif feeds_print:
            setdef(bp, SUFFIX); fixed += 1; log("set SUFFIX"); R["ok"].append("SUFFIX")
        else:
            # fallback: short string -> suffix, else mid
            if len(bv) <= 4:
                setdef(bp, SUFFIX); fixed += 1; log("set SUFFIX fb"); R["ok"].append("SUFFIX_fb")
            else:
                setdef(bp, MID); fixed += 1; log("set MID fb"); R["ok"].append("MID_fb")

# Also fix PREFIX case when B links to "To String (Float)" - handle separately if missed
for n in nodes:
    if "Append" not in title(n) and "Concat" not in title(n):
        continue
    ap = find_pin(n, "A", "Input")
    bp = find_pin(n, "B", "Input")
    a_links = (ap.list_connected_pins() or []) if ap else []
    b_links = (bp.list_connected_pins() or []) if bp else []
    if not a_links and b_links:
        bt = title(b_links[0].get_owning_node())
        if "Float" in bt or "Double" in bt:
            setdef(ap, PREFIX); log("set PREFIX2"); R["ok"].append("PREFIX2")

bel.compile_blueprint(mbp)
R["mgr"] = str(mbp.get_editor_property("status"))
log("mgr " + R["mgr"])

# Verify
seen = set(); q = [ev]; nodes = []
while q:
    cur = q.pop(0)
    if not cur or id(cur) in seen: continue
    seen.add(id(cur)); nodes.append(cur)
    for p in bel.list_all_pins(cur):
        for c in (p.list_connected_pins() or []):
            q.append(c.get_owning_node())
vals = []
for n in nodes:
    if "Append" in title(n) or "Concat" in title(n):
        for pn in ("A", "B"):
            p = find_pin(n, pn, "Input")
            if not p: continue
            if p.list_connected_pins(): continue
            try: vals.append(str(p.get_pin_value()))
            except: pass
R["literals"] = vals
R["fixed"] = fixed

if "ERROR" not in R["mgr"]:
    eas.save_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
open(r"E:\UE\FarmSim25D\Saved\rest_summary_fix.json", "w", encoding="utf-8").write(
    json.dumps(R, indent=2, ensure_ascii=False, default=str))
print(json.dumps(R, indent=2, ensure_ascii=False, default=str))