#include "GITraffic.h"
#include "GIAnimBudget.h"
#include "GIPlayerCharacter.h"
#include "GameFramework/Character.h"
#include "GIGameUserSettings.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "GIAnimInstance.h"
#include "GIAssetSettings.h"

AGITraffic::AGITraffic()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AGITraffic::BeginPlay()
{
	Super::BeginPlay();
	if (VehicleMeshes.Num() == 0)
	{
		return;
	}
	float Density = 1.f;
	if (const UGIGameUserSettings* GS = UGIGameUserSettings::Get())
	{
		Density = 0.5f + 0.25f * GS->CrowdDensity;
	}
	FRandomStream Rand(99);
	for (int32 L = 0; L < Lanes.Num(); ++L)
	{
		const int32 N = FMath::Max(1, FMath::RoundToInt(Lanes[L].Count * Density));
		for (int32 i = 0; i < N; ++i)
		{
			const int32 MeshIdx = Rand.RandRange(0, VehicleMeshes.Num() - 1);
			UStaticMesh* Mesh = VehicleMeshes[MeshIdx];
			if (!Mesh)
			{
				continue;
			}
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
			C->SetMobility(EComponentMobility::Movable);
			C->SetupAttachment(RootComponent);
			C->SetStaticMesh(Mesh);
			C->SetUsingAbsoluteLocation(true);
			C->SetUsingAbsoluteRotation(true);
			C->SetCollisionProfileName(TEXT("BlockAll"));
			C->SetCanEverAffectNavigation(false);
			C->RegisterComponent();
			Comps.Add(C);
			FVehicle V;
			V.Comp = C;
			V.Lane = L;
			V.X = FMath::Lerp(MinX, MaxX, (i + Rand.FRand() * 0.6f) / N);
			const FVector Size = Mesh->GetBoundingBox().GetSize();
			const bool bBike = Size.Y < 110.f;
			V.bFourWheeler = !bBike;
			V.MeshYaw = VehicleMeshYaws.IsValidIndex(MeshIdx) ? VehicleMeshYaws[MeshIdx] : 0.f;
			V.MaxSpeed = Speed * Rand.FRandRange(0.65f, 1.25f) * (bBike ? 1.15f : 1.f);
			V.Speed = V.MaxSpeed;
			V.Wobble = Rand.FRandRange(0.f, 10.f);
			AddRiders(V, Rand);
			Vehicles.Add(V);
		}
	}
}

void AGITraffic::AddRider(FVehicle& V, FRandomStream& Rand, const FVector& PelvisOffset, bool bDriver)
{
	const TArray<FGICharacterLook>& Looks = UGIAssetSettings::Get().PedestrianLooks;
	if (Looks.Num() == 0)
	{
		return;
	}
	const FGICharacterLook& Look = Looks[Rand.RandRange(0, Looks.Num() - 1)];
	USkeletalMesh* Mesh = Look.Mesh.LoadSynchronous();
	if (!Mesh)
	{
		return;
	}
	USkeletalMeshComponent* P = GIAnimBudget::NewPersonComponent(this);
	P->SetupAttachment(RootComponent);
	P->SetUsingAbsoluteLocation(true);
	P->SetUsingAbsoluteRotation(true);
	P->RegisterComponent();
	P->SetSkeletalMesh(Mesh);
	P->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
	P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	P->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	P->bEnableUpdateRateOptimizations = true;
	UGIAssetSettings::ApplyLookVariety(P, Look, Rand);
	if (UGIAnimInstance* Anim = Cast<UGIAnimInstance>(P->GetAnimInstance()))
	{
		Anim->Params.Mode = bDriver ? EGIPoseMode::RideBike : EGIPoseMode::Sit;
		Anim->Params.MeshBaseRotation = FRotator(0.f, -90.f, 0.f).Quaternion();
		Anim->Params.TimeOffset = Rand.FRandRange(0.f, 6.f);
	}
	V.Riders.Add(P);
	V.RiderOffsets.Add(PelvisOffset - FVector(0.f, 0.f, UGIAnimInstance::GetSitPelvisHeight()));
	RiderComps.Add(P);
}

void AGITraffic::AddRiders(FVehicle& V, FRandomStream& Rand)
{
	const FVector Size = V.Comp->GetStaticMesh()->GetBoundingBox().GetSize();
	if (!V.bFourWheeler)
	{
		// Bike: rider + often a pillion, sometimes a family of three (very Indian).
		AddRider(V, Rand, FVector(-10.f, 0.f, 88.f), true);
		if (Rand.FRand() < 0.6f)
		{
			AddRider(V, Rand, FVector(-46.f, 0.f, 92.f), false);
		}
		if (Rand.FRand() < 0.22f)
		{
			AddRider(V, Rand, FVector(-76.f, 0.f, 96.f), false);
		}
	}
	else if (Size.Z > 140.f && Size.X > 280.f && Size.Y > 140.f)
	{
		// Car: right-hand drive, sometimes a passenger.
		AddRider(V, Rand, FVector(8.f, 34.f, 62.f), true);
		if (Rand.FRand() < 0.5f)
		{
			AddRider(V, Rand, FVector(8.f, -34.f, 62.f), false);
		}
	}
	else
	{
		// Auto-rickshaw: driver up front, passengers squeezed on the back bench.
		AddRider(V, Rand, FVector(30.f, 0.f, 86.f), true);
		const int32 N = Rand.RandRange(1, 3);
		for (int32 k = 0; k < N; ++k)
		{
			AddRider(V, Rand, FVector(-52.f, (k - (N - 1) * 0.5f) * 34.f, 80.f), false);
		}
	}
}

bool AGITraffic::HasVehicleNear(const FVector& Location, float MaxDist) const
{
	for (const FVehicle& V : Vehicles)
	{
		if (V.Comp && FVector::DistSquared(V.Comp->GetComponentLocation(), Location) < MaxDist * MaxDist)
		{
			return true;
		}
	}
	return false;
}

bool AGITraffic::TakeVehicle(const FVector& Location, float MaxDist, FTransform& OutTransform, UStaticMesh*& OutMesh, float& OutMeshYaw, bool& bOutFourWheeler)
{
	int32 Best = INDEX_NONE;
	float BestD = MaxDist * MaxDist;
	for (int32 i = 0; i < Vehicles.Num(); ++i)
	{
		const FVehicle& V = Vehicles[i];
		const float D = V.Comp ? FVector::DistSquared(V.Comp->GetComponentLocation(), Location) : 1e18f;
		if (D < BestD)
		{
			BestD = D;
			Best = i;
		}
	}
	if (Best == INDEX_NONE)
	{
		return false;
	}
	FVehicle& V = Vehicles[Best];
	const float Dir = Lanes[V.Lane].Direction >= 0.f ? 1.f : -1.f;
	OutTransform = FTransform(FRotator(0.f, Dir > 0.f ? 0.f : 180.f, 0.f), V.Comp->GetComponentLocation());
	OutMesh = V.Comp->GetStaticMesh();
	OutMeshYaw = V.MeshYaw;
	bOutFourWheeler = V.bFourWheeler;
	for (USkeletalMeshComponent* R : V.Riders)
	{
		if (R)
		{
			RiderComps.Remove(R);
			R->DestroyComponent();
		}
	}
	Comps.Remove(V.Comp);
	V.Comp->DestroyComponent();
	Vehicles.RemoveAt(Best);
	return true;
}

void AGITraffic::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector P = Player ? Player->GetActorLocation() : FVector(1e9f);
	const float Now = GetWorld()->GetTimeSeconds();

	SignificanceTimer -= DeltaSeconds;
	if (SignificanceTimer <= 0.f)
	{
		SignificanceTimer = 0.5f;
		const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
		if (PC && PC->PlayerCameraManager)
		{
			const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
			const UGIGameUserSettings* GS = UGIGameUserSettings::Get();
			const float ShadowDistSq = FMath::Square(GS ? GS->GetCrowdShadowDistanceCm() : 6000.f);
			const float Cull = GS ? GS->GetCrowdCullDistanceCm() : 16000.f;
			for (USkeletalMeshComponent* R : RiderComps)
			{
				if (R)
				{
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

	HitCooldown -= DeltaSeconds;
	ACharacter* PlayerChar = UGameplayStatics::GetPlayerCharacter(this, 0);
	for (FVehicle& V : Vehicles)
	{
		const FGITrafficLane& L = Lanes[V.Lane];
		// Getting hit by an auto: knocked aside, a little damage (they brake for you, so it's rare).
		if (PlayerChar && HitCooldown <= 0.f && V.Speed > 250.f && V.Comp
			&& V.Comp->Bounds.GetBox().ExpandBy(25.f).IsInsideOrOn(PlayerChar->GetActorLocation()))
		{
			const float Dir = L.Direction >= 0.f ? 1.f : -1.f;
			const float Side = PlayerChar->GetActorLocation().Y >= L.Y ? 1.f : -1.f;
			PlayerChar->LaunchCharacter(FVector(Dir * V.Speed * 0.8f, Side * 500.f, 320.f), true, true);
			if (AGIPlayerCharacter* GI = Cast<AGIPlayerCharacter>(PlayerChar))
			{
				GI->ApplyDamageSimple(10.f, false);
				GI->OnPopup.Broadcast(NSLOCTEXT("GTAIndia", "AutoHit", "Auto se takkar! HP -10"));
			}
			V.Speed *= 0.2f;
			HitCooldown = 1.2f;
		}
		const float Dir = L.Direction >= 0.f ? 1.f : -1.f;
		// Distance to the nearest obstacle ahead in the lane (other vehicles or the player).
		float Gap = 1e9f;
		for (const FVehicle& O : Vehicles)
		{
			if (&O == &V || O.Lane != V.Lane)
			{
				continue;
			}
			const float D = (O.X - V.X) * Dir;
			if (D > 0.f)
			{
				Gap = FMath::Min(Gap, D);
			}
		}
		if (FMath::Abs(P.Y - L.Y) < 260.f && FMath::Abs(P.Z - L.Z) < 400.f)
		{
			const float D = (P.X - V.X) * Dir;
			if (D > 0.f)
			{
				Gap = FMath::Min(Gap, D);
			}
		}
		const float Want = Gap < 450.f ? 0.f : (Gap < 1500.f ? V.MaxSpeed * (Gap - 450.f) / 1050.f : V.MaxSpeed);
		V.Speed = FMath::FInterpTo(V.Speed, Want, DeltaSeconds, Want < V.Speed ? 4.f : 1.2f);
		V.X += Dir * V.Speed * DeltaSeconds;
		if (V.X > MaxX)
		{
			V.X = MinX;
		}
		else if (V.X < MinX)
		{
			V.X = MaxX;
		}
		const float Sway = 18.f * FMath::Sin(Now * 0.7f + V.Wobble);
		const float TravelYaw = Dir > 0.f ? 0.f : 180.f;
		const FVector VLoc(V.X, L.Y + Sway, L.Z);
		V.Comp->SetWorldLocationAndRotation(VLoc, FRotator(0.f, TravelYaw + V.MeshYaw, 0.f));
		const FRotator TravelRot(0.f, TravelYaw, 0.f);
		for (int32 r = 0; r < V.Riders.Num(); ++r)
		{
			if (V.Riders[r])
			{
				V.Riders[r]->SetWorldLocationAndRotation(VLoc + TravelRot.RotateVector(V.RiderOffsets[r]), FRotator(0.f, TravelYaw - 90.f, 0.f));
			}
		}
	}
}
