#include "GICharacterMovement.h"
#include "GIRiver.h"
#include "GameFramework/Character.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"

UGICharacterMovement::UGICharacterMovement()
{
	MaxWalkSpeed = BaseWalkSpeed;
	JumpZVelocity = 460.f;
	AirControl = 0.3f;
	// Weighty but responsive: gradual acceleration, smooth braking and turning.
	MaxAcceleration = 1350.f;
	BrakingDecelerationWalking = 1250.f;
	GroundFriction = 6.f;
	RotationRate = FRotator(0.f, 400.f, 0.f);
	bOrientRotationToMovement = true;
	MaxStepHeight = 50.f;
	SetWalkableFloorAngle(50.f);
	bCanWalkOffLedges = true;
	bImpartBaseVelocityX = true;
	bImpartBaseVelocityY = true;
	bImpartBaseAngularVelocity = true;
	NavAgentProps.bCanSwim = true;
}

bool UGICharacterMovement::TraceGround(const FVector& From, float MaxDist, FHitResult& OutHit) const
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GISwimGround), false, CharacterOwner);
	return GetWorld()->LineTraceSingleByChannel(OutHit, From, From - FVector(0, 0, MaxDist), ECC_Visibility, Params);
}

void UGICharacterMovement::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	AGIRiver* River = AGIRiver::Get(this);
	if (River && UpdatedComponent && CharacterOwner)
	{
		const FVector Loc = UpdatedComponent->GetComponentLocation();
		const float HalfHeight = CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		WaterDepth = 0.f;
		if (River->IsInWaterArea(Loc))
		{
			FHitResult Hit;
			const float WaterZ = River->GetWaterZ();
			if (TraceGround(FVector(Loc.X, Loc.Y, FMath::Max(Loc.Z, WaterZ) + 50.f), 3000.f, Hit))
			{
				WaterDepth = FMath::Max(0.f, WaterZ - Hit.ImpactPoint.Z);
			}
			else
			{
				WaterDepth = 10000.f; // bottomless
			}

			const float FeetZ = Loc.Z - HalfHeight;
			if (IsClimbingOut())
			{
			}
			else if (!IsSurfaceSwimming())
			{
				const bool bFeetInWater = FeetZ < WaterZ - 20.f;
				if (bFeetInWater && WaterDepth > SwimEnterDepth && (MovementMode == MOVE_Walking || MovementMode == MOVE_Falling))
				{
					SetMovementMode(MOVE_Custom, GIMOVE_Swim);
				}
			}
			else if (WaterDepth < SwimExitDepth)
			{
				SetMovementMode(MOVE_Falling);
			}
		}
		else if (IsSurfaceSwimming())
		{
			SetMovementMode(MOVE_Falling);
		}
	}

	// Walking speed: sprint, wading slow-down.
	float Walk = bWantsWalk ? SlowWalkSpeed : (bWantsSprint ? SprintWalkSpeed : BaseWalkSpeed);
	if (WaterDepth > 40.f && !IsSurfaceSwimming())
	{
		Walk *= FMath::GetMappedRangeValueClamped(FVector2D(40.f, 120.f), FVector2D(0.7f, 0.35f), WaterDepth);
	}
	MaxWalkSpeed = Walk;

	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}

float UGICharacterMovement::GetMaxSpeed() const
{
	if (IsSurfaceSwimming())
	{
		return bWantsSprint ? SurfaceSwimSprintSpeed : SurfaceSwimSpeed;
	}
	return Super::GetMaxSpeed();
}

bool UGICharacterMovement::IsUnderwater() const
{
	const AGIRiver* River = AGIRiver::Get(this);
	return River && UpdatedComponent && IsSurfaceSwimming()
		&& UpdatedComponent->GetComponentLocation().Z < River->GetWaterZ() - SwimCenterDepth - 80.f;
}

void UGICharacterMovement::PhysClimbOut(float DeltaTime)
{
	ClimbTime += DeltaTime;
	const float A = GetClimbAlpha();
	// Rise first (pull-up), then shuffle forward onto the step.
	const float Up = FMath::SmoothStep(0.f, 0.65f, A);
	const float Fwd = FMath::SmoothStep(0.45f, 1.f, A);
	const FVector P(FMath::Lerp(ClimbStart.X, ClimbTarget.X, Fwd), FMath::Lerp(ClimbStart.Y, ClimbTarget.Y, Fwd), FMath::Lerp(ClimbStart.Z, ClimbTarget.Z, Up));
	UpdatedComponent->SetWorldLocation(P, false, nullptr, ETeleportType::None);
	Velocity = FVector::ZeroVector;
	if (A >= 1.f)
	{
		SetMovementMode(MOVE_Falling);
	}
}

bool UGICharacterMovement::IsMovingOnGround() const
{
	return Super::IsMovingOnGround();
}

void UGICharacterMovement::PhysCustom(float DeltaTime, int32 Iterations)
{
	if (CustomMovementMode == GIMOVE_Swim)
	{
		PhysSurfaceSwim(DeltaTime);
		return;
	}
	if (CustomMovementMode == GIMOVE_Climb)
	{
		PhysClimbOut(DeltaTime);
		return;
	}
	Super::PhysCustom(DeltaTime, Iterations);
}

void UGICharacterMovement::PhysSurfaceSwim(float DeltaTime)
{
	if (DeltaTime < MIN_TICK_TIME)
	{
		return;
	}
	AGIRiver* River = AGIRiver::Get(this);
	if (!River)
	{
		SetMovementMode(MOVE_Falling);
		return;
	}

	RestorePreAdditiveRootMotionVelocity();

	// Horizontal: accelerate towards input, with water drag.
	const float MaxSpeed = GetMaxSpeed();
	FVector Accel = Acceleration;
	Accel.Z = 0.f;
	FVector HorizVel(Velocity.X, Velocity.Y, 0.f);
	if (!Accel.IsNearlyZero())
	{
		const FVector Wish = Accel.GetSafeNormal() * MaxSpeed * FMath::Min(1.f, Accel.Size() / FMath::Max(GetMaxAcceleration(), 1.f));
		HorizVel = FMath::VInterpTo(HorizVel, Wish, DeltaTime, 2.2f);
	}
	else
	{
		HorizVel = FMath::VInterpTo(HorizVel, FVector::ZeroVector, DeltaTime, 1.4f);
	}

	// Vertical: spring to the swim height with a gentle bob.
	const float Bob = 4.f * FMath::Sin(GetWorld()->GetTimeSeconds() * 2.2f);
	// Diving: stay above the river bed.
	float DiveDepth = 0.f;
	if (bWantsDive)
	{
		DiveDepth = FMath::Clamp(WaterDepth - 140.f, 0.f, 230.f);
	}
	const float TargetZ = River->GetWaterZ() - SwimCenterDepth - DiveDepth + (DiveDepth > 0.f ? 0.f : Bob);
	const float CurZ = UpdatedComponent->GetComponentLocation().Z;
	float VZ = Velocity.Z;
	VZ += ((TargetZ - CurZ) * 6.f - VZ * 3.5f) * DeltaTime * 3.f;
	VZ = FMath::Clamp(VZ, -600.f, 300.f);

	Velocity = FVector(HorizVel.X, HorizVel.Y, VZ);

	const FVector Delta = Velocity * DeltaTime;
	FHitResult Hit(1.f);
	SafeMoveUpdatedComponent(Delta, UpdatedComponent->GetComponentQuat(), true, Hit);
	if (Hit.IsValidBlockingHit())
	{
		// Try to climb out onto steps / banks.
		const FVector Loc = UpdatedComponent->GetComponentLocation();
		const float HalfHeight = CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		FHitResult Ledge;
		const FVector Ahead = Loc + HorizVel.GetSafeNormal() * (CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleRadius() + 30.f);
		if (!bWantsDive && !HorizVel.IsNearlyZero() && TraceGround(Ahead + FVector(0, 0, HalfHeight + 80.f), HalfHeight * 2.f + 120.f, Ledge)
			&& Ledge.ImpactNormal.Z > 0.7f && Ledge.ImpactPoint.Z < Loc.Z + HalfHeight)
		{
			// Haul yourself out onto the steps (animated, see PhysClimbOut).
			ClimbStart = Loc;
			ClimbTarget = FVector(Ledge.ImpactPoint.X, Ledge.ImpactPoint.Y, Ledge.ImpactPoint.Z + HalfHeight + 5.f) + HorizVel.GetSafeNormal() * 25.f;
			ClimbTime = 0.f;
			ClimbDuration = FMath::GetMappedRangeValueClamped(FVector2D(30.f, 150.f), FVector2D(0.8f, 1.4f), ClimbTarget.Z - ClimbStart.Z);
			Velocity = FVector::ZeroVector;
			SetMovementMode(MOVE_Custom, GIMOVE_Climb);
			return;
		}
		SlideAlongSurface(Delta, 1.f - Hit.Time, Hit.Normal, Hit, true);
	}

	if (!bJustTeleported && !HasAnimRootMotion())
	{
		// keep Velocity as integrated
	}

	// Face movement direction.
	if (!HorizVel.IsNearlyZero(10.f))
	{
		const FRotator Want = HorizVel.Rotation();
		const FRotator Cur = UpdatedComponent->GetComponentRotation();
		const FRotator NewRot = FMath::RInterpTo(Cur, FRotator(0.f, Want.Yaw, 0.f), DeltaTime, 4.f);
		FHitResult RotHit;
		SafeMoveUpdatedComponent(FVector::ZeroVector, NewRot, false, RotHit);
	}
}
