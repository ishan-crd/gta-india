#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "GIHUD.generated.h"

class ASceneCapture2D;
class UTextureRenderTarget2D;
class UMaterialInstanceDynamic;
class UFont;
class AGIPlayerCharacter;

/** GTA-style HUD drawn on the canvas: mission box, health, money, minimap, markers, prompts. */
UCLASS()
class GTAINDIA_API AGIHUD : public AHUD
{
	GENERATED_BODY()

public:
	AGIHUD();

	/** Hide gameplay HUD while menus / title are up. */
	bool bGameplayHUDVisible = false;

	void AddPopup(const FText& Text);

protected:
	virtual void BeginPlay() override;
	virtual void DrawHUD() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FPopup
	{
		FText Text;
		float Age = 0.f;
	};

	AGIPlayerCharacter* GetPlayerCharacter() const;
	void BindPlayer();
	void EnsureMinimap();
	void DrawMissionBox(float S);
	void DrawStats(const AGIPlayerCharacter* Player, float S);
	void DrawMinimap(const AGIPlayerCharacter* Player, float S);
	void DrawWorldMarker(float S);
	void DrawPrompt(const AGIPlayerCharacter* Player, float S);
	void DrawBanner(float S);
	void DrawDeath(float S);
	void DrawFPS(float S);

	void Rect(float X, float Y, float W, float H, const FLinearColor& C);
	void Text(const FString& Str, float X, float Y, UFont* Font, float Scale, const FLinearColor& C, bool bCenterX = false, bool bShadow = true);
	FVector2D TextSize(const FString& Str, UFont* Font, float Scale);
	void Disc(const FVector2D& Center, float Radius, const FLinearColor& C, int32 Sides = 24);
	void Triangle(const FVector2D& A, const FVector2D& B, const FVector2D& C, const FLinearColor& Color);

	UPROPERTY() TObjectPtr<ASceneCapture2D> MinimapCapture;
	UPROPERTY() TObjectPtr<UTextureRenderTarget2D> MinimapRT;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> MinimapMID;
	UPROPERTY() TObjectPtr<UFont> BigFont;
	UPROPERTY() TObjectPtr<UFont> MedFont;
	UPROPERTY() TObjectPtr<UFont> SmallFont;

	TArray<FPopup> Popups;
	FString Subtitle;
	float SubtitleTime = 0.f;
	float MinimapTimer = 0.f;
	float SmoothedFPS = 60.f;
	float DisplayedHealth = 100.f;
	TWeakObjectPtr<AGIPlayerCharacter> BoundPlayer;
	FDelegateHandle PopupHandle;
};
