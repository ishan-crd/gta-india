#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameUserSettings.h"
#include "GIGameUserSettings.generated.h"

/** Anti-aliasing choices exposed in the menu (maps to r.AntiAliasingMethod). */
UENUM()
enum class EGIAntiAliasing : uint8
{
	Off = 0,
	FXAA = 1,
	TAA = 2,
	TSR = 4,
};

/**
 * Engine scalability settings + game-specific options (crowd density, FOV, mouse, motion blur...).
 * Saved to Saved/Config/<Platform>/GameUserSettings.ini.
 */
UCLASS(Config = GameUserSettings, ConfigDoNotCheckDefaults)
class GTAINDIA_API UGIGameUserSettings : public UGameUserSettings
{
	GENERATED_BODY()

public:
	UGIGameUserSettings();

	static UGIGameUserSettings* Get();

	/** 0 = Low .. 3 = Ultra. */
	UPROPERTY(Config) int32 CrowdDensity = 2;
	UPROPERTY(Config) float ScreenPercentage = 100.f;
	UPROPERTY(Config) uint8 AntiAliasing = (uint8)EGIAntiAliasing::TSR;
	UPROPERTY(Config) bool bMotionBlur = true;
	UPROPERTY(Config) bool bFilmGrain = false;
	UPROPERTY(Config) bool bVolumetricFog = true;
	UPROPERTY(Config) float FieldOfView = 90.f;
	UPROPERTY(Config) float MouseSensitivity = 1.f;
	UPROPERTY(Config) bool bInvertY = false;
	UPROPERTY(Config) bool bShowFPS = false;
	UPROPERTY(Config) bool bFirstRunDone = false;
	/** Multiplier on every draw / cull distance (r.ViewDistanceScale). */
	UPROPERTY(Config) float DrawDistance = 1.f;
	/** Multiplier on how far dynamic shadows reach (r.Shadow.DistanceScale). */
	UPROPERTY(Config) float ShadowDistance = 1.f;
	/** People further than this (metres) are not drawn. */
	UPROPERTY(Config) float CrowdDrawDistance = 160.f;
	/** 0 = no crowd shadows, 1 = near (25 m), 2 = far (60 m). */
	UPROPERTY(Config) int32 CrowdShadows = 2;
	/** Post-process sharpening 0..1 (helps when resolution scale < 100%). */
	UPROPERTY(Config) float Sharpen = 0.4f;

	float GetCrowdCullDistanceCm() const { return CrowdDrawDistance * 100.f; }
	float GetCrowdShadowDistanceCm() const { return CrowdShadows == 0 ? 0.f : (CrowdShadows == 1 ? 2500.f : 6000.f); }
	/** Applies a preset to the game-specific options too. */
	void ApplyGamePreset(int32 Quality);

	/** Max pedestrians + train riders for the current crowd density. */
	int32 GetCrowdBudget() const;

	/** Apply the game-specific console variables (called after ApplySettings). */
	void ApplyGameSettings();

	/** Picks settings from the hardware benchmark on first launch. */
	void AutoDetectIfFirstRun();

	virtual void ApplySettings(bool bCheckForCommandLineOverrides) override;
	virtual void SetToDefaults() override;
};
