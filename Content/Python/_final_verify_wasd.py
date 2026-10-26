import unreal
bel = unreal.BlueprintEditorLibrary
def log(m):
    unreal.log("[FINAL] "+str(m)); print("[FINAL] "+str(m))
bp = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Blueprints/BP_TopDownCharacter")
log("char status="+str(bp.status))
imc = unreal.EditorAssetLibrary.load_asset("/Game/TopDown/Input/IMC_Default")
txt = imc.get_editor_property("default_key_mappings").export_text()
log("keys EFRGH WASD = {} {} {} {} {} / {}".format(
    "Key=E" in txt, "Key=F" in txt, "Key=R" in txt, "Key=G" in txt, "Key=H" in txt,
    all(("Key="+k) in txt for k in "WASD")))
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
for h in sds.k2_gather_subobject_data_for_blueprint(bp):
    data=lib.get_data(h); obj=lib.get_object_for_blueprint(data, bp)
    if obj and "SpringArm" in obj.get_class().get_name():
        r=obj.get_editor_property("relative_rotation")
        log("SpringArm p={:.0f} y={:.0f}".format(r.pitch, r.yaw))
ge = unreal.BlueprintGraphEditor.get_graph_editor(bel.find_graph(bp, "EventGraph"))
for n in ge.list_all_nodes():
    if bel.get_node_title(n)=="AddMovementInput":
        wd=[bel.get_node_title(c.get_owning_node()) for c in bel.list_all_pins(n) if False]
        for p in bel.list_all_pins(n):
            if "WorldDirection" in str(p.get_pin_name()):
                log("AMI.WD <- "+str([bel.get_node_title(c.get_owning_node()) for c in p.list_connected_pins()]))
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CELL=100.0
covered=set(); ps=None; floor=False
for a in eas.get_all_level_actors():
    lab=a.get_actor_label() or ""; cn=a.get_class().get_name(); loc=a.get_actor_location()
    if lab=="FarmCollisionFloor": floor=True
    if "PlayerStart" in cn or lab=="PlayerStart":
        ps=(int(loc.x),int(loc.y),int(loc.z), int(loc.x//CELL), int(loc.y//CELL))
    if lab.startswith("VMF_") and any(k in lab for k in ("Grass","Path","Water","Bridge","Cliff","Bank","Soil","Hoe","Yard")):
        covered.add((int(loc.x//CELL), int(loc.y//CELL)))
hoe=[(x,y) for y in range(20,24) for x in range(25,28) if (x,y) not in covered]
log("PS={} floor={} covered={} hoe_holes={}".format(ps, floor, len(covered), hoe))
try:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("level saved")
except Exception as e:
    log("save "+str(e))
log("OK")
