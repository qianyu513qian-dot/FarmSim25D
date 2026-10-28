# -*- coding: utf-8 -*-
import unreal, json
REPORT = {"factories": [], "font_assets": [], "errors": []}
# list restaurant assets
for a in unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant", False):
    asset = unreal.EditorAssetLibrary.load_asset(a.split(".")[0])
    REPORT["font_assets"].append({"path": a, "class": asset.get_class().get_name() if asset else None})

# try create Font from FontFace
face_path = "/Game/Farm/Restaurant/Font_SimHei"
face = unreal.EditorAssetLibrary.load_asset(face_path)
REPORT["face_class"] = face.get_class().get_name() if face else None

out_path = "/Game/Farm/Restaurant/Font_SimHei_TR"
if unreal.EditorAssetLibrary.does_asset_exist(out_path):
    unreal.EditorAssetLibrary.delete_asset(out_path)

factory = None
for name in ("FontFactory", "TrueTypeFontFactory", "CompositeFontFactory"):
    try:
        factory = getattr(unreal, name)()
        REPORT["factories"].append(name + "=ok")
        break
    except Exception as e:
        REPORT["factories"].append(name + "=" + str(e))

font = None
if factory:
    try:
        font = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "Font_SimHei_TR", "/Game/Farm/Restaurant", unreal.Font, factory)
        REPORT["created"] = font.get_path_name() if font else None
        REPORT["created_class"] = font.get_class().get_name() if font else None
    except Exception as e:
        REPORT["errors"].append("create_asset " + str(e))

# Inspect Font properties
if font:
    props = []
    for p in ["font_cache_type", "composite_font", "legacy_font_name", "import_options"]:
        try:
            props.append({p: str(font.get_editor_property(p))[:200]})
        except Exception as e:
            props.append({p: "ERR " + str(e)})
    REPORT["font_props"] = props
    # Try set offline + typeface from face
    try:
        font.set_editor_property("font_cache_type", unreal.FontCacheType.OFFLINE)
        REPORT["set_offline"] = True
    except Exception as e:
        REPORT["set_offline"] = str(e)
    try:
        # Runtime composite font
        font.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
        REPORT["set_runtime"] = True
    except Exception as e:
        REPORT["set_runtime"] = str(e)

# Also check if FontFace can be used via CompositeFont API
try:
    REPORT["CompositeFont"] = str(dir(unreal.CompositeFont))[:500]
except Exception as e:
    REPORT["CompositeFont"] = str(e)
try:
    REPORT["Typeface"] = str(dir(unreal.Typeface))[:500]
except Exception as e:
    REPORT["Typeface"] = str(e)
try:
    REPORT["TypefaceEntry"] = str(dir(unreal.TypefaceEntry))[:500]
except Exception as e:
    REPORT["TypefaceEntry"] = str(e)

if font:
    unreal.EditorAssetLibrary.save_asset(out_path)

open(r"E:\UE\FarmSim25D\Saved\restaurant_font_probe.json","w",encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))
