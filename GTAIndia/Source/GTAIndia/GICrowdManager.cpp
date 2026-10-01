#include "GICrowdManager.h"
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

static const FQuat GMeshBase = FRotator(0.f, -90.f, 0.f).Quaternion();

AGICrowdManager::AGICrowdManager()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AGICrowdManager::BeginPlay()
{
	Super::BeginPlay();
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
	USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(this);
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

	TotalLaneWeight = 0.f;
	for (const FGIWalkLane& L : Lanes)
	{
		TotalLaneWeight += FMath::Max(L.Weight, 0.f);
	}

	const int32 NumWalkers = Lanes.Num() > 0 ? FMath::RoundToInt(Budget * WalkerShare) : 0;
	const int32 NumStatic = FMath::Min(Budget - NumWalkers, Spots.Num());

	// Walkers distributed by lane weight.
	for (int32 i = 0; i < NumWalkers; ++i)
	{
		float Pick = Rand.FRandRange(0.f, TotalLaneWeight);
		int32 LaneIdx = 0;
		for (int32 l = 0; l < Lanes.Num(); ++l)
		{
			Pick -= FMath::Max(Lanes[l].Weight, 0.f);
			if (Pick <= 0.f)
			{
				LaneIdx = l;
				break;
			}
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
		P.Lane = LaneIdx;
		P.T = Rand.FRand();
		P.Dir = Rand.FRand() < 0.5f ? -1.f : 1.f;
		P.Lateral = Rand.FRandRange(-0.5f, 0.5f) * Lanes[LaneIdx].Width;
		P.Speed = Rand.FRandRange(85.f, 145.f);
		P.NextTrace = Rand.FRandRange(0.f, 0.3f);
		const FVector Pos = FMath::Lerp(Lanes[LaneIdx].Start, Lanes[LaneIdx].End, P.T);
		P.GroundZ = Pos.Z;
		Ground(Pos, P.GroundZ);
		if (P.Anim)
		{
			P.Anim->Params.MeshBaseRotation = GMeshBase;
			P.Anim->Params.TimeOffset = Rand.FRandRange(0.f, 5.f);
		}
		People.Add(P);
	}

	// Static people, highest priority first.
	TArray<int32> Order;
	for (int32 i = 0; i < Spots.Num(); ++i)
	{
		Order.Add(i);
	}
	Order.Sort([this](int32 A, int32 B) { return Spots[A].Priority > Spots[B].Priority; });
	for (int32 i = 0; i < NumStatic; ++i)
	{
		const FGIStaticSpot& S = Spots[Order[i]];
		FName Gender;
		USkeletalMeshComponent* C = SpawnComp(Rand, &Gender);
		if (!C)
		{
			break;
		}
		float Z = S.Location.Z;
		if (!S.bFixedZ)
		{
			Ground(S.Location, Z);
		}
		const bool bSitting = S.Mode == EGIPoseMode::Sit || S.Mode == EGIPoseMode::SitArmsOut || S.Mode == EGIPoseMode::SitTalk;
		C->SetWorldLocationAndRotation(FVector(S.Location.X, S.Location.Y, Z + (bSitting ? -(UGIAnimInstance::GetSitPelvisHeight() - 12.f) : 0.f)), FRotator(0.f, S.Yaw - 90.f, 0.f));
		if (UGIAnimInstance* Anim = Cast<UGIAnimInstance>(C->GetAnimInstance()))
		{
			Anim->Params.Mode = S.Mode;
			Anim->Params.MeshBaseRotation = GMeshBase;
			Anim->Params.TimeOffset = Rand.FRandRange(0.f, 8.f);
		}
		FPerson P;
		P.Comp = C;
		P.Anim = Cast<UGIAnimInstance>(C->GetAnimInstance());
		P.Gender = Gender;
		P.BaseMode = S.Mode;
		P.BaseYaw = S.Yaw;
		P.Yaw = S.Yaw;
		P.bSitting = bSitting;
		People.Add(P); // Lane = INDEX_NONE -> static
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
				Say(P, TEXT("ambient"), false);
				break;
			}
		}
	}
}
