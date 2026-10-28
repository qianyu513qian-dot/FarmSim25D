import unreal, json
REPORT={}
bel=unreal.BlueprintEditorLibrary
eas=unreal.EditorAssetLibrary
wbp=eas.load_asset("/Game/Farm/UI/WBP_RestOrderList")
REPORT["wbp"]=str(wbp)
try:
    bel.compile_blueprint(wbp)
    REPORT["wbp_status"]=str(wbp.get_editor_property("status"))
except Exception as e:
    REPORT["wbp_compile_err"]=str(e)[:200]
# list widget names
try:
    wt=wbp.widget_tree
    REPORT["root"]=str(wt.root_widget) if wt else None
    names=[]
    def walk(w,d=0):
        if not w or d>20: return
        names.append(str(w.get_name()))
        try:
            for c in w.get_all_children() or []:
                walk(c,d+1)
        except Exception:
            pass
        try:
            # PanelWidget
            n=w.get_children_count() if hasattr(w,'get_children_count') else 0
            for i in range(n):
                walk(w.get_child_at(i),d+1)
        except Exception:
            pass
    if wt and wt.root_widget: walk(wt.root_widget)
    REPORT["widgets"]=names
except Exception as e:
    REPORT["tree_err"]=str(e)[:200]
# blueprint variables
try:
    # WidgetBlueprint generated vars
    REPORT["vars"]=[str(v.var_name) for v in (wbp.new_variables or [])]
except Exception as e:
    REPORT["vars_err"]=str(e)[:80]
mbp=eas.load_asset("/Game/Farm/Restaurant/BP_RestaurantManager")
customs=[]
mge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(mbp))
for n in mge.list_all_nodes():
    if n.get_class().get_name()=="K2Node_CustomEvent":
        t=str(bel.get_node_title(n))
        if "TableHL" in t or "SyncHeldTable" in t or t=="SyncHeldMesh":
            customs.append(t)
REPORT["mgr_customs"]=customs
REPORT["mgr_status"]=str(mbp.get_editor_property("status"))
open(r"E:\UE\FarmSim25D\Saved\restaurant_probe_after_crash.json","w",encoding="utf-8").write(json.dumps(REPORT,indent=2,ensure_ascii=False))
print(json.dumps(REPORT,indent=2,ensure_ascii=False)[:4000])