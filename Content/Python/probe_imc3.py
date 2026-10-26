# -*- coding: utf-8 -*-
import unreal
path = "/Game/TopDown/Input/IMC_Default"
ad = unreal.EditorAssetLibrary.find_asset_data(path)
unreal.log("asset_data valid=" + str(ad.is_valid()) + " soft=" + str(ad.to_soft_object_path()) + " pkg=" + str(ad.package_name))
obj = ad.get_asset()
unreal.log("get_asset=" + str(obj) + " type=" + str(type(obj)))
obj2 = unreal.load_object(None, path + ".IMC_Default")
unreal.log("load_object=" + str(obj2))
obj3 = unreal.load_asset(path)
unreal.log("unreal.load_asset=" + str(obj3))
# open package
pkg = unreal.load_package(str(ad.package_name))
unreal.log("pkg=" + str(pkg))
if obj is None and pkg:
    obj = unreal.find_object(pkg, "IMC_Default")
    unreal.log("find_object=" + str(obj))
imc = obj or obj2 or obj3
if imc:
    txt = imc.get_editor_property("default_key_mappings").export_text()
    unreal.log("len=" + str(len(txt)))
    unreal.log("E=" + str("Key=E" in txt) + " F=" + str("Key=F" in txt) + " R=" + str("Key=R" in txt) + " Water=" + str("IA_Water" in txt))
    # print all Key= snippets
    import re
    for m in re.finditer(r"Action=\"[^\"]+\".*?Key=[A-Za-z0-9]+", txt):
        unreal.log("K: " + m.group(0)[-120:])
else:
    unreal.log_error("still no imc")
