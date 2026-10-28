"""Serial offscreen PIE review via the project's Unreal MCP client."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Content/Python'))
import ue_mcp_client as mcp

mcp.connect()
action = sys.argv[1]
args = {}
if action == 'preview':
    out = ROOT / 'Saved/VisualReview'
    out.mkdir(exist_ok=True)
    request = {'hour':float(sys.argv[2]),'name':sys.argv[3]}
    if len(sys.argv)>4: request['location'] = [float(v) for v in sys.argv[4:7]]
    (out / 'request.json').write_text(json.dumps(request))
    for script in ['farm_dn_visual_preview.py','farm_dn_visual_shot.py']:
        result = mcp.rpc('tools/call', {'name':'call_tool','arguments':{'toolset_name':'farm_mcp_tools.FarmDayNightTools','tool_name':'run_project_script','arguments':{'script_name':script}}})
        if result.get('isError'): raise RuntimeError(result)
        report = json.loads(json.loads(result['content'][0]['text'])['returnValue'])
        if not report['ok']: raise RuntimeError(report)
        time.sleep(2)
    print(json.dumps(report))
    sys.exit(0)
tool = {'start':'StartPIE','start_window':'StartPIE','stop':'StopPIE'}[action]
if action in ('start','start_window'):
    args = {'options': {'bSimulate':False,'playMode':'PlayMode_InEditorFloating' if action=='start_window' else 'PlayMode_InViewPort','warmupSeconds':3}}
result = mcp.rpc('tools/call', {'name':'call_tool','arguments':{'toolset_name':'EditorToolset.EditorAppToolset','tool_name':tool,'arguments':args}})
if result.get('isError'): raise RuntimeError(result)
print(result)
