#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "GIBike.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class USpringArmComponent;
class UCameraComponent;
class AGIPlayerCharacter;
class UAudioComponent;

/**
 * Arcade motorbike. Kinematic: ground-following traces, swept collision, lean. The player
 * character sits on it; optional "stacked" passengers reproduce the famous overloaded-bike look.
 */
UCLASS()
class GTAINDIA_API AGIBike : public APawn
{
	GENERATED_BODY()

public:
	AGIBike();

	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<UBoxComponent> Collision;
	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<USceneComponent> Seat;
	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere, Category = "Bike") TObjectPtr<UAudioComponent> EngineAudio;

	/** Extra people stacked behind / on top of the rider. */
	UPROPERTY(EditAnywhere, Category = "Bike") int32 StackedPassengers = 3;
	UPROPERTY(EditAnywhere, Category = "Bike") float MaxSpeed = 2200.f;
	UPROPERTY(EditAnywhere, Category = "Bike") float MaxReverseSpeed = 450.f;
	UPROPERTY(EditAnywhere, Category = "Bike") float Acceleration = 750.f;
	UPROPERTY(EditAnywhere, Category = "Bike") float BrakeDeceleration = 2200.f;
	UPROPERTY(EditAnywhere, Category = "Bike") float MaxYawRate = 80.f;

	void Mount(AGIPlayerCharacter* Character);
	void Dismount();
	bool HasRider() const { return Rider != nullptr; }
	USceneComponent* GetSeatComponent() const { return Seat; }
	float GetSpeedKmh() const { return FMath::Abs(Speed) * 0.036f; }

	// Input from the controller.
	void SetThrottle(float V) { ThrottleInput = V; }
	void SetSteer(float V) { SteerInput = V; }
	void SetBrake(bool b) { bBrake = b; }
	void Honk();
	void NotifyLookInput();

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void OnConstruction(const FTransform& Transform) override;

private:
	void BuildPassengers();
	void ApplyMeshSettings();
	bool GroundAt(const FVector& Point, FHitResult& Hit) const;

	UPROPERTY() TObjectPtr<AGIPlayerCharacter> Rider;
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> Passengers;

	float ThrottleInput = 0.f;
	float SteerInput = 0.f;
	bool bBrake = false;
	float Speed = 0.f;
	float SteerSmoothed = 0.f;
	float Lean = 0.f;
	float VerticalVelocity = 0.f;
	float Pitch = 0.f;
	float LastLookTime = -100.f;
};
