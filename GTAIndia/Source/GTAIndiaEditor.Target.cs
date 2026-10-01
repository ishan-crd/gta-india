using UnrealBuildTool;

public class GTAIndiaEditorTarget : TargetRules
{
	public GTAIndiaEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("GTAIndia");
	}
}
