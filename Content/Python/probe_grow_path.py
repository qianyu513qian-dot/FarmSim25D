# -*- coding: utf-8 -*-
"""Probe grow path: IMC G, GrowCell, WaterCell VisualizeCell states, ApplyState 3/4 meshes."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"
PV = "/Game/Farm/Grid/BP_PlotVisual"
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"


def log(m):
    unreal.log("[GROW_PROBE] " + str(m))


def find_pin(node, name_substr, direction=None):
    if not node:
        return None
    for p in bel.list_all_pins(node):
        if name_substr.lower().replace(" ", "") in str(p.get_pin_name()).lower().replace(" ", ""):
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def pin_val(p):
    try:
        return str(p.get_pin_value())
    except Exception:
        return "?"


# --- IMC G / IA_Grow ---
log("=== IMC ===")
imc = unreal.load_asset(IMC)
if imc:
    try:
        mappings = imc.get_editor_property("mappings") or imc.get_editor_property("Mappings")
        for m in mappings:
            try:
                action = m.get_editor_property("action") or m.get_editor_property("Action")
                key = m.get_editor_property("key") or m.get_editor_property("Key")
                an = action.get_name() if action else "?"
                kn = str(key)
                if any(x in an.upper() + kn.upper() for x in ("GROW", "WATER", "PLANT", "HARVEST", "INTERACT", "G", "R", "F", "H", "E")):
                    log("map action={} key={}".format(an, kn))
            except Exception as e:
                log("map err " + str(e))
    except Exception as e:
        log("IMC mappings: " + str(e))
        # try enhanced input API
        try:
            for m in imc.mappings:
                log("m=" + str(m))
        except Exception as e2:
            log(str(e2))
else:
    # search
    for a in unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False):
        if "IMC" in a and "Default" in a:
            log("IMC cand " + a)

# --- Character Grow wiring ---
log("=== CHAR Grow/Water ===")
char = unreal.load_asset(CHAR)
for gname in bel.list_graph_names(char):
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(char, str(gname)))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if any(k in t for k in ("Grow", "Water", "IA_Grow", "IA_Water", "Started", "Triggered")):
            if any(k in t for k in ("Grow", "Water", "IA_")):
                log("CHAR[{}] {}".format(gname, t))
                for p in bel.list_all_pins(n):
                    d = str(p.get_pin_direction())
                    cps = list(p.list_connected_pins())
                    v = pin_val(p)
                    if cps or (v and v not in ("", "0", "False", "?")):
                        log("  {}.{} dir={} val=[{}] <-{}".format(
                            t, p.get_pin_name(), d, v,
                            [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:4]))

# --- GrowCell / WaterCell graphs ---
log("=== GrowCell / WaterCell ===")
bp = unreal.load_asset(MGR)
for fname in ("WaterCell", "GrowCell", "HarvestCell"):
    g = bel.find_graph(bp, fname)
    if not g:
        log(fname + " MISSING")
        continue
    ge = unreal.BlueprintGraphEditor.get_graph_editor(g)
    try:
        errs = ge.list_nodes_with_errors()
        log("{} errors={}".format(fname, len(errs)))
        for n in errs:
            log("  ERR " + bel.get_node_title(n))
    except Exception as e:
        log(str(e))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        # Focus on state checks, Set, VisualizeCell, Branch, Equal
        interesting = any(k in t for k in (
            "Visualize", "Equal", "Branch", "Set", "Return", "DrawDebug",
            "Get", "Plot", "State", "Watered", "Ready", "Planted"))
        if not interesting and t not in (fname,):
            continue
        for p in bel.list_all_pins(n):
            d = str(p.get_pin_direction())
            cps = list(p.list_connected_pins())
            v = pin_val(p)
            # show input pins with values or connections, and key outputs
            if "INPUT" in d.upper() or "input" in d.lower():
                if cps or (v and v not in ("", "?")):
                    log("  {}.{} =[{}] <-{}".format(
                        t, p.get_pin_name(), v,
                        [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:3]))
            elif "Visualize" in t or t == "Return Node":
                if cps or (v and v not in ("", "?")):
                    log("  {}.{} dir={} =[{}] ->{}".format(
                        t, p.get_pin_name(), d, v,
                        [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in cps][:3]))

# --- ApplyState states 2/3/4 mesh wiring ---
log("=== ApplyState meshes ===")
pv = unreal.load_asset(PV)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(pv, "ApplyState"))
# Walk SetStaticMesh nodes and their NewMesh sources
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    if "SetStaticMesh" in t.replace(" ", "") or t == "Set Static Mesh":
        self_c = find_pin(n, "self", "Input")
        mesh_c = find_pin(n, "NewMesh", "Input")
        self_from = []
        mesh_from = []
        if self_c:
            self_from = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name()), pin_val(c)) for c in self_c.list_connected_pins()]
        if mesh_c:
            mesh_from = [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name()), pin_val(c)) for c in mesh_c.list_connected_pins()]
            if not mesh_from:
                mesh_from = [("LITERAL", pin_val(mesh_c))]
        log("SetStaticMesh self={} mesh={}".format(self_from, mesh_from))
    if "Equal" in t.lower() or t.startswith("Equal"):
        log("Equal A_conn={} B=[{}]".format(
            [(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in (find_pin(n, "A", "Input").list_connected_pins() if find_pin(n, "A", "Input") else [])],
            pin_val(find_pin(n, "B", "Input"))))

# CDO mesh vars
gen = unreal.load_object(None, PV + ".BP_PlotVisual_C")
cdo = unreal.get_default_object(gen) if gen else None
if cdo:
    for vn in ("Mesh_SoilDry", "Mesh_SoilWet", "Mesh_Seed", "Mesh_Grow", "Mesh_Mature"):
        try:
            v = cdo.get_editor_property(vn)
            log("CDO.{}={}".format(vn, v.get_path_name() if v else None))
        except Exception as e:
            log("CDO.{} {}".format(vn, e))

log("=== DONE ===")
