#include "GITraffic.h"
#include "GIPlayerCharacter.h"
#include "GameFramework/Character.h"
#include "GIGameUserSettings.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

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
			UStaticMesh* Mesh = VehicleMeshes[Rand.RandRange(0, VehicleMeshes.Num() - 1)];
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
			V.MaxSpeed = Speed * Rand.FRandRange(0.65f, 1.25f);
			V.Speed = V.MaxSpeed;
			V.Wobble = Rand.FRandRange(0.f, 10.f);
			Vehicles.Add(V);
		}
	}
}

void AGITraffic::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector P = Player ? Player->GetActorLocation() : FVector(1e9f);
	const float Now = GetWorld()->GetTimeSeconds();

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
		V.Comp->SetWorldLocationAndRotation(FVector(V.X, L.Y + Sway, L.Z), FRotator(0.f, Dir > 0.f ? 0.f : 180.f, 0.f));
	}
}
