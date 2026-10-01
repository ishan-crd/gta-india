#include "GIPlayerCharacter.h"
#include "GIAssetSettings.h"
#include "GIBike.h"
#include "GICharacterMovement.h"
#include "GIGameUserSettings.h"
#include "GIRiver.h"
#include "GITrain.h"
#include "GITraffic.h"
#include "GIDharavi.h"
#include "Engine/StaticMesh.h"
#include "GTAIndia.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "AnimationRuntime.h"
#include "UObject/ConstructorHelpers.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"

#define LOCTEXT_NAMESPACE "GTAIndia"

AGIPlayerCharacter::AGIPlayerCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UGICharacterMovement>(ACharacter::CharacterMovementComponentName))
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(34.f, 90.f);
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = DefaultArmLength;
	// Close GTA-style chase framing: head height, slightly over the right shoulder.
	CameraBoom->SocketOffset = FVector(0.f, 32.f, 78.f);
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.f;
	CameraBoom->ProbeSize = 14.f;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	UnderwaterMurk = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("UnderwaterMurk"));
	UnderwaterMurk->SetupAttachment(FollowCamera);
	UnderwaterMurk->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	UnderwaterMurk->SetCastShadow(false);
	UnderwaterMurk->SetVisibility(false);
	UnderwaterMurk->SetRelativeScale3D(FVector(14.f));
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		if (Sphere.Succeeded())
		{
			UnderwaterMurk->SetStaticMesh(Sphere.Object);
		}
	}

	DeliveryBox = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DeliveryBox"));
	DeliveryBox->SetupAttachment(GetMesh());
	DeliveryBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	GetMesh()->SetRelativeLocation(FVector(0.f, 0.f, -90.f));
	GetMesh()->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
	GetMesh()->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}

UGICharacterMovement* AGIPlayerCharacter::GetGIMovement() const
{
	return Cast<UGICharacterMovement>(GetCharacterMovement());
}

UGIAnimInstance* AGIPlayerCharacter::GetGIAnim() const
{
	return Cast<UGIAnimInstance>(GetMesh()->GetAnimInstance());
}

bool AGIPlayerCharacter::IsSwimming() const
{
	const UGICharacterMovement* Move = GetGIMovement();
	return Move && Move->IsSurfaceSwimming();
}

void AGIPlayerCharacter::SetupLook()
{
	const UGIAssetSettings& S = UGIAssetSettings::Get();
	const AGILevelProfile* Profile = AGILevelProfile::Get(this);
	if (USkeletalMesh* Mesh = (Profile && Profile->PlayerMesh) ? Profile->PlayerMesh.Get() : S.PlayerMesh.LoadSynchronous())
	{
		GetMesh()->SetSkeletalMesh(Mesh);
		GetMesh()->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
	}
	if (Profile)
	{
		// Scene-specific chase camera (the Trial lane: low, close, centred, like the reference shot).
		DefaultArmLength = Profile->ArmLength;
		CameraBoom->TargetArmLength = Profile->ArmLength;
		CameraBoom->SocketOffset = Profile->SocketOffset;
		CameraBoom->CameraLagSpeed = Profile->CameraLagSpeed;
		CameraBoom->bEnableCameraRotationLag = Profile->RotationLagSpeed > 0.f;
		CameraBoom->CameraRotationLagSpeed = Profile->RotationLagSpeed;
		if (Profile->WalkSpeed > 0.f)
		{
			if (UGICharacterMovement* Move = GetGIMovement())
			{
				Move->BaseWalkSpeed = Profile->WalkSpeed;
			}
		}
		if (AController* C = GetController())
		{
			C->SetControlRotation(FRotator(Profile->StartPitch, GetActorRotation().Yaw, 0.f));
		}
	}
	if (UStaticMesh* Box = S.DeliveryBoxMesh.LoadSynchronous())
	{
		DeliveryBox->SetStaticMesh(Box);
		// DeliveryBoxOffset is a mesh-space position (reference pose); convert it to the bone's space so
		// the box follows the spine without depending on the bone's axis convention.
		DeliveryBox->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, S.DeliveryBoxBone);
		// No delivery in Dharavi: the walk-around has no bag on his back (like the clip).
		if (GetWorld() && (GetWorld()->GetMapName().Contains(TEXT("Mumbai")) || (Profile && Profile->bHideBag)))
		{
			bNoBox = true;
			DeliveryBox->SetVisibility(false);
		}
		if (const USkeletalMesh* SK = GetMesh()->GetSkeletalMeshAsset())
		{
			const int32 BoneIdx = SK->GetRefSkeleton().FindBoneIndex(S.DeliveryBoxBone);
			if (BoneIdx != INDEX_NONE)
			{
				const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(SK->GetRefSkeleton(), BoneIdx);
				const FTransform WantCS(FQuat::Identity, S.DeliveryBoxOffset);
				DeliveryBox->SetRelativeTransform(WantCS.GetRelativeTransform(BoneCS));
			}
		}
	}
	if (UMaterialInterface* Murk = S.UnderwaterMaterial.LoadSynchronous())
	{
		UnderwaterMurk->SetMaterial(0, Murk);
	}
	// Underwater grade (applied with blend weight 0/1 when the camera dips below the surface).
	FPostProcessSettings& PP = FollowCamera->PostProcessSettings;
	PP.bOverride_SceneColorTint = true;
	PP.SceneColorTint = FLinearColor(0.75f, 0.62f, 0.3f);
	PP.bOverride_ColorSaturation = true;
	PP.ColorSaturation = FVector4(0.55f, 0.55f, 0.55f, 1.f);
	PP.bOverride_VignetteIntensity = true;
	PP.VignetteIntensity = 0.9f;
	PP.bOverride_DepthOfFieldFocalDistance = true;
	PP.DepthOfFieldFocalDistance = 220.f;
	PP.bOverride_DepthOfFieldFstop = true;
	PP.DepthOfFieldFstop = 1.2f;
	PP.bOverride_BloomIntensity = true;
	PP.BloomIntensity = 1.6f;
	FollowCamera->PostProcessBlendWeight = 0.f;

	MeshBaseRotation = GetMesh()->GetRelativeRotation().Quaternion();
	MeshBaseLocation = GetMesh()->GetRelativeLocation();
}

void AGIPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();
	SetupLook();
	RespawnTransform = GetActorTransform();
	Health = MaxHealth;
	ApplyUserSettings();
	if (UGICharacterMovement* Move = GetGIMovement())
	{
		Move->MaxWalkSpeed = Move->BaseWalkSpeed;
	}
}

void AGIPlayerCharacter::ApplyUserSettings()
{
	if (UGIGameUserSettings* Settings = UGIGameUserSettings::Get())
	{
		if (Settings->CameraVersion < 1)
		{
			// New over-the-shoulder framing: a tighter lens than the old 90 default.
			Settings->CameraVersion = 1;
			if (Settings->FieldOfView >= 89.f)
			{
				Settings->FieldOfView = 75.f;
			}
			Settings->SaveSettings();
		}
		FollowCamera->SetFieldOfView(Settings->FieldOfView);
		BaseFOV = Settings->FieldOfView;
		if (const AGILevelProfile* Profile = AGILevelProfile::Get(this))
		{
			if (Profile->FieldOfView > 0.f)
			{
				BaseFOV = Profile->FieldOfView;
				FollowCamera->SetFieldOfView(BaseFOV);
			}
		}
	}
}

void AGIPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bDead)
	{
		UpdateAnimation(DeltaSeconds);
		DeadTimer -= DeltaSeconds;
		if (DeadTimer <= 0.f)
		{
			Respawn();
		}
		return;
	}

	UpdateWater(DeltaSeconds);
	UpdateAnimation(DeltaSeconds);
	UpdateUnderwaterCamera();
	UpdateFootIK(DeltaSeconds);
	UpdateCameraFeel(DeltaSeconds);

	InteractionTimer -= DeltaSeconds;
	if (InteractionTimer <= 0.f)
	{
		InteractionTimer = 0.15f;
		UpdateInteraction();
	}

	// Fell out of the world.
	if (GetActorLocation().Z < -5000.f)
	{
		Die();
	}
}

void AGIPlayerCharacter::UpdateUnderwaterCamera()
{
	const AGIRiver* River = AGIRiver::Get(this);
	const FVector Cam = FollowCamera->GetComponentLocation();
	const bool bUnder = River && River->IsInWaterArea(Cam) && Cam.Z < River->GetWaterZ() - 8.f;
	if (bUnder != bCameraUnderwater)
	{
		bCameraUnderwater = bUnder;
		FollowCamera->PostProcessBlendWeight = bUnder ? 1.f : 0.f;
		UnderwaterMurk->SetVisibility(bUnder);
	}
}

void AGIPlayerCharacter::InputWalk(bool bOn)
{
	if (UGICharacterMovement* Move = GetGIMovement())
	{
		Move->bWantsWalk = bOn;
	}
}

void AGIPlayerCharacter::UpdateFootIK(float DeltaSeconds)
{
	// Plant each foot on the real step geometry (the ghats are all steps). Traces use complex collision
	// so we hit the stone treads, not the smooth ramp the capsule walks on.
	const UGICharacterMovement* Move = GetGIMovement();
	const bool bActive = Move && Move->IsMovingOnGround() && !IsRiding() && !bDead && Move->GetWaterDepth() < 60.f;
	float TargetL = 0.f, TargetR = 0.f;
	if (bActive)
	{
		const float HalfH = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const float BaseZ = GetActorLocation().Z - HalfH;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(GIFootIK), true, this);
		auto Probe = [&](FName Bone) -> float
		{
			if (GetMesh()->GetBoneIndex(Bone) == INDEX_NONE)
			{
				return 0.f;
			}
			const FVector F = GetMesh()->GetSocketLocation(Bone);
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByChannel(Hit, FVector(F.X, F.Y, BaseZ + 55.f), FVector(F.X, F.Y, BaseZ - 65.f), ECC_Visibility, Q))
			{
				return FMath::Clamp(Hit.ImpactPoint.Z - BaseZ, -50.f, 50.f);
			}
			return 0.f;
		};
		TargetL = Probe(TEXT("LeftFoot"));
		TargetR = Probe(TEXT("RightFoot"));
	}
	FootOffL = FMath::FInterpTo(FootOffL, TargetL, DeltaSeconds, 14.f);
	FootOffR = FMath::FInterpTo(FootOffR, TargetR, DeltaSeconds, 14.f);
	const float Speed = GetVelocity().Size2D();
	IKAlpha = FMath::FInterpTo(IKAlpha, bActive ? FMath::GetMappedRangeValueClamped(FVector2D(150.f, 450.f), FVector2D(1.f, 0.55f), Speed) : 0.f, DeltaSeconds, 8.f);
	if (UGIAnimInstance* Anim = GetGIAnim())
	{
		Anim->Params.FootOffsetL = FootOffL;
		Anim->Params.FootOffsetR = FootOffR;
		Anim->Params.PelvisOffset = FMath::Min3(FootOffL, FootOffR, 0.f);
		Anim->Params.IKAlpha = IKAlpha;
	}
}

void AGIPlayerCharacter::UpdateCameraFeel(float DeltaSeconds)
{
	// Lean into turns, proportional to yaw rate and speed.
	const float Yaw = GetActorRotation().Yaw;
	const float YawRate = FMath::FindDeltaAngleDegrees(LastYaw, Yaw) / FMath::Max(DeltaSeconds, 1e-3f);
	LastYaw = Yaw;
	const float Speed = GetVelocity().Size2D();
	const float WantLean = FMath::Clamp(YawRate * Speed * 0.00009f, -9.f, 9.f);
	Lean = FMath::FInterpTo(Lean, IsSwimming() ? 0.f : WantLean, DeltaSeconds, 6.f);
	if (UGIAnimInstance* Anim = GetGIAnim())
	{
		Anim->Params.LeanRoll = Lean;
	}
	// Sprint FOV kick.
	const UGICharacterMovement* Move = GetGIMovement();
	const bool bSprinting = Move && Move->bWantsSprint && Speed > 380.f && Move->IsMovingOnGround();
	FollowCamera->SetFieldOfView(FMath::FInterpTo(FollowCamera->FieldOfView, BaseFOV + (bSprinting ? 6.f : 0.f), DeltaSeconds, 4.f));
	// Fade the player out when the camera is squeezed against them (tight spots on the ghats).
	const float CamDist = FVector::Dist(FollowCamera->GetComponentLocation(), GetActorLocation() + FVector(0, 0, 40.f));
	const bool bHide = CamDist < 60.f && !IsRiding();
	if (bHide != bOwnerHidden)
	{
		bOwnerHidden = bHide;
		GetMesh()->SetVisibility(!bHide, true);
		if (bNoBox)
		{
			DeliveryBox->SetVisibility(false);
		}
		GetMesh()->bCastHiddenShadow = true;
		DeliveryBox->bCastHiddenShadow = true;
	}
}

void AGIPlayerCharacter::InputDive(bool bOn)
{
	if (UGICharacterMovement* Move = GetGIMovement())
	{
		Move->bWantsDive = bOn;
	}
}

void AGIPlayerCharacter::UpdateWater(float DeltaSeconds)
{
	const UGICharacterMovement* Move = GetGIMovement();
	if (!Move || IsRiding())
	{
		return;
	}
	float Drain = 0.f;
	if (Move->IsSurfaceSwimming())
	{
		Drain = SwimDrainPerSecond * (Move->IsUnderwater() ? 2.5f : 1.f);
	}
	else if (Move->IsWading())
	{
		Drain = WadeDrainPerSecond;
	}
	if (Drain > 0.f)
	{
		Health = FMath::Max(0.f, Health - Drain * DeltaSeconds);
		DrainAccumulator += Drain * DeltaSeconds;
		if (DrainAccumulator >= 10.f)
		{
			DrainAccumulator -= 10.f;
			OnPopup.Broadcast(LOCTEXT("HpMinus10", "HP -10"));
		}
		if (Health <= 0.f)
		{
			Die();
		}
	}
}

void AGIPlayerCharacter::UpdateAnimation(float DeltaSeconds)
{
	UGIAnimInstance* Anim = GetGIAnim();
	const UGICharacterMovement* Move = GetGIMovement();
	if (!Anim || !Move)
	{
		return;
	}
	const bool bSwim = Move->IsSurfaceSwimming();
	const UGIAssetSettings& AS = UGIAssetSettings::Get();
	if (bSwim && !bWasSwimming)
	{
		if (USoundBase* S = AS.Splash.LoadSynchronous())
		{
			UGameplayStatics::PlaySoundAtLocation(this, S, GetActorLocation());
		}
	}
	bWasSwimming = bSwim;
	if (bSwim && GetVelocity().Size2D() > 80.f)
	{
		StrokeTimer -= DeltaSeconds;
		if (StrokeTimer <= 0.f)
		{
			StrokeTimer = 0.68f;
			if (USoundBase* S = AS.SwimStroke.LoadSynchronous())
			{
				UGameplayStatics::PlaySoundAtLocation(this, S, GetActorLocation(), 0.7f, FMath::FRandRange(0.9f, 1.1f));
			}
		}
	}
	Anim->Params.Speed = GetVelocity().Size2D();
	Anim->Params.VerticalSpeed = GetVelocity().Z;
	Anim->Params.bInAir = Move->IsFalling();
	Anim->Params.MeshBaseRotation = MeshBaseRotation;
	PickUpTimer = FMath::Max(0.f, PickUpTimer - DeltaSeconds);
	if (ActionTimer > 0.f)
	{
		ActionTimer = FMath::Max(0.f, ActionTimer - DeltaSeconds);
		if (ActionTimer <= 0.f && HandProp)
		{
			HandProp->SetVisibility(false);
		}
	}
	if (bDead)
	{
		Anim->Params.Mode = EGIPoseMode::Dead;
	}
	else if (ActionTimer > 0.f)
	{
		Anim->Params.Mode = ActionMode;
		Anim->Params.ActionAlpha = 1.f - ActionTimer / FMath::Max(ActionDuration, 0.01f);
	}
	else if (PickUpTimer > 0.f)
	{
		Anim->Params.Mode = EGIPoseMode::PickUp;
	}
	else if (Move->IsClimbingOut())
	{
		Anim->Params.Mode = EGIPoseMode::ClimbOut;
		Anim->Params.ActionAlpha = Move->GetClimbAlpha();
	}
	else if (IsRiding())
	{
		Anim->Params.Mode = EGIPoseMode::RideBike;
		Anim->Params.bInAir = false;
	}
	else if (bSwim)
	{
		Anim->Params.Mode = EGIPoseMode::Swim;
	}
	else if (Move->IsWading() && Move->GetWaterDepth() > 70.f)
	{
		Anim->Params.Mode = EGIPoseMode::Wade;
	}
	else
	{
		Anim->Params.Mode = EGIPoseMode::Locomotion;
	}

	// Lay the body down in the water while swimming.
	SwimBlend = FMath::FInterpTo(SwimBlend, bSwim ? 1.f : 0.f, DeltaSeconds, 4.f);
	if (!IsRiding())
	{
		if (UGIAnimInstance::HasSwimClip())
		{
			// The clip lies prone around standing hip height: lift it only so far that the back is at the
			// waterline (head, shoulders and the food box above, body in the water - like the clip).
			const FVector Loc = MeshBaseLocation + FVector(0.f, 0.f, 38.f * SwimBlend);
			GetMesh()->SetRelativeLocationAndRotation(Loc, MeshBaseRotation);
		}
		else
		{
			const FQuat Prone = FQuat(FVector::RightVector, FMath::DegreesToRadians(78.f)) * MeshBaseRotation;
			const FQuat Rot = FQuat::Slerp(MeshBaseRotation, Prone, SwimBlend);
			const FVector ProneLoc = -Prone.RotateVector(FVector(0.f, 0.f, 105.f)) + FVector(0.f, 0.f, 12.f);
			GetMesh()->SetRelativeLocationAndRotation(FMath::Lerp(MeshBaseLocation, ProneLoc, SwimBlend), Rot);
		}
	}

	const float WantArm = bSwim ? DefaultArmLength + 110.f : DefaultArmLength;
	CameraBoom->TargetArmLength = FMath::FInterpTo(CameraBoom->TargetArmLength, WantArm, DeltaSeconds, 3.f);
}

AGIBike* AGIPlayerCharacter::FindNearbyBike(float MaxDist) const
{
	AGIBike* Best = nullptr;
	float BestD = MaxDist * MaxDist;
	for (TActorIterator<AGIBike> It(GetWorld()); It; ++It)
	{
		const float D = FVector::DistSquared(It->GetActorLocation(), GetActorLocation());
		if (D < BestD && !It->HasRider())
		{
			BestD = D;
			Best = *It;
		}
	}
	return Best;
}

AGITrain* AGIPlayerCharacter::FindNearbyTrain(FVector& OutRoofPoint) const
{
	for (TActorIterator<AGITrain> It(GetWorld()); It; ++It)
	{
		if (It->GetRoofPointNear(GetActorLocation(), 950.f, OutRoofPoint))
		{
			return *It;
		}
	}
	return nullptr;
}

void AGIPlayerCharacter::UpdateInteraction()
{
	Prompt = FText::GetEmpty();
	if (IsRiding())
	{
		Prompt = LOCTEXT("PromptExitBike", "[F / Y] Gaadi se utro");
		return;
	}
	if (IsSwimming())
	{
		return;
	}
	if (FindNearbyBike(380.f))
	{
		Prompt = LOCTEXT("PromptBike", "[F / Y] Gaadi chalao");
		return;
	}
	for (TActorIterator<AGITraffic> It(GetWorld()); It; ++It)
	{
		if (It->HasVehicleNear(GetActorLocation(), 420.f))
		{
			Prompt = LOCTEXT("PromptTakeVehicle", "[F / Y] Gaadi le lo");
			return;
		}
	}
	for (TActorIterator<AGIChaiStall> It(GetWorld()); It; ++It)
	{
		if (It->CanServe(this))
		{
			Prompt = LOCTEXT("PromptChai", "[E / X] Cutting chai lo (\u20B910)");
			return;
		}
	}
	for (TActorIterator<AGICricketGame> It(GetWorld()); It; ++It)
	{
		if (It->WantsBallFromPlayer(this))
		{
			Prompt = LOCTEXT("PromptBall", "[E / X] Ball wapas phenko");
			return;
		}
	}
	FVector Roof;
	if (AGITrain* Train = FindNearbyTrain(Roof))
	{
		if (GetActorLocation().Z < Roof.Z - 150.f)
		{
			Prompt = LOCTEXT("PromptTrain", "[E / X] Train pe chadho");
			return;
		}
	}
	const int32 Ferry = FerryDirection();
	if (Ferry > 0)
	{
		Prompt = LOCTEXT("PromptFerryEast", "[E / X] Naav se Dashashwamedh Ghat (\u20B920)");
	}
	else if (Ferry < 0)
	{
		Prompt = LOCTEXT("PromptFerryWest", "[E / X] Naav se wapas gaon ke ghat (\u20B920)");
	}
}

int32 AGIPlayerCharacter::FerryDirection() const
{
	const FVector L = GetActorLocation();
	if (IsSwimming() || FMath::Abs(L.X) > 14000.f || !AGIRiver::Get(this))   // ferries only where there is a river
	{
		return 0;
	}
	if (L.Y > -200.f && L.Y < 900.f && L.Z < 500.f)
	{
		return 1;
	}
	if (L.Y < -15000.f && L.Y > -16600.f && L.Z < 500.f)
	{
		return -1;
	}
	return 0;
}

void AGIPlayerCharacter::TakeFerry(int32 Direction)
{
	if (Money < 20)
	{
		OnPopup.Broadcast(LOCTEXT("NoMoney", "Paise nahi hain! Tairke jao."));
		return;
	}
	Money -= 20;
	OnPopup.Broadcast(LOCTEXT("FerryPaid", "-\u20B920  Naav wala"));
	const FVector Dest = Direction > 0 ? FVector(GetActorLocation().X, -16300.f, 700.f) : FVector(GetActorLocation().X, 1500.f, 900.f);
	SetActorLocation(Dest, false, nullptr, ETeleportType::TeleportPhysics);
	SetActorRotation(FRotator(0.f, Direction > 0 ? -90.f : 90.f, 0.f));
	GetCharacterMovement()->SetMovementMode(MOVE_Falling);
}

void AGIPlayerCharacter::InputMove(const FInputActionValue& Value)
{
	if (bDead || !Controller || PickUpTimer > 0.f || ActionTimer > 0.f)
	{
		return;
	}
	const FVector2D V = Value.Get<FVector2D>();
	const FRotator YawRot(0.f, Controller->GetControlRotation().Yaw, 0.f);
	AddMovementInput(FRotationMatrix(YawRot).GetUnitAxis(EAxis::X), V.Y);
	AddMovementInput(FRotationMatrix(YawRot).GetUnitAxis(EAxis::Y), V.X);
}

void AGIPlayerCharacter::InputLook(const FInputActionValue& Value)
{
	// Clamp single-frame spikes (cursor warps over a remote stream without pointer lock); a stick
	// never exceeds 1 and a real mouse flick stays under this (~285 px in one frame).
	const FVector2D Raw = Value.Get<FVector2D>();
	const FVector2D V(FMath::Clamp(Raw.X, -20.f, 20.f), FMath::Clamp(Raw.Y, -20.f, 20.f));
	float Sens = 1.f;
	bool bInvert = false;
	if (const UGIGameUserSettings* S = UGIGameUserSettings::Get())
	{
		Sens = S->MouseSensitivity;
		bInvert = S->bInvertY;
	}
	AddControllerYawInput(V.X * Sens);
	AddControllerPitchInput((bInvert ? -V.Y : V.Y) * Sens);
}

void AGIPlayerCharacter::InputJumpStart()
{
	if (!bDead && !IsSwimming())
	{
		Jump();
	}
}

void AGIPlayerCharacter::InputJumpStop()
{
	StopJumping();
}

void AGIPlayerCharacter::InputSprint(bool bOn)
{
	if (UGICharacterMovement* Move = GetGIMovement())
	{
		Move->bWantsSprint = bOn;
	}
}

void AGIPlayerCharacter::InputInteract()
{
	if (bDead || IsRiding() || ActionTimer > 0.f)
	{
		return;
	}
	for (TActorIterator<AGICricketGame> It(GetWorld()); It; ++It)
	{
		if (It->WantsBallFromPlayer(this))
		{
			It->PlayerReturnsBall(this);
			return;
		}
	}
	for (TActorIterator<AGIChaiStall> It(GetWorld()); It; ++It)
	{
		if (It->CanServe(this))
		{
			It->Serve(this);
			return;
		}
	}
	if (const int32 Ferry = FerryDirection())
	{
		TakeFerry(Ferry);
		return;
	}
	FVector Roof;
	if (AGITrain* Train = FindNearbyTrain(Roof))
	{
		if (GetActorLocation().Z < Roof.Z - 150.f)
		{
			// Climb onto the roof (the train keeps moving; character movement follows its base).
			SetActorLocation(Roof + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 10.f), false, nullptr, ETeleportType::TeleportPhysics);
			GetCharacterMovement()->SetMovementMode(MOVE_Falling);
			OnPopup.Broadcast(LOCTEXT("OnTrain", "Train ki chhat pe!"));
		}
	}
}

void AGIPlayerCharacter::InputVehicle()
{
	if (bDead)
	{
		return;
	}
	if (IsRiding())
	{
		RidingBike->Dismount();
		return;
	}
	if (AGIBike* Bike = FindNearbyBike(380.f))
	{
		Bike->Mount(this);
		return;
	}
	// Flag down / take over a passing auto, car or bike: its people get off and you drive.
	for (TActorIterator<AGITraffic> It(GetWorld()); It; ++It)
	{
		FTransform Xf;
		UStaticMesh* Mesh = nullptr;
		float MeshYaw = 0.f;
		bool bFour = false;
		if (It->TakeVehicle(GetActorLocation(), 420.f, Xf, Mesh, MeshYaw, bFour))
		{
			Xf.AddToTranslation(FVector(0.f, 0.f, 80.f));
			AGIBike* V = GetWorld()->SpawnActorDeferred<AGIBike>(AGIBike::StaticClass(), Xf, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
			if (V)
			{
				V->MeshOverride = Mesh;
				V->MeshYawOverride = MeshYaw;
				V->bFourWheeler = bFour;
				V->FinishSpawning(Xf);
				V->Mount(this);
				OnPopup.Broadcast(LOCTEXT("TookVehicle", "\"Arre! Meri gaadi!\""));
			}
			return;
		}
	}
}

void AGIPlayerCharacter::AttachToBike(AGIBike* Bike)
{
	RidingBike = Bike;
	GetCharacterMovement()->DisableMovement();
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AttachToComponent(Bike->GetSeatComponent(), FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	// Capsule centre sits at the seat point: put the pelvis there.
	GetMesh()->SetRelativeLocationAndRotation(FVector(MeshBaseLocation.X, MeshBaseLocation.Y, -UGIAnimInstance::GetSitPelvisHeight()), MeshBaseRotation);
}

void AGIPlayerCharacter::DetachFromBike()
{
	AGIBike* Bike = RidingBike;
	RidingBike = nullptr;
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	if (Bike)
	{
		const FVector Side = Bike->GetActorRightVector() * -110.f;
		SetActorLocationAndRotation(Bike->GetActorLocation() + Side + FVector(0, 0, 100.f), FRotator(0.f, Bike->GetActorRotation().Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	}
	GetCharacterMovement()->SetMovementMode(MOVE_Falling);
}

void AGIPlayerCharacter::PlayAction(EGIPoseMode Mode, float Duration, UStaticMesh* Prop)
{
	ActionMode = Mode;
	ActionDuration = Duration;
	ActionTimer = Duration;
	GetCharacterMovement()->StopMovementImmediately();
	if (Prop)
	{
		if (!HandProp)
		{
			HandProp = NewObject<UStaticMeshComponent>(this);
			HandProp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			HandProp->SetupAttachment(GetMesh(), TEXT("hand_r"));
			HandProp->RegisterComponent();
		}
		HandProp->SetStaticMesh(Prop);
		HandProp->SetRelativeLocationAndRotation(FVector(4.f, 7.f, 0.f), FRotator::ZeroRotator);
		HandProp->SetVisibility(true);
	}
}

void AGIPlayerCharacter::PlayPickUp()
{
	PickUpTimer = 1.6f;
	GetCharacterMovement()->StopMovementImmediately();
}

void AGIPlayerCharacter::AddMoney(int32 Amount)
{
	Money += Amount;
	const FText Sign = Amount >= 0 ? FText::FromString(TEXT("+")) : FText::FromString(TEXT("-"));
	OnPopup.Broadcast(FText::Format(LOCTEXT("MoneyPopup", "{0}₹{1}"), Sign, FText::AsNumber(FMath::Abs(Amount))));
}

void AGIPlayerCharacter::ApplyDamageSimple(float Amount, bool bShowPopup)
{
	if (bDead)
	{
		return;
	}
	Health = FMath::Max(0.f, Health - Amount);
	if (bShowPopup)
	{
		OnPopup.Broadcast(FText::Format(LOCTEXT("HpPopup", "HP -{0}"), FText::AsNumber(FMath::RoundToInt(Amount))));
	}
	if (Health <= 0.f)
	{
		Die();
	}
}

void AGIPlayerCharacter::Die()
{
	if (bDead)
	{
		return;
	}
	if (IsRiding())
	{
		RidingBike->Dismount();
	}
	bDead = true;
	DeadTimer = 4.f;
	Health = 0.f;
	GetCharacterMovement()->DisableMovement();
}

void AGIPlayerCharacter::Respawn()
{
	bDead = false;
	Health = MaxHealth;
	DrainAccumulator = 0.f;
	SetActorTransform(RespawnTransform, false, nullptr, ETeleportType::TeleportPhysics);
	GetCharacterMovement()->SetMovementMode(MOVE_Falling);
	if (Controller)
	{
		Controller->SetControlRotation(RespawnTransform.Rotator());
	}
	const int32 Bill = FMath::Min(Money, 100);
	if (Bill > 0)
	{
		Money -= Bill;
		OnPopup.Broadcast(FText::Format(LOCTEXT("HospitalBill", "Hospital ka bill: -₹{0}"), FText::AsNumber(Bill)));
	}
}

#undef LOCTEXT_NAMESPACE
