#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GICharacterMovement.generated.h"

enum EGICustomMove : uint8
{
	GIMOVE_None = 0,
	GIMOVE_Swim = 1,
	GIMOVE_Climb = 2,
};

/**
 * Character movement with a self-contained surface-swimming mode driven by AGIRiver (no physics
 * volumes needed) and slow wading in shallow water.
 */
UCLASS()
class GTAINDIA_API UGICharacterMovement : public UCharacterMovementComponent
{
	GENERATED_BODY()

public:
	UGICharacterMovement();

	bool IsSurfaceSwimming() const { return MovementMode == MOVE_Custom && CustomMovementMode == GIMOVE_Swim; }
	bool IsClimbingOut() const { return MovementMode == MOVE_Custom && CustomMovementMode == GIMOVE_Climb; }
	/** 0..1 progress of the climb-out (for the animation). */
	float GetClimbAlpha() const { return FMath::Clamp(ClimbTime / ClimbDuration, 0.f, 1.f); }
	/** Hold to dive under the surface while swimming. */
	bool bWantsDive = false;
	/** True while the swimmer is well below the surface. */
	bool IsUnderwater() const;
	virtual bool IsMovingOnGround() const override;

	/** Water depth under the character this frame (0 if dry). */
	float GetWaterDepth() const { return WaterDepth; }
	bool IsWading() const { return !IsSurfaceSwimming() && WaterDepth > 40.f; }

	/** Horizontal swim speed (cm/s). */
	UPROPERTY(EditAnywhere, Category = "Swim") float SurfaceSwimSpeed = 330.f;
	UPROPERTY(EditAnywhere, Category = "Swim") float SurfaceSwimSprintSpeed = 470.f;
	/** Capsule centre sits this far below the water surface while swimming. */
	UPROPERTY(EditAnywhere, Category = "Swim") float SwimCenterDepth = 55.f;
	/** Water deeper than this (from the floor) starts swimming. */
	UPROPERTY(EditAnywhere, Category = "Swim") float SwimEnterDepth = 135.f;
	/** Water shallower than this lets the character stand up again. */
	UPROPERTY(EditAnywhere, Category = "Swim") float SwimExitDepth = 115.f;

	bool bWantsSprint = false;

	/** Ground speeds (cm/s): matched to the measured walk (1.15 m/s) / jog (2.54 m/s) clips. */
	float BaseWalkSpeed = 345.f;
	float SprintWalkSpeed = 485.f;
	float SlowWalkSpeed = 125.f;
	bool bWantsWalk = false;

protected:
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void PhysCustom(float DeltaTime, int32 Iterations) override;
	virtual float GetMaxSpeed() const override;

private:
	float WaterDepth = 0.f;
	FVector ClimbStart = FVector::ZeroVector;
	FVector ClimbTarget = FVector::ZeroVector;
	float ClimbTime = 0.f;
	float ClimbDuration = 1.1f;
	void PhysClimbOut(float DeltaTime);
	bool TraceGround(const FVector& From, float MaxDist, FHitResult& OutHit) const;
	void PhysSurfaceSwim(float DeltaTime);
};
