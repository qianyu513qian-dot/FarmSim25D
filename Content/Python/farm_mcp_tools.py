"""Project tooling exposed through Epic's Toolset Registry / Unreal MCP."""
from pathlib import Path
import json
import traceback
import unreal
import toolset_registry

@unreal.uclass()
class FarmDayNightTools(unreal.ToolsetDefinition):
    """Build and validate FarmSim's runtime Blueprints without desktop interaction."""

    @toolset_registry.tool_call
    @staticmethod
    def run_project_script(script_name: str) -> str:
        """Run a named day/night authoring or validation script inside Content/Python.

        Args:
            script_name: Basename starting with farm_dn_, ending in .py.
        Returns:
            JSON result, including errors and script-produced report.
        """
        if Path(script_name).name != script_name or not script_name.startswith('farm_dn_') or not script_name.endswith('.py'):
            raise ValueError('Expected a farm_dn_*.py project script basename')
        path = Path(unreal.Paths.project_content_dir()) / 'Python' / script_name
        scope = {'__file__': str(path), '__name__': '__main__', 'REPORT': {}}
        try:
            exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), scope)
            result = {'ok': True, 'script': script_name, 'report': scope['REPORT']}
        except Exception:
            result = {'ok': False, 'script': script_name, 'error': traceback.format_exc()}
        output = Path(unreal.Paths.project_saved_dir()) / 'DayNight'
        output.mkdir(exist_ok=True)
        (output / (script_name + '.json')).write_text(json.dumps(result, default=str, indent=2), encoding='utf-8')
        return json.dumps(result, default=str)
