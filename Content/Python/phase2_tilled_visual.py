# -*- coding: utf-8 -*-
"""Fix TillCell enum write + draw brown box on success. No open_editor, no rename."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"


def pos(x, y):
    return unreal.IntPoint(int(x), int(y))


def connect(a, b, label=""):
    if a is None or b is None:
        unreal.log_warning("skip " + label)
        return False
    ok = a.try_create_connection(b)
    unreal.log("conn[{}] {}->{} : {}".format(label, a.get_pin_name(), b.get_pin_name(), ok))
    return ok


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def set_val(pin, value, label=""):
    if not pin:
        unreal.log_warning("no pin " + label)
        return
    try:
        pin.set_pin_value(str(value))
        unreal.log("set {} = {} -> {}".format(label, value, pin.get_pin_value()))
    except Exception as ex:
        unreal.log_warning("set {}: {}".format(label, ex))


def main():
    unreal.log("=== phase2_tilled_visual start ===")
    bp = unreal.EditorAssetLibrary.load_asset(MGR)
    g = bel.find_graph(bp, "TillCell")
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)

    entry = None
    equal = None
    set_elem = None
    success_returns = []
    is_valid = None
    branches = []

    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t == "TillCell":
            entry = n
        elif "Equal" in t.lower():
            equal = n
        elif "Set Array" in t:
            set_elem = n
        elif t == "Return Node":
            success_returns.append(n)
        elif t == "IsValidCell":
            is_valid = n
        elif t == "Branch":
            branches.append(n)
        unreal.log("node: " + t)

    # Dump equal + set_elem pins
    for n, label in ((equal, "equal"), (set_elem, "set")):
        if not n:
            continue
        for p in bel.list_all_pins(n):
            try:
                v = p.get_pin_value()
            except Exception:
                v = ""
            unreal.log("{} pin {} val=[{}] dir={}".format(label, p.get_pin_name(), v, p.get_pin_direction()))

    # E_PlotState: Empty=0, Tilled=1 (from earlier design). Try set by name too.
    # Equal: Item == Empty → for compare pin B
    if equal:
        # typically A=Item from Get, B=literal
        bpin = find_pin(equal, "B", "Input") or None
        # list all input pins that aren't A
        for p in bel.list_all_pins(equal):
            if "INPUT" in str(p.get_pin_direction()):
                unreal.log("equal input " + str(p.get_pin_name()) + " = " + str(p.get_pin_value() if hasattr(p, "get_pin_value") else ""))
        # Try set the unconnected or literal side to Empty
        for p in bel.list_all_pins(equal):
            if "INPUT" not in str(p.get_pin_direction()):
                continue
            cps = list(p.list_connected_pins())
            if len(cps) == 0:
                for candidate in ("Empty", "NewEnumerator0", "0"):
                    set_val(p, candidate, "equal." + str(p.get_pin_name()))
                    unreal.log("try equal val now=" + str(p.get_pin_value()))
                    break

    if set_elem:
        item = find_pin(set_elem, "Item", "Input")
        for candidate in ("Tilled", "NewEnumerator1", "1"):
            set_val(item, candidate, "set.Item")
            unreal.log("set Item now=" + str(item.get_pin_value()))
            # stop if looks like Tilled
            v = str(item.get_pin_value())
            if "Tilled" in v or v == "1" or "Enumerator1" in v:
                break

    # Find success return (Success=true) — wire DrawDebug after Set Array then, before Return
    # Current: Set Array then -> Return Success=true
    # New: Set Array then -> GridToWorld -> DrawDebugBox -> Return

    # Remove any previous DrawDebugBox in TillCell
    remove = []
    for n in ge.list_all_nodes():
        if "DrawDebug" in bel.get_node_title(n) or bel.get_node_title(n) == "GridToWorld":
            remove.append(n)
        if bel.get_node_title(n) == "Get CellSize":
            remove.append(n)
    if remove:
        ge.remove_nodes(remove)
        unreal.log("removed old visual nodes " + str(len(remove)))

    # Re-find set_elem after remove
    set_elem = None
    for n in ge.list_all_nodes():
        if "Set Array" in bel.get_node_title(n):
            set_elem = n
    if not set_elem:
        unreal.log_warning("no Set Array Elem")
        return

    then_set = find_pin(set_elem, "then", "Output")
    # Break link from set then to Return, insert GridToWorld + DrawDebug
    old_targets = list(then_set.list_connected_pins()) if then_set else []
    for cp in old_targets:
        try:
            then_set.break_single_pin_link(cp)
        except Exception:
            try:
                then_set.break_pin_links()
                break
            except Exception as ex:
                unreal.log_warning(str(ex))

    # self for GridToWorld: pure self from function
    g2w = ge.add_call_function_node("/Game/Farm/Grid/BP_GridManager.BP_GridManager_C:GridToWorld")
    bel.set_node_pos(g2w, pos(900, 200))
    # GridToWorld needs self + GridX + GridY
    # Entry outputs GridX/GridY
    connect(find_pin(entry, "GridX", "Output"), find_pin(g2w, "GridX", "Input") or find_pin(g2w, "Grid X", "Input"), "gx-g2w")
    connect(find_pin(entry, "GridY", "Output"), find_pin(g2w, "GridY", "Input") or find_pin(g2w, "Grid Y", "Input"), "gy-g2w")
    # self: leave default (self) for member call inside same BP — usually auto

    get_cs = ge.add_get_member_variable_node("CellSize")
    bel.set_node_pos(get_cs, pos(900, 400))

    # Extent = (CellSize/2 - 2, CellSize/2 - 2, 5) approx — use Make Vector
    # Simpler: Extent pin set to 45,45,2 if CellSize=100
    dbg = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:DrawDebugBox")
    bel.set_node_pos(dbg, pos(1200, 200))

    connect(then_set, find_pin(dbg, "execute", "Input"), "set->dbg")
    # GridToWorld may be pure or impure
    g2w_exec = find_pin(g2w, "execute", "Input")
    if g2w_exec:
        # need exec chain through g2w
        # reconnect: set -> g2w -> dbg
        find_pin(dbg, "execute", "Input").break_pin_links()
        connect(then_set, g2w_exec, "set->g2w")
        connect(find_pin(g2w, "then", "Output"), find_pin(dbg, "execute", "Input"), "g2w->dbg")
    connect(find_pin(g2w, "ReturnValue", "Output") or find_pin(g2w, "WorldLocation", "Output") or find_pin(g2w, "Return Value", "Output"),
            find_pin(dbg, "Center", "Input"), "center")

    # Dump g2w pins
    for p in bel.list_all_pins(g2w):
        unreal.log("g2w " + str(p.get_pin_name()) + " " + str(p.get_pin_direction()))

    # Extent: make vector from CellSize
    # Try MakeVector
    make_v = None
    for path in [
        "/Script/Engine.KismetMathLibrary:MakeVector",
        "Make Vector",
    ]:
        try:
            if path.startswith("/"):
                make_v = ge.add_call_function_node(path)
            else:
                make_v = ge.create_node_from_name(path, unreal.Vector2D(1000, 450), [])
            if make_v and len(bel.list_all_pins(make_v)) > 0:
                unreal.log("make_v ok " + path)
                break
            if make_v:
                ge.remove_nodes([make_v])
                make_v = None
        except Exception as ex:
            unreal.log_warning(str(ex))

    if make_v:
        bel.set_node_pos(make_v, pos(1000, 450))
        # float * 0.45 * CellSize — or set X=Y=45 Z=4 literals
        set_val(find_pin(make_v, "X", "Input"), "45.0", "ext.X")
        set_val(find_pin(make_v, "Y", "Input"), "45.0", "ext.Y")
        set_val(find_pin(make_v, "Z", "Input"), "4.0", "ext.Z")
        connect(find_pin(make_v, "ReturnValue", "Output"), find_pin(dbg, "Extent", "Input"), "extent")
    else:
        set_val(find_pin(dbg, "Extent", "Input"), "45.0,45.0,4.0", "extent-direct")

    # Brown color
    set_val(find_pin(dbg, "LineColor", "Input"), "(R=0.45,G=0.28,B=0.10,A=1.0)", "color")
    set_val(find_pin(dbg, "Duration", "Input"), "99999.0", "dur")
    set_val(find_pin(dbg, "Thickness", "Input"), "3.0", "thick")

    # dbg then -> Return (success true)
    # Find return with Success=true
    ret_true = None
    for n in ge.list_all_nodes():
        if bel.get_node_title(n) != "Return Node":
            continue
        sp = find_pin(n, "Success", "Input")
        if not sp:
            continue
        try:
            v = str(sp.get_pin_value()).lower()
        except Exception:
            v = ""
        unreal.log("return Success=" + v)
        if v == "true" or v == "1":
            ret_true = n
    if not ret_true:
        # pick return that was connected to set
        for cp in old_targets:
            if bel.get_node_title(cp.get_owning_node()) == "Return Node":
                ret_true = cp.get_owning_node()
                break
    if ret_true:
        connect(find_pin(dbg, "then", "Output"), find_pin(ret_true, "execute", "Input"), "dbg->ret")
        set_val(find_pin(ret_true, "Success", "Input"), "true", "ret.success")

    # Ensure set Item is Tilled again after any churn
    set_elem = None
    for n in ge.list_all_nodes():
        if "Set Array" in bel.get_node_title(n):
            set_elem = n
    if set_elem:
        item = find_pin(set_elem, "Item", "Input")
        set_val(item, "Tilled", "final.Item")
        unreal.log("final Item=" + str(item.get_pin_value()))

    try:
        bel.compile_blueprint(bp)
        unreal.log("compile ok")
    except Exception as ex:
        unreal.log_warning("compile: " + str(ex))
    unreal.EditorAssetLibrary.save_asset(MGR)
    unreal.log("=== phase2_tilled_visual done ===")


if __name__ == "__main__":
    main()