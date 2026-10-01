#include "GIGameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "Engine/Engine.h"

UGIGameUserSettings::UGIGameUserSettings()
{
}

UGIGameUserSettings* UGIGameUserSettings::Get()
{
	return GEngine ? Cast<UGIGameUserSettings>(GEngine->GetGameUserSettings()) : nullptr;
}

int32 UGIGameUserSettings::GetCrowdBudget() const
{
	static const int32 Budgets[] = { 80, 200, 360, 560 };
	return Budgets[FMath::Clamp(CrowdDensity, 0, 3)];
}

static void SetCVarInt(const TCHAR* Name, int32 Value)
{
	if (IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(Name))
	{
		CVar->Set(Value, ECVF_SetByGameSetting);
	}
}

static void SetCVarFloat(const TCHAR* Name, float Value)
{
	if (IConsoleVariable* CVar = IConsoleManager::Get().FindConsoleVariable(Name))
	{
		CVar->Set(Value, ECVF_SetByGameSetting);
	}
}

void UGIGameUserSettings::ApplyGameSettings()
{
	SetCVarFloat(TEXT("r.ScreenPercentage"), FMath::Clamp(ScreenPercentage, 30.f, 100.f));
	SetCVarInt(TEXT("r.AntiAliasingMethod"), AntiAliasing);
	SetCVarInt(TEXT("r.MotionBlurQuality"), bMotionBlur ? 3 : 0);
	SetCVarInt(TEXT("r.Tonemapper.GrainQuantization"), 1);
	SetCVarInt(TEXT("r.FilmGrain"), bFilmGrain ? 1 : 0);
	SetCVarInt(TEXT("r.VolumetricFog"), bVolumetricFog ? 1 : 0);
	SetCVarFloat(TEXT("r.ViewDistanceScale"), FMath::Clamp(DrawDistance, 0.4f, 2.f));
	SetCVarFloat(TEXT("r.Shadow.DistanceScale"), FMath::Clamp(ShadowDistance, 0.3f, 2.f));
	SetCVarFloat(TEXT("r.Tonemapper.Sharpen"), FMath::Clamp(Sharpen, 0.f, 2.f));
}

void UGIGameUserSettings::ApplyGamePreset(int32 Q)
{
	Q = FMath::Clamp(Q, 0, 3);
	SetOverallScalabilityLevel(Q);
	CrowdDensity = Q;
	ScreenPercentage = Q == 0 ? 67.f : (Q == 1 ? 80.f : 100.f);
	AntiAliasing = (uint8)(Q == 0 ? EGIAntiAliasing::FXAA : EGIAntiAliasing::TSR);
	bVolumetricFog = Q >= 2;
	bMotionBlur = Q >= 2;
	static const float Draw[] = { 0.6f, 0.8f, 1.f, 1.25f };
	static const float Shadow[] = { 0.5f, 0.75f, 1.f, 1.2f };
	static const float Crowd[] = { 80.f, 120.f, 160.f, 220.f };
	DrawDistance = Draw[Q];
	ShadowDistance = Shadow[Q];
	CrowdDrawDistance = Crowd[Q];
	CrowdShadows = Q == 0 ? 0 : (Q == 1 ? 1 : 2);
	Sharpen = Q <= 1 ? 0.7f : 0.4f;
}

void UGIGameUserSettings::ApplySettings(bool bCheckForCommandLineOverrides)
{
	Super::ApplySettings(bCheckForCommandLineOverrides);
	ApplyGameSettings();
}

void UGIGameUserSettings::SetToDefaults()
{
	Super::SetToDefaults();
	CrowdDensity = 2;
	ScreenPercentage = 100.f;
	AntiAliasing = (uint8)EGIAntiAliasing::TSR;
	bMotionBlur = true;
	bFilmGrain = false;
	bVolumetricFog = true;
	FieldOfView = 90.f;
	MouseSensitivity = 1.f;
	bInvertY = false;
	bShowFPS = false;
	DrawDistance = 1.f;
	ShadowDistance = 1.f;
	CrowdDrawDistance = 160.f;
	CrowdShadows = 2;
	Sharpen = 0.4f;
}

void UGIGameUserSettings::AutoDetectIfFirstRun()
{
	if (bFirstRunDone)
	{
		return;
	}
	bFirstRunDone = true;
	RunHardwareBenchmark();
	ApplyHardwareBenchmarkResults();
	const int32 Overall = GetOverallScalabilityLevel();
	ApplyGamePreset(Overall < 0 ? 2 : Overall);
	ApplySettings(false);
	SaveSettings();
}
