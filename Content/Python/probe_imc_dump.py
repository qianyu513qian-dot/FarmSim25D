import unreal
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
dkm = imc.get_editor_property("default_key_mappings")
txt = dkm.export_text()
unreal.log("[IMCDUMP] len="+str(len(txt)))
# print in chunks
for i in range(0, min(len(txt), 4000), 500):
    unreal.log("[IMCDUMP] " + txt[i:i+500])
# also list action assets
for name in ("IA_Move","IA_Interact","IA_Plant","IA_Water","IA_Grow","IA_Harvest","IA_SetDestination"):
    p = "/Game/TopDown/Input/Actions/" + name
    unreal.log("[IMCDUMP] {} exists={}".format(p, unreal.EditorAssetLibrary.does_asset_exist(p)))
