# -*- coding: utf-8 -*-
"""Fix Tick chain (restore Grid debug + HUD at end) and DrawDebugString Text pin."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[HUD_FIX2] " + str(m))
    print("[HUD_FIX2] " + str(m))

def pos(x, y):
    return unreal.IntPoint(int(x), int(y))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def find_pin(node, name_substr, direction=None, exact=False):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        pn = str(p.get_pin_name())
        if exact:
            match = pn == name_substr
        else:
            match = name_substr.lower() in pn.lower()
        if match:
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name() if a else None, b.get_pin_name() if b else None, ok))
    return ok

def set_val(pin, value, label=""):
    if not pin:
        log("no pin " + label)
        return False
    try:
        pin.set_pin_value(str(value))
        log("set {}={!r}".format(label, value))
        return True
    except Exception as e:
        log("set {} FAIL {}".format(label, e))
        return False

def out_pin(node, prefer=None):
    if prefer:
        p = find_pin(node, prefer, "Output", exact=True) or find_pin(node, prefer, "Output")
        if p:
            return p
    outs = [p for p in bel.list_all_pins(node) if "output" in str(p.get_pin_direction()).lower()]
    return outs[0] if outs else None

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)

# --- Dump Tick chain ---
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_Event":
        continue
    if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
        tick = n
        break

log("=== Tick BEFORE ===")
thenp = find_pin(tick, "then", "Output")
queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
seen = set()
tick_nodes = []
while queue:
    cur, d = queue.pop(0)
    if id(cur) in seen or d > 15:
        continue
    seen.add(id(cur))
    tick_nodes.append(cur)
    log("  " * d + title(cur))
    for pn in ("then", "else"):
        tp = find_pin(cur, pn, "Output")
        if tp:
            for c in conn(tp):
                queue.append((c.get_owning_node(), d + 1))

# Identify key nodes in EventGraph
w2g = None
g2w = None
grid_print = None
dbg_box = None
upd_from_tick = []
for n in ge.list_all_nodes():
    t = title(n)
    if t == "WorldToGrid":
        # prefer one connected from Tick
        w2g = n
    if t == "GridToWorld":
        g2w = n
    if t == "PrintString":
        # check InString for Grid
        isp = find_pin(n, "InString", "Input")
        try:
            # linked or literal
            val = isp.get_pin_value() if isp else ""
        except Exception:
            val = ""
        # Grid print usually has Format or linked string containing Grid
        # Keep candidates
        if grid_print is None:
            grid_print = n  # will refine
    if "DrawDebugBox" in t:
        dbg_box = n
    if t == "UpdateFarmHUD":
        upd_from_tick.append(n)

# Find Grid PrintString: one whose InString is connected from Append/Format involving Grid, OR Key empty with short duration
# Walk from Tick specifically
log("=== rebuild Tick chain ===")
# Desired: Tick -> WorldToGrid -> GridToWorld -> PrintString(Grid) -> DrawDebugBox -> UpdateFarmHUD

# Find WorldToGrid that Tick currently points to (or any)
tick_then = find_pin(tick, "then", "Output")
first = conn(tick_then)[0].get_owning_node() if conn(tick_then) else None
log("Tick first=" + (title(first) if first else "None"))

# Collect UpdateFarmHUD nodes - keep plant/harvest ones, identify orphans
# For Tick we want ONE UpdateFarmHUD at the very end.

# Find PrintString that is in the old tick path - InString linked, often Key empty Duration small
# Dump all PrintString InString values
prints = []
for n in ge.list_all_nodes():
    if title(n) != "PrintString":
        continue
    isp = find_pin(n, "InString", "Input")
    kp = find_pin(n, "Key", "Input")
    dp = find_pin(n, "Duration", "Input")
    try:
        ival = isp.get_pin_value() if isp else ""
    except Exception:
        ival = "?"
    try:
        kval = kp.get_pin_value() if kp else ""
    except Exception:
        kval = "?"
    try:
        dval = dp.get_pin_value() if dp else ""
    except Exception:
        dval = "?"
    ilinks = len(conn(isp)) if isp else 0
    log("PrintString InString={!r} links={} Key={!r} Dur={!r}".format(ival, ilinks, kval, dval))
    prints.append((n, ival, kval, dval, ilinks))

# Grid debug Print typically has Key empty or not FarmHUD, InString linked
grid_print = None
for n, ival, kval, dval, ilinks in prints:
    if kval == "FarmHUD":
        continue
    if ilinks >= 1 or (ival and "Grid" in ival):
        grid_print = n
        log("chosen grid_print")
        break
if not grid_print:
    # fallback: any PrintString that is not FarmHUD and has links
    for n, ival, kval, dval, ilinks in prints:
        if kval != "FarmHUD" and ilinks >= 1:
            grid_print = n
            break

# Find DrawDebugBox
dbg_box = None
for n in ge.list_all_nodes():
    if "DrawDebugBox" in title(n):
        dbg_box = n
        log("found DrawDebugBox")
        break

# Find WorldToGrid / GridToWorld used for foot grid (from Tick originally)
# Prefer nodes that have GetActorLocation or similar upstream - just use first WorldToGrid
w2g = None
g2w = None
for n in ge.list_all_nodes():
    if title(n) == "WorldToGrid" and w2g is None:
        w2g = n
    if title(n) == "GridToWorld" and g2w is None:
        g2w = n
log("w2g={} g2w={} grid_print={} dbg={}".format(bool(w2g), bool(g2w), bool(grid_print), bool(dbg_box)))

# Break Tick.then and rebuild cleanly
try:
    tick_then.break_pin_links()
    log("broke Tick.then")
except Exception as e:
    log(str(e))

# Also break exec chains between these nodes so we can rewire
for n in (w2g, g2w, grid_print, dbg_box):
    if not n:
        continue
    for pname in ("execute", "then"):
        p = find_pin(n, pname, None, exact=True) or find_pin(n, pname)
        if p and pname == "then":
            try:
                # only break then outputs so we can relink
                p.break_pin_links()
            except Exception:
                pass

# Remove orphan UpdateFarmHUD that was wrongly inserted mid-chain from Tick
# Keep UpdateFarmHUD nodes that are connected from plant/harvest/beginplay
# Strategy: remove ALL UpdateFarmHUD call nodes, then re-add:
#  - one at end of BeginPlay (after Set GridManagerRef)
#  - one at end of Tick
#  - plant/harvest already have their own - need to check if we break those

# Actually DON'T remove plant/harvest UpdateFarmHUD. Only fix Tick path.
# Find UpdateFarmHUD nodes whose execute is currently linked from Tick path or dangling from our bad wire
upd_nodes = [n for n in ge.list_all_nodes() if title(n) == "UpdateFarmHUD"]
log("UpdateFarmHUD count=" + str(len(upd_nodes)))
for n in upd_nodes:
    exe = find_pin(n, "execute", "Input")
    srcs = conn(exe) if exe else []
    src_titles = [title(s.get_owning_node()) for s in srcs]
    log("  upd inbound from " + str(src_titles))

# Rewire Tick chain:
# Tick -> W2G -> G2W -> GridPrint -> DrawDebugBox -> (new) UpdateFarmHUD
if w2g:
    connect(tick_then, find_pin(w2g, "execute", "Input"), "Tick->W2G")
if w2g and g2w:
    connect(find_pin(w2g, "then", "Output"), find_pin(g2w, "execute", "Input"), "W2G->G2W")
if g2w and grid_print:
    connect(find_pin(g2w, "then", "Output"), find_pin(grid_print, "execute", "Input"), "G2W->GridPrint")
elif g2w and dbg_box:
    connect(find_pin(g2w, "then", "Output"), find_pin(dbg_box, "execute", "Input"), "G2W->Dbg")
if grid_print and dbg_box:
    connect(find_pin(grid_print, "then", "Output"), find_pin(dbg_box, "execute", "Input"), "GridPrint->Dbg")

# End node for appending HUD
end_then = None
if dbg_box:
    end_then = find_pin(dbg_box, "then", "Output")
elif grid_print:
    end_then = find_pin(grid_print, "then", "Output")
elif g2w:
    end_then = find_pin(g2w, "then", "Output")
else:
    end_then = tick_then

# Break end_then existing links (may point to wrongly placed UpdateFarmHUD)
if end_then:
    try:
        end_then.break_pin_links()
    except Exception:
        pass

# Prefer reuse an UpdateFarmHUD that has no inbound, else create new
upd_free = None
for n in upd_nodes:
    exe = find_pin(n, "execute", "Input")
    if exe and len(conn(exe)) == 0:
        upd_free = n
        break
if not upd_free:
    upd_free = ge.add_call_function_node("/Game/TopDown/Blueprints/BP_TopDownCharacter.BP_TopDownCharacter_C:UpdateFarmHUD")
    bel.set_node_pos(upd_free, pos(2400, 700))
    log("created new UpdateFarmHUD for Tick")
else:
    log("reusing free UpdateFarmHUD")
connect(end_then, find_pin(upd_free, "execute", "Input"), "end->HUD")

# --- Fix DrawDebugString Text pin in UpdateFarmHUD ---
ug = bel.find_graph(bp, "UpdateFarmHUD")
uge = unreal.BlueprintGraphEditor.get_graph_editor(ug)
print_n = None
dds = None
for n in uge.list_all_nodes():
    t = title(n)
    if t == "PrintString":
        print_n = n
    if "DrawDebugString" in t:
        dds = n

if dds:
    log("DDS pins: " + str([(str(p.get_pin_name()), str(p.get_pin_direction())) for p in bel.list_all_pins(dds)]))
    # Exact Text pin (not TextLocation)
    text_pin = find_pin(dds, "Text", "Input", exact=True)
    if not text_pin:
        # sometimes named differently
        for p in bel.list_all_pins(dds):
            if str(p.get_pin_name()) == "Text" and "input" in str(p.get_pin_direction()).lower():
                text_pin = p
                break
    log("text_pin=" + str(text_pin.get_pin_name() if text_pin else None))
    # Break wrong TextLocation string links if any string was wrongly connected
    # Get string source from PrintString InString
    in_str = find_pin(print_n, "InString", "Input") if print_n else None
    srcs = conn(in_str) if in_str else []
    if text_pin and srcs:
        try:
            text_pin.break_pin_links()
        except Exception:
            pass
        connect(srcs[0], text_pin, "str->dds.Text")
    elif text_pin:
        set_val(text_pin, "*** Money / Seeds / Crops", "dds_text_lit")
    # Ensure duration / color
    set_val(find_pin(dds, "Duration", "Input", exact=True) or find_pin(dds, "Duration", "Input"), "0.1", "dds_dur")
    color_p = find_pin(dds, "TextColor", "Input", exact=True) or find_pin(dds, "Color", "Input", exact=True)
    if color_p:
        set_val(color_p, "(R=1.000000,G=1.000000,B=0.000000,A=1.000000)", "dds_color")
else:
    log("NO DDS in UpdateFarmHUD")

# Ensure PrintString still loud
if print_n:
    set_val(find_pin(print_n, "Duration", "Input"), "999.0", "dur")
    set_val(find_pin(print_n, "Key", "Input"), "FarmHUD", "key")
    set_val(find_pin(print_n, "bPrintToScreen", "Input"), "true", "scr")
    set_val(find_pin(print_n, "TextColor", "Input"), "(R=1.000000,G=1.000000,B=0.000000,A=1.000000)", "col")

# Enable screen messages
try:
    unreal.SystemLibrary.execute_console_command(None, "EnableAllScreenMessages")
except Exception:
    pass

# Compile + verify
try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))

log("=== Tick AFTER ===")
thenp = find_pin(tick, "then", "Output")
queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
seen = set()
while queue:
    cur, d = queue.pop(0)
    if id(cur) in seen or d > 15:
        continue
    seen.add(id(cur))
    log("  " * d + title(cur))
    for pn in ("then", "else"):
        tp = find_pin(cur, pn, "Output")
        if tp:
            for c in conn(tp):
                queue.append((c.get_owning_node(), d + 1))

log("=== BeginPlay ===")
begin = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_Event":
        continue
    if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
        continue
    begin = n
    break
thenp = find_pin(begin, "then", "Output")
queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
seen = set()
while queue:
    cur, d = queue.pop(0)
    if id(cur) in seen or d > 12:
        continue
    seen.add(id(cur))
    log("  " * d + title(cur))
    tp = find_pin(cur, "then", "Output")
    if tp:
        for c in conn(tp):
            queue.append((c.get_owning_node(), d + 1))

# Errors
try:
    errs = list(ge.list_nodes_with_errors())
    log("EG errs=" + str(len(errs)))
    for n in errs[:15]:
        log("  ERR " + title(n))
except Exception as e:
    log(str(e))
try:
    errs = list(uge.list_nodes_with_errors())
    log("HUD errs=" + str(len(errs)))
    for n in errs:
        log("  ERR " + title(n))
except Exception as e:
    log(str(e))

# Dump DDS pins after fix
if dds:
    for p in bel.list_all_pins(dds):
        try:
            val = p.get_pin_value()
        except Exception:
            val = "?"
        log("DDS {} dir={} val={!r} links={}".format(p.get_pin_name(), p.get_pin_direction(), val, len(conn(p))))

unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
try:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
except Exception as e:
    log(str(e))
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception as e:
    log(str(e))
log("DONE")
