# -*- coding: utf-8 -*-
"""Fix Chinese labels + bind FontFace into Runtime Font for TextRender."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"steps": [], "errors": [], "labels": []}

# Unicode escapes — never rely on source file encoding
CN = {
    "OpenSign": "\u5f00\u4e1a\u724c",   # 开业牌
    "Stove": "\u7076\u53f0",             # 灶台
    "Table1": "\u9910\u684c1",           # 餐桌1
    "Table2": "\u9910\u684c2",           # 餐桌2
    "Trash": "\u5783\u573e\u6876",       # 垃圾桶
}
COLORS = {
    "OpenSign": (1.0, 0.95, 0.2),
    "Stove": (1.0, 0.45, 0.15),
    "Table1": (0.35, 0.85, 1.0),
    "Table2": (0.35, 1.0, 0.55),
    "Trash": (0.85, 0.85, 0.85),
}
TARGET = {
    "OpenSign": "Restaurant_OpenSign",
    "Stove": "Restaurant_Stove",
    "Table1": "Restaurant_Table1",
    "Table2": "Restaurant_Table2",
    "Trash": "Restaurant_Trash",
}
TEXT_WORLD_SIZE = 56.0
TEXT_Z_OFFSET = 100.0

def log(m):
    unreal.log("[REST_LABELFIX] " + str(m))
    REPORT["steps"].append(str(m))

def find_by_label():
    d = {}
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label() or ""
        d[lab] = a
    return d

# ---- Build Runtime Font with FontFace ----
face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
font_path = "/Game/Farm/Restaurant/Font_SimHei_TR"
font = unreal.EditorAssetLibrary.load_asset(font_path) if unreal.EditorAssetLibrary.does_asset_exist(font_path) else None
if font is None:
    font = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "Font_SimHei_TR", "/Game/Farm/Restaurant", unreal.Font, unreal.FontFactory())
log("face={} font={}".format(face.get_class().get_name() if face else None,
                              font.get_class().get_name() if font else None))

# Wire composite font default typeface to our FontFace
wired = False
if font and face:
    try:
        font.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
    except Exception as e:
        REPORT["errors"].append("cache_type " + str(e))
    # Try several API shapes for composite font / typeface
    try:
        cf = font.get_editor_property("composite_font")
        REPORT["cf_type"] = str(type(cf))
        # Inspect fields
        fields = []
        for name in dir(cf):
            if name.startswith("_"):
                continue
            fields.append(name)
        REPORT["cf_fields"] = fields[:80]
        # default_typeface may be a Typeface-like struct with fonts array
        for attr in ("default_typeface", "DefaultTypeface"):
            try:
                tf = getattr(cf, attr) if hasattr(cf, attr) else cf.get_editor_property(attr)
                REPORT["tf_" + attr] = str(type(tf))
                tf_fields = [n for n in dir(tf) if not n.startswith("_")]
                REPORT["tf_fields_" + attr] = tf_fields[:80]
            except Exception as e:
                REPORT["tf_" + attr] = "ERR " + str(e)
    except Exception as e:
        REPORT["errors"].append("cf inspect " + str(e))

    # Method A: set_editor_property nested via make struct if available
    try:
        # In UE5 Python, CompositeFont has default_typeface with fonts: Array(TypefaceEntry)
        # TypefaceEntry has name + font (FontFace)
        entry = None
        for cls_name in ("TypefaceEntry", "CompositeSubFont"):
            if hasattr(unreal, cls_name):
                REPORT["has_" + cls_name] = True
        # Try constructing via unreal.TypefaceEntry if exported under different path
        # Fallback: use Font's legacy offline import — re-import as Font with TrueTypeFontFactory
    except Exception as e:
        REPORT["errors"].append("wireA " + str(e))

# Method B: re-import TTF as Font via TrueTypeFontFactory if available
if not wired:
    try:
        # Delete empty Font and reimport
        ttf = r"C:\Windows\Fonts\simhei.ttf"
        # Some engines create both FontFace and Font when destination_name ends specially
        # Use FontFactory with import options
        task = unreal.AssetImportTask()
        task.filename = ttf
        task.destination_path = "/Game/Farm/Restaurant"
        task.destination_name = "Font_SimHei_Offline"
        task.replace_existing = True
        task.automated = True
        task.save = True
        # Prefer Font factory
        try:
            opts = unreal.FontImportOptions()
            REPORT["FontImportOptions"] = "ok"
        except Exception as e:
            REPORT["FontImportOptions"] = str(e)
            opts = None
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        # Scan what got created
        created = []
        for a in unreal.EditorAssetLibrary.list_assets("/Game/Farm/Restaurant", False):
            if "SimHei" in a or "simhei" in a:
                asset = unreal.EditorAssetLibrary.load_asset(a.split(".")[0])
                created.append({"path": a, "class": asset.get_class().get_name() if asset else None})
        REPORT["reimport"] = created
        # Prefer a Font class asset
        for c in created:
            if c["class"] == "Font":
                font = unreal.EditorAssetLibrary.load_asset(c["path"].split(".")[0])
                wired = True
                log("using_font " + c["path"])
                break
    except Exception as e:
        REPORT["errors"].append("reimport " + str(e))

# Method C: manually build composite font using struct helpers
if font and face and not wired:
    try:
        # UE 5.4+ sometimes exposes:
        # font.composite_font.default_typeface.fonts = [ TypefaceEntry(name="Default", font=face) ]
        cf = font.get_editor_property("composite_font")
        # Try set via dict-like API
        try:
            tf = cf.get_editor_property("default_typeface")
        except Exception:
            tf = None
            try:
                tf = cf.default_typeface
            except Exception:
                pass
        if tf is not None:
            # fonts array
            try:
                fonts_arr = tf.get_editor_property("fonts")
            except Exception:
                try:
                    fonts_arr = tf.fonts
                except Exception:
                    fonts_arr = None
            REPORT["fonts_arr_type"] = str(type(fonts_arr))
            # Build entry using struct
            # In many UE versions TypefaceEntry is not exposed; try FontFace assignment via
            # unreal.Array
            try:
                # Some builds: tf.set_editor_property("fonts", [...])
                # Try creating entry from existing empty slot
                if fonts_arr is not None and len(list(fonts_arr)) > 0:
                    entry0 = list(fonts_arr)[0]
                    REPORT["entry0_type"] = str(type(entry0))
                    entry_fields = [n for n in dir(entry0) if not n.startswith("_")]
                    REPORT["entry0_fields"] = entry_fields[:60]
                    try:
                        entry0.set_editor_property("font", face)
                        wired = True
                        log("wired entry0.font")
                    except Exception as e:
                        try:
                            entry0.font = face
                            wired = True
                            log("wired entry0.font attr")
                        except Exception as e2:
                            REPORT["errors"].append("entry font " + str(e) + " / " + str(e2))
                    # write back
                    try:
                        tf.set_editor_property("fonts", fonts_arr)
                        cf.set_editor_property("default_typeface", tf)
                        font.set_editor_property("composite_font", cf)
                    except Exception as e:
                        REPORT["errors"].append("writeback " + str(e))
                else:
                    REPORT["fonts_arr_empty"] = True
            except Exception as e:
                REPORT["errors"].append("fonts_arr " + str(e))
    except Exception as e:
        REPORT["errors"].append("methodC " + str(e))

REPORT["wired"] = wired
if font:
    try:
        unreal.EditorAssetLibrary.save_asset(font.get_path_name().split(".")[0])
    except Exception as e:
        REPORT["errors"].append("save font " + str(e))

# ---- Update InteractLabel + RestLabel TextRender ----
actors = find_by_label()

# Destroy old RestLabel_* and respawn clean
for lab, a in list(actors.items()):
    if lab.startswith("RestLabel_"):
        eas.destroy_actor(a)
        log("destroyed " + lab)
actors = find_by_label()

use_font = font if (font and font.get_class().get_name() == "Font") else None
REPORT["use_font"] = use_font.get_path_name() if use_font else None

for key, cn in CN.items():
    target_name = TARGET[key]
    target = actors.get(target_name)
    if not target:
        REPORT["errors"].append("missing " + target_name)
        continue
    # InteractLabel
    for prop in ("InteractLabel", "interact_label"):
        try:
            target.set_editor_property(prop, cn)
            break
        except Exception:
            pass
    loc = target.get_actor_location()
    label_loc = unreal.Vector(loc.x, loc.y, loc.z + TEXT_Z_OFFSET)
    label_name = "RestLabel_" + key
    la = eas.spawn_actor_from_class(unreal.TextRenderActor, label_loc, unreal.Rotator(90.0, 0.0, 0.0))
    if not la:
        REPORT["errors"].append("spawn fail " + label_name)
        continue
    la.set_actor_label(label_name)
    try:
        la.set_folder_path("Restaurant/Labels")
    except Exception:
        pass
    tr = la.get_component_by_class(unreal.TextRenderComponent)
    if tr is None:
        comps = list(la.get_components_by_class(unreal.TextRenderComponent))
        tr = comps[0] if comps else None
    if not tr:
        REPORT["errors"].append("no tr " + label_name)
        continue
    # Set text via multiple APIs
    ok_text = False
    for setter in (
        lambda: tr.set_editor_property("text", cn),
        lambda: tr.set_text(cn),
        lambda: setattr(tr, "text", cn),
    ):
        try:
            setter()
            ok_text = True
            break
        except Exception:
            pass
    try:
        tr.set_editor_property("world_size", TEXT_WORLD_SIZE)
    except Exception:
        try:
            tr.set_world_size(TEXT_WORLD_SIZE)
        except Exception:
            pass
    try:
        tr.set_editor_property("horizontal_alignment", unreal.HorizontalTextAligment.HTA_CENTER)
    except Exception:
        pass
    rgb = COLORS[key]
    try:
        tr.set_text_render_color(unreal.Color(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255))
    except Exception:
        try:
            tr.set_editor_property("text_render_color", unreal.Color(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255), 255))
        except Exception:
            pass
    if use_font:
        try:
            tr.set_editor_property("font", use_font)
            log("font_set " + label_name)
        except Exception as e:
            REPORT["errors"].append("font_set " + label_name + " " + str(e))
    # Read back text codepoints for verification
    got = None
    try:
        got = tr.get_editor_property("text")
    except Exception:
        try:
            got = str(tr.text)
        except Exception:
            pass
    cps = [hex(ord(c)) for c in str(got)] if got is not None else []
    REPORT["labels"].append({
        "name": label_name,
        "cn": cn,
        "cn_cps": [hex(ord(c)) for c in cn],
        "got": str(got),
        "got_cps": cps,
        "ok_text": ok_text,
        "loc": [round(label_loc.x,1), round(label_loc.y,1), round(label_loc.z,1)],
    })
    log("label {} cn_ok={} got_cps={}".format(label_name, cps == [hex(ord(c)) for c in cn], cps))

# Folder furniture
for name in TARGET.values():
    a = find_by_label().get(name)
    if a:
        try:
            a.set_folder_path("Restaurant")
        except Exception:
            pass

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    REPORT["level_saved"] = True
except Exception as e:
    try:
        unreal.EditorLevelLibrary.save_current_level()
        REPORT["level_saved"] = True
    except Exception as e2:
        REPORT["level_saved"] = False
        REPORT["errors"].append(str(e2))

# Also save font assets
for p in ("/Game/Farm/Restaurant/Font_SimHei_TR", "/Game/Farm/Restaurant/Font_SimHei_Offline", "/Game/Farm/Restaurant/Font_SimHei"):
    if unreal.EditorAssetLibrary.does_asset_exist(p):
        try:
            unreal.EditorAssetLibrary.save_asset(p)
        except Exception:
            pass

out = r"E:\UE\FarmSim25D\Saved\restaurant_labelfix.json"
open(out, "w", encoding="utf-8").write(json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps({"wired": REPORT.get("wired"), "use_font": REPORT.get("use_font"),
                  "labels": REPORT.get("labels"), "errors": REPORT.get("errors"),
                  "reimport": REPORT.get("reimport"), "cf_fields": REPORT.get("cf_fields"),
                  "tf_fields_default_typeface": REPORT.get("tf_fields_default_typeface"),
                  "entry0_fields": REPORT.get("entry0_fields"),
                  "level_saved": REPORT.get("level_saved")}, ensure_ascii=False, indent=2))