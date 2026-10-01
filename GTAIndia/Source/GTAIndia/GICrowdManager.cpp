#include "GICrowdManager.h"
#include "GIAnimBudget.h"
#include "GIAssetSettings.h"
#include "GIGameUserSettings.h"
#include "GIPlayerCharacter.h"
#include "GIBike.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerStart.h"
#include "GIDharavi.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

static const FQuat GMeshBase = FRotator(0.f, -90.f, 0.f).Quaternion();

AGICrowdManager::AGICrowdManager()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AGICrowdManager::BeginPlay()
{
	Super::BeginPlay();
	GIAnimBudget::EnableForWorld(GetWorld());
	Rebuild();
}

void AGICrowdManager::Clear()
{
	for (USkeletalMeshComponent* C : Comps)
	{
		if (C)
		{
			C->DestroyComponent();
		}
	}
	Comps.Reset();
	People.Reset();
}

bool AGICrowdManager::Ground(const FVector& P, float& OutZ) const
{
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(GICrowdGround), false, this);
	if (APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0))
	{
		Params.AddIgnoredActor(Player);
	}
	if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0, 0, 250.f), P - FVector(0, 0, 800.f), ECC_Visibility, Params))
	{
		OutZ = Hit.ImpactPoint.Z;
		return true;
	}
	return false;
}

USkeletalMeshComponent* AGICrowdManager::SpawnComp(FRandomStream& Rand, FName* OutGender)
{
	const TArray<FGICharacterLook>& Looks = UGIAssetSettings::Get().PedestrianLooks;
	if (Looks.Num() == 0)
	{
		return nullptr;
	}
	float Total = 0.f;
	for (const FGICharacterLook& L : Looks)
	{
		Total += FMath::Max(L.Weight, 0.f);
	}
	float Pick = Rand.FRandRange(0.f, Total);
	const FGICharacterLook* Chosen = &Looks[0];
	for (const FGICharacterLook& L : Looks)
	{
		Pick -= FMath::Max(L.Weight, 0.f);
		if (Pick <= 0.f)
		{
			Chosen = &L;
			break;
		}
	}
	USkeletalMesh* Mesh = Chosen->Mesh.LoadSynchronous();
	if (!Mesh)
	{
		return nullptr;
	}
	const FGICharacterLook* LookForVariety = Chosen;
	if (OutGender)
	{
		*OutGender = Chosen->Tag;
	}
	USkeletalMeshComponent* C = GIAnimBudget::NewPersonComponent(this);
	C->SetupAttachment(RootComponent);
	C->SetUsingAbsoluteLocation(true);
	C->SetUsingAbsoluteRotation(true);
	C->RegisterComponent();
	C->SetSkeletalMesh(Mesh);
	C->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	C->bEnableUpdateRateOptimizations = true;
	C->SetCachedMaxDrawDistance(UGIGameUserSettings::Get() ? UGIGameUserSettings::Get()->GetCrowdCullDistanceCm() : CullDistance);
	C->SetCastShadow(true);
	// Slight size variety.
	C->SetWorldScale3D(FVector(Rand.FRandRange(0.94f, 1.05f)));
	UGIAssetSettings::ApplyLookVariety(C, *LookForVariety, Rand);
	Comps.Add(C);
	return C;
}

FVector AGICrowdManager::BubbleCenter() const
{
	if (const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0))
	{
		return Player->GetActorLocation();
	}
	if (const AActor* Start = UGameplayStatics::GetActorOfClass(this, APlayerStart::StaticClass()))
	{
		return Start->GetActorLocation();
	}
	return Lanes.Num() > 0 ? Lanes[0].Start : FVector::ZeroVector;
}

void AGICrowdManager::GatherLanes(const FVector& Center, TArray<FLaneCand>& Out) const
{
	Out.Reset();
	const float R = BubbleRadius * 0.95f;
	for (int32 l = 0; l < Lanes.Num(); ++l)
	{
		const FGIWalkLane& L = Lanes[l];
		const FVector D = L.End - L.Start;
		const float Len2 = FMath::Max(D.SizeSquared2D(), 1.f);
		const float T = FMath::Clamp(((Center.X - L.Start.X) * D.X + (Center.Y - L.Start.Y) * D.Y) / Len2, 0.f, 1.f);
		const float Dist = FVector::Dist2D(L.Start + D * T, Center);
		if (Dist < R && FMath::Abs(L.Start.Z + D.Z * T - Center.Z) < 2500.f)
		{
			FLaneCand C;
			C.Lane = l;
			C.T = T;
			C.HalfSpan = FMath::Sqrt(R * R - Dist * Dist) / FMath::Sqrt(Len2);
			C.Weight = FMath::Max(L.Weight, 0.01f) * FMath::Min(1.f, C.HalfSpan * FMath::Sqrt(Len2) / 3000.f);
			Out.Add(C);
		}
	}
}

bool AGICrowdManager::IsInView(const FVector& Pos, const FVector& Cam, const FVector& CamFwd)
{
	const FVector D = Pos + FVector(0, 0, 90.f) - Cam;
	const float Dist = D.Size();
	return Dist < 9000.f && FVector::DotProduct(D / FMath::Max(Dist, 1.f), CamFwd) > 0.42f;
}

bool AGICrowdManager::PickLanePoint(const TArray<FLaneCand>& Cands, const FVector& Center, const FVector* Cam, const FVector& CamFwd,
	FRandomStream& Rand, int32& OutLane, float& OutT, float& OutLat) const
{
	float Total = 0.f;
	for (const FLaneCand& C : Cands)
	{
		Total += C.Weight;
	}
	if (Total <= 0.f)
	{
		return false;
	}
	for (int32 Try = 0; Try < 6; ++Try)
	{
		float Pick = Rand.FRandRange(0.f, Total);
		const FLaneCand* C = &Cands[0];
		for (const FLaneCand& X : Cands)
		{
			Pick -= X.Weight;
			if (Pick <= 0.f)
			{
				C = &X;
				break;
			}
		}
		const FGIWalkLane& L = Lanes[C->Lane];
		const float T = FMath::Clamp(C->T + Rand.FRandRange(-C->HalfSpan, C->HalfSpan), 0.f, 1.f);
		const float Lat = Rand.FRandRange(-0.5f, 0.5f) * L.Width;
		const FVector Pos = L.Start + (L.End - L.Start) * T;
		if (Cam && (FVector::Dist2D(Pos, Center) < 1500.f || IsInView(Pos, *Cam, CamFwd)))
		{
			continue;
		}
		OutLane = C->Lane;
		OutT = T;
		OutLat = Lat;
		return true;
	}
	return false;
}

void AGICrowdManager::PlaceWalker(FPerson& P, int32 Lane, float T, float Lat, FRandomStream& Rand)
{
	P.Lane = Lane;
	P.T = T;
	P.Lateral = Lat;
	P.Dir = Rand.FRand() < 0.5f ? -1.f : 1.f;
	P.PauseTime = 0.f;
	P.Dodge = 0.f;
	const FGIWalkLane& L = Lanes[Lane];
	const FVector Axis = L.End - L.Start;
	const FVector Dir2D = FVector(Axis.X, Axis.Y, 0.f).GetSafeNormal();
	FVector Pos = L.Start + Axis * T + FVector(-Dir2D.Y, Dir2D.X, 0.f) * Lat;
	P.GroundZ = Pos.Z;
	Ground(Pos, P.GroundZ);
	Pos.Z = P.GroundZ;
	P.Yaw = (Dir2D * P.Dir).Rotation().Yaw;
	if (P.Comp)
	{
		P.Comp->SetWorldLocationAndRotation(Pos, FRotator(0.f, P.Yaw - 90.f, 0.f));
	}
}

void AGICrowdManager::PlaceStatic(FPerson& P, int32 SpotIdx, FRandomStream& Rand)
{
	if (P.Spot != INDEX_NONE && SpotUsed.IsValidIndex(P.Spot))
	{
		SpotUsed[P.Spot] = false;
	}
	P.Spot = SpotIdx;
	SpotUsed[SpotIdx] = true;
	const FGIStaticSpot& S = Spots[SpotIdx];
	float Z = S.Location.Z;
	if (!S.bFixedZ)
	{
		Ground(S.Location, Z);
	}
	const bool bSitting = S.Mode == EGIPoseMode::Sit || S.Mode == EGIPoseMode::SitArmsOut || S.Mode == EGIPoseMode::SitTalk;
	P.Comp->SetWorldLocationAndRotation(FVector(S.Location.X, S.Location.Y, Z + (bSitting ? -(UGIAnimInstance::GetSitPelvisHeight() - 12.f) : 0.f)),
		FRotator(0.f, S.Yaw - 90.f, 0.f));
	if (P.Anim)
	{
		P.Anim->Params.Mode = S.Mode;
		P.Anim->Params.MeshBaseRotation = GMeshBase;
		P.Anim->Params.TimeOffset = Rand.FRandRange(0.f, 8.f);
	}
	P.BaseMode = S.Mode;
	P.BaseYaw = S.Yaw;
	P.Yaw = S.Yaw;
	P.bSitting = bSitting;
}

void AGICrowdManager::Rebuild()
{
	Clear();
	int32 Budget = 140;
	if (const UGIGameUserSettings* GS = UGIGameUserSettings::Get())
	{
		Budget = GS->GetCrowdBudget();
	}
	Budget = FMath::RoundToInt(Budget * BudgetShare);
	FRandomStream Rand(4321);
	BubbleRand.Initialize(777);
	SpotUsed.Init(false, Spots.Num());

	TotalLaneWeight = 0.f;
	for (const FGIWalkLane& L : Lanes)
	{
		TotalLaneWeight += FMath::Max(L.Weight, 0.f);
	}
	const FVector Center = BubbleCenter();
	TArray<FLaneCand> Cands;
	GatherLanes(Center, Cands);

	const int32 NumWalkers = Cands.Num() > 0 ? FMath::RoundToInt(Budget * WalkerShare) : 0;
	const int32 NumStatic = FMath::Min(Budget - NumWalkers, Spots.Num());

	// Walkers on lanes around the player.
	for (int32 i = 0; i < NumWalkers; ++i)
	{
		int32 Lane;
		float T, Lat;
		if (!PickLanePoint(Cands, Center, nullptr, FVector::ForwardVector, Rand, Lane, T, Lat))
		{
			break;
		}
		FName Gender;
		USkeletalMeshComponent* C = SpawnComp(Rand, &Gender);
		if (!C)
		{
			break;
		}
		FPerson P;
		P.Comp = C;
		P.Gender = Gender;
		P.Anim = Cast<UGIAnimInstance>(C->GetAnimInstance());
		P.Speed = Rand.FRandRange(85.f, 145.f);
		P.NextTrace = Rand.FRandRange(0.f, 0.3f);
		if (P.Anim)
		{
			P.Anim->Params.MeshBaseRotation = GMeshBase;
			P.Anim->Params.TimeOffset = Rand.FRandRange(0.f, 5.f);
		}
		PlaceWalker(P, Lane, T, Lat, Rand);
		People.Add(P);
	}

	// Static people on the spots nearest the player (priority breaks ties).
	TArray<int32> Order;
	for (int32 i = 0; i < Spots.Num(); ++i)
	{
		Order.Add(i);
	}
	Order.Sort([this, &Center](int32 A, int32 B)
	{
		const float SA = FVector::Dist2D(Spots[A].Location, Center) - Spots[A].Priority * 1500.f;
		const float SB = FVector::Dist2D(Spots[B].Location, Center) - Spots[B].Priority * 1500.f;
		return SA < SB;
	});
	for (int32 i = 0; i < NumStatic; ++i)
	{
		FName Gender;
		USkeletalMeshComponent* C = SpawnComp(Rand, &Gender);
		if (!C)
		{
			break;
		}
		FPerson P;
		P.Comp = C;
		P.Anim = Cast<UGIAnimInstance>(C->GetAnimInstance());
		P.Gender = Gender;
		PlaceStatic(P, Order[i], Rand);
		People.Add(P); // Lane = INDEX_NONE -> static
	}
}

void AGICrowdManager::UpdateBubble()
{
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC || !PC->PlayerCameraManager || People.Num() == 0)
	{
		return;
	}
	const FVector Center = BubbleCenter();
	const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
	const FVector CamFwd = PC->PlayerCameraManager->GetCameraRotation().Vector();
	const float R2 = FMath::Square(BubbleRadius);

	TArray<FLaneCand> Cands;
	GatherLanes(Center, Cands);
	TArray<int32> FreeSpots;
	for (int32 i = 0; i < Spots.Num(); ++i)
	{
		if (!SpotUsed[i] && FVector::DistSquared2D(Spots[i].Location, Center) < R2 * 0.8f && FMath::Abs(Spots[i].Location.Z - Center.Z) < 2500.f
			&& FVector::Dist2D(Spots[i].Location, Center) > 1500.f && !IsInView(Spots[i].Location, Cam, CamFwd))
		{
			FreeSpots.Add(i);
		}
	}

	int32 Moved = 0;
	for (FPerson& P : People)
	{
		if (Moved >= 24)
		{
			break;
		}
		if (!P.Comp || P.AngryTimer > 0.f)
		{
			continue;
		}
		const FVector Pos = P.Comp->GetComponentLocation();
		if (FVector::DistSquared2D(Pos, Center) < R2 || P.Comp->WasRecentlyRendered(0.25f))
		{
			continue;
		}
		if (P.Lane != INDEX_NONE)
		{
			int32 Lane;
			float T, Lat;
			if (Cands.Num() > 0 && PickLanePoint(Cands, Center, &Cam, CamFwd, BubbleRand, Lane, T, Lat))
			{
				PlaceWalker(P, Lane, T, Lat, BubbleRand);
				++Moved;
			}
		}
		else if (FreeSpots.Num() > 0)
		{
			const int32 k = BubbleRand.RandRange(0, FreeSpots.Num() - 1);
			PlaceStatic(P, FreeSpots[k], BubbleRand);
			FreeSpots.RemoveAtSwap(k);
			++Moved;
		}
	}
}

void AGICrowdManager::UpdateUmbrellas()
{
	// Monsoon: most people walking about open an umbrella (held up in the right hand).
	const AGIWeather* W = AGIWeather::Get(this);
	const bool bWant = W && (bUmbrellasOut ? W->GetRainAmount() > 0.3f : W->GetRainAmount() > 0.5f);
	if (bWant == bUmbrellasOut)
	{
		return;
	}
	bUmbrellasOut = bWant;
	for (int32 i = 0; i < People.Num(); ++i)
	{
		FPerson& P = People[i];
		const bool bThis = bWant && P.Comp && (P.Lane != INDEX_NONE || P.BaseMode == EGIPoseMode::Talk) && (i * 7919) % 10 < 7;
		if (bThis && !P.Umbrella)
		{
			if (UStaticMesh* Mesh = W->PickUmbrella(i))
			{
				P.Umbrella = NewObject<UStaticMeshComponent>(this);
				P.Umbrella->SetStaticMesh(Mesh);
				P.Umbrella->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				P.Umbrella->SetupAttachment(P.Comp);
				// Mesh space: the body faces +Y, its right side is -X; handle at the raised right hand.
				P.Umbrella->SetRelativeLocation(FVector(-24.f, 16.f, 112.f));
				P.Umbrella->RegisterComponent();
				UmbrellaComps.Add(P.Umbrella);
			}
		}
		if (P.Umbrella)
		{
			P.Umbrella->SetVisibility(bThis);
		}
		if (P.Anim)
		{
			P.Anim->Params.bHoldUmbrella = bThis && P.Umbrella != nullptr;
		}
	}
}

void AGICrowdManager::UpdateSignificance()
{
	// Shadows are the main cost of a big crowd: only people near the camera cast them.
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC || !PC->PlayerCameraManager)
	{
		return;
	}
	const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
	const UGIGameUserSettings* GS = UGIGameUserSettings::Get();
	const float ShadowDistSq = FMath::Square(GS ? GS->GetCrowdShadowDistanceCm() : 6000.f);
	const float Cull = GS ? GS->GetCrowdCullDistanceCm() : CullDistance;
	for (USkeletalMeshComponent* C : Comps)
	{
		if (!C)
		{
			continue;
		}
		const bool bShadow = FVector::DistSquared(C->GetComponentLocation(), Cam) < ShadowDistSq;
		if (C->CastShadow != bShadow)
		{
			C->SetCastShadow(bShadow);
		}
		if (!FMath::IsNearlyEqual(C->CachedMaxDrawDistance, Cull))
		{
			C->SetCachedMaxDrawDistance(Cull);
		}
	}
}

void AGICrowdManager::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	SignificanceTimer -= DeltaSeconds;
	if (SignificanceTimer <= 0.f)
	{
		SignificanceTimer = 0.5f;
		UpdateSignificance();
		UpdateUmbrellas();
	}
	BubbleTimer -= DeltaSeconds;
	if (BubbleTimer <= 0.f)
	{
		BubbleTimer = 0.3f;
		UpdateBubble();
	}
	UpdateSpeech(DeltaSeconds);
	const float Now = GetWorld()->GetTimeSeconds();
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector PlayerLoc = Player ? Player->GetActorLocation() : FVector(1e9f);

	for (FPerson& P : People)
	{
		if (P.Lane == INDEX_NONE || !P.Comp)
		{
			continue;
		}
		const FGIWalkLane& L = Lanes[P.Lane];
		const FVector Axis = L.End - L.Start;
		const float Len = FMath::Max(Axis.Size2D(), 1.f);
		const FVector Dir2D = FVector(Axis.X, Axis.Y, 0.f) / Len;
		const FVector Right(-Dir2D.Y, Dir2D.X, 0.f);

		float MoveSpeed = P.Speed;
		if (P.PauseTime > 0.f)
		{
			P.PauseTime -= DeltaSeconds;
			MoveSpeed = 0.f;
		}
		else
		{
			P.T += P.Dir * P.Speed * DeltaSeconds / Len;
			if (P.T > 1.f || P.T < 0.f)
			{
				P.T = FMath::Clamp(P.T, 0.f, 1.f);
				P.Dir = -P.Dir;
				P.PauseTime = FMath::FRandRange(0.5f, 3.f);
			}
			else if (FMath::FRand() < DeltaSeconds * 0.02f)
			{
				P.PauseTime = FMath::FRandRange(1.f, 5.f); // stop to chat / look around
			}
		}

		FVector Pos = L.Start + Axis * P.T + Right * P.Lateral;

		// Step aside when the player comes close.
		const float DistToPlayer = FVector::Dist2D(Pos, PlayerLoc);
		const float WantDodge = DistToPlayer < 120.f && FMath::Abs(Pos.Z - PlayerLoc.Z) < 250.f
			? FMath::Sign(FVector::DotProduct(Pos - PlayerLoc, Right) + 0.01f) * (120.f - DistToPlayer) * 0.8f : 0.f;
		P.Dodge = FMath::FInterpTo(P.Dodge, WantDodge, DeltaSeconds, 3.f);
		Pos += Right * P.Dodge;

		if (Now >= P.NextTrace)
		{
			P.NextTrace = Now + 0.25f + FMath::FRand() * 0.1f;
			float Z;
			if (Ground(Pos, Z))
			{
				P.GroundZ = Z;
			}
		}
		const float CurZ = P.Comp->GetComponentLocation().Z;
		const float NewZ = FMath::Abs(CurZ - P.GroundZ) > 300.f ? P.GroundZ : FMath::FInterpTo(CurZ, P.GroundZ, DeltaSeconds, 10.f);
		Pos.Z = NewZ;

		const float WantYaw = P.AngryTimer > 0.f ? P.Yaw : (Dir2D * P.Dir).Rotation().Yaw;
		if (MoveSpeed > 0.f && P.AngryTimer <= 0.f)
		{
			P.Yaw = FMath::FixedTurn(P.Yaw, WantYaw, 360.f * DeltaSeconds);
		}
		P.Comp->SetWorldLocationAndRotation(Pos, FRotator(0.f, P.Yaw - 90.f, 0.f));
		if (P.Anim)
		{
			P.Anim->Params.Speed = MoveSpeed;
		}
	}
}

bool AGICrowdManager::Say(FPerson& P, FName Category, bool bSubtitle)
{
	const TArray<FGIVoiceLine>& Lines = UGIAssetSettings::Get().VoiceLines;
	TArray<const FGIVoiceLine*> Pick;
	for (const FGIVoiceLine& L : Lines)
	{
		if (L.Category == Category && (P.Gender.IsNone() || L.Gender == P.Gender))
		{
			Pick.Add(&L);
		}
	}
	if (Pick.Num() == 0 || !P.Comp)
	{
		return false;
	}
	const FGIVoiceLine* L = Pick[FMath::RandRange(0, Pick.Num() - 1)];
	USoundBase* Sound = L->Sound.LoadSynchronous();
	if (!Sound)
	{
		return false;
	}
	if (!VoiceAttenuation)
	{
		VoiceAttenuation = UGIAssetSettings::MakeAttenuation(this, 350.f, 2600.f);
	}
	UGameplayStatics::SpawnSoundAtLocation(this, Sound, P.Comp->GetComponentLocation() + FVector(0, 0, 160.f), FRotator::ZeroRotator,
		1.f, FMath::FRandRange(0.96f, 1.04f), 0.f, VoiceAttenuation);
	P.SpeakCooldown = FMath::FRandRange(8.f, 15.f);
	UE_LOG(LogTemp, Display, TEXT("GISpeech: [%s/%s] %s"), *Category.ToString(), *P.Gender.ToString(), *L->Text);
	if (bSubtitle)
	{
		if (AGIPlayerCharacter* Player = Cast<AGIPlayerCharacter>(UGameplayStatics::GetPlayerCharacter(this, 0)))
		{
			Player->OnPopup.Broadcast(FText::FromString(FString::Printf(TEXT("\"%s\""), *L->Text)));
		}
	}
	return true;
}

void AGICrowdManager::React(FPerson& P, const FVector& PlayerLoc)
{
	// Turn to face the player and tell them off.
	const FVector To = PlayerLoc - P.Comp->GetComponentLocation();
	P.Yaw = To.Rotation().Yaw;
	P.Comp->SetWorldRotation(FRotator(0.f, P.Yaw - 90.f, 0.f));
	P.AngryTimer = 2.2f;
	P.PauseTime = FMath::Max(P.PauseTime, 2.2f);
	if (P.Anim && !P.bSitting)
	{
		P.Anim->Params.Mode = EGIPoseMode::Angry;
	}
}

void AGICrowdManager::UpdateSpeech(float DeltaSeconds)
{
	ACharacter* PlayerChar = UGameplayStatics::GetPlayerCharacter(this, 0);
	AGIPlayerCharacter* Player = Cast<AGIPlayerCharacter>(PlayerChar);
	if (!Player || Player->IsDead())
	{
		return;
	}
	const AGIBike* Bike = Player->GetRidingBike();
	const FVector PL = Bike ? Bike->GetActorLocation() : Player->GetActorLocation();
	const float PSpeed = Bike ? Bike->GetSpeedKmh() / 0.036f : Player->GetVelocity().Size2D();
	AmbientTimer -= DeltaSeconds;
	BumpCooldown -= DeltaSeconds;
	BikeCooldown -= DeltaSeconds;
	SwimCooldown -= DeltaSeconds;

	TArray<int32> Near;
	for (int32 i = 0; i < People.Num(); ++i)
	{
		FPerson& P = People[i];
		if (!P.Comp)
		{
			continue;
		}
		P.SpeakCooldown -= DeltaSeconds;
		if (P.AngryTimer > 0.f)
		{
			P.AngryTimer -= DeltaSeconds;
			if (P.AngryTimer <= 0.f)
			{
				if (P.Anim)
				{
					P.Anim->Params.Mode = P.BaseMode;
				}
				if (P.Lane == INDEX_NONE)
				{
					P.Yaw = P.BaseYaw;
					P.Comp->SetWorldRotation(FRotator(0.f, P.BaseYaw - 90.f, 0.f));
				}
			}
		}
		const FVector C = P.Comp->GetComponentLocation();
		const float D = FVector::Dist2D(C, PL);
		const float DZ = FMath::Abs(C.Z + 90.f - PL.Z);
		if (D < 1600.f && DZ < 600.f)
		{
			Near.Add(i);
		}
		// Bumped into on foot.
		if (!Bike && D < 70.f && DZ < 160.f && PSpeed > 90.f && BumpCooldown <= 0.f && P.SpeakCooldown <= 0.f)
		{
			React(P, PL);
			Say(P, TEXT("bump"), true);
			const FVector Away = (PL - C).GetSafeNormal2D();
			PlayerChar->LaunchCharacter(Away * 260.f, true, false);   // a small shove back
			BumpCooldown = 1.2f;
		}
		// Bike roaring past.
		else if (Bike && D < 380.f && DZ < 250.f && PSpeed > 450.f && BikeCooldown <= 0.f && P.SpeakCooldown <= 0.f)
		{
			React(P, PL);
			Say(P, TEXT("bike"), true);
			BikeCooldown = 2.5f;
		}
	}
	// Somebody reacts when you jump into the Ganga.
	const bool bSwim = Player->IsSwimming();
	if (bSwim && !bPlayerWasSwimming && SwimCooldown <= 0.f && Near.Num() > 0)
	{
		Say(People[Near[FMath::RandRange(0, Near.Num() - 1)]], TEXT("swim"), true);
		SwimCooldown = 25.f;
	}
	bPlayerWasSwimming = bSwim;
	// Background chatter from people around you.
	if (AmbientTimer <= 0.f)
	{
		AmbientTimer = FMath::FRandRange(2.5f, 6.f);
		for (int32 Try = 0; Try < 4 && Near.Num() > 0; ++Try)
		{
			FPerson& P = People[Near[FMath::RandRange(0, Near.Num() - 1)]];
			if (P.SpeakCooldown <= 0.f && FVector::Dist2D(P.Comp->GetComponentLocation(), PL) > 150.f)
			{
				Say(P, AmbientCategory, false);
				break;
			}
		}
	}
}
