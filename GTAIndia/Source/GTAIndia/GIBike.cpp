#include "GIBike.h"
#include "GIAnimInstance.h"
#include "GIAssetSettings.h"
#include "GIPlayerCharacter.h"
#include "GIRiver.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"

#define LOCTEXT_NAMESPACE "GTAIndia"

static constexpr float GroundClearance = 18.f;

AGIBike::AGIBike()
{
	PrimaryActorTick.bCanEverTick = true;
	AutoPossessAI = EAutoPossessAI::Disabled;

	Collision = CreateDefaultSubobject<UBoxComponent>(TEXT("Collision"));
	Collision->SetBoxExtent(FVector(95.f, 32.f, 50.f));
	Collision->SetCollisionProfileName(TEXT("Vehicle"));
	RootComponent = Collision;

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Collision);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Seat = CreateDefaultSubobject<USceneComponent>(TEXT("Seat"));
	Seat->SetupAttachment(Collision);
	Seat->SetRelativeLocation(FVector(-10.f, 0.f, 20.f)); // pelvis ~88 cm above the ground

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(Collision);
	CameraBoom->TargetArmLength = 440.f;
	CameraBoom->SocketOffset = FVector(0.f, 0.f, 125.f);
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 8.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);

	EngineAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("EngineAudio"));
	EngineAudio->SetupAttachment(Collision);
	EngineAudio->bAutoActivate = false;
}

void AGIBike::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyMeshSettings();
}

void AGIBike::ApplyMeshSettings()
{
	const UGIAssetSettings& S = UGIAssetSettings::Get();
	if (UStaticMesh* Mesh = S.BikeMesh.LoadSynchronous())
	{
		Body->SetStaticMesh(Mesh);
		Body->SetRelativeRotation(FRotator(0.f, S.BikeMeshYaw, 0.f));
		Body->SetRelativeLocation(FVector(0.f, 0.f, -(Collision->GetUnscaledBoxExtent().Z + GroundClearance)) + S.BikeMeshOffset);
		Body->SetRelativeScale3D(FVector(S.BikeMeshScale));
	}
}

void AGIBike::BeginPlay()
{
	Super::BeginPlay();
	ApplyMeshSettings();
	BuildPassengers();
	if (USoundBase* Engine = UGIAssetSettings::Get().BikeEngine.LoadSynchronous())
	{
		EngineAudio->SetSound(Engine);
		EngineAudio->AttenuationSettings = UGIAssetSettings::MakeAttenuation(this, 400.f, 4000.f);
	}
}

void AGIBike::BuildPassengers()
{
	const TArray<FGICharacterLook>& Looks = UGIAssetSettings::Get().PedestrianLooks;
	if (Looks.Num() == 0)
	{
		return;
	}
	for (int32 i = 0; i < StackedPassengers; ++i)
	{
		USkeletalMesh* Mesh = Looks[(i * 3 + 1) % Looks.Num()].Mesh.LoadSynchronous();
		if (!Mesh)
		{
			continue;
		}
		USkeletalMeshComponent* P = NewObject<USkeletalMeshComponent>(this);
		P->SetupAttachment(Seat);
		P->RegisterComponent();
		P->SetSkeletalMesh(Mesh);
		P->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
		P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		// Stack: first behind the rider, then climbing up on shoulders.
		const FVector Offset = i == 0 ? FVector(-38.f, 0.f, 0.f) : FVector(-30.f + 4.f * i, 0.f, 72.f * i);
		P->SetRelativeLocationAndRotation(Offset + FVector(0.f, 0.f, -UGIAnimInstance::GetSitPelvisHeight()), FRotator(0.f, -90.f, 0.f));
		if (UGIAnimInstance* Anim = Cast<UGIAnimInstance>(P->GetAnimInstance()))
		{
			Anim->Params.Mode = (i == StackedPassengers - 1 && i > 0) ? EGIPoseMode::SitArmsOut : EGIPoseMode::Sit;
			Anim->Params.MeshBaseRotation = FRotator(0.f, -90.f, 0.f).Quaternion();
			Anim->Params.TimeOffset = 1.3f * i;
		}
		Passengers.Add(P);
	}
}

bool AGIBike::GroundAt(const FVector& Point, FHitResult& Hit) const
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GIBikeGround), false, this);
	if (Rider)
	{
		Params.AddIgnoredActor(Rider);
	}
	return GetWorld()->LineTraceSingleByChannel(Hit, Point + FVector(0, 0, 120.f), Point - FVector(0, 0, 400.f), ECC_Visibility, Params);
}

void AGIBike::Mount(AGIPlayerCharacter* Character)
{
	if (!Character || Rider)
	{
		return;
	}
	APlayerController* PC = Cast<APlayerController>(Character->GetController());
	Rider = Character;
	Character->AttachToBike(this);
	if (PC)
	{
		const FRotator ControlRot = PC->GetControlRotation();
		PC->Possess(this);
		PC->SetControlRotation(FRotator(ControlRot.Pitch, GetActorRotation().Yaw, 0.f));
	}
}

void AGIBike::Dismount()
{
	if (!Rider)
	{
		return;
	}
	AGIPlayerCharacter* Char = Rider;
	APlayerController* PC = Cast<APlayerController>(GetController());
	Rider = nullptr;
	Char->DetachFromBike();
	if (PC)
	{
		PC->Possess(Char);
	}
	ThrottleInput = SteerInput = 0.f;
	bBrake = true;
}

void AGIBike::NotifyLookInput()
{
	LastLookTime = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
}

void AGIBike::Honk()
{
	if (Rider)
	{
		if (USoundBase* Horn = UGIAssetSettings::Get().BikeHorn.LoadSynchronous())
		{
			UGameplayStatics::PlaySoundAtLocation(this, Horn, GetActorLocation());
		}
		else
		{
			Rider->OnPopup.Broadcast(LOCTEXT("Horn", "Pom Pom!"));
		}
	}
}

void AGIBike::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.05f);

	const float Throttle = Rider ? ThrottleInput : 0.f;
	const float SteerIn = Rider ? SteerInput : 0.f;
	const bool bBraking = !Rider || bBrake;

	// Longitudinal.
	if (bBraking)
	{
		Speed = FMath::FInterpConstantTo(Speed, 0.f, Dt, BrakeDeceleration);
	}
	if (Throttle > 0.05f)
	{
		const float Accel = Speed < 0.f ? BrakeDeceleration : Acceleration * (1.f - 0.6f * FMath::Clamp(Speed / MaxSpeed, 0.f, 1.f));
		Speed = FMath::Min(Speed + Accel * Throttle * Dt, MaxSpeed);
	}
	else if (Throttle < -0.05f)
	{
		const float Accel = Speed > 0.f ? BrakeDeceleration : Acceleration * 0.5f;
		Speed = FMath::Max(Speed + Accel * Throttle * Dt, -MaxReverseSpeed);
	}
	else
	{
		Speed = FMath::FInterpConstantTo(Speed, 0.f, Dt, 250.f); // rolling drag
	}

	// Steering + lean.
	SteerSmoothed = FMath::FInterpTo(SteerSmoothed, SteerIn, Dt, 6.f);
	const float SpeedAlpha = FMath::Clamp(FMath::Abs(Speed) / 400.f, 0.f, 1.f);
	const float HighSpeedDamp = 1.f - 0.5f * FMath::Clamp(FMath::Abs(Speed) / MaxSpeed, 0.f, 1.f);
	const float YawDelta = SteerSmoothed * MaxYawRate * SpeedAlpha * HighSpeedDamp * Dt * FMath::Sign(Speed == 0.f ? 1.f : Speed);
	const float TargetLean = SteerSmoothed * 26.f * FMath::Clamp(FMath::Abs(Speed) / 1400.f, 0.f, 1.f);
	Lean = FMath::FInterpTo(Lean, TargetLean, Dt, 5.f);

	FRotator Rot = GetActorRotation();
	Rot.Yaw += YawDelta;

	// Horizontal move with sweep.
	const FVector Fwd = FRotator(0.f, Rot.Yaw, 0.f).Vector();
	FHitResult Hit;
	AddActorWorldOffset(Fwd * Speed * Dt, true, &Hit);
	if (Hit.IsValidBlockingHit())
	{
		const float Impact = FMath::Abs(Speed);
		if (Impact > 1300.f && Rider)
		{
			Rider->ApplyDamageSimple(FMath::RoundToFloat(Impact / 150.f));
		}
		// Slide along walls, lose speed.
		const FVector Slide = FVector::VectorPlaneProject(Fwd * Speed * Dt * (1.f - Hit.Time), Hit.ImpactNormal);
		AddActorWorldOffset(FVector(Slide.X, Slide.Y, 0.f), true);
		Speed *= 0.35f;
	}

	// Ground follow using front / rear wheel contact points.
	const FVector Loc = GetActorLocation();
	FHitResult Front, Rear;
	const bool bF = GroundAt(Loc + Fwd * 65.f, Front);
	const bool bR = GroundAt(Loc - Fwd * 65.f, Rear);
	const float HalfH = Collision->GetScaledBoxExtent().Z;
	if (bF || bR)
	{
		const float GroundZ = bF && bR ? (Front.ImpactPoint.Z + Rear.ImpactPoint.Z) * 0.5f : (bF ? Front.ImpactPoint.Z : Rear.ImpactPoint.Z);
		const float TargetZ = GroundZ + HalfH + GroundClearance;
		if (Loc.Z - TargetZ > 25.f && VerticalVelocity <= 0.f)
		{
			VerticalVelocity -= 980.f * Dt;
			SetActorLocation(FVector(Loc.X, Loc.Y, FMath::Max(TargetZ, Loc.Z + VerticalVelocity * Dt)));
		}
		else
		{
			VerticalVelocity = 0.f;
			SetActorLocation(FVector(Loc.X, Loc.Y, FMath::FInterpTo(Loc.Z, TargetZ, Dt, 18.f)));
		}
		if (bF && bR)
		{
			const float TargetPitch = FMath::RadiansToDegrees(FMath::Atan2(Front.ImpactPoint.Z - Rear.ImpactPoint.Z, 130.f));
			Pitch = FMath::FInterpTo(Pitch, TargetPitch, Dt, 10.f);
		}
	}
	else
	{
		VerticalVelocity -= 980.f * Dt;
		SetActorLocation(Loc + FVector(0, 0, VerticalVelocity * Dt));
	}

	SetActorRotation(FRotator(Pitch, Rot.Yaw, Lean));

	// Engine note follows speed.
	if (EngineAudio->Sound)
	{
		if (Rider && !EngineAudio->IsPlaying())
		{
			EngineAudio->Play();
		}
		else if (!Rider && EngineAudio->IsPlaying())
		{
			EngineAudio->FadeOut(0.6f, 0.f);
		}
		const float Rev = FMath::Clamp(FMath::Abs(Speed) / MaxSpeed, 0.f, 1.f);
		EngineAudio->SetPitchMultiplier(0.75f + Rev * 1.35f + (ThrottleInput > 0.1f ? 0.1f : 0.f));
		EngineAudio->SetVolumeMultiplier(0.45f + Rev * 0.4f);
	}

	// Drowned in the river?
	if (AGIRiver* River = AGIRiver::Get(this))
	{
		const FVector L = GetActorLocation();
		if (River->IsInWaterArea(L) && L.Z < River->GetWaterZ() - 20.f)
		{
			Speed = 0.f;
			if (Rider)
			{
				AGIPlayerCharacter* R = Rider;
				Dismount();
				R->OnPopup.Broadcast(LOCTEXT("BikeSank", "Bike Ganga mein doob gayi!"));
			}
		}
	}

	// Camera: swing behind the bike when the player isn't looking around.
	if (Rider)
	{
		if (APlayerController* PC = Cast<APlayerController>(GetController()))
		{
			if (GetWorld()->GetTimeSeconds() - LastLookTime > 1.2f && FMath::Abs(Speed) > 300.f)
			{
				FRotator CR = PC->GetControlRotation();
				CR.Yaw = FMath::FixedTurn(CR.Yaw, GetActorRotation().Yaw, 90.f * Dt);
				CR.Pitch = FMath::FixedTurn(CR.Pitch, -12.f, 30.f * Dt);
				PC->SetControlRotation(CR);
			}
		}
	}
}

#undef LOCTEXT_NAMESPACE
