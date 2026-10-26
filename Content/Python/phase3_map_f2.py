# -*- coding: utf-8 -*-
import unreal

IMC = "/Game/TopDown/Input/IMC_Default"
IA_PLANT = "/Game/TopDown/Input/Actions/IA_Plant"
IA_INTERACT = "/Game/TopDown/Input/Actions/IA_Interact"

imc = unreal.EditorAssetLibrary.load_asset(IMC)
ia_p = unreal.EditorAssetLibrary.load_asset(IA_PLANT)
ia_i = unreal.EditorAssetLibrary.load_asset(IA_INTERACT)

dkm = imc.get_editor_property("default_key_mappings")
unreal.log("dkm=" + str(dkm) + " type=" + str(type(dkm)))
for m in dir(dkm):
    if not m.startswith("_"):
        unreal.log("dkm." + m)

# Try mappings via get_mappings or similar on IMC
for m in dir(imc):
    if not m.startswith("_") and ("map" in m.lower() or "key" in m.lower()):
        unreal.log("imc." + m)

# Key import_text
for txt in ("F", "E", "(F)", "Key(F)", "F_Key"):
    k = unreal.Key()
    try:
        k.import_text(txt)
        unreal.log("import_text {!r} -> export={!r} dict={}".format(txt, k.export_text(), k.to_dict()))
    except Exception as ex:
        unreal.log_warning("import {}: {}".format(txt, ex))

# Copy key from interact mapping via map_key result from a known-good approach
# Try: get_mappings method
for meth in ("get_mappings", "get_default_key_mappings", "get_mappings_for_action"):
    if hasattr(imc, meth):
        try:
            r = getattr(imc, meth)() if meth != "get_mappings_for_action" else getattr(imc, meth)(ia_i)
            unreal.log(meth + " -> " + str(r))
        except Exception as ex:
            unreal.log_warning(meth + ": " + str(ex))

# EnhancedInputLibrary?
if hasattr(unreal, "EnhancedInputLibrary"):
    unreal.log("EnhancedInputLibrary yes")
    for m in dir(unreal.EnhancedInputLibrary):
        if not m.startswith("_"):
            unreal.log("  " + m)

# Inspect MappingData fields
try:
    for prop in ("mappings", "Mappings", "key_mappings", "KeyMappings"):
        try:
            v = dkm.get_editor_property(prop)
            unreal.log("dkm.{}={}".format(prop, v))
            try:
                for i, item in enumerate(list(v)):
                    unreal.log("  item{}={}".format(i, item))
                    if i > 20:
                        break
            except Exception as ex:
                unreal.log_warning("iter: " + str(ex))
        except Exception as ex:
            unreal.log_warning("prop {}: {}".format(prop, ex))
except Exception as ex:
    unreal.log_warning(str(ex))

# map_key with import_text F
k = unreal.Key()
k.import_text("F")
unreal.log("F key export=" + k.export_text() + " dict=" + str(k.to_dict()))
try:
    imc.unmap_all_keys_from_action(ia_p)
except Exception as ex:
    unreal.log_warning(str(ex))
m = imc.map_key(ia_p, k)
unreal.log("mapped=" + str(m))
try:
    unreal.log("m.key export=" + m.get_editor_property("key").export_text())
    unreal.log("m.action=" + str(m.get_editor_property("action")))
except Exception as ex:
    unreal.log_warning(str(ex))
unreal.EditorAssetLibrary.save_asset(IMC)

# Also try mapping E on interact to see format
try:
    maps_i = imc.get_mappings_for_action(ia_i) if hasattr(imc, "get_mappings_for_action") else None
    unreal.log("interact maps=" + str(maps_i))
except Exception as ex:
    unreal.log_warning(str(ex))
