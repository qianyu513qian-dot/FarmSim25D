import unreal
from collections import Counter
from pathlib import Path
import json
bel = unreal.BlueprintEditorLibrary
actors = list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
REPORT['actors'] = []
REPORT['counts'] = dict(Counter(a.get_class().get_name() for a in actors))
for a in actors:
    label = a.get_actor_label()
    if any(s in label.lower() for s in ['house','light','moon','sun','postprocess','gridmanager','bridge','dock','harbor','lamp','camera','start']):
        row = {'label': label, 'path': a.get_path_name(), 'class': a.get_class().get_name(), 'location': str(a.get_actor_location()), 'rotation': str(a.get_actor_rotation()), 'tags': list(map(str,a.tags))}
        row['components'] = []
        for c in a.get_components_by_class(unreal.ActorComponent):
            props={}
            for p in ['intensity','light_color','mobility','real_time_capture','projection_mode','ortho_width','settings','static_mesh']:
                try: props[p]=str(c.get_editor_property(p))
                except: pass
            if props: row['components'].append({'name':c.get_name(), **props})
        REPORT['actors'].append(row)
REPORT['blueprints']={}
for path in ['/Game/Farm/Grid/BP_GridManager','/Game/Farm/UI/WBP_FarmHUD','/Game/TopDown/Blueprints/BP_TopDownCharacter','/Game/TopDown/Blueprints/BP_TopDownPlayerController']:
    bp=unreal.load_asset(path)
    if not bp: continue
    data={'variables':{},'graphs':{}}
    cdo=unreal.get_default_object(bp.generated_class())
    for name in bel.list_member_variable_names(bp):
        try: data['variables'][str(name)]=str(cdo.get_editor_property(str(name)))
        except: pass
    for name in bel.list_graph_names(bp):
        ge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp,str(name)))
        nodes=[]
        for n in ge.list_all_nodes():
            pins=[]
            for p in bel.list_all_pins(n):
                pins.append({'name':str(p.get_pin_name()),'dir':str(p.get_pin_direction()),'value':p.get_pin_value(),'links':[str(q.get_path_name()) if hasattr(q,'get_path_name') else str(q) for q in p.list_connected_pins()]})
            nodes.append({'name':n.get_name(),'title':str(bel.get_node_title(n)),'pins':pins})
        data['graphs'][str(name)]=nodes
    REPORT['blueprints'][path]=data
out=Path(unreal.Paths.project_saved_dir())/'DayNight'/'inspection.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(REPORT,default=str,indent=2),encoding='utf-8')
REPORT={'report_file':str(out),'counts':REPORT['counts'],'actor_summary':[{k:v for k,v in a.items() if k not in ['components']} for a in REPORT['actors']]}
