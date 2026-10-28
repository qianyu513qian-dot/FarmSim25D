# -*- coding: utf-8 -*-
import unreal, json
font = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei_TR")
face = unreal.EditorAssetLibrary.load_asset("/Game/Farm/Restaurant/Font_SimHei")
out = {"font_class": font.get_class().get_name() if font else None,
       "face_class": face.get_class().get_name() if face else None}
if font:
    try:
        out["cache"] = str(font.get_editor_property("font_cache_type"))
    except Exception as e:
        out["cache_err"] = str(e)
    try:
        cf = font.get_editor_property("composite_font")
        tf = cf.get_editor_property("default_typeface") if hasattr(cf, "get_editor_property") else None
        try:
            tf = cf.default_typeface
        except Exception:
            pass
        fonts = None
        try:
            fonts = list(tf.get_editor_property("fonts"))
        except Exception:
            try:
                fonts = list(tf.fonts)
            except Exception as e:
                out["fonts_err"] = str(e)
        if fonts is not None:
            out["typeface_entries"] = len(fonts)
            if fonts:
                e0 = fonts[0]
                try:
                    f = e0.get_editor_property("font")
                except Exception:
                    f = getattr(e0, "font", None)
                out["entry0_font"] = f.get_path_name() if f else None
                try:
                    out["entry0_name"] = str(e0.get_editor_property("name"))
                except Exception:
                    out["entry0_name"] = str(getattr(e0, "name", None))
    except Exception as e:
        out["cf_err"] = str(e)

# Also confirm all 5 still good after save reload state
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
labels = {}
for a in eas.get_all_level_actors():
    lab = a.get_actor_label() or ""
    if lab.startswith("RestLabel_"):
        tr = a.get_component_by_class(unreal.TextRenderComponent)
        rot = a.get_actor_rotation()
        labels[lab] = {
            "rot": [round(rot.pitch,1), round(rot.yaw,1), round(rot.roll,1)],
            "size": float(tr.world_size) if tr else None,
            "cps": [hex(ord(c)) for c in str(tr.text)] if tr else None,
            "fwd": [round(tr.get_forward_vector().x,3), round(tr.get_forward_vector().y,3), round(tr.get_forward_vector().z,3)] if tr else None,
            "loc": [round(a.get_actor_location().x,1), round(a.get_actor_location().y,1), round(a.get_actor_location().z,1)],
        }
out["labels"] = labels
# expected cps
expect = {
    "RestLabel_OpenSign": ["0x5f00","0x4e1a","0x724c"],
    "RestLabel_Stove": ["0x7076","0x53f0"],
    "RestLabel_Table1": ["0x9910","0x684c","0x31"],
    "RestLabel_Table2": ["0x9910","0x684c","0x32"],
    "RestLabel_Trash": ["0x5783","0x573e","0x6876"],
}
out["cn_ok"] = all(labels.get(k,{}).get("cps")==v for k,v in expect.items())
out["rot_ok"] = all(labels.get(k,{}).get("rot")==[45.0,135.0,0.0] for k in expect)
print(json.dumps(out, ensure_ascii=False, indent=2))
