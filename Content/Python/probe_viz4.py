# -*- coding: utf-8 -*-
"""Probe spawn nodes + scene soil labels + TillCell success chain pins."""
import unreal

bel = unreal.BlueprintEditorLibrary
MGR = "/Game/Farm/Grid/BP_GridManager"

def log(m):
    unreal.log("[PROBE_VIZ4] " + str(m))

def dump_pins(node, label):
    for p in bel.list_all_pins(node):
        val = ""
        try:
            val = str(p.get_pin_value())
        except Exception:
            pass
        cps = list(p.list_connected_pins())
        log("  [{}] {} dir={} val=[{}] conn={}".format(
            label, p.get_pin_name(), p.get_pin_direction(), val, len(cps)))
        for cp in cps[:4]:
            log("    -> {}.{}".format(bel.get_node_title(cp.get_owning_node()), cp.get_pin_name()))

def main():
    log("=== start ===")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("Soil_") or lab.startswith("Hoe") or "Untilled" in lab or lab.startswith("Crop"):
            loc = a.get_actor_location()
            sc = a.get_actor_scale3d()
            tags = list(a.tags) if hasattr(a, "tags") else []
            log("actor {} loc=({:.1f},{:.1f},{:.1f}) sc=({:.4f},{:.4f},{:.4f}) tags={}".format(
                lab, loc.x, loc.y, loc.z, sc.x, sc.y, sc.z, tags))
            n += 1
            if n > 25:
                break
    log("soil-ish count sampled=" + str(n))

    # TillCell exec chain around Set/Debug/Return
    bp = unreal.load_asset(MGR)
    ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "TillCell"))
    for n in ge.list_all_nodes():
        t = bel.get_node_title(n)
        if t in ("Set Array Elem", "DrawDebugBox", "GridToWorld", "Return Node", "MakeVector") or "Debug" in t:
            log("NODE " + t)
            dump_pins(n, t)

    # Probe spawn in a throwaway: use GrowCell? Better temporary on HarvestCell? Use EventGraph add+remove
    ege = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(bp))
    created = []
    for name in [
        "Spawn Actor from Class",
        "Gameplay|Spawn Actor from Class",
        "Get All Actors with Tag",
        "Destroy Actor",
        "Set Actor Hidden In Game",
        "Is Valid",
        "Make Transform",
        "Make Literal Name",
        "Conv_StringToName",
        "Concat_StrStr",
        "BuildString_Int",
        "Format Text",
    ]:
        try:
            node = ege.create_node_from_name(name, unreal.Vector2D(20, 20), [])
            if node:
                pins = [str(p.get_pin_name()) for p in bel.list_all_pins(node)]
                log("CREATE OK {} pins={}".format(name, pins))
                created.append(node)
            else:
                log("CREATE NONE " + name)
        except Exception as e:
            log("CREATE FAIL {}: {}".format(name, e))

    for path in [
        "/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass",
        "/Script/Engine.GameplayStatics:FinishSpawningActor",
        "/Script/Engine.KismetSystemLibrary:IsValid",
        "/Script/Engine.Actor:K2_DestroyActor",
        "/Script/Engine.Actor:SetActorHiddenInGame",
        "/Script/Engine.KismetMathLibrary:MakeTransform",
        "/Script/Engine.KismetStringLibrary:Concat_StrStr",
        "/Script/Engine.KismetStringLibrary:Conv_IntToString",
        "/Script/Engine.KismetStringLibrary:Conv_StringToName",
        "/Script/Engine.KismetSystemLibrary:MakeLiteralName",
        "/Game/Farm/Grid/BP_PlotVisual.BP_PlotVisual_C:ApplyState",
        "/Script/Engine.StaticMeshComponent:SetStaticMesh",
        "/Script/Engine.PrimitiveComponent:SetVisibility",
        "/Script/Engine.SceneComponent:SetRelativeScale3D",
    ]:
        try:
            node = ege.add_call_function_node(path)
            if node and len(bel.list_all_pins(node)) > 0:
                pins = [str(p.get_pin_name()) for p in bel.list_all_pins(node)]
                log("CALL OK {} pins={}".format(path.split(":")[-1], pins))
                created.append(node)
            else:
                log("CALL empty " + path)
                if node:
                    created.append(node)
        except Exception as e:
            log("CALL FAIL {}: {}".format(path, e))

    if created:
        ege.remove_nodes(created)
        log("removed " + str(len(created)))
    log("=== done ===")

if __name__ == "__main__":
    main()
