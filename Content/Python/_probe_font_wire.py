# -*- coding: utf-8 -*-
import unreal, json
face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
tr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
off = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_Offline")
out = {}
for name, f in (("TR", tr), ("Offline", off)):
    info = {"class": f.get_class().get_name()}
    try:
        info["cache"] = str(f.get_editor_property("font_cache_type"))
    except Exception as e:
        info["cache"] = str(e)
    try:
        cf = f.get_editor_property("composite_font")
        info["cf_export"] = cf.export_text()[:1500]
        info["cf_dict"] = cf.to_dict()
    except Exception as e:
        info["cf_err"] = str(e)
    # legacy
    for p in ("legacy_font_name", "LegacyFontName", "legacy_font_size", "LegacyFontSize", "textures", "Textures"):
        try:
            info[p] = str(f.get_editor_property(p))[:200]
        except Exception as e:
            info[p] = "ERR"
    out[name] = info
# Face source
try:
    out["face_source"] = str(face.get_editor_property("source_filename"))
except Exception as e:
    try:
        out["face_source"] = str(face.source_filename)
    except Exception as e2:
        out["face_source"] = str(e) + "/" + str(e2)
try:
    out["face_export"] = str(face.export_to_text() if hasattr(face,"export_to_text") else "n/a")[:200]
except Exception:
    pass

# Try wire via import_text on composite - build typeface entry text
# Typical export format for CompositeFont...
cf = tr.get_editor_property("composite_font")
out["tr_cf_before"] = cf.export_text()[:800]

# Attempt: use FontFace path in DefaultTypeface
# From UE Source, CompositeFont export looks like:
# (DefaultTypeface=(Fonts=((Name="Regular",Font=...))))
face_path = face.get_path_name()
# Try import
payload = '(DefaultTypeface=(Fonts=((Name="Default",Font="{}"))))'.format(face_path)
try:
    cf2 = tr.get_editor_property("composite_font")
    cf2.import_text(payload)
    tr.set_editor_property("composite_font", cf2)
    out["import_try"] = "ok"
    out["tr_cf_after"] = tr.get_editor_property("composite_font").export_text()[:800]
except Exception as e:
    out["import_try"] = str(e)

# Also try Offline font on one label as test
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if (a.get_actor_label() or "") == "RestLabel_OpenSign":
        comp = a.get_component_by_class(unreal.TextRenderComponent)
        out["open_font_now"] = comp.font.get_path_name() if comp.font else None
        # Prefer Offline if it has real glyphs
        use = off if off else tr
        try:
            # Offline might be better for TextRender historically
            if off:
                # check offline cache type - Offline fonts use texture atlas
                cache = str(off.get_editor_property("font_cache_type"))
                out["offline_cache"] = cache
                if "OFFLINE" in cache.upper() or "0" in cache:
                    # Offline fonts often don't have CJK unless baked - Runtime+FontFace is correct approach
                    pass
        except Exception as e:
            out["offline_check"] = str(e)
        break

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
