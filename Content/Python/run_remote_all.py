# -*- coding: utf-8 -*-
"""Run a UE Python script on ALL discovered remote nodes."""
import sys
import time
import os

RE_PATH = r"E:\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
if RE_PATH not in sys.path:
    sys.path.insert(0, RE_PATH)

from remote_execution import RemoteExecution, MODE_EXEC_FILE


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_remote_all.py <script.py>")
        return 2
    script = os.path.abspath(sys.argv[1])
    if not os.path.isfile(script):
        print("NOT FOUND:", script)
        return 2

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
            print("NO_NODES")
            return 1
        print("NODES:", [(n.get("node_id"), n.get("project_name")) for n in nodes])
        farm = [n for n in nodes if "FarmSim" in str(n.get("project_name", ""))] or list(nodes)
        rc = 0
        for node in farm:
            nid = node["node_id"]
            print("CONNECT:", nid, node.get("project_name"))
            try:
                remote.open_command_connection(nid)
                result = remote.run_command(script, unattended=True, exec_mode=MODE_EXEC_FILE, raise_on_failure=False)
                print("RESULT[{}]:".format(nid[:8]), result)
                # print key output lines
                if isinstance(result, dict):
                    for o in (result.get("output") or []):
                        line = o.get("output", "")
                        if line and not line.endswith("\r\n") and ("SUNMOON" in line or "FIX_SKY" in line or "VERIFY" in line or "ERR" in line or "DONE" in line or "FAIL" in line or "Moon" in line or "error" in line.lower()):
                            print("  ", line)
                    if not result.get("success", True):
                        rc = 1
                remote.close_command_connection(nid)
            except Exception as e:
                print("NODE ERR", nid, e)
                rc = 1
                try:
                    remote.close_command_connection(nid)
                except Exception:
                    pass
        return rc
    finally:
        remote.stop()


if __name__ == "__main__":
    sys.exit(main() or 0)
