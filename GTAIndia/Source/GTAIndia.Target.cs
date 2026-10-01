using UnrealBuildTool;

public class GTAIndiaTarget : TargetRules
{
	public GTAIndiaTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("GTAIndia");
	}
}
