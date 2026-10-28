# -*- coding: utf-8 -*-
"""Wire FontFace into Font composite_font; verify TextRender font has glyphs."""
import unreal, json

REPORT = {"steps": [], "errors": []}
face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
font = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
REPORT["face"] = face.get_path_name() if face else None
REPORT["font"] = font.get_path_name() if font else None

cf = font.get_editor_property("composite_font")
d = None
try:
    d = cf.to_dict()
    REPORT["cf_dict"] = {k: str(v)[:300] for k, v in d.items()}
except Exception as e:
    REPORT["errors"].append("to_dict " + str(e))

# Try export_text
try:
    REPORT["cf_export"] = cf.export_text()[:1500]
except Exception as e:
    REPORT["errors"].append("export " + str(e))

# Get default_typeface via get_editor_property
try:
    tf = cf.get_editor_property("default_typeface")
    REPORT["tf_type"] = str(type(tf))
    try:
        REPORT["tf_dict"] = {k: str(v)[:300] for k, v in tf.to_dict().items()}
    except Exception as e:
        REPORT["tf_dict_err"] = str(e)
    try:
        REPORT["tf_export"] = tf.export_text()[:1500]
    except Exception as e:
        REPORT["tf_export_err"] = str(e)
    fonts = None
    try:
        fonts = tf.get_editor_property("fonts")
        REPORT["fonts_len"] = len(list(fonts)) if fonts is not None else None
        REPORT["fonts_items"] = []
        for i, ent in enumerate(list(fonts) if fonts is not None else []):
            item = {"i": i, "type": str(type(ent))}
            try:
                item["dict"] = {k: str(v)[:200] for k, v in ent.to_dict().items()}
            except Exception as e:
                item["dict_err"] = str(e)
            try:
                item["export"] = ent.export_text()[:400]
            except Exception as e:
                item["export_err"] = str(e)
            REPORT["fonts_items"].append(item)
    except Exception as e:
        REPORT["fonts_err"] = str(e)
except Exception as e:
    REPORT["errors"].append("tf " + str(e))

# Attempt wire: set font face on entry 0, or rebuild via import_text
wired = False
try:
    tf = cf.get_editor_property("default_typeface")
    fonts = list(tf.get_editor_property("fonts"))
    if fonts:
        ent = fonts[0]
        # set font property to face
        try:
            ent.set_editor_property("font", face)
            wired = True
            REPORT["steps"].append("set entry0.font")
        except Exception as e:
            REPORT["errors"].append("set font prop " + str(e))
        # also try name
        try:
            ent.set_editor_property("name", "Default")
        except Exception:
            pass
        # write back array
        try:
            tf.set_editor_property("fonts", fonts)
            cf.set_editor_property("default_typeface", tf)
            font.set_editor_property("composite_font", cf)
            font.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
            REPORT["steps"].append("writeback ok")
        except Exception as e:
            REPORT["errors"].append("writeback " + str(e))
    else:
        # empty — try import_text to inject
        REPORT["steps"].append("fonts empty, try import_text")
except Exception as e:
    REPORT["errors"].append("wire " + str(e))

# If still empty, craft Typeface via import_text on CompositeFont
if not wired or (REPORT.get("fonts_len") == 0):
    try:
        # Build a minimal composite font text. Format varies by engine version.
        # Common runtime composite:
        face_path = face.get_path_name()
        # Try Python struct construction via set_editor_properties with nested dicts
        # First discover TypefaceEntry struct
        for name in dir(unreal):
            if "ypeface" in name or "ontFace" in name or name.startswith("Font"):
                if "ype" in name.lower() or name in ("Font", "FontFace", "CompositeFont"):
                    pass
        typeface_names = [n for n in dir(unreal) if "ypeface" in n.lower() or "Typeface" in n]
        REPORT["typeface_api"] = typeface_names
        # Try unreal.find_object / load
    except Exception as e:
        REPORT["errors"].append("craft " + str(e))

# Alternative: use Font's editor utility to add typeface — SubobjectData?
# Try: duplicate Engine Roboto Font and replace face
try:
    roboto = unreal.EditorAssetLibrary.load_asset("/Engine/EngineFonts/Roboto")
    if roboto:
        rcf = roboto.get_editor_property("composite_font")
        REPORT["roboto_export"] = rcf.export_text()[:2000]
        REPORT["roboto_cache"] = str(roboto.get_editor_property("font_cache_type"))
except Exception as e:
    REPORT["errors"].append("roboto " + str(e))

# After wire, re-read
try:
    cf2 = font.get_editor_property("composite_font")
    REPORT["after_export"] = cf2.export_text()[:1500]
    tf2 = cf2.get_editor_property("default_typeface")
    fonts2 = list(tf2.get_editor_property("fonts"))
    REPORT["after_fonts_len"] = len(fonts2)
    if fonts2:
        try:
            REPORT["after_entry0"] = fonts2[0].export_text()[:500]
            fobj = fonts2[0].get_editor_property("font")
            REPORT["after_face"] = fobj.get_path_name() if fobj else None
        except Exception as e:
            REPORT["after_entry_err"] = str(e)
except Exception as e:
    REPORT["errors"].append("after " + str(e))

unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/Font_SimHei_TR")

# Verify labels still have correct text + font assigned
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
labs = []
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("RestLabel_"):
        tr = a.get_component_by_class(unreal.TextRenderComponent)
        row = {"label": lab}
        if tr:
            try:
                t = tr.get_editor_property("text")
                row["text_cps"] = [hex(ord(c)) for c in str(t)]
                row["text"] = str(t)
            except Exception as e:
                row["text_err"] = str(e)
            try:
                f = tr.get_editor_property("font")
                row["font"] = f.get_path_name() if f else None
                row["font_class"] = f.get_class().get_name() if f else None
            except Exception as e:
                row["font_err"] = str(e)
            try:
                row["world_size"] = float(tr.get_editor_property("world_size"))
            except Exception:
                pass
        labs.append(row)
REPORT["labels_now"] = labs
REPORT["wired"] = wired

open(r"E:\UE\FarmSim25D\Saved\restaurant_font_wire.json","w",encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))