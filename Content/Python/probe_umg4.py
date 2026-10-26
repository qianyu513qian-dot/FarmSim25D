# -*- coding: utf-8 -*-
import unreal

wbp = unreal.load_asset("/Game/Farm/UI/WBP_FarmHUD")
tree = unreal.load_object(wbp, "WidgetTree")

def log(m):
    print("[CM]", m)
    unreal.log("[CM] " + str(m))

# Try call_method ConstructWidget
for args in (
    ("ConstructWidget",),
):
    pass

# Probe call_method with UClass
try:
    # Reflect: ConstructWidget(TSubclassOf<UWidget> WidgetType, FName Name)
    r = tree.call_method("ConstructWidget", (unreal.TextBlock.static_class(), "TxtMoney"))
    log("ConstructWidget TextBlock -> " + str(r))
except Exception as e:
    log("CM1 " + str(e))

try:
    r = tree.call_method("ConstructWidget", unreal.TextBlock.static_class(), unreal.Name("TxtMoney"))
    log("CM2 -> " + str(r))
except Exception as e:
    log("CM2 " + str(e))

try:
    r = tree.call_method("ConstructWidget", [unreal.CanvasPanel.static_class(), unreal.Name("RootCanvas")])
    log("CM3 -> " + str(r))
except Exception as e:
    log("CM3 " + str(e))

# new_object under tree
try:
    canvas = unreal.new_object(unreal.CanvasPanel, tree, unreal.Name("RootCanvas"))
    log("new_object canvas " + str(canvas))
    # set root via call_method
    try:
        tree.call_method("SetRootWidget", (canvas,))
        log("SetRootWidget ok")
    except Exception as e:
        log("SetRootWidget " + str(e))
    try:
        tree.set_editor_property("RootWidget", canvas)
        log("set RootWidget ok")
    except Exception as e:
        log("set RootWidget " + str(e))
except Exception as e:
    log("new_object " + str(e))

# Check UMG Editor subsystem
log("subsystems-ish: " + str([x for x in dir(unreal) if "Widget" in x][:50]))
