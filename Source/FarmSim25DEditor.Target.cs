using UnrealBuildTool;
public class FarmSim25DEditorTarget : TargetRules
{
    public FarmSim25DEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("FarmSim25D");
    }
}
