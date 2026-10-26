# -*- coding: utf-8 -*-
"""Run script on every FarmSim remote node (ignore close quirks)."""
import sys, time, os
RE_PATH = r"E:\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
if RE_PATH not in sys.path:
    sys.path.insert(0, RE_PATH)
from remote_execution import RemoteExecution, MODE_EXEC_FILE

def main():
    script = os.path.abspath(sys.argv[1])
    remote = RemoteExecution()
    remote.start()
    try:
        nodes = []
        for i in range(20):
            time.sleep(0.5)
            nodes = remote.remote_nodes
            if nodes:
                break
        if not nodes:
            print("NO_NODES"); return 1
        farm = [n for n in nodes if "FarmSim" in str(n.get("project_name", ""))] or list(nodes)
        print("NODES", [n["node_id"][:8] for n in farm])
        for node in farm:
            nid = node["node_id"]
            print("CONNECT", nid[:8])
            try:
                remote.open_command_connection(nid)
                result = remote.run_command(script, unattended=True, exec_mode=MODE_EXEC_FILE, raise_on_failure=False)
                ok = True
                if isinstance(result, dict):
                    for o in (result.get("output") or []):
                        line = (o.get("output") or "").rstrip()
                        if line and ("FIX_SKY" in line or "VERIFY" in line or "DONE" in line or "ERR" in line or "SetIntensity" in line or "errors" in line or "Moon" in line or "SunLight" in line or "MoonLight" in line or "FarmSun" in line or "FarmMoon" in line or "yaw" in line.lower() or "FORMULA" in line or "Apply" in line):
                            print(" ", line)
                    ok = result.get("success", True)
                print("OK" if ok else "FAIL", nid[:8])
            except Exception as e:
                print("ERR", nid[:8], e)
            # don't close — some RE versions lack close_command_connection(nid)
        return 0
    finally:
        try:
            remote.stop()
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(main() or 0)
