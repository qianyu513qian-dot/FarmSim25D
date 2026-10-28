"""Register project authoring tools when Epic's official MCP plugins are enabled."""
import unreal
try:
    import farm_dn_bootstrap
except ImportError:
    unreal.log('Farm MCP tooling requires the editor ToolsetRegistry plugin.')
