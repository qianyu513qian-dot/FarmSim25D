# -*- coding: utf-8 -*-
"""Verify Move cam-relative graph: Self wiring, casts, compile errors; patch if needed."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/TopDown/Blueprints/BP_TopDownCharacter"

def log(m):
    unreal.log("[FIX3] " + str(m)); print("[FIX3] " + str(m))

def find_pin(node, name_substr, direction=None):
    if not node: return None
    for p in bel.list_all_pins(node):
        if name_substr.lower() in str(p.get_pin_name()).lower():
            if direction is None or direction.lower() in str(p.get_pin_direction()).lower():
                return p
    return None

def connect(a, b, label=""):
    if a is None or b is None:
        log("skip "+label); return False
    ok = a.try_create_connection(b)
    log("conn[{}] : {}".format(label, ok)); return ok

bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))

# Find GetComponentByClass and related
gcc = None
get_rot = None
for n in ge.list_all_nodes():
    t = bel.get_node_title(n)
    cn = n.get_class().get_name()
    if "GetComponentByClass" in t or "Get Component By Class" in t:
        gcc = n
        log("GCC title="+t)
        for p in bel.list_all_pins(n):
            val=""
            try: val=str(p.get_pin_value())
            except: pass
            cps=[(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  GCC.{} =[{}] <-{}".format(p.get_pin_name(), val, cps))
    if "K2_GetComponentRotation" in t or t == "Get World Rotation" or "GetComponentRotation" in t:
        # only the one fed by gcc
        get_rot = n
        for p in bel.list_all_pins(n):
            cps=[(bel.get_node_title(c.get_owning_node()), str(c.get_pin_name())) for c in p.list_connected_pins()]
            log("  ROT.{} <-{}".format(p.get_pin_name(), cps))

# Ensure Self -> GCC.self
if gcc:
    self_pin = find_pin(gcc, "self", "Input")
    if self_pin and not list(self_pin.list_connected_pins()):
        # create Self node
        self_n = None
        for name in ("Self", "Get Self", "GetSelfReference"):
            try:
                self_n = ge.create_node_from_name(name, unreal.Vector2D(-1900, -300), [])
                if self_n:
                    log("created "+name); break
            except Exception as e:
                log(str(e))
        if not self_n:
            try:
                self_n = ge.add_call_function_node("/Script/Engine.KismetSystemLibrary:GetSelfReference")
            except Exception:
                pass
        # Often just leaving self unconnected uses owning blueprint - check compile
        if self_n:
            connect(find_pin(self_n, "self", "Output") or find_pin(self_n, "ReturnValue", "Output") or find_pin(self_n, "Self", "Output"),
                    self_pin, "self->gcc")
    # ComponentClass value
    cp = find_pin(gcc, "ComponentClass", "Input")
    if cp:
        try:
            log("ComponentClass val="+str(cp.get_pin_value()))
            # Force proper class
            cp.set_pin_value("/Script/Engine.CameraComponent")
            log("set ComponentClass -> "+str(cp.get_pin_value()))
        except Exception as e:
            log("class set "+str(e))
            # try CameraComponent path alternate
            try:
                cp.set_pin_value("CameraComponent")
            except Exception as e2:
                log(str(e2))

# Cast ReturnValue ActorComponent -> SceneComponent / CameraComponent before GetRotation?
# If rot.self is connected directly from GCC.ReturnValue and compile ok, UE may auto-cast.
if get_rot and gcc:
    rot_self = find_pin(get_rot, "self", "Input")
    cps = list(rot_self.list_connected_pins()) if rot_self else []
    log("rot.self connected from "+str([(bel.get_node_title(c.get_owning_node()), c.get_pin_name()) for c in cps]))

# Compile errors
try:
    errs = ge.list_nodes_with_errors()
    log("EventGraph errors n="+str(len(errs)))
    for n in errs:
        log("  ERR "+bel.get_node_title(n))
except Exception as e:
    log(str(e))
try:
    bel.compile_blueprint(bp)
    log("compile ok")
except Exception as e:
    log("compile "+str(e))

# Check blueprint status
try:
    status = bp.status if hasattr(bp, "status") else None
    log("bp.status="+str(status))
except Exception as e:
    log(str(e))

unreal.EditorAssetLibrary.save_asset(CHAR)

# Also confirm IMC still good + holes still filled
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
txt = imc.get_editor_property("default_key_mappings").export_text()
log("IMC E={} F={} R={} G={} H={} WASD={}".format(
    "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt,
    all(("Key="+k) in txt for k in "WASD")))

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CELL=100.0
kinds=("Grass","Path","Water","Bridge","Cliff","Bank","Soil","Hoe","Yard")
covered=set()
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""
    if lab.startswith("VMF_") and any(k in lab for k in kinds):
        loc=a.get_actor_location()
        covered.add((int(loc.x//CELL), int(loc.y//CELL)))
hoe=[(x,y) for y in range(20,24) for x in range(25,28) if (x,y) not in covered]
log("hoe_holes="+str(hoe)+" covered="+str(len(covered)))

# SpringArm final
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=lib.get_data(h); obj=lib.get_object_for_blueprint(data, bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r=obj.get_editor_property("relative_rotation")
        log("FINAL SpringArm p={:.1f} y={:.1f} arm={}".format(r.pitch, r.yaw, obj.get_editor_property("target_arm_length")))

try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    try: unreal.EditorLevelLibrary.save_current_level()
    except Exception: pass
log("DONE")
