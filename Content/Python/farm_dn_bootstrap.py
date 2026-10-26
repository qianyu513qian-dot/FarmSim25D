import farm_mcp_tools
import unreal
from toolset_registry.registration import Registration
farm_mcp_tools.registration = Registration([farm_mcp_tools.FarmDayNightTools])
farm_mcp_tools.registration.register()
unreal.SystemLibrary.execute_console_command(None, 'ModelContextProtocol.RefreshTools')
print('FarmDayNightTools registered with Epic Unreal MCP')
