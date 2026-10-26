# -*- coding: utf-8 -*-
"""Remove broken CreateWidget chain from BeginPlay; keep UpdateFarmHUD only.
Verify GetActorOfClass still points at BP_GridManager.
"""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[INV_E] " + str(m))
    print("[INV_E] " + str(m))

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

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok))
    return ok

def title(n):
    try:
        return str(bel.get_node_title(n))
    except Exception:
        return n.get_class().get_name()

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

# Identify nodes
begin = None
get_actor = None
set_gm = None
create_w = None
add_vp = None
set_hud = None
upd = None

for n in nodes:
    t = title(n)
    cn = n.get_class().get_name()
    if cn == "K2Node_Event" and not any(str(p.get_pin_name())=="DeltaSeconds" for p in bel.list_all_pins(n)):
        begin = n
    if t == "GetActorOfClass" or "Get Actor Of Class" in t:
        get_actor = n
        # dump ActorClass value
        for p in bel.list_all_pins(n):
            if "Class" in str(p.get_pin_name()):
                try:
                    log("GetActorOfClass.{}={!r}".format(p.get_pin_name(), p.get_pin_value()))
                except Exception as e:
                    log(str(e))
    if cn == "K2Node_VariableSet":
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()) == "GridManagerRef":
                set_gm = n
            if str(p.get_pin_name()) == "FarmHUDWidget":
                set_hud = n
    if t == "Create Widget" or t.startswith("Create Widget"):
        create_w = n
        log("Create Widget pins=" + str([(str(p.get_pin_name()), str(p.get_pin_direction()), (p.get_pin_value() if hasattr(p,'get_pin_value') else '')) for p in bel.list_all_pins(n)]))
    if t == "Add to Viewport" or t == "AddToViewport":
        add_vp = n
    if t == "UpdateFarmHUD":
        # may be multiple
        if find_pin(n, "execute", "Input"):
            # check if connected from BeginPlay side by walking - collect all
            pass

# Find UpdateFarmHUD that is in BeginPlay chain
upd_begin = None
if set_gm:
    then = find_pin(set_gm, "then", "Output")
    for c in conn(then):
        n = c.get_owning_node()
        log("after SetGM: " + title(n))
        if title(n) == "Create Widget":
            create_w = n
        # walk
        cur_then = find_pin(n, "then", "Output")
        queue = [n]
        seen=set()
        while queue:
            cur = queue.pop(0)
            if id(cur) in seen: continue
            seen.add(id(cur))
            t = title(cur)
            log("  chain: " + t)
            if t == "UpdateFarmHUD":
                upd_begin = cur
            if t == "Add to Viewport" or "AddToViewport" in t or t == "Add to Viewport":
                add_vp = cur
            if "FarmHUDWidget" in t or (cur.get_class().get_name()=="K2Node_VariableSet" and find_pin(cur, "FarmHUDWidget")):
                set_hud = cur
            tp = find_pin(cur, "then", "Output")
            if tp:
                for cc in conn(tp):
                    queue.append(cc.get_owning_node())

log("create_w={} add_vp={} set_hud={} upd={}".format(bool(create_w), bool(add_vp), bool(set_hud), bool(upd_begin)))

# Rewire: Set GridManagerRef.then -> UpdateFarmHUD.execute
# Remove create/add/set_hud nodes
if set_gm and upd_begin:
    # break set_gm.then
    then_gm = find_pin(set_gm, "then", "Output")
    try:
        then_gm.break_pin_links()
        log("broke SetGM.then")
    except Exception as e:
        log(str(e))
    connect(then_gm, find_pin(upd_begin, "execute", "Input"), "GM->UpdateHUD")

# Also break any inbound to create_w / orphan the UMG nodes
to_remove = []
for n in (create_w, add_vp, set_hud):
    if not n:
        continue
    # break all exec pins
    for p in bel.list_all_pins(n):
        try:
            if conn(p):
                p.break_pin_links()
        except Exception:
            pass
    to_remove.append(n)

if to_remove:
    try:
        ge.remove_nodes(to_remove)
        log("removed {} UMG nodes".format(len(to_remove)))
    except Exception as e:
        log("remove fail " + str(e))

# Ensure GetActorOfClass class is GridManager
if get_actor:
    for p in bel.list_all_pins(get_actor):
        pn = str(p.get_pin_name())
        if pn in ("ActorClass", "Class"):
            cur = ""
            try:
                cur = p.get_pin_value() or ""
            except Exception:
                pass
            log("GetActor class now={!r}".format(cur))
            if "GridManager" not in cur:
                for val in (
                    "/Game/Farm/Grid/BP_GridManager.BP_GridManager_C",
                    "BlueprintGeneratedClass'/Game/Farm/Grid/BP_GridManager.BP_GridManager_C'",
                ):
                    try:
                        p.set_pin_value(val)
                        log("restored class -> {!r}".format(p.get_pin_value()))
                        if "GridManager" in (p.get_pin_value() or ""):
                            break
                    except Exception as e:
                        log(str(e))

# Final BeginPlay walk
log("=== BeginPlay final ===")
thenp = find_pin(begin, "then", "Output")
queue = [(c.get_owning_node(), 0) for c in conn(thenp)]
seen=set()
while queue:
    cur,d = queue.pop(0)
    if id(cur) in seen or d>10: continue
    seen.add(id(cur))
    log("  "*d + title(cur))
    tp = find_pin(cur, "then", "Output")
    if tp:
        for c in conn(tp):
            queue.append((c.get_owning_node(), d+1))

# Re-verify plant seed branch condition (SeedCount > 0)
log("=== Plant brief ===")
for n in nodes:
    p = find_pin(n, "InputAction")
    if not p: continue
    try:
        if "IA_Plant" not in (p.get_pin_value() or ""):
            continue
    except Exception:
        continue
    started = find_pin(n, "Started", "Output")
    queue = [(c.get_owning_node(), 0, "S") for c in conn(started)]
    seen=set()
    while queue:
        cur,d,via=queue.pop(0)
        if id(cur) in seen or d>10: continue
        seen.add(id(cur))
        log("  "*d + "[{}] {}".format(via, title(cur)))
        for cp in bel.list_all_pins(cur):
            if str(cp.get_pin_name()) in ("then","else"):
                for c in conn(cp):
                    queue.append((c.get_owning_node(), d+1, str(cp.get_pin_name())))

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))

# Check errors
try:
    errs = ge.list_nodes_with_errors()
    log("errors=" + str(len(errs)))
    for n in errs[:10]:
        log(" ERR " + title(n))
except Exception as e:
    log(str(e))

unreal.EditorAssetLibrary.save_asset(CHAR)
try:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
except Exception as e:
    log(str(e))

# Force save level if loaded
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    if world:
        unreal.EditorLevelLibrary.save_current_level()
        log("saved current level")
except Exception as e:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        subsystem.save_current_level()
        log("saved level via subsystem")
    except Exception as e2:
        log("level save: {} / {}".format(e, e2))

# CDO defaults still good?
try:
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    for prop in ("Money", "SeedCount", "CropCount", "TomatoSellPrice"):
        log("CDO {}={}".format(prop, cdo.get_editor_property(prop)))
except Exception as e:
    log("CDO " + str(e))

log("DONE")
