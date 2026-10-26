# -*- coding: utf-8 -*-
"""Fix GrowCell/HarvestCell IsValidCell exec; remap IMC G/R/H keys; ensure grow prints."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
IMC = "/Game/TopDown/Input/IMC_Default"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"


def log(m):
    unreal.log("[FIX_GROW] " + str(m))


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
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
        log("set {}={!r}".format(label, pin.get_pin_value()))
    except Exception as e:
        log("set fail {}: {}".format(label, e))


def fix_isvalid_exec(bp, fname):
    """Wire: Entry.then -> IsValidCell.execute -> Branch (was Entry.then -> Branch, IsValidCell unexecuted)."""
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, fname))
    entry = None
    isvalid = None
    first_branch = None  # the IsValidCell condition branch

    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        cls = n.get_class().get_name()
        if cls == "K2Node_FunctionEntry" or t == fname:
            entry = n
        if "IsValidCell" in t:
            isvalid = n

    if not entry or not isvalid:
        log(fname + " missing entry/isvalid")
        return False

    # Find branch whose Condition comes from IsValidCell
    iv_ret = find_pin(isvalid, "Return", "Output")
    for cp in (iv_ret.list_connected_pins() if iv_ret else []):
        own = cp.get_owning_node()
        if bel.get_node_title(own) == "Branch":
            first_branch = own
            break

    if not first_branch:
        log(fname + " no branch on IsValidCell return")
        return False

    # Check if already fixed
    iv_exec = find_pin(isvalid, "execute", "Input")
    already = list(iv_exec.list_connected_pins()) if iv_exec else []
    if already:
        log(fname + " IsValidCell already has exec from " + str(
            [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in already]))
        return True

    entry_then = find_pin(entry, "then", "Output")
    br_exec = find_pin(first_branch, "execute", "Input")

    # Break entry.then -> branch.execute
    try:
        entry_then.break_pin_links(False)
    except Exception:
        try:
            entry_then.break_pin_links()
        except Exception as e:
            log(fname + " break entry.then: " + str(e))

    # Also break anything into branch.execute that isn't IsValidCell.then
    if br_exec:
        for cp in list(br_exec.list_connected_pins()):
            try:
                br_exec.break_single_pin_link(cp)
            except Exception:
                pass

    # entry.then -> IsValidCell.execute
    connect(entry_then, iv_exec, fname + ".entry->iv")
    # IsValidCell.then -> Branch.execute
    connect(find_pin(isvalid, "then", "Output"), br_exec, fname + ".iv->br")

    # Ensure GridX/GridY connected
    for axis in ("GridX", "GridY", "Grid X", "Grid Y"):
        ep = find_pin(entry, axis.replace(" ", ""), "Output") or find_pin(entry, axis, "Output")
        ip = find_pin(isvalid, axis.replace(" ", ""), "Input") or find_pin(isvalid, axis, "Input")
        if ep and ip and not list(ip.list_connected_pins()):
            connect(ep, ip, fname + "." + axis)

    log(fname + " IsValidCell exec FIXED")
    return True


def remap_imc_keys():
    imc = unreal.load_asset(IMC)
    if not imc:
        log("no IMC")
        return

    pairs = [
        ("/Game/TopDown/Input/Actions/IA_Interact", "E"),
        ("/Game/TopDown/Input/Actions/IA_Plant", "F"),
        ("/Game/TopDown/Input/Actions/IA_Water", "R"),
        ("/Game/TopDown/Input/Actions/IA_Grow", "G"),
        ("/Game/TopDown/Input/Actions/IA_Harvest", "H"),
    ]
    for path, key_name in pairs:
        action = unreal.load_asset(path)
        if not action:
            log("missing action " + path)
            continue
        # Unmap existing keys for this action then remap
        try:
            imc.unmap_all_keys_from_action(action)
            log("unmapped all for " + action.get_name())
        except Exception as e:
            log("unmap {}: {}".format(action.get_name(), e))
        try:
            key = unreal.Key(key_name)
            imc.map_key(action, key)
            log("mapped {} -> {}".format(action.get_name(), key_name))
        except Exception as e:
            # try Key structure differently
            try:
                key = unreal.Key()
                key.set_editor_property("key_name", key_name)
                imc.map_key(action, key)
                log("mapped (alt) {} -> {}".format(action.get_name(), key_name))
            except Exception as e2:
                log("map_key fail {} {}: {} / {}".format(action.get_name(), key_name, e, e2))

    unreal.EditorAssetLibrary.save_asset(IMC)
    # Verify
    dkm = imc.get_editor_property("default_key_mappings")
    try:
        for m in dkm.mappings:
            try:
                a = m.get_editor_property("action")
                k = m.get_editor_property("key")
                an = a.get_name() if a else "?"
                if an.startswith("IA_"):
                    log("VERIFY {} key={}".format(an, k))
            except Exception as e:
                log("verify err " + str(e))
    except Exception as e:
        log("verify list " + str(e))


def ensure_grow_prints():
    """Make sure character prints Grew! / Cannot grow on GrowCell result."""
    char = unreal.load_asset(CHAR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(char, "EventGraph"))

    grow_call = None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) == "GrowCell":
            grow_call = n
            break
    if not grow_call:
        log("no GrowCell on character")
        return

    # Find branch after GrowCell
    then_pin = find_pin(grow_call, "then", "Output")
    success_pin = find_pin(grow_call, "Success", "Output")
    branch = None
    if then_pin:
        for cp in then_pin.list_connected_pins():
            if bel.get_node_title(cp.get_owning_node()) == "Branch":
                branch = cp.get_owning_node()
    if not branch:
        log("no branch after GrowCell — add one with prints")
        branch = ge.add_branch_node()
        bel.set_node_pos(branch, pos(2400, 800))
        connect(then_pin, find_pin(branch, "execute", "Input"), "grow->br")
        connect(success_pin, find_pin(branch, "Condition", "Input"), "succ->cond")

    # Check if prints exist on then/else
    def has_print_on(exec_pin, text_sub):
        if not exec_pin:
            return False
        for cp in exec_pin.list_connected_pins():
            own = cp.get_owning_node()
            if "Print" in bel.get_node_title(own):
                s = find_pin(own, "InString", "Input") or find_pin(own, "In String", "Input")
                try:
                    if s and text_sub.lower() in str(s.get_pin_value()).lower():
                        return True
                except Exception:
                    return True
        return False

    then_br = find_pin(branch, "then", "Output")
    else_br = find_pin(branch, "else", "Output")

    if not has_print_on(then_br, "grew") and not has_print_on(then_br, "Grown"):
        # If then already connected, insert print before
        existing = list(then_br.list_connected_pins()) if then_br else []
        pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(2700, 750))
        set_val(find_pin(pr, "InString", "Input") or find_pin(pr, "In String", "Input"), "Grew! (Ready)", "grew")
        set_val(find_pin(pr, "Duration", "Input"), "2.0", "dur")
        if existing:
            try:
                then_br.break_pin_links(False)
            except Exception:
                then_br.break_pin_links()
            connect(then_br, find_pin(pr, "execute", "Input"), "br->print")
            # reconnect first existing if it was a print or continue — leave dangling ok for success path end
        else:
            connect(then_br, find_pin(pr, "execute", "Input"), "br->print")
        log("added Grew! print")
    else:
        log("Grew print exists")

    if not has_print_on(else_br, "cannot grow") and not has_print_on(else_br, "Cannot grow"):
        existing = list(else_br.list_connected_pins()) if else_br else []
        pr = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
        bel.set_node_pos(pr, pos(2700, 900))
        set_val(find_pin(pr, "InString", "Input") or find_pin(pr, "In String", "Input"), "Cannot grow", "nogrow")
        set_val(find_pin(pr, "Duration", "Input"), "2.0", "dur")
        if existing:
            try:
                else_br.break_pin_links(False)
            except Exception:
                else_br.break_pin_links()
        connect(else_br, find_pin(pr, "execute", "Input"), "brelse->print")
        log("added Cannot grow print")
    else:
        log("Cannot grow print exists")

    try:
        bel.compile_blueprint(char)
    except Exception as e:
        log("char compile " + str(e))
    unreal.EditorAssetLibrary.save_asset(CHAR)


def bump_crop_z_for_growth():
    """Raise CropMesh default Z so growing/mature stick up more obviously."""
    pv = unreal.load_asset("/Game/Farm/Grid/BP_PlotVisual")
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(pv):
        data = sub.k2_find_subobject_data_from_handle(h)
        try:
            vname = str(lib.get_variable_name(data) or "")
            obj = lib.get_object(data)
            if vname == "CropMesh" and obj:
                obj.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, 15.0))
                log("CropMesh Z=15")
        except Exception as e:
            log("cropz " + str(e))
    try:
        bel.compile_blueprint(pv)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset("/Game/Farm/Grid/BP_PlotVisual")


log("=== START ===")
bp = unreal.load_asset(MGR)
fix_isvalid_exec(bp, "GrowCell")
fix_isvalid_exec(bp, "HarvestCell")
try:
    bel.compile_blueprint(bp)
    log("GM compile ok")
except Exception as e:
    log("GM compile " + str(e))
unreal.EditorAssetLibrary.save_asset(MGR)

remap_imc_keys()
ensure_grow_prints()
bump_crop_z_for_growth()

# Verify GrowCell chain
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "GrowCell"))
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if t in ("GrowCell",) or "IsValidCell" in t or t == "Branch":
        for p in bel.list_all_pins(n):
            if str(p.get_pin_name()).lower() in ("execute", "then", "else"):
                cps = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
                if cps:
                    log("VERIFY {}.{} -> {}".format(t, p.get_pin_name(), cps))

log("=== END ===")
