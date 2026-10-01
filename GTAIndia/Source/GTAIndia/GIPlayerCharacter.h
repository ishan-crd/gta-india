#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "InputActionValue.h"
#include "GIAnimInstance.h"
#include "GIPlayerCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UGICharacterMovement;
class AGIBike;
class AGITrain;

DECLARE_MULTICAST_DELEGATE_OneParam(FGIFloatingTextEvent, const FText& /*Text*/);

/** The delivery guy. */
UCLASS()
class GTAINDIA_API AGIPlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AGIPlayerCharacter(const FObjectInitializer& ObjectInitializer);

	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<UCameraComponent> FollowCamera;
	UPROPERTY(VisibleAnywhere, Category = "Look") TObjectPtr<UStaticMeshComponent> DeliveryBox;
	/** Murky sphere around the camera, shown only when the camera is under the Ganga. */
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<UStaticMeshComponent> UnderwaterMurk;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stats") float MaxHealth = 100.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Stats") float Health = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Stats") int32 Money = 2350;
	/** HP lost per second while swimming in the Ganga. */
	UPROPERTY(EditAnywhere, Category = "Stats") float SwimDrainPerSecond = 0.9f;
	UPROPERTY(EditAnywhere, Category = "Stats") float WadeDrainPerSecond = 0.15f;

	UGICharacterMovement* GetGIMovement() const;
	UGIAnimInstance* GetGIAnim() const;

	bool IsDead() const { return bDead; }
	bool IsSwimming() const;
	bool IsRiding() const { return RidingBike != nullptr; }
	AGIBike* GetRidingBike() const { return RidingBike; }

	void AddMoney(int32 Amount);
	void ApplyDamageSimple(float Amount, bool bShowPopup = true);
	void RestoreHealth() { Health = MaxHealth; }

	/** Prompt shown on the HUD (e.g. "[E] Train pe chadho"). Empty = none. */
	FText GetPrompt() const { return Prompt; }

	/** Mount / dismount (called by the bike). */
	void AttachToBike(AGIBike* Bike);
	void DetachFromBike();

	/** Respawn point used after dying. */
	FTransform RespawnTransform;

	/** Broadcast when a floating popup should be shown ("HP -10", "+₹150"...). */
	FGIFloatingTextEvent OnPopup;

	/** Called by the controller. */
	void InputMove(const FInputActionValue& Value);
	void InputLook(const FInputActionValue& Value);
	void InputJumpStart();
	void InputJumpStop();
	void InputSprint(bool bOn);
	void InputInteract();
	void InputVehicle();
	void InputDive(bool bOn);
	void InputWalk(bool bOn);
	bool IsCameraUnderwater() const { return bCameraUnderwater; }

	void ApplyUserSettings();

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void SetupLook();
	void UpdateAnimation(float DeltaSeconds);
	void UpdateInteraction();
	void UpdateWater(float DeltaSeconds);
	void Die();
	void Respawn();
	AGIBike* FindNearbyBike(float MaxDist) const;
	AGITrain* FindNearbyTrain(FVector& OutRoofPoint) const;
	/** Boat ferry between the ghats: 0 = none, 1 = to the east bank, -1 = back to the west bank. */
	int32 FerryDirection() const;
	void TakeFerry(int32 Direction);

	UPROPERTY() TObjectPtr<AGIBike> RidingBike;

	FText Prompt;
	bool bDead = false;
	float DeadTimer = 0.f;
	float SwimBlend = 0.f;
	float DrainAccumulator = 0.f;
	float InteractionTimer = 0.f;
	FQuat MeshBaseRotation = FQuat::Identity;
	FVector MeshBaseLocation = FVector::ZeroVector;
	float DefaultArmLength = 380.f;
	bool bWasSwimming = false;
	bool bCameraUnderwater = false;
	float LastYaw = 0.f;
	float Lean = 0.f;
	float FootOffL = 0.f, FootOffR = 0.f, IKAlpha = 0.f;
	float BaseFOV = 90.f;
	bool bOwnerHidden = false;
	void UpdateFootIK(float DeltaSeconds);
	void UpdateCameraFeel(float DeltaSeconds);
	void UpdateUnderwaterCamera();
	float PickUpTimer = 0.f;

public:
	/** Plays the pick-up animation and briefly freezes movement. */
	void PlayPickUp();
	float StrokeTimer = 0.f;
};
