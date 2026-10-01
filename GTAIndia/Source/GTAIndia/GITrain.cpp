#include "GITrain.h"
#include "GIAnimBudget.h"
#include "GIPlayerCharacter.h"
#include "GIAnimInstance.h"
#include "GIAssetSettings.h"
#include "GIGameUserSettings.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

AGITrain::AGITrain()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Movable);
}

void AGITrain::BuildCars()
{
	for (UStaticMeshComponent* C : Cars)
	{
		if (C)
		{
			C->DestroyComponent();
		}
	}
	Cars.Reset();

	const UGIAssetSettings& S = UGIAssetSettings::Get();
	TArray<UStaticMesh*> CarMeshes;
	for (const TSoftObjectPtr<UStaticMesh>& P : S.TrainCarMeshes)
	{
		if (UStaticMesh* M = P.LoadSynchronous())
		{
			CarMeshes.Add(M);
		}
	}
	UStaticMesh* Engine = S.TrainEngineMesh.LoadSynchronous();
	if (CarMeshes.Num() == 0)
	{
		return;
	}

	const FRotator MeshRot(0.f, S.TrainMeshYaw, 0.f);
	const FVector Scale(S.TrainMeshScale);
	const FBox B = CarMeshes[0]->GetBoundingBox();
	const FVector Size = MeshRot.RotateVector(B.GetSize() * Scale).GetAbs();
	CarLength = Size.X;
	CarWidth = Size.Y;
	CarHeight = Size.Z;

	float X = 0.f;
	const int32 Total = NumCars + (Engine ? 1 : 0);
	for (int32 i = 0; i < Total; ++i)
	{
		UStaticMesh* Mesh = (Engine && i == 0) ? Engine : CarMeshes[i % CarMeshes.Num()];
		const FBox MB = Mesh->GetBoundingBox();
		const FVector MSize = MeshRot.RotateVector(MB.GetSize() * Scale).GetAbs();
		// Centre the mesh on its car slot, bottom at local Z = 0. Cars trail behind the lead (-X).
		const FVector Center = MeshRot.RotateVector(MB.GetCenter() * Scale);
		const float Bottom = MeshRot.RotateVector(MB.Min * Scale).Z;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("Car_%d"), i));
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(RootComponent);
		C->SetStaticMesh(Mesh);
		C->SetRelativeScale3D(Scale);
		C->SetRelativeRotation(MeshRot);
		C->SetRelativeLocation(FVector(-X - MSize.X * 0.5f - Center.X, -Center.Y, -FMath::Min(Bottom, MeshRot.RotateVector(MB.Max * Scale).Z)));
		C->SetCollisionProfileName(TEXT("BlockAll"));
		C->SetCanEverAffectNavigation(false);
		C->RegisterComponent();
		Cars.Add(C);
		X += MSize.X + CarGap;
	}
	TrainLength = X;
}

void AGITrain::BeginPlay()
{
	Super::BeginPlay();
	BuildCars();
	BuildRiders();
	if (USoundBase* Loop = UGIAssetSettings::Get().TrainLoop.LoadSynchronous())
	{
		Rumble = NewObject<UAudioComponent>(this);
		Rumble->SetupAttachment(Cars.Num() > 0 ? static_cast<USceneComponent*>(Cars[Cars.Num() / 2].Get()) : RootComponent.Get());
		Rumble->SetSound(Loop);
		Rumble->AttenuationSettings = UGIAssetSettings::MakeAttenuation(this, 2500.f, 15000.f);
		Rumble->RegisterComponent();
		Rumble->Play();
	}
}

void AGITrain::BuildRiders()
{
	const TArray<FGICharacterLook>& Looks = UGIAssetSettings::Get().PedestrianLooks;
	if (Looks.Num() == 0 || Cars.Num() == 0)
	{
		return;
	}
	int32 Budget = 60;
	if (const UGIGameUserSettings* GS = UGIGameUserSettings::Get())
	{
		Budget = FMath::RoundToInt(GS->GetCrowdBudget() * CrowdShare);
	}
	FRandomStream Rand(1234);
	const int32 PerCar = FMath::Max(1, Budget / Cars.Num());

	for (int32 CarIdx = 0; CarIdx < Cars.Num(); ++CarIdx)
	{
		UStaticMeshComponent* Car = Cars[CarIdx];
		const FBox CarBox = Car->Bounds.GetBox(); // world
		const FVector LocalCenter = GetActorTransform().InverseTransformPosition(CarBox.GetCenter());
		// Real roof surface (the bounds include vents, footsteps and the cab pantograph): trace the car.
		auto RoofZAt = [this, Car, &CarBox](float LocalX, float LocalY, float& OutZ) -> bool
		{
			const FVector W = GetActorTransform().TransformPosition(FVector(LocalX, LocalY, 0.f));
			FHitResult Hit;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(GITrainRoof), true);
			if (Car->LineTraceComponent(Hit, FVector(W.X, W.Y, CarBox.Max.Z + 200.f), FVector(W.X, W.Y, CarBox.Min.Z), Q))
			{
				OutZ = GetActorTransform().InverseTransformPosition(Hit.ImpactPoint).Z;
				return true;
			}
			return false;
		};
		float Roof = GetActorTransform().InverseTransformPosition(CarBox.Max).Z;
		RoofZAt(LocalCenter.X + 120.f, LocalCenter.Y, Roof);
		const float HalfLen = CarBox.GetExtent().X - 150.f;
		// Body half-width at roof level: walk in from the bounds until the trace hits a surface near roof height.
		float HalfWid = CarBox.GetExtent().Y;
		for (float Y = CarBox.GetExtent().Y; Y > 60.f; Y -= 8.f)
		{
			float Z;
			if (RoofZAt(LocalCenter.X + 120.f, LocalCenter.Y + Y, Z) && Z > Roof - 70.f)
			{
				HalfWid = Y;
				break;
			}
		}

		for (int32 k = 0; k < PerCar; ++k)
		{
			const FGICharacterLook& Look = Looks[Rand.RandRange(0, Looks.Num() - 1)];
			USkeletalMesh* Mesh = Look.Mesh.LoadSynchronous();
			if (!Mesh)
			{
				continue;
			}
			USkeletalMeshComponent* P = GIAnimBudget::NewPersonComponent(this);
			P->SetupAttachment(RootComponent);
			P->RegisterComponent();
			P->SetSkeletalMesh(Mesh);
			P->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
			P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			P->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
			P->bEnableUpdateRateOptimizations = true;
			UGIAssetSettings::ApplyLookVariety(P, Look, Rand);

			EGIPoseMode Mode = EGIPoseMode::Sit;
			FVector Pos;
			float Yaw;
			const float Roll = Rand.FRand();
			const float XAlong = Rand.FRandRange(-HalfLen, HalfLen);
			const float DoorX = DoorOffsets.Num() > 0 ? DoorOffsets[Rand.RandRange(0, DoorOffsets.Num() - 1)] : CarBox.GetExtent().X - 90.f;
			if (Roll < 0.3f)
			{
				// Sitting on the roof edge, legs dangling outside.
				const float Side = Rand.FRand() < 0.5f ? -1.f : 1.f;
				// On the roof edge facing out, legs hanging over the side (like the clip).
				Pos = FVector(LocalCenter.X + XAlong, LocalCenter.Y + Side * (HalfWid - 32.f), Roof);
				Yaw = (Side > 0.f ? 90.f : -90.f) + Rand.FRandRange(-20.f, 20.f);
			}
			else if (Roll < 0.72f)
			{
				// Sitting in the middle of the roof.
				Pos = FVector(LocalCenter.X + XAlong, LocalCenter.Y + Rand.FRandRange(-HalfWid * 0.4f, HalfWid * 0.4f), Roof);
				Yaw = Rand.FRandRange(-180.f, 180.f);
				// Packed rows like the reference: mostly sitting/chatting, some standing.
				const float Lane = FMath::RoundToFloat(Rand.FRandRange(-1.f, 1.f) * 1.4f) / 1.4f;
				Pos.Y = LocalCenter.Y + Lane * HalfWid * 0.45f + Rand.FRandRange(-12.f, 12.f);
				const float R2 = Rand.FRand();
				Mode = R2 < 0.12f ? EGIPoseMode::Locomotion : (R2 < 0.2f ? EGIPoseMode::Talk : (R2 < 0.6f ? EGIPoseMode::SitTalk : EGIPoseMode::Sit));
			}
			else
			{
				const float Side = Rand.FRand() < 0.5f ? -1.f : 1.f;
				const float Floor = GetActorTransform().InverseTransformPosition(CarBox.Min).Z + 125.f;
				if (Rand.FRand() < 0.6f)
				{
					// Hanging out of an open door, holding the grab pole.
					Pos = FVector(LocalCenter.X + DoorX + Rand.FRandRange(-45.f, 45.f), LocalCenter.Y + Side * (HalfWid + 22.f), Roof - CarHeight * 0.55f - 60.f);
					Yaw = Side > 0.f ? 90.f : -90.f;
					Mode = EGIPoseMode::Hang;
				}
				else
				{
					// Standing packed in the doorway, looking out.
					Pos = FVector(LocalCenter.X + DoorX + Rand.FRandRange(-40.f, 40.f), LocalCenter.Y + Side * (HalfWid - Rand.FRandRange(25.f, 70.f)), Floor);
					Yaw = (Side > 0.f ? 90.f : -90.f) + Rand.FRandRange(-35.f, 35.f);
					Mode = Rand.FRand() < 0.5f ? EGIPoseMode::Talk : EGIPoseMode::Locomotion;
				}
			}
			if (Mode == EGIPoseMode::Sit || Mode == EGIPoseMode::SitTalk || ((Mode == EGIPoseMode::Locomotion || Mode == EGIPoseMode::Talk) && Pos.Z >= Roof - 1.f))
			{
				float Z = Roof;
				RoofZAt(Pos.X, Pos.Y, Z);
				const bool bSit = Mode == EGIPoseMode::Sit || Mode == EGIPoseMode::SitTalk;
				// Seated: pelvis on the roof (same rule as people sitting on the ghats). Standing: feet on it.
				Pos.Z = Z + (bSit ? -(UGIAnimInstance::GetSitPelvisHeight() - 12.f) : 0.f);
			}
			// Mesh faces +Y in its own space, so add the standard -90 yaw.
			const FRotator MeshRot(0.f, Yaw - 90.f, 0.f);
			P->SetRelativeLocationAndRotation(Pos, MeshRot);
			if (UGIAnimInstance* Anim = Cast<UGIAnimInstance>(P->GetAnimInstance()))
			{
				Anim->Params.Mode = Mode;
				Anim->Params.MeshBaseRotation = FRotator(0.f, -90.f, 0.f).Quaternion();
				Anim->Params.TimeOffset = Rand.FRandRange(0.f, 10.f);
			}
			Riders.Add(P);
		}
	}
}

void AGITrain::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	FVector Loc = GetActorLocation();
	Loc.X += Speed * DeltaSeconds;

	const bool bPastEnd = Speed > 0.f ? (Loc.X - TrainLength > TrackEndX) : (Loc.X + TrainLength < TrackStartX);
	if (bPastEnd)
	{
		const float NewX = Speed > 0.f ? TrackStartX : TrackEndX;
		const FVector Delta(NewX - Loc.X, 0.f, 0.f);
		// Carry the player along if they are riding the roof.
		if (ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0))
		{
			if (OwnsComponent(Player->GetMovementBase()))
			{
				Player->TeleportTo(Player->GetActorLocation() + Delta, Player->GetActorRotation());
			}
		}
		Loc.X = NewX;
	}
	SetActorLocation(Loc);

	CheckPlayerHit(DeltaSeconds);
	SignificanceTimer -= DeltaSeconds;
	if (SignificanceTimer <= 0.f)
	{
		SignificanceTimer = 0.5f;
		if (const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
		{
			if (PC->PlayerCameraManager)
			{
				const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
				const UGIGameUserSettings* GS = UGIGameUserSettings::Get();
				const float ShadowDistSq = FMath::Square(GS ? GS->GetCrowdShadowDistanceCm() : 6000.f);
				const float Cull = GS ? GS->GetCrowdCullDistanceCm() * 1.3f : 20000.f;
				for (USkeletalMeshComponent* R : Riders)
				{
					if (!R)
					{
						continue;
					}
					const bool bShadow = FVector::DistSquared(R->GetComponentLocation(), Cam) < ShadowDistSq;
					if (R->CastShadow != bShadow)
					{
						R->SetCastShadow(bShadow);
					}
					if (!FMath::IsNearlyEqual(R->CachedMaxDrawDistance, Cull))
					{
						R->SetCachedMaxDrawDistance(Cull);
					}
				}
			}
		}
	}

	HornTimer -= DeltaSeconds;
	if (HornTimer <= 0.f && Cars.Num() > 0)
	{
		HornTimer = FMath::FRandRange(14.f, 26.f);
		if (USoundBase* Horn = UGIAssetSettings::Get().TrainHorn.LoadSynchronous())
		{
			static USoundAttenuation* HornAtt = nullptr;
			if (!HornAtt)
			{
				HornAtt = UGIAssetSettings::MakeAttenuation(GetTransientPackage(), 3000.f, 30000.f);
				HornAtt->AddToRoot();
			}
			UGameplayStatics::PlaySoundAtLocation(this, Horn, Cars[0]->GetComponentLocation(), 1.f, 1.f, 0.f, HornAtt);
		}
	}
}

bool AGITrain::OwnsComponent(const UPrimitiveComponent* Comp) const
{
	return Comp && Comp->GetOwner() == this;
}

bool AGITrain::GetRoofPointNear(const FVector& Location, float MaxDist, FVector& OutPoint) const
{
	float Best = MaxDist;
	bool bFound = false;
	for (const UStaticMeshComponent* Car : Cars)
	{
		if (!Car)
		{
			continue;
		}
		const FBox Box = Car->Bounds.GetBox();
		const FVector C = Box.GetCenter();
		const FVector E = Box.GetExtent();
		const float X = FMath::Clamp(Location.X, C.X - E.X + 100.f, C.X + E.X - 100.f);
		const float DistXY = FVector2D(Location.X - X, Location.Y - C.Y).Size() - E.Y;
		if (DistXY < Best && Location.Z < Box.Max.Z + 300.f)
		{
			Best = DistXY;
			// Lead the point a little so the moving train doesn't slide out from under the player.
			OutPoint = FVector(X + Speed * 0.15f, C.Y, Box.Max.Z);
			bFound = true;
		}
	}
	return bFound;
}

void AGITrain::CheckPlayerHit(float DeltaSeconds)
{
	// A moving train knocks the player aside (with damage) instead of swallowing them.
	HitCooldown -= DeltaSeconds;
	ACharacter* Player = UGameplayStatics::GetPlayerCharacter(this, 0);
	if (!Player || HitCooldown > 0.f || OwnsComponent(Player->GetMovementBase()))
	{
		return;
	}
	const FVector P = Player->GetActorLocation();
	for (int32 i = 0; i < Cars.Num(); ++i)
	{
		const UStaticMeshComponent* Car = Cars[i];
		if (!Car)
		{
			continue;
		}
		const FBox Box = Car->Bounds.GetBox().ExpandBy(FVector(30.f, 45.f, 0.f));
		if (!Box.IsInsideOrOn(P) || P.Z > Box.Max.Z - 40.f)
		{
			continue;
		}
		const float Side = P.Y >= Box.GetCenter().Y ? 1.f : -1.f;
		const float FrontX = Speed >= 0.f ? Box.Max.X : Box.Min.X;
		const bool bNose = i == 0 && FMath::Abs(P.X - FrontX) < 260.f;
		if (!bNose)
		{
			// Brushing the side of a coach (e.g. walking up to climb on): just nudge clear, no damage.
			Player->LaunchCharacter(FVector(Speed * 0.25f, Side * 260.f, 0.f), false, false);
			HitCooldown = 0.4f;
			break;
		}
		Player->LaunchCharacter(FVector(Speed * 0.5f, Side * 1400.f, 520.f), true, true);
		if (AGIPlayerCharacter* GI = Cast<AGIPlayerCharacter>(Player))
		{
			GI->ApplyDamageSimple(15.f, false);
			GI->OnPopup.Broadcast(NSLOCTEXT("GTAIndia", "TrainHit", "Train se takkar! HP -15"));
		}
		HitCooldown = 3.f;
		break;
	}
}
