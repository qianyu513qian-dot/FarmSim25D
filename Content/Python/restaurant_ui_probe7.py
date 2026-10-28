# -*- coding: utf-8 -*-
"""Find WBPs with roots; try ObjectIterator; try duplicate engine WBP; try import_text RootWidget."""
import unreal

def log(m):
    unreal.log("[UI_P7] " + str(m))
    print("[UI_P7] " + str(m))

ar = unreal.AssetRegistryHelpers.get_asset_registry()
# Project WBPs
wbps = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/UMGEditor", "WidgetBlueprint"), True)
log("project+engine WBP count=" + str(len(list(wbps or []))))
for a in list(wbps or [])[:40]:
    log("  " + str(a.package_name) + " / " + str(a.asset_name))

# ObjectIterator on RestOrderList tree
wbp = unreal.load_asset("/Game/Farm/UI/WBP_RestOrderList")
tree = unreal.load_object(wbp, "WidgetTree")
log("iter widgets with outer tree:")
count = 0
for o in unreal.ObjectIterator(unreal.Widget):
    try:
        if o.get_outer() == tree or (o.get_outer() and o.get_outer().get_outer() == tree):
            log("  {} {} outer={}".format(o.get_name(), o.get_class().get_name(), o.get_outer().get_name()))
            count += 1
    except Exception:
        pass
log("count=" + str(count))

# Also iter ALL objects with path containing RestOrderList
for o in unreal.ObjectIterator(unreal.Object):
    try:
        pn = o.get_path_name()
        if "WBP_RestOrderList" in pn and "WidgetTree" in pn:
            log("obj " + pn + " cls=" + o.get_class().get_name())
    except Exception:
        pass

# Try duplicate a known engine editor widget? Too heavy.
# Try call_method on WidgetTree
for meth in ("SetRootWidget", "RebuildWidget", "ConstructWidget", "CreateWidget"):
    try:
        r = tree.call_method(meth, ())
        log("call {} = {}".format(meth, r))
    except Exception as e:
        log("call {} {}".format(meth, str(e)[:120]))

# Use EditorAssetLibrary duplicate from WBP_FarmHUD and inspect
# Check FarmHUD objects
fh = unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD")
ft = unreal.load_object(fh, "WidgetTree")
for o in unreal.ObjectIterator(unreal.Widget):
    try:
        if "WBP_FarmHUD" in o.get_path_name():
            log("FarmHUD widget " + o.get_path_name())
    except Exception:
        pass

# CRITICAL breakthrough attempt: use unreal.WidgetTree's property via export/import of whole asset text
# Or use AssetExportTask
log("AssetExportTask=" + str(getattr(unreal, "AssetExportTask", None)))
log("Exporter=" + str(getattr(unreal, "Exporter", None)))

# Try SubobjectData to add component - gather handles
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
tbp = unreal.load_asset("/Game/Farm/Restaurant/BP_RestaurantTable")
handles = sub.k2_gather_subobject_data_for_blueprint(tbp)
log("table subobjects=" + str(len(list(handles or []))))
for i, h in enumerate(list(handles or [])[:15]):
    try:
        data = sub.k2_find_subobject_data_from_handle(h)
        # data fields
        log("  [{}] data type={} dirs={}".format(i, type(data), [x for x in dir(data) if not x.startswith('_') and not x.startswith('static')][:20]))
        # try get display name
        for attr in ("get_variable_name", "get_class", "get_object", "get_display_name"):
            if hasattr(data, attr):
                try:
                    log("    {}={}".format(attr, getattr(data, attr)()))
                except Exception as e:
                    log("    {} err {}".format(attr, e))
        # properties on handle vs data
        try:
            log("    export=" + data.export_text()[:200])
        except Exception as e:
            log("    export " + str(e)[:80])
    except Exception as e:
        log("  [{}] {}".format(i, e))

log("DONE7")
