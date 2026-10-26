# -*- coding: utf-8 -*-
import unreal
IMC = "/Game/TopDown/Input/IMC_Default"
IA_W = "/Game/TopDown/Input/Actions/IA_Water"
IA_P = "/Game/TopDown/Input/Actions/IA_Plant"
IA_I = "/Game/TopDown/Input/Actions/IA_Interact"
imc = unreal.EditorAssetLibrary.load_asset(IMC)
txt = imc.get_editor_property("default_key_mappings").export_text()
unreal.log("HAS E=" + str("Key=E" in txt) + " F=" + str("Key=F" in txt) + " R=" + str("Key=R" in txt))
unreal.log("HAS Interact=" + str("IA_Interact" in txt) + " Plant=" + str("IA_Plant" in txt) + " Water=" + str("IA_Water" in txt))
# dump mapping lines containing E F R Water Plant Interact
for part in txt.replace("),(", ")|(").split("|"):
    if any(k in part for k in ("Key=E", "Key=F", "Key=R", "IA_Water", "IA_Plant", "IA_Interact")):
        unreal.log("MAP: " + part[:200])
for p in (IA_I, IA_P, IA_W):
    unreal.log("asset " + p + " exists=" + str(unreal.EditorAssetLibrary.does_asset_exist(p)))
