# -*- coding: utf-8 -*-
import unreal, json
tr_font = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
cf = tr_font.get_editor_property("composite_font")
before = cf.export_text()
# Restore correct wiring from known-good export
payload = '(DefaultTypeface=(Fonts=((Name="Regular",Font=(FontFaceAsset="/Script/Engine.FontFace\'/Game/Farm/Restaurant/Font_SimHei.Font_SimHei\'")))),FallbackTypeface=(Typeface=(Fonts=),ScalingFactor=1.000000),SubTypefaces=,bEnableAscentDescentOverride=True)'
cf.import_text(payload)
tr_font.set_editor_property("composite_font", cf)
try:
    tr_font.set_editor_property("font_cache_type", unreal.FontCacheType.RUNTIME)
except Exception:
    pass
after = tr_font.get_editor_property("composite_font").export_text()
saved = unreal.EditorAssetLibrary.save_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
# Re-apply font on all labels to be safe
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
n = 0
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("RestLabel_"):
        comp = a.get_component_by_class(unreal.TextRenderComponent)
        if comp:
            try:
                comp.set_font(tr_font)
            except Exception:
                comp.set_editor_property("font", tr_font)
            n += 1
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    level_saved = True
except Exception:
    level_saved = False
print(json.dumps({
    "before": before,
    "after": after,
    "wired_ok": "Font_SimHei.Font_SimHei" in after and "FontFaceAsset" in after,
    "font_saved": saved,
    "labels_refonted": n,
    "level_saved": level_saved,
}, ensure_ascii=False, indent=2))
