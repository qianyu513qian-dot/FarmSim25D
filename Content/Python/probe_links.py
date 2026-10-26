# -*- coding: utf-8 -*-
"""Probe pin link APIs that actually work in UE5.8."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[L] " + str(m))
    print("[L] " + str(m))

bp = unreal.load_asset(CHAR)
eg = bel.find_graph(bp, "EventGraph")
ge = unreal.BlueprintGraphEditor.get_graph_editor(eg)
nodes = list(ge.list_all_nodes())

# Find Planted print
target = None
for n in nodes:
    for p in bel.list_all_pins(n):
        if str(p.get_pin_name()) == "InString":
            try:
                if p.get_pin_value() == "Planted!":
                    target = n
            except Exception:
                pass
log("Planted node=" + str(target))

if target:
    for p in bel.list_all_pins(target):
        pn = str(p.get_pin_name())
        methods = [m for m in dir(p) if "link" in m.lower() or "connect" in m.lower() or "Linked" in m]
        log("pin {} methods={}".format(pn, methods))
        for mname in ("get_linked_to", "GetLinkedTo", "linked_to", "has_any_connections", "is_connected"):
            if hasattr(p, mname):
                try:
                    r = getattr(p, mname)
                    r = r() if callable(r) else r
                    log("  {}.{} => {!r}".format(pn, mname, r))
                except Exception as e:
                    log("  {}.{} ERR {}".format(pn, mname, e))
        # try bel helpers
    log("bel pin helpers: " + str([x for x in dir(bel) if "pin" in x.lower() or "link" in x.lower() or "connect" in x.lower()][:40]))
    log("ge helpers: " + str([x for x in dir(ge) if "link" in x.lower() or "connect" in x.lower() or "pin" in x.lower()][:40]))

# Try Schema break/find
log("has EdGraphSchema_K2=" + str(hasattr(unreal, "EdGraphSchema_K2")))
# Check pin linked via get_editor_property
if target:
    for p in bel.list_all_pins(target):
        if str(p.get_pin_name()) != "execute":
            continue
        for prop in dir(p):
            if prop.startswith("_"):
                continue
            if "link" in prop.lower() or "Linked" in prop:
                try:
                    v = getattr(p, prop)
                    if callable(v):
                        v = v()
                    log("exec.{}={!r}".format(prop, v))
                except Exception as e:
                    log("exec.{} ERR {}".format(prop, e))
