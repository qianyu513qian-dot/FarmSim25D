# -*- coding: utf-8 -*-
"""Run a UE Python script via Remote Execution. Usage: python run_remote.py path\\to\\script.py"""
import sys
import time
import os

RE_PATH = r"E:\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
if RE_PATH not in sys.path:
    sys.path.insert(0, RE_PATH)

from remote_execution import RemoteExecution, MODE_EXEC_FILE

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_remote.py <script.py>")
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
            print("NO_NODES: editor remote execution not discovered (is Python Remote Execution enabled?)")
            return 1
        print("NODES:", [(n.get("node_id"), n.get("project_name"), n.get("user")) for n in nodes])
        # Prefer FarmSim25D if multiple
        node = nodes[0]
        for n in nodes:
            pn = (n.get("project_name") or "") + " " + (n.get("data") or str(n))
            if "FarmSim" in str(n):
                node = n
                break
        nid = node["node_id"]
        print("CONNECT:", nid, node)
        remote.open_command_connection(nid)
        # ExecuteFile with path
        cmd = script
        print("RUN:", cmd)
        result = remote.run_command(cmd, unattended=True, exec_mode=MODE_EXEC_FILE, raise_on_failure=False)
        print("RESULT:", result)
        return 0 if (result is None or result.get("success", True)) else 1
    finally:
        remote.stop()

if __name__ == "__main__":
    sys.exit(main() or 0)
