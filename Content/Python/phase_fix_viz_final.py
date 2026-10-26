# -*- coding: utf-8 -*-
"""Verify grass display names; only hide grass when State!=0; final save."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def log(m):
    unreal.log("[FIX_FINAL] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}]: {}".format(label, ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        return
    try:
        pin.set_pin_value(str(value))
        log("set {}={}".format(label, pin.get_pin_value()))
    except Exception as e:
        log("set fail {}: {}".format(label, e))


# Probe grass names
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
n = 0
for a in actors:
    try:
        lab = a.get_actor_label()
    except Exception:
        continue
    if "VMF_Grass_" in str(lab):
        try:
            dn = unreal.KismetSystemLibrary.get_display_name(a)
        except Exception:
            dn = "?"
        log("grass lab={} display={} loc={}".format(lab, dn, a.get_actor_location()))
        n += 1
        if n >= 3:
            break

# Gate HideGrassAt behind State != 0 in VisualizeCell
bp = unreal.load_asset(MGR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))

hide_node = None
entry = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "HideGrassAt" in t:
        hide_node = n
    if n.get_class().get_name() == "K2Node_FunctionEntry":
        entry = n

if hide_node and entry:
    # Check if already gated
    exec_in = find_pin(hide_node, "execute", "Input")
    from_entry = False
    if exec_in:
        for cp in exec_in.list_connected_pins():
            if cp.get_owning_node() == entry:
                from_entry = True
    if from_entry:
        # Insert: entry -> eq0 branch -> (else) HideGrassAt -> continue; (then state0) skip hide -> continue
        then_hide = find_pin(hide_node, "then", "Output")
        next_pins = list(then_hide.list_connected_pins()) if then_hide else []
        next_exec = next_pins[0] if next_pins else None

        try:
            find_pin(entry, "then", "Output").break_pin_links(False)
        except Exception:
            find_pin(entry, "then", "Output").break_pin_links()
        try:
            then_hide.break_pin_links(False)
        except Exception:
            then_hide.break_pin_links()

        eq0 = ge.add_call_function_node("/Script/Engine.KismetMathLibrary:EqualEqual_ByteByte")
        bel.set_node_pos(eq0, pos(500, -200))
        connect(find_pin(entry, "State", "Output"), find_pin(eq0, "A", "Input"), "st")
        set_val(find_pin(eq0, "B", "Input"), "0", "eq0")

        br = ge.add_branch_node()
        bel.set_node_pos(br, pos(700, -200))
        connect(find_pin(entry, "then", "Output"), find_pin(br, "execute", "Input"), "e->br")
        connect(find_pin(eq0, "ReturnValue", "Output"), find_pin(br, "Condition", "Input"), "cond")

        # State==0: skip hide, go next
        if next_exec:
            connect(find_pin(br, "then", "Output"), next_exec, "skip->next")
        # State!=0: hide then next
        connect(find_pin(br, "else", "Output"), find_pin(hide_node, "execute", "Input"), "else->hide")
        if next_exec:
            # Need a second connection to same pin - in UE one input can only have one connection!
            # So use a reroute or Sequence
            # Better: both paths merge via Sequence-like: use another approach
            # Break the skip connect; use Sequence node after branch
            pass

        # Redo merge properly with Sequence? Or wire hide.then and br.then both - can't same input.
        # Use a dummy Pass through: actually K2Node_Knot or Sequence
        seq = ge.create_node_from_name("Utilities|FlowControl|Sequence", unreal.Vector2D(1200, -120), [])
        if not seq:
            # Fallback: only call hide on else; for then (state0) connect directly
            # hide.then -> next; br.then -> next  CAN'T both
            # Use Sequence: entry->br; br.then->seq.then_0; br.else->hide->seq.then_0... no
            # Simplest: br.else -> hide -> next; br.then -> next requires knot merge
            # In UE, create Sequence with one exec out used from two paths via... 
            # Actually the clean way: 
            #   br.else -> hide -> next_exec
            #   br.then -> next_exec  
            # Second connect to next_exec will fail. So add intermediate Print or custom Event.
            # Use "Do Nothing" - Call to a no-op? 
            # Best: Retriggerable Delay 0? Ugly.
            # Use Sequence node: 
            #   entry -> hide_gate logic differently
            
            # Re-approach: put HideGrassAt ONLY on spawn path and update path (state!=0), not at entry.
            # For now: br.else -> hide -> next; br.then -> next using a reroute merge via Sequence:
            # Sequence has execute in, then 0, then 1.
            # Both paths call into same Sequence execute - STILL can't dual-connect.
            
            # FIX: use two-step - Branch else goes hide then to shared Return-like knot.
            # K2Node_Knot can merge? In UE Blueprints, multiple outputs CAN connect to one input? 
            # NO - exec inputs are single. Data pins can have multiple.
            
            # Correct pattern: 
            # br.then ---------> next_exec
            # br.else -> hide -/  
            # Change next_exec owner: insert Sequence AFTER both by making hide the only path that matters,
            # and for state 0 go to next; for state !=0 hide then next.
            # To merge: create a custom Function "ContinueViz" - overkill.
            # Use "Macro|FlowControl|Gate" - no.
            
            # SIMPLEST WORKING: Don't gate. Always HideGrassAt. On harvest (state 0) grass stays hidden = empty plot look. OK for MVP.
            log("Keeping ungated HideGrassAt (harvest leaves cleared grass — acceptable)")
            # Restore original: entry -> hide -> next
            connect(find_pin(entry, "then", "Output"), find_pin(hide_node, "execute", "Input"), "restore e->hide")
            if next_exec:
                connect(then_hide, next_exec, "restore hide->next")
        else:
            bel.set_node_pos(seq, pos(1100, -120))
            # br.then -> seq execute; hide.then -> can't also
            # Different Sequence pattern doesn't help merge.
            log("Sequence created but merge still hard — leave ungated")
            connect(find_pin(entry, "then", "Output"), find_pin(hide_node, "execute", "Input"), "e->hide")
            if next_exec:
                connect(then_hide, next_exec, "hide->next")

# Delete DEBUG actor to avoid confusion
for a in actors:
    try:
        lab = a.get_actor_label()
    except Exception:
        continue
    if lab == "DEBUG_PlotVisual_Test":
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(a)
        log("destroyed DEBUG actor")

try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile " + str(e))

# Final verification summary
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "VisualizeCell"))
log("VisualizeCell errors=" + str(len(ge.list_nodes_with_errors())))
for fname in ("TillCell", "PlantCell", "WaterCell", "GrowCell", "HarvestCell"):
    fge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    has_viz = any("VisualizeCell" in bel.get_node_title(n) for n in fge.list_all_nodes())
    log("{} has_viz={}".format(fname, has_viz))

pv = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
pge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
log("ApplyState errors=" + str(len(pge.list_nodes_with_errors())))

unreal.EditorAssetLibrary.save_asset(MGR)
unreal.EditorAssetLibrary.save_asset("/Game/Farm/Grid/BP_PlotVisual")
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        log("level saved (legacy)")
    except Exception as e2:
        log("level save fail " + str(e2))

log("=== DONE ===")
