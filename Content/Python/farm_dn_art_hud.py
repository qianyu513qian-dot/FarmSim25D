"""Retire only prototype HUD/debug draws; retain interaction execution chains."""
import unreal
bel=unreal.BlueprintEditorLibrary
bp=unreal.load_asset('/Game/TopDown/Blueprints/BP_TopDownCharacter')
REPORT={'muted':[],'prints':[]}
def upstream_text(node,seen=None):
    seen=set() if seen is None else seen
    if node.get_path_name() in seen: return ''
    seen.add(node.get_path_name()); result=''
    for p in bel.list_all_pins(node):
        if 'INPUT' not in str(p.get_pin_direction()).upper(): continue
        result+=' '+str(p.get_pin_value())
        if str(p.get_pin_name())=='execute': continue
        for q in p.list_connected_pins(): result+=upstream_text(q.get_owning_node(),seen)
    return result
for name in ['EventGraph','UpdateFarmHUD']:
    graph=bel.find_graph(bp,name)
    if not graph: continue
    ge=unreal.BlueprintGraphEditor.get_graph_editor(graph)
    for node in ge.list_all_nodes():
        title=str(bel.get_node_title(node)); pins={str(p.get_pin_name()):p for p in bel.list_all_pins(node)}
        if title=='PrintString':
            text=upstream_text(node)
            REPORT['prints'].append({'graph':name,'values':{k:str(v.get_pin_value()) for k,v in pins.items() if k in ['Key','Duration']},'text':text[:350]})
            if name=='UpdateFarmHUD' or 'Grid' in text or 'FarmHUD' in text or '*** Money' in text:
                for k in ['bPrintToScreen','bPrintToLog']:
                    if k in pins: pins[k].set_pin_value('false')
                REPORT['muted'].append(name+':'+title)
        if 'DrawDebugString' in title and name=='UpdateFarmHUD':
            before=list(pins['execute'].list_connected_pins()); after=list(pins['then'].list_connected_pins())
            pins['execute'].break_pin_links(); pins['then'].break_pin_links()
            for a in before:
                for b in after: assert a.try_create_connection(b)
            REPORT['muted'].append('world-space money text')
        if 'DrawDebugBox' in title:
            if 'LineColor' in pins: pins['LineColor'].set_pin_value('(R=0.85,G=0.66,B=0.24,A=1.0)')
            if 'Thickness' in pins: pins['Thickness'].set_pin_value('1.5')
    assert not ge.list_nodes_with_errors()
bel.compile_blueprint(bp)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
