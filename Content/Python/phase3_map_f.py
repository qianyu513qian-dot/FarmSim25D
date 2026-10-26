# -*- coding: utf-8 -*-
import unreal

IMC = "/Game/TopDown/Input/IMC_Default"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"
IA_INTERACT = "/Game/TopDown/Input/Actions/IA_Interact"

imc = unreal.EditorAssetLibrary.load_asset(IMC)
ia_p = unreal.EditorAssetLibrary.load_asset(IA_PLANT)
ia_i = unreal.EditorAssetLibrary.load_asset(IA_INTERACT)

# Dump default_key_mappings
try:
    dkm = imc.get_editor_property("default_key_mappings")
    unreal.log("default_key_mappings type=" + str(type(dkm)) + " len=" + str(len(list(dkm))))
    for i, m in enumerate(list(dkm)):
        try:
            action = m.get_editor_property("action")
            key = m.get_editor_property("key")
            unreal.log("map[{}] action={} key={}".format(i, action, key))
            try:
                unreal.log("  key_name=" + str(key.get_editor_property("key_name")))
            except Exception as ex:
                unreal.log_warning("  key_name: " + str(ex))
        except Exception as ex:
            unreal.log_warning("map {}: {}".format(i, ex))
except Exception as ex:
    unreal.log_warning("dkm: " + str(ex))

# How to construct Key properly
unreal.log("Key methods:")
k = unreal.Key()
for m in dir(k):
    if not m.startswith("_"):
        unreal.log("  Key." + m)

# Try Keys from unreal.Keys or InputCore
for name in ("Keys", "InputKey", "EKeys"):
    if hasattr(unreal, name):
        unreal.log("has unreal." + name)
        obj = getattr(unreal, name)
        for attr in ("E", "F", "W", "A"):
            if hasattr(obj, attr):
                unreal.log("  {}.{}={}".format(name, attr, getattr(obj, attr)))

# Probe Key constructor
for args in (("F",), ("E",)):
    try:
        # In some versions Key is created via make
        pass
    except Exception:
        pass

# Try map via setting default_key_mappings array
try:
    # First unmap plant
    try:
        imc.unmap_all_keys_from_action(ia_p)
    except Exception as ex:
        unreal.log_warning(str(ex))

    # Build EnhancedActionKeyMapping manually
    mapping = unreal.EnhancedActionKeyMapping()
    mapping.set_editor_property("action", ia_p)
    # Find how E key looks in existing mapping
    dkm = list(imc.get_editor_property("default_key_mappings"))
    e_key = None
    for m in dkm:
        a = m.get_editor_property("action")
        if a and "IA_Interact" in str(a):
            e_key = m.get_editor_property("key")
            unreal.log("Interact key object=" + str(e_key) + " repr=" + repr(e_key))
            # export text?
            try:
                unreal.log("Interact key export=" + str(e_key.export_text() if hasattr(e_key, "export_text") else "n/a"))
            except Exception:
                pass
            for prop in ("key_name", "KeyName"):
                try:
                    unreal.log("  {}={}".format(prop, e_key.get_editor_property(prop)))
                except Exception as ex:
                    unreal.log_warning("  {}: {}".format(prop, ex))
            break

    # Try creating F key like E
    fk = unreal.Key()
    for val in ("F", "F_Key", "Keyboard_F"):
        try:
            fk.set_editor_property("key_name", val)
            unreal.log("set key_name {!r} -> {!r}".format(val, fk.get_editor_property("key_name")))
        except Exception as ex:
            unreal.log_warning(str(ex))

    # map_key again and inspect result key
    m = imc.map_key(ia_p, fk)
    unreal.log("map result=" + str(m))
    try:
        unreal.log("result.key=" + str(m.get_editor_property("key")))
        unreal.log("result.key_name=" + str(m.get_editor_property("key").get_editor_property("key_name")))
    except Exception as ex:
        unreal.log_warning(str(ex))

    unreal.EditorAssetLibrary.save_asset(IMC)
    dkm2 = list(imc.get_editor_property("default_key_mappings"))
    unreal.log("after save count=" + str(len(dkm2)))
    for i, m in enumerate(dkm2):
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = ""
        try:
            kn = k.get_editor_property("key_name")
        except Exception:
            kn = str(k)
        unreal.log("  [{}] {} key={}".format(i, a, kn))
except Exception as ex:
    unreal.log_warning("manual: " + str(ex))
