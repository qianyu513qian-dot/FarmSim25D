"""Create IA_Move (Axis2D) and map WASD onto IMC_Default. Does NOT edit Character Event Graph."""
import unreal

ACTIONS_DIR = "/Game/TopDown/Input/Actions"
IMC_PATH = "/Game/TopDown/Input/IMC_Default"
IA_PATH = ACTIONS_DIR + "/IA_Move"

def ensure_ia_move():
    if unreal.EditorAssetLibrary.does_asset_exist(IA_PATH):
        ia = unreal.EditorAssetLibrary.load_asset(IA_PATH)
        unreal.log("IA_Move exists")
    else:
        factory = unreal.InputActionFactory()
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        ia = asset_tools.create_asset("IA_Move", ACTIONS_DIR, unreal.InputAction, factory)
        unreal.log("Created IA_Move")
    ia.set_editor_property("value_type", unreal.InputActionValueType.AXIS2D)
    unreal.EditorAssetLibrary.save_asset(IA_PATH)
    return ia

def mapping_keys(imc, ia):
    # Clear existing mappings for this action then re-add (idempotent-ish)
    try:
        mappings = list(imc.get_editor_property("mappings"))
    except Exception:
        mappings = []
    # Use map_key API
    # W: swizzle YXZ
    # S: negate + swizzle YXZ
    # A: negate
    # D: plain
    keys = [
        (unreal.Key.W, True, False),   # swizzle, negate
        (unreal.Key.S, True, True),
        (unreal.Key.A, False, True),
        (unreal.Key.D, False, False),
        (unreal.Key.UP, True, False),
        (unreal.Key.DOWN, True, True),
        (unreal.Key.LEFT, False, True),
        (unreal.Key.RIGHT, False, False),
    ]
    for key, do_swizzle, do_negate in keys:
        try:
            m = imc.map_key(ia, key)
        except Exception as e:
            unreal.log_warning("map_key failed {}: {}".format(key, e))
            continue
        mods = []
        if do_negate:
            neg = unreal.InputModifierNegate()
            mods.append(neg)
        if do_swizzle:
            sw = unreal.InputModifierSwizzleAxis()
            try:
                sw.set_editor_property("order", unreal.InputAxisSwizzle.YXZ)
            except Exception:
                pass
            mods.append(sw)
        if mods:
            try:
                m.set_editor_property("modifiers", mods)
            except Exception as e:
                unreal.log_warning("set modifiers: {}".format(e))

def main():
    ia = ensure_ia_move()
    if not unreal.EditorAssetLibrary.does_asset_exist(IMC_PATH):
        unreal.log_error("Missing IMC_Default")
        return
    imc = unreal.EditorAssetLibrary.load_asset(IMC_PATH)
    mapping_keys(imc, ia)
    unreal.EditorAssetLibrary.save_asset(IMC_PATH)
    unreal.log("WASD mapped on IMC_Default. Bind IA_Move in BP_TopDownCharacter manually.")

if __name__ == "__main__":
    main()
