using UnrealBuildTool;

public class GTAIndia : ModuleRules
{
	public GTAIndia(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
			"UMG", "Slate", "SlateCore", "DeveloperSettings", "ApplicationCore", "RenderCore", "RHI", "AnimationCore"
		});
	}
}
