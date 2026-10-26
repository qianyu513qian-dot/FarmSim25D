# -*- coding: utf-8 -*-
"""Diagnose Farm HUD: UpdateFarmHUD graph, BeginPlay chain, PrintString pins, screen messages."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
WBP = "/Game/Farm/UI/WBP_FarmHUD"

def log(m):
    unreal.log("[HUD_DIAG] " + str(m))
    print("[HUD_DIAG] " + str(m))

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def conn(p):
    try:
        return list(p.list_connected_pins() or [])
    except Exception:
        return []

bp = unreal.load_asset(CHAR)
log("bp=" + str(bool(bp)))
names = [str(x).split(".")[-1] for x in bel.list_member_variable_names(bp)]
for v in ("Money", "SeedCount", "CropCount", "TomatoSellPrice", "FarmHUDWidget"):
    log("var {}={}".format(v, v in names))
try:
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    for prop in ("Money", "SeedCount", "CropCount", "TomatoSellPrice"):
        log("CDO {}={}".format(prop, cdo.get_editor_property(prop)))
except Exception as e:
    log("CDO " + str(e))

graphs = [str(g) for g in bel.list_graph_names(bp)]
log("graphs has UpdateFarmHUD=" + str("UpdateFarmHUD" in graphs))

# Dump UpdateFarmHUD
if "UpdateFarmHUD" in graphs:
    ug = bel.find_graph(bp, "UpdateFarmHUD")
    uge = unreal.BlueprintGraphEditor.get_graph_editor(ug)
    log("UpdateFarmHUD nodes=" + str(len(list(uge.list_all_nodes()))))
    try:
        errs = uge.list_nodes_with_errors()
        log("UpdateFarmHUD errs=" + str(len(errs)))
        for n in errs:
            log("  ERR " + title(n))
    except Exception as e:
        log("err list " + str(e))
    for n in uge.list_all_nodes():
        t = title(n)
        cn = n.get_class().get_name()
        log("  NODE {} | {}".format(t, cn))
        if "Print" in t or "PrintString" in cn or "Print" in cn:
            for p in bel.list_all_pins(n):
                try:
                    val = p.get_pin_value()
                except Exception:
                    val = "?"
                links = len(conn(p))
                log("    pin {} dir={} val={!r} links={}".format(p.get_pin_name(), p.get_pin_direction(), val, links))

# BeginPlay walk
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
begin = None
tick = None
for n in ge.list_all_nodes():
    if n.get_class().get_name() != "K2Node_Event":
        continue
    if any(str(p.get_pin_name()) == "DeltaSeconds" for p in bel.list_all_pins(n)):
        tick = n
    else:
        begin = n
log("begin={} tick={}".format(bool(begin), bool(tick)))

def walk(start_pin, label, depth=12):
    log("=== {} ===".format(label))
    if not start_pin:
        log("  NO PIN")
        return
    queue = [(c.get_owning_node(), 0) for c in conn(start_pin)]
    seen = set()
    while queue:
        cur, d = queue.pop(0)
        if id(cur) in seen or d > depth:
            continue
        seen.add(id(cur))
        log("  " * d + title(cur))
        for pn in ("then", "else"):
            tp = find_pin(cur, pn, "Output")
            if tp:
                for c in conn(tp):
                    queue.append((c.get_owning_node(), d + 1))

if begin:
    walk(find_pin(begin, "then", "Output"), "BeginPlay")
if tick:
    walk(find_pin(tick, "then", "Output"), "Tick", depth=8)

# Count UpdateFarmHUD calls in EG
upd_calls = 0
for n in ge.list_all_nodes():
    if title(n) == "UpdateFarmHUD":
        upd_calls += 1
        exe = find_pin(n, "execute", "Input")
        log("UpdateFarmHUD call inbound_links={}".format(len(conn(exe)) if exe else -1))
log("UpdateFarmHUD calls in EG=" + str(upd_calls))

# WBP state
log("WBP exists=" + str(unreal.EditorAssetLibrary.does_asset_exist(WBP)))
if unreal.EditorAssetLibrary.does_asset_exist(WBP):
    wbp = unreal.load_asset(WBP)
    try:
        tree = unreal.load_object(wbp, "WidgetTree")
        log("tree=" + str(tree))
        try:
            root = tree.get_editor_property("root_widget")
            log("root=" + str(root))
        except Exception as e:
            log("root err " + str(e))
        try:
            allw = tree.get_editor_property("all_widgets")
            log("all_widgets count=" + str(len(list(allw)) if allw else 0))
            if allw:
                for w in list(allw)[:20]:
                    log("  widget " + str(w))
        except Exception as e:
            log("all_widgets " + str(e))
    except Exception as e:
        log("tree load " + str(e))

# Screen message CVar
try:
    # try read console var
    for name in ("EnableAllScreenMessages", "r.EnableAllScreenMessages"):
        pass
    log("trying enable screen messages via console")
    unreal.SystemLibrary.execute_console_command(None, "EnableAllScreenMessages")
    log("EnableAllScreenMessages issued")
except Exception as e:
    log("console " + str(e))

# Look for any existing WidgetBlueprints to duplicate
try:
    assets = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False)
    wbps = [a for a in assets if "WBP_" in a or "Widget" in a]
    log("game widgets sample=" + str(wbps[:30]))
except Exception as e:
    log("list assets " + str(e))

log("DONE DIAG")
