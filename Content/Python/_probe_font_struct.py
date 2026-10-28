# -*- coding: utf-8 -*-
import unreal, json
font = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
out = {"face": face.get_path_name() if face else None, "font": font.get_path_name() if font else None}
# dump composite font structure
cf = font.get_editor_property("composite_font")
out["cf_type"] = str(type(cf))
out["cf_dir"] = [n for n in dir(cf) if not n.startswith("_")]
# try common property names
for prop in ("default_typeface", "DefaultTypeface", "fallback_typeface", "FallbackTypeface", "sub_typefaces", "SubTypefaces"):
    try:
        val = cf.get_editor_property(prop)
        out["prop_"+prop] = str(type(val)) + " " + str(val)[:200]
    except Exception as e:
        out["prop_"+prop] = "ERR " + str(e)
# Font itself props
out["font_props"] = []
for n in dir(font):
    if n.startswith("_"): continue
    if any(k in n.lower() for k in ("font", "face", "type", "compos", "cache", "legacy")):
        out["font_props"].append(n)

# Try LegacyFontName / font faces for offline fonts
try:
    out["font_cache_type"] = str(font.get_editor_property("font_cache_type"))
except Exception as e:
    out["font_cache_type"] = str(e)

# List all assets in Restaurant folder
assets = unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant", recursive=True)
out["restaurant_assets"] = [a for a in assets]

# Can we assign font.composite_font via restructuring?
# Method: create new Font via factory from FontFace if possible
# Or set runtime typeface through EditorAssetLibrary / FontEditor

# Inspect Typeface / TypefaceEntry availability
out["has_Typeface"] = hasattr(unreal, "Typeface")
out["has_TypefaceEntry"] = hasattr(unreal, "TypefaceEntry")
out["has_CompositeFont"] = hasattr(unreal, "CompositeFont")
if hasattr(unreal, "TypefaceEntry"):
    out["TypefaceEntry_dir"] = [n for n in dir(unreal.TypefaceEntry) if not n.startswith("_")][:40]
if hasattr(unreal, "Typeface"):
    out["Typeface_dir"] = [n for n in dir(unreal.Typeface) if not n.startswith("_")][:40]

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
