# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"
IMC = "/Game/TopDown/Input/IMC_Default"
IA = "/Game/TopDown/Input/Actions/IA_Interact"


def find_pin(node, name_substr, direction=None):
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None


def main():
    unreal.log("=== phase2_hoe_polish start ===")
    # Probe Key attributes
    keys = [a for a in dir(unreal.Key) if not a.startswith("_")]
    unreal.log("Key attrs sample: " + str(keys[:40]))
    for name in ("E", "W", "A", "S", "D", "SpaceBar", "LeftMouseButton"):
        unreal.log("hasattr Key.{} = {}".format(name, hasattr(unreal.Key, name)))

    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    ia = unreal.EditorAssetLibrary.load_asset(IA)

    # Try map like WASD — Key.W works in setup script
    mapped = False
    for maker in [
        lambda: unreal.Key.W,  # sanity
    ]:
        pass
    # Construct Key by importing from existing mapping
    dkm = imc.get_editor_property("default_key_mappings")
    mappings = dkm.get_editor_property("mappings") if hasattr(dkm, "get_editor_property") else None
    unreal.log("mappings type " + str(type(mappings)))
    try:
        mappings = dkm.mappings
    except Exception:
        pass
    # Get a working Key from W mapping and see structure
    try:
        raw = str(dkm)
        unreal.log("dkm str ok")
    except Exception:
        pass

    # Method: duplicate W mapping structure via map_key with Key from Name
    # UE5.8 python often: unreal.Key.E doesn't exist but unreal.find_object or
    # from unreal import Key — try InputKeySelector style
    candidates = []
    try:
        candidates.append(("Key.W", unreal.Key.W))
    except Exception as ex:
        unreal.log_warning(str(ex))
    # Enumerate all Key.* that look like letters
    for a in dir(unreal.Key):
        if len(a) == 1 and a.isalpha():
            candidates.append(("Key." + a, getattr(unreal.Key, a)))
    unreal.log("letter keys: " + str([c[0] for c in candidates]))

    # Alternative: EnhancedInputLibrary / InputCoreTypes
    try:
        e = unreal.InputCoreTypes.get_key("E")
        unreal.log("get_key E = " + str(e))
    except Exception as ex:
        unreal.log_warning("get_key: " + str(ex))

    # Try creating EnhancedActionKeyMapping and append to default_key_mappings
    try:
        # Copy key from existing W mapping by parsing — use map_key with same type as W
        wkey = unreal.Key.W
        unreal.log("W key struct = " + str(wkey))
        # Can we modify key_name?
        try:
            unreal.log("W key_name = " + str(wkey.get_editor_property("key_name")))
        except Exception as ex:
            unreal.log_warning(str(ex))
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Use AssetImport or text export — try map_key with keys from FKey table via Name
    for expr in [
        'unreal.load_object(None, "/Script/InputCore.Key")',
    ]:
        pass

    # Practical approach used by community: 
    # key = unreal.Key(); unreal.SystemLibrary... 
    # Or: imc.map_key(ia, unreal.Key.E) after ensuring
    # Check if it's lowercase
    for attr in dir(unreal.Key):
        if "e" == attr.lower() or attr.endswith("E") and len(attr) <= 3:
            unreal.log("candidate attr " + attr)

    # Read setup_wasd - it used unreal.Key.W successfully. Why no E?
    # Perhaps only keys already referenced get generated? Try forcing via
    # unreal.EditorAssetLibrary.load_asset and copy mapping from another project — skip.
    
    # Use DefaultKeyMappings import_text
    try:
        data = imc.get_editor_property("default_key_mappings")
        # Get mappings array and append
        arr = data.get_editor_property("mappings")
        unreal.log("arr len before " + str(len(arr)))
        # Build new mapping as string import
        new_map = unreal.EnhancedActionKeyMapping()
        new_map.set_editor_property("action", ia)
        # Steal key object from a known key by creating FKey via make
        # In UE Python 5.x: 
        key = unreal.Key()
        # Try set via export/import text on the mapping
        try:
            # EnhancedActionKeyMapping export
            txt = new_map.export_text() if hasattr(new_map, "export_text") else None
            unreal.log("export " + str(txt))
        except Exception as ex:
            unreal.log_warning(str(ex))
        # import_text on key field
        try:
            k = new_map.get_editor_property("key")
            # Struct has import_text?
            if hasattr(k, "import_text"):
                k.import_text("E")
                unreal.log("key after import_text " + str(k))
            else:
                # set on mapping via import
                new_map.import_text('(Action=None,Key=E)')
                unreal.log("mapping import " + str(new_map))
        except Exception as ex:
            unreal.log_warning("key import: " + str(ex))

        # Try setting key_name with Name("E") then map_key
        k2 = unreal.Key()
        try:
            k2.set_editor_property("key_name", "E")
            unreal.log("k2=" + str(k2) + " name=" + str(k2.get_editor_property("key_name")))
            m = imc.map_key(ia, k2)
            unreal.log("map with set key_name: " + str(m))
            mapped = True
        except Exception as ex:
            unreal.log_warning(str(ex))
    except Exception as ex:
        unreal.log_warning("arr approach: " + str(ex))

    # Another approach: use unreal.InputMappingContext.map_key with Key from C++ exposed constants
    # Check unreal.Keys module path
    for modname in ("Keys", "InputCoreTypes", "InputKey"):
        try:
            mod = getattr(unreal, modname)
            unreal.log("found " + modname + " " + str(dir(mod)[:20]))
        except Exception:
            pass

    # Fix PrintString messages via set_pin_value
    cbp = unreal.EditorAssetLibrary.load_asset(CHAR)
    cge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))
    for n in cge.list_all_nodes():
        if bel.get_node_title(n) != "Print String":
            continue
        # Check if in hoe chain: connected from Branch
        ein = find_pin(n, "execute", "Input")
        from_br = False
        if ein:
            for cp in list(ein.list_connected_pins()):
                if bel.get_node_title(cp.get_owning_node()) == "Branch":
                    from_br = True
        if not from_br:
            continue
        insp = find_pin(n, "InString", "Input")
        # Which branch?
        owner_br = None
        for cp in list(ein.list_connected_pins()):
            owner_br = cp.get_owning_node()
            pin_name = str(cp.get_pin_name())
            break
        msg = "Tilled!" if pin_name == "then" else "Cannot till"
        try:
            insp.set_pin_value(msg)
            unreal.log("set_pin_value " + msg + " ok")
        except Exception as ex:
            unreal.log_warning("set_pin_value: " + str(ex))
            for meth in dir(insp):
                if "default" in meth.lower() or "value" in meth.lower() or "string" in meth.lower():
                    unreal.log("  pin." + meth)

    try:
        bel.compile_blueprint(cbp)
        unreal.log("compile ok")
    except Exception as ex:
        unreal.log_warning(str(ex))
    unreal.EditorAssetLibrary.save_asset(CHAR)
    unreal.EditorAssetLibrary.save_asset(IMC)
    unreal.log("IMC final: " + str(imc.get_editor_property("default_key_mappings")))
    unreal.log("=== phase2_hoe_polish done ===")


if __name__ == "__main__":
    main()