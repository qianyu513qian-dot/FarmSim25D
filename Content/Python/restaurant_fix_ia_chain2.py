# -*- coding: utf-8 -*-
"""IA Started -> GetAllActorsWithTag (pure GetPlayerPawn). Set Tag=RestInteract."""
import unreal, json
bel=unreal.BlueprintEditorLibrary
cbp=unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
cge=unreal.BlueprintGraphEditor.get_graph_editor(bel.find_event_graph(cbp))

def find_pin(node, substr, direction=None):
    if not node: return None
    substr=substr.lower()
    for p in bel.list_all_pins(node):
        if substr in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

ia=gat=fe=till=None
for n in cge.list_all_nodes():
    t=bel.get_node_title(n)
    if "IA_Interact" in t: ia=n
    if t=="GetAllActorsWithTag": gat=n
    if "For Each Loop" in t or "ForEachLoop" in t: fe=n
    if t=="TillSoil": till=n

started=find_pin(ia,"Started","Output")
gat_exec=find_pin(gat,"execute","Input")
# break started
if started:
    try: bel.break_pin_links(started)
    except Exception:
        for cp in list(started.list_connected_pins()):
            try: started.break_link_to(cp)
            except Exception: pass
if gat_exec:
    try: bel.break_pin_links(gat_exec)
    except Exception: pass

ok1=started.try_create_connection(gat_exec) if started and gat_exec else False
# Tag
tag=find_pin(gat,"Tag","Input")
try: tag.set_default_value("RestInteract"); tag_ok=True
except Exception:
    try: tag.set_pin_value("RestInteract"); tag_ok=True
    except Exception as e:
        tag_ok=str(e)

# World context? GetAllActorsWithTag may need WorldContext self — often auto.
# Ensure fe completed -> till
if fe and till:
    done=find_pin(fe,"Completed","Output")
    tex=find_pin(till,"execute","Input")
    if done and tex and not list(done.list_connected_pins()):
        done.try_create_connection(tex)

compile_ok=bel.compile_blueprint(cbp)
unreal.EditorAssetLibrary.save_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")

# verify
chain=[]
started=find_pin(ia,"Started","Output")
q=[cp.get_owning_node() for cp in started.list_connected_pins()] if started else []
seen=set()
while q and len(chain)<20:
    n=q.pop(0)
    if id(n) in seen: continue
    seen.add(id(n)); chain.append(bel.get_node_title(n))
    for p in bel.list_all_pins(n):
        if "output" not in str(p.get_pin_direction()).lower(): continue
        for cp in p.list_connected_pins():
            q.append(cp.get_owning_node())

tag_val=""
try: tag_val=tag.get_default_as_string()
except Exception:
    try: tag_val=str(tag.get_pin_value())
    except Exception: tag_val="?"

els=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
els.save_current_level()
out={"IA_gat":ok1,"tag":tag_val,"tag_ok":tag_ok,"compile":compile_ok,"chain":chain}
open(r"E:\UE\FarmSim25D\Saved\restaurant_ia_fix2.json","w",encoding="utf-8").write(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
