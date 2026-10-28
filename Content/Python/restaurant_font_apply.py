# -*- coding: utf-8 -*-
"""Apply CJK-capable font to RestLabel_* TextRenders; wire SimHei into Font_SimHei_TR."""
import unreal, json

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"steps": [], "errors": [], "labels": []}

face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
font_tr = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
roboto = unreal.EditorAssetLibrary.load_asset("/Engine/EngineFonts/Roboto")

# Wire SimHei into Font_SimHei_TR via import_text (mirrors Roboto structure)
if font_tr and face:
    face_path = face.get_path_name()  # /Game/Farm/Restaurant/Font_SimHei.Font_SimHei
    # Use same quoting style as Roboto export
    text = (
        '(DefaultTypeface=(Fonts=((Name="Regular",Font=(FontFaceAsset="/Script/Engine.FontFace\'{0}\'"))))),'
        'FallbackTypeface=(Typeface=(Fonts=((Name="Regular",Font=(FontFaceAsset="/Script/Engine.FontFace\'/Engine/EngineFonts/Faces/DroidSansFallback.DroidSansFallback\'"))))),ScalingFactor=1.000000),'
        'SubTypefaces=,bEnableAscentDescentOverride=True)'
    ).format(face_path)
    # Also try simpler variants
    variants = [
        text,
        '(DefaultTypeface=(Fonts=((Name="Regular",Font=(FontFaceAsset="/Script/Engine.FontFace\'/Game/Farm/Restaurant/Font_SimHei.Font_SimHei\'"))))),FallbackTypeface=(Typeface=(Fonts=),ScalingFactor=1.000000),SubTypefaces=,bEnableAscentDescentOverride=True)',
    ]
    cf = font_tr.get_editor_property("composite_font")
    for i, v in enumerate(variants):
        try:
            cf.import_text(v)
            font_tr.set_editor_property("composite_font", cf)
            font_tr.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
            after = font_tr.get_editor_property("composite_font").export_text()
            REPORT["steps"].append("import_variant_{} after={}".format(i, after[:300]))
            if "Font_SimHei" in after or "SimHei" in after:
                REPORT["simhei_wired"] = True
                REPORT["steps"].append("simhei wired via variant " + str(i))
                break
        except Exception as e:
            REPORT["errors"].append("import {}: {}".format(i, e))
    try:
        unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
    except Exception as e:
        REPORT["errors"].append("save tr " + str(e))

# Prefer wired SimHei font; fallback to Roboto (has DroidSansFallback CJK)
prefer = None
if font_tr:
    try:
        exp = font_tr.get_editor_property("composite_font").export_text()
        if "Fonts=((" in exp and "Fonts=)," not in exp.replace("FallbackTypeface=(Typeface=(Fonts=)", ""):
            # crude: default typeface has entries if DefaultTypeface=(Fonts=(( appears
            if "DefaultTypeface=(Fonts=((" in exp:
                prefer = font_tr
                REPORT["steps"].append("prefer Font_SimHei_TR")
    except Exception as e:
        REPORT["errors"].append("prefer check " + str(e))
if prefer is None:
    prefer = roboto
    REPORT["steps"].append("prefer Roboto (DroidSansFallback CJK)")

REPORT["applied_font"] = prefer.get_path_name() if prefer else None

for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if not lab.startswith("RestLabel_"):
        continue
    tr = a.get_component_by_class(unreal.TextRenderComponent)
    if not tr:
        REPORT["errors"].append("no tr " + lab)
        continue
    try:
        tr.set_editor_property("font", prefer)
        REPORT["steps"].append("set font " + lab)
    except Exception as e:
        REPORT["errors"].append("set font {} {}".format(lab, e))
    # Ensure readable size + facing up for top-down
    try:
        tr.set_editor_property("world_size", 64.0)
    except Exception:
        pass
    try:
        a.set_actor_rotation(unreal.Rotator(90.0, 0.0, 0.0), False)
    except Exception:
        pass
    # bump Z a bit higher if needed
    loc = a.get_actor_location()
    row = {"label": lab, "loc": [round(loc.x,1), round(loc.y,1), round(loc.z,1)]}
    try:
        t = tr.get_editor_property("text")
        row["cps"] = [hex(ord(c)) for c in str(t)]
        row["font"] = tr.get_editor_property("font").get_path_name()
    except Exception as e:
        row["err"] = str(e)
    REPORT["labels"].append(row)

# Confirm furniture still spaced
furn = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("Restaurant_") or lab.startswith("RestChair_"):
        loc = a.get_actor_location()
        furn[lab] = [round(loc.x,1), round(loc.y,1), round(loc.z,1)]
REPORT["furniture"] = furn

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

# Final font export
if font_tr:
    REPORT["final_tr_export"] = font_tr.get_editor_property("composite_font").export_text()[:800]

open(r"E:\UE\FarmSim25D\Saved\restaurant_font_apply.json","w",encoding="utf-8").write(
    json.dumps(REPORT, ensure_ascii=False, indent=2))
print(json.dumps(REPORT, ensure_ascii=False, indent=2))