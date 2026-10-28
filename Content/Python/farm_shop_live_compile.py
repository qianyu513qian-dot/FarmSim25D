# -*- coding: utf-8 -*-
"""Live Coding compile for seed shop C++ (new UCLASS needs UHT)."""
import unreal, os, time, json
from datetime import datetime

REPORT = {"ok": False, "steps": [], "dll_before": None, "dll_after": None}
DLL = r"E:\UE\FarmSim25D\Binaries\Win64\UnrealEditor-FarmSim25D.dll"
OUT = r"E:\UE\FarmSim25D\Saved\shop_live_compile.json"

def log(m):
    REPORT["steps"].append(str(m))
    unreal.log("[shop_lc] " + str(m))

def mtime():
    try:
        return os.path.getmtime(DLL)
    except Exception:
        return 0

def main():
    REPORT["dll_before"] = datetime.fromtimestamp(mtime()).isoformat(sep=" ", timespec="seconds") if mtime() else None
    w = unreal.UnrealEditorSubsystem().get_editor_world()
    for cmd in ("LiveCoding.Enable 1", "LiveCoding.CompileSync"):
        try:
            unreal.SystemLibrary.execute_console_command(w, cmd)
            log("ok " + cmd)
        except Exception as e:
            log("fail " + cmd + ": " + repr(e))
    before = mtime()
    # CompileSync should block; poll anyway
    for i in range(90):
        time.sleep(1)
        after = mtime()
        REPORT["dll_after"] = datetime.fromtimestamp(after).isoformat(sep=" ", timespec="seconds") if after else None
        if after > before + 0.5:
            REPORT["ok"] = True
            log("dll updated at t+" + str(i))
            break
        if i % 10 == 0:
            log("wait " + str(i))
    open(OUT, "w", encoding="utf-8").write(json.dumps(REPORT, indent=2))
    print(json.dumps(REPORT, indent=2))
    return REPORT

main()
