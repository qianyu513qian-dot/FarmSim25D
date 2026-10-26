"""Serial stdlib client for Epic's local Unreal MCP (no UI automation)."""
import json
import urllib.request
import sys
import os
from pathlib import Path

URL = os.environ.get('UE_MCP_URL','http://127.0.0.1:8000/mcp')
SESSION = None

def rpc(method, params=None, notification=False):
    global SESSION
    body = {'jsonrpc': '2.0', 'method': method}
    if not notification:
        body['id'] = 1
    if params is not None:
        body['params'] = params
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if SESSION:
        headers['Mcp-Session-Id'] = SESSION
    request = urllib.request.Request(URL, json.dumps(body).encode(), headers)
    with urllib.request.urlopen(request, timeout=180) as response:
        SESSION = response.headers.get('Mcp-Session-Id', SESSION)
        raw = response.read().decode()
    if not raw:
        return None
    if raw.lstrip().startswith('{'):
        data = json.loads(raw)
    else:
        data = [json.loads(line[5:]) for line in raw.splitlines() if line.startswith('data:')][-1]
    if 'error' in data:
        raise RuntimeError(data['error'])
    return data.get('result')

def connect():
    result = rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'FarmSim-background', 'version': '1.0'}})
    rpc('notifications/initialized', notification=True)
    return result

if __name__ == '__main__':
    init = connect()
    if len(sys.argv) == 1:
        result = {'initialize': init, 'tools': rpc('tools/list')}
    elif sys.argv[1] == 'script':
        result = rpc('tools/call', {'name': 'call_tool', 'arguments': {'toolset_name': 'farm_mcp_tools.FarmDayNightTools', 'tool_name': 'run_project_script', 'arguments': {'script_name': sys.argv[2]}}})
        if not result.get('isError'):
            result = json.loads(json.loads(result['content'][0]['text'])['returnValue'])
    else:
        args = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig')) if len(sys.argv) > 2 else {}
        result = rpc('tools/call', {'name': sys.argv[1], 'arguments': args})
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if isinstance(result,dict) and (result.get('ok') is False or result.get('isError')):
        sys.exit(1)
