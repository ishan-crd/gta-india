#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "InputActionValue.h"
#include "GIPlayerController.generated.h"

class SGIMenu;
class SWidget;
class ACameraActor;
class AGIPlayerCharacter;
class AGIBike;
class UAudioComponent;

UENUM()
enum class EGIMenuPage : uint8
{
	None,
	Title,
	Pause,
	Settings,
	Controls,
	Credits,
};

/**
 * Routes Enhanced Input to the character or bike, and owns the title / pause / settings menus.
 */
UCLASS()
class GTAINDIA_API AGIPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AGIPlayerController();

	// Menu callbacks (from Slate).
	void StartGame();
	void ResumeGame();
	void QuitToTitle();
	void QuitGame();
	void OpenPage(EGIMenuPage Page);
	void CloseSettings();
	void OnSettingsChanged(bool bCrowdChanged);

	bool IsInMenu() const { return CurrentPage != EGIMenuPage::None; }

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void OnPossess(APawn* InPawn) override;
	virtual void PlayerTick(float DeltaTime) override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	void UpdateMappingContexts();
	void ShowMenu(EGIMenuPage Page);
	void HideMenu();
	void UpdateTitleCamera(float DeltaTime);

	AGIPlayerCharacter* GetCharacter() const;
	AGIBike* GetBike() const;

	// Input handlers
	void OnMove(const FInputActionValue& V);
	void OnLook(const FInputActionValue& V);
	void OnJumpStarted();
	void OnJumpCompleted();
	void OnSprintStarted();
	void OnSprintCompleted();
	void OnInteract();
	void OnVehicle();
	void OnPause();
	void OnThrottle(const FInputActionValue& V);
	void OnThrottleCompleted();
	void OnSteer(const FInputActionValue& V);
	void OnSteerCompleted();
	void OnBrakeStarted();
	void OnBrakeCompleted();
	void OnHorn();
	void OnDiveStarted();
	void OnWalkStarted();
	void OnWalkCompleted();
	void OnDiveCompleted();

	TSharedPtr<SGIMenu> Menu;
	TSharedPtr<SWidget> MenuContainer;
	EGIMenuPage CurrentPage = EGIMenuPage::None;
	EGIMenuPage SettingsReturnPage = EGIMenuPage::Title;
	bool bInGame = false;

	UPROPERTY() TObjectPtr<ACameraActor> TitleCamera;
	UPROPERTY() TObjectPtr<UAudioComponent> AmbRiver;
	UPROPERTY() TObjectPtr<UAudioComponent> AmbCity;
	UPROPERTY() TObjectPtr<UAudioComponent> AmbBells;
	void UpdateAmbience();
	float TitleTime = 0.f;

	// Automated screenshots: -GIShots=<file>, one shot per line:
	//   <name> cam <x> <y> <z> <pitch> <yaw>      free camera
	//   <name> player <x> <y> <z> <yaw> [pitch]  gameplay view with HUD
	//   <name> title | pause | settings          menus
	struct FGIShot
	{
		FString Name;
		FString Kind;
		FVector Loc = FVector::ZeroVector;
		FRotator Rot = FRotator::ZeroRotator;
		FString Program;
	};
	int32 SeqFrame = 0;
	int32 RouteIndex = 0;
	float RouteStuckTimer = 0.f;
	FVector RouteLastPos = FVector::ZeroVector;
	void LogLine(const FString& Line);
	float SeqNext = 0.f;
	void TickSequence(const FGIShot& Shot);
	TArray<FGIShot> Shots;
	int32 ShotIndex = -1;
	float ShotTimer = 0.f;
	bool bShotTaken = false;
	float ShotTakenAt = 0.f;
	FString ShotDir;
	// Perf samples for the current shot (ms)
	TArray<float> PerfFrame, PerfGame, PerfRender, PerfGPU;
	void WritePerf(const FString& ShotName);
	void LoadShots();
	void TickShots(float DeltaTime);
	void BeginShot(const FGIShot& Shot);
};
