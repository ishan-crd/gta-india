#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "GIBike.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class UStaticMesh;
class USkeletalMeshComponent;
class USpringArmComponent;
class UCameraComponent;
class AGIPlayerCharacter;
class UAudioComponent;

/**
 * Arcade vehicle the player drives: the motorbike by default, or an auto-rickshaw / car when spawned
 * with a mesh override and bFourWheeler (no lean, wider body, driver seat). Kinematic: ground-following
 * traces, swept collision.
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

	/** Extra people riding pillion behind the rider. */
	UPROPERTY(EditAnywhere, Category = "Bike") int32 StackedPassengers = 0;
	/** Drive a different vehicle (auto, car) with this mesh instead of the configured bike. */
	UPROPERTY(EditAnywhere, Category = "Bike") TObjectPtr<UStaticMesh> MeshOverride;
	UPROPERTY(EditAnywhere, Category = "Bike") float MeshYawOverride = 0.f;
	/** Autos / cars: no lean, wider collision, driver seat further forward (cars: right-hand drive). */
	UPROPERTY(EditAnywhere, Category = "Bike") bool bFourWheeler = false;
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
	float WheelBase = 65.f;
};
