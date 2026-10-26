using UnrealBuildTool;
public class FarmSim25DTarget : TargetRules
{
    public FarmSim25DTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("FarmSim25D");
    }
}
