#include "GIDharavi.h"
#include "GIStory.h"
#include "GIAnimBudget.h"
#include "GIAnimInstance.h"
#include "GIAssetSettings.h"
#include "GIPlayerCharacter.h"
#include "Components/AudioComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/LightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Light.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"

#define LOCTEXT_NAMESPACE "GTAIndia"

static const FName GHandR(TEXT("hand_r"));

// ------------------------------------------------------------------------------------------ voice
bool GIVoice::Say(UObject* WorldContext, FName Category, const FVector& Location, bool bSubtitle, FName Gender)
{
	const TArray<FGIVoiceLine>& Lines = UGIAssetSettings::Get().VoiceLines;
	TArray<const FGIVoiceLine*> Pick;
	for (const FGIVoiceLine& L : Lines)
	{
		if (L.Category == Category && (Gender.IsNone() || L.Gender == Gender))
		{
			Pick.Add(&L);
		}
	}
	if (Pick.Num() == 0 || !WorldContext)
	{
		return false;
	}
	const FGIVoiceLine* L = Pick[FMath::RandRange(0, Pick.Num() - 1)];
	if (USoundBase* Sound = L->Sound.LoadSynchronous())
	{
		static USoundAttenuation* Att = nullptr;
		if (!Att)
		{
			Att = UGIAssetSettings::MakeAttenuation(GetTransientPackage(), 400.f, 3000.f);
			Att->AddToRoot();
		}
		UGameplayStatics::SpawnSoundAtLocation(WorldContext, Sound, Location, FRotator::ZeroRotator, 1.f, FMath::FRandRange(0.97f, 1.03f), 0.f, Att);
	}
	if (bSubtitle)
	{
		if (AGIPlayerCharacter* Player = Cast<AGIPlayerCharacter>(UGameplayStatics::GetPlayerCharacter(WorldContext, 0)))
		{
			Player->OnPopup.Broadcast(FText::FromString(FString::Printf(TEXT("\"%s\""), *L->Text)));
		}
	}
	return true;
}

namespace
{
	USkeletalMeshComponent* NewPerson(AActor* Owner, USkeletalMesh* Mesh, EGIPoseMode Mode, float TimeOffset)
	{
		USkeletalMeshComponent* C = GIAnimBudget::NewPersonComponent(Owner);
		C->SetupAttachment(Owner->GetRootComponent());
		C->RegisterComponent();
		C->SetSkeletalMesh(Mesh);
		C->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
		if (UGIAnimInstance* Anim = Cast<UGIAnimInstance>(C->GetAnimInstance()))
		{
			Anim->Params.Mode = Mode;
			Anim->Params.MeshBaseRotation = FRotator(0.f, -90.f, 0.f).Quaternion();
			Anim->Params.TimeOffset = TimeOffset;
		}
		return C;
	}

	UStaticMeshComponent* NewProp(AActor* Owner, UStaticMesh* Mesh, USceneComponent* Parent = nullptr, FName Socket = NAME_None)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Owner);
		C->SetStaticMesh(Mesh);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetupAttachment(Parent ? Parent : Owner->GetRootComponent(), Socket);
		C->RegisterComponent();
		return C;
	}

	AGIPlayerCharacter* GetPlayer(const UObject* Ctx)
	{
		return Cast<AGIPlayerCharacter>(UGameplayStatics::GetPlayerCharacter(Ctx, 0));
	}
}

// ------------------------------------------------------------------------------------- chai stall
AGIChaiStall::AGIChaiStall()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AGIChaiStall::BeginPlay()
{
	Super::BeginPlay();
	USkeletalMesh* Mesh = VendorMesh;
	if (!Mesh)
	{
		const TArray<FGICharacterLook>& Looks = UGIAssetSettings::Get().PedestrianLooks;
		for (const FGICharacterLook& L : Looks)
		{
			if (L.Tag == TEXT("male"))
			{
				Mesh = L.Mesh.LoadSynchronous();
				break;
			}
		}
	}
	if (Mesh)
	{
		Vendor = NewPerson(this, Mesh, EGIPoseMode::Pour, 0.f);
		Vendor->SetRelativeLocationAndRotation(VendorOffset, FRotator(0.f, -90.f - 90.f, 0.f));
		if (KettleMesh)
		{
			Kettle = NewProp(this, KettleMesh, Vendor, GHandR);
			Kettle->SetRelativeLocationAndRotation(FVector(0.f, 6.f, 0.f), FRotator(0.f, 0.f, 0.f));
		}
	}
}

void AGIChaiStall::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Cooldown -= DeltaSeconds;
	if (ReplyTimer > 0.f)
	{
		ReplyTimer -= DeltaSeconds;
		if (ReplyTimer <= 0.f)
		{
			GIVoice::Say(this, TEXT("chai_vendor"), GetActorLocation() + FVector(0, 0, 160.f));
		}
	}
	AmbientTimer -= DeltaSeconds;
	if (AmbientTimer <= 0.f)
	{
		AmbientTimer = FMath::FRandRange(14.f, 26.f);
		const AGIPlayerCharacter* P = GetPlayer(this);
		if (P && FVector::Dist(P->GetActorLocation(), GetActorLocation()) < 1500.f)
		{
			GIVoice::Say(this, TEXT("chai_call"), GetActorLocation() + FVector(0, 0, 160.f), false);
		}
	}
}

bool AGIChaiStall::CanServe(const AGIPlayerCharacter* Player) const
{
	return Player && Cooldown <= 0.f && FVector::Dist2D(Player->GetActorLocation(), GetActorLocation()) < 300.f;
}

void AGIChaiStall::Serve(AGIPlayerCharacter* Player)
{
	if (!CanServe(Player))
	{
		return;
	}
	if (Player->Money < Price)
	{
		Player->OnPopup.Broadcast(LOCTEXT("NoChaiMoney", "Paise nahi hain, boss!"));
		return;
	}
	Cooldown = 12.f;
	Player->Money -= Price;
	Player->Heal(HealAmount);
	Player->bDidChai = true;
	// Face the stall and sip.
	const FVector To = GetActorLocation() - Player->GetActorLocation();
	Player->SetActorRotation(FRotator(0.f, To.Rotation().Yaw, 0.f));
	Player->PlayAction(EGIPoseMode::Drink, 4.5f, GlassMesh);
	GIVoice::Say(this, TEXT("player_chai"), Player->GetActorLocation() + FVector(0, 0, 160.f));
	ReplyTimer = 1.8f;
	Player->OnPopup.Broadcast(FText::Format(LOCTEXT("ChaiBought", "Cutting chai  -₹{0}   +{1} HP"), FText::AsNumber(Price), FText::AsNumber(FMath::RoundToInt(HealAmount))));
}

// --------------------------------------------------------------------------------- gully cricket
AGICricketGame::AGICricketGame()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

AGICricketGame::FKid AGICricketGame::MakeKid(FRandomStream& Rand, const FVector& LocalPos, float Yaw, float Scale)
{
	FKid K;
	if (KidMeshes.Num() == 0)
	{
		return K;
	}
	USkeletalMesh* Mesh = KidMeshes[Rand.RandRange(0, KidMeshes.Num() - 1)];
	if (!Mesh)
	{
		return K;
	}
	K.Comp = NewPerson(this, Mesh, EGIPoseMode::Locomotion, Rand.FRandRange(0.f, 6.f));
	K.Comp->SetRelativeScale3D(FVector(Scale));
	K.Anim = Cast<UGIAnimInstance>(K.Comp->GetAnimInstance());
	K.Home = LocalPos;
	K.Yaw = Yaw;
	KidComps.Add(K.Comp);
	PlaceKid(K, LocalPos, Yaw, 0.f);
	return K;
}

void AGICricketGame::PlaceKid(FKid& K, const FVector& LocalPos, float Yaw, float Speed)
{
	if (!K.Comp)
	{
		return;
	}
	K.Comp->SetRelativeLocationAndRotation(LocalPos, FRotator(0.f, Yaw - 90.f, 0.f));
	if (K.Anim)
	{
		K.Anim->Params.Speed = Speed;
	}
}

void AGICricketGame::BeginPlay()
{
	Super::BeginPlay();
	FRandomStream Rand(GetUniqueID());
	if (StumpsMesh)
	{
		for (const float X : { -25.f, PitchLength + 25.f })
		{
			UStaticMeshComponent* S = NewProp(this, StumpsMesh);
			S->SetRelativeLocationAndRotation(FVector(X, 0.f, 0.f), FRotator(0.f, 90.f, 0.f));
			PropComps.Add(S);
		}
	}
	Batsman = MakeKid(Rand, FVector(20.f, 30.f, 0.f), 0.f, Rand.FRandRange(0.7f, 0.78f));
	Bowler = MakeKid(Rand, FVector(PitchLength + 650.f, -20.f, 0.f), 180.f, Rand.FRandRange(0.68f, 0.76f));
	Keeper = MakeKid(Rand, FVector(-170.f, 0.f, 0.f), 0.f, Rand.FRandRange(0.62f, 0.7f));
	if (Batsman.Anim)
	{
		Batsman.Anim->Params.Mode = EGIPoseMode::Bat;
	}
	if (Keeper.Anim)
	{
		Keeper.Anim->Params.Mode = EGIPoseMode::Bat;
	}
	if (Bowler.Anim)
	{
		Bowler.Anim->Params.Mode = EGIPoseMode::Bowl;
	}
	for (int32 i = 0; i < NumFielders; ++i)
	{
		const float X = Rand.FRandRange(-200.f, PitchLength + 450.f);
		const float Side = (i % 2 == 0) ? 1.f : -1.f;
		const float Y = Side * Rand.FRandRange(160.f, LaneHalfWidth * 0.9f);
		const FVector Pos(X, Y, 0.f);
		const float Yaw = (FVector(PitchLength * 0.3f, 0.f, 0.f) - Pos).Rotation().Yaw;
		FKid F = MakeKid(Rand, Pos, Yaw, Rand.FRandRange(0.6f, 0.8f));
		if (F.Anim)
		{
			F.Anim->Params.Mode = Rand.FRand() < 0.5f ? EGIPoseMode::Talk : EGIPoseMode::Locomotion;
		}
		Fielders.Add(F);
	}
	if (BatMesh && Batsman.Comp)
	{
		Bat = NewProp(this, BatMesh, Batsman.Comp, GHandR);
		Bat->SetRelativeLocationAndRotation(FVector(0.f, 4.f, 0.f), FRotator(0.f, 0.f, 90.f));
	}
	if (BallMesh)
	{
		Ball = NewProp(this, BallMesh);
		Ball->SetUsingAbsoluteLocation(true);
		Ball->SetWorldLocation(GetActorTransform().TransformPosition(FVector(PitchLength + 650.f, -20.f, 110.f)));
	}
	SetState(EState::WalkBack);
}

void AGICricketGame::SetState(EState S)
{
	State = S;
	StateTime = 0.f;
}

void AGICricketGame::LaunchBall(const FVector& FromWorld, const FVector& ToWorld, float Duration, float ArcHeight, bool bBounce)
{
	BallFrom = FromWorld;
	BallTo = ToWorld;
	BallDur = FMath::Max(Duration, 0.05f);
	BallT = 0.f;
	BallArc = ArcHeight;
	bBallBounce = bBounce;
	if (Ball)
	{
		Ball->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		Ball->SetUsingAbsoluteLocation(true);
	}
}

FVector AGICricketGame::BallTargetNearPlayer() const
{
	const AGIPlayerCharacter* P = GetPlayer(this);
	if (!P)
	{
		return GetActorLocation();
	}
	const FVector Dir = (GetActorLocation() - P->GetActorLocation()).GetSafeNormal2D();
	FVector T = P->GetActorLocation() + Dir * 160.f;
	T.Z = GetActorLocation().Z + 4.f;
	return T;
}

bool AGICricketGame::GetWaitingBall(FVector& Out) const
{
	if (State == EState::WaitPlayer && Ball)
	{
		Out = Ball->GetComponentLocation();
		return true;
	}
	return false;
}

bool AGICricketGame::WantsBallFromPlayer(const AGIPlayerCharacter* Player) const
{
	return Player && State == EState::WaitPlayer && Ball && FVector::Dist2D(Player->GetActorLocation(), Ball->GetComponentLocation()) < 260.f;
}

void AGICricketGame::PlayerReturnsBall(AGIPlayerCharacter* Player)
{
	if (!WantsBallFromPlayer(Player))
	{
		return;
	}
	Thrower = Player;
	const FVector To = (Bowler.Comp ? Bowler.Comp->GetComponentLocation() : GetActorLocation()) - Player->GetActorLocation();
	Player->SetActorRotation(FRotator(0.f, To.Rotation().Yaw, 0.f));
	Player->PlayAction(EGIPoseMode::Throw, 1.15f, nullptr);
	if (Ball && Player->GetMesh())
	{
		Ball->SetUsingAbsoluteLocation(false);
		Ball->AttachToComponent(Player->GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, GHandR);
		Ball->SetRelativeLocation(FVector(0.f, 8.f, 0.f));
	}
	SetState(EState::PlayerThrow);
}

void AGICricketGame::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	StateTime += DeltaSeconds;
	ToPlayerCooldown -= DeltaSeconds;
	const FTransform& Xf = GetActorTransform();
	const FVector Crease(PitchLength, -20.f, 0.f), RunStart(PitchLength + 650.f, -20.f, 0.f);
	auto HandWorld = [](const FKid& K) { return K.Comp ? K.Comp->GetSocketLocation(GHandR) : FVector::ZeroVector; };

	// Ball flight.
	if (Ball && BallT < 1.f && (State == EState::Flight || State == EState::Hit || State == EState::Return || State == EState::Cheer))
	{
		BallT = FMath::Min(1.f, BallT + DeltaSeconds / BallDur);
		FVector P;
		if (bBallBounce)
		{
			// Pitches at 65% of the way, small hop after.
			const float B = 0.65f;
			if (BallT < B)
			{
				const float t = BallT / B;
				P = FMath::Lerp(BallFrom, FMath::Lerp(BallFrom, BallTo, B), t);
				P.Z = FMath::Lerp(BallFrom.Z, Xf.GetLocation().Z + 3.f, t * t);
			}
			else
			{
				const float t = (BallT - B) / (1.f - B);
				P = FMath::Lerp(FMath::Lerp(BallFrom, BallTo, B), BallTo, t);
				P.Z = FMath::Lerp(Xf.GetLocation().Z + 3.f, BallTo.Z, t) + 4.f * BallArc * t * (1.f - t);
			}
		}
		else
		{
			P = FMath::Lerp(BallFrom, BallTo, BallT);
			P.Z += 4.f * BallArc * BallT * (1.f - BallT);
		}
		Ball->SetWorldLocation(P);
	}

	switch (State)
	{
	case EState::WalkBack:
	{
		// Bowler walks back to his mark.
		const float A = FMath::Clamp(StateTime / 3.5f, 0.f, 1.f);
		PlaceKid(Bowler, FMath::Lerp(Crease, RunStart, A), 0.f, A < 1.f ? 120.f : 0.f);
		if (Ball && Bowler.Comp)
		{
			Ball->SetWorldLocation(HandWorld(Bowler));
		}
		if (StateTime > 4.6f)
		{
			SetState(EState::RunUp);
		}
		break;
	}
	case EState::RunUp:
	{
		const float A = FMath::Clamp(StateTime / 1.5f, 0.f, 1.f);
		PlaceKid(Bowler, FMath::Lerp(RunStart, Crease, A), 180.f, 380.f);
		if (Ball)
		{
			Ball->SetWorldLocation(HandWorld(Bowler));
		}
		if (A >= 1.f)
		{
			SetState(EState::Deliver);
		}
		break;
	}
	case EState::Deliver:
	{
		const float A = FMath::Clamp(StateTime / 0.6f, 0.f, 1.f);
		PlaceKid(Bowler, Crease, 180.f, 0.f);
		if (Bowler.Anim)
		{
			Bowler.Anim->Params.ActionAlpha = A;
		}
		if (Ball)
		{
			Ball->SetWorldLocation(HandWorld(Bowler));
		}
		if (A >= 0.62f)
		{
			LaunchBall(HandWorld(Bowler), Xf.TransformPosition(FVector(35.f, 25.f, 45.f)), 0.75f, 30.f, true);
			SetState(EState::Flight);
		}
		break;
	}
	case EState::Flight:
	{
		if (Bowler.Anim)
		{
			Bowler.Anim->Params.ActionAlpha = FMath::Min(1.f, 0.62f + StateTime / 0.6f);
		}
		if (Batsman.Anim)
		{
			Batsman.Anim->Params.ActionAlpha = FMath::Clamp((StateTime - 0.25f) / 0.75f, 0.f, 1.f);
		}
		if (BallT >= 1.f)
		{
			// Whack! Sometimes it rolls right to the player.
			const AGIPlayerCharacter* P = GetPlayer(this);
			bBallToPlayer = P && ToPlayerCooldown <= 0.f && FVector::Dist2D(P->GetActorLocation(), GetActorLocation()) < 2600.f
				&& FMath::Abs(P->GetActorLocation().Z - GetActorLocation().Z) < 300.f;
			if (bBallToPlayer)
			{
				LaunchBall(Ball->GetComponentLocation(), BallTargetNearPlayer(), 1.3f, 160.f, false);
			}
			else
			{
				if (FMath::FRand() < 0.35f)
				{
					GIVoice::Say(this, TEXT("kids_play"), GetActorLocation() + FVector(0, 0, 120.f), false);
				}
				CatcherIdx = Fielders.Num() > 0 ? FMath::RandRange(0, Fielders.Num() - 1) : 0;
				const FVector To = Fielders.IsValidIndex(CatcherIdx) ? HandWorld(Fielders[CatcherIdx]) : Xf.TransformPosition(RunStart);
				LaunchBall(Ball->GetComponentLocation(), To, 1.1f, 220.f, false);
			}
			SetState(EState::Hit);
		}
		break;
	}
	case EState::Hit:
	{
		if (Batsman.Anim)
		{
			Batsman.Anim->Params.ActionAlpha = FMath::Min(1.f, 0.6f + StateTime);
		}
		if (BallT >= 1.f)
		{
			if (Batsman.Anim)
			{
				Batsman.Anim->Params.ActionAlpha = 0.f;
			}
			if (Bowler.Anim)
			{
				Bowler.Anim->Params.ActionAlpha = 0.f;
			}
			if (bBallToPlayer)
			{
				ShoutTimer = 0.f;
				ToPlayerCooldown = 40.f;
				SetState(EState::WaitPlayer);
			}
			else
			{
				SetState(EState::Return);
			}
		}
		break;
	}
	case EState::Return:
	{
		// The fielder throws it back to the bowler.
		if (Fielders.IsValidIndex(CatcherIdx) && Fielders[CatcherIdx].Anim)
		{
			UGIAnimInstance* A = Fielders[CatcherIdx].Anim;
			A->Params.Mode = EGIPoseMode::Throw;
			A->Params.ActionAlpha = FMath::Clamp(StateTime / 0.9f, 0.f, 1.f);
			if (StateTime < 0.55f && Ball)
			{
				Ball->SetWorldLocation(HandWorld(Fielders[CatcherIdx]));
			}
			else if (StateTime >= 0.55f && StateTime - DeltaSeconds < 0.55f)
			{
				LaunchBall(HandWorld(Fielders[CatcherIdx]), HandWorld(Bowler), 0.9f, 140.f, false);
			}
			if (StateTime > 1.6f)
			{
				A->Params.Mode = EGIPoseMode::Talk;
				A->Params.ActionAlpha = 0.f;
				SetState(EState::WalkBack);
			}
		}
		else if (StateTime > 1.f)
		{
			SetState(EState::WalkBack);
		}
		break;
	}
	case EState::WaitPlayer:
	{
		ShoutTimer -= DeltaSeconds;
		if (ShoutTimer <= 0.f)
		{
			ShoutTimer = 6.f;
			GIVoice::Say(this, TEXT("kids_ball"), GetActorLocation() + FVector(0, 0, 120.f));
		}
		// Everyone looks at the player and waves.
		if (const AGIPlayerCharacter* P = GetPlayer(this))
		{
			for (FKid& F : Fielders)
			{
				if (F.Comp)
				{
					const float Yaw = (P->GetActorLocation() - F.Comp->GetComponentLocation()).Rotation().Yaw - Xf.Rotator().Yaw;
					F.Comp->SetRelativeRotation(FRotator(0.f, Yaw - 90.f, 0.f));
				}
			}
		}
		if (StateTime > 45.f)
		{
			// Someone runs and fetches it eventually.
			if (Ball)
			{
				LaunchBall(Ball->GetComponentLocation(), HandWorld(Bowler), 1.2f, 150.f, false);
			}
			SetState(EState::Cheer);
		}
		break;
	}
	case EState::PlayerThrow:
	{
		if (StateTime >= 0.7f && StateTime - DeltaSeconds < 0.7f && Ball)
		{
			const FVector From = Ball->GetComponentLocation();
			LaunchBall(From, HandWorld(Bowler) + FVector(0, 0, 20.f), 1.0f, 180.f, false);
			for (FKid* K : { &Batsman, &Bowler, &Keeper })
			{
				if (K->Anim)
				{
					K->Anim->Params.Mode = EGIPoseMode::Cheer;
				}
			}
			for (FKid& F : Fielders)
			{
				if (F.Anim)
				{
					F.Anim->Params.Mode = EGIPoseMode::Cheer;
				}
			}
			GIVoice::Say(this, TEXT("kids_cheer"), GetActorLocation() + FVector(0, 0, 120.f));
			if (AGIPlayerCharacter* P = Thrower.Get())
			{
				P->bReturnedBall = true;
			}
			SetState(EState::Cheer);
		}
		break;
	}
	case EState::Cheer:
	{
		if (StateTime > 3.2f)
		{
			if (Batsman.Anim) { Batsman.Anim->Params.Mode = EGIPoseMode::Bat; }
			if (Keeper.Anim) { Keeper.Anim->Params.Mode = EGIPoseMode::Bat; }
			if (Bowler.Anim) { Bowler.Anim->Params.Mode = EGIPoseMode::Bowl; }
			for (FKid& F : Fielders)
			{
				if (F.Anim)
				{
					F.Anim->Params.Mode = EGIPoseMode::Talk;
				}
				PlaceKid(F, F.Home, F.Yaw, 0.f);
			}
			SetState(EState::WalkBack);
		}
		break;
	}
	}
}

// ------------------------------------------------------------------------------------- weather
AGIWeather::AGIWeather()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Movable);
}

AGIWeather* AGIWeather::Get(const UObject* WorldContext)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGIWeather> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

UStaticMesh* AGIWeather::PickUmbrella(int32 Seed) const
{
	return UmbrellaMeshes.Num() > 0 ? UmbrellaMeshes[FMath::Abs(Seed) % UmbrellaMeshes.Num()].Get() : nullptr;
}

void AGIWeather::BeginPlay()
{
	Super::BeginPlay();
	for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It)
	{
		Sun = *It;
		SunBaseRotation = It->GetActorRotation();
		if (ULightComponent* L = It->GetLightComponent())
		{
			SunIntensity = L->Intensity;
			SunTemp = L->Temperature;
		}
		break;
	}
	for (TActorIterator<ASkyLight> It(GetWorld()); It; ++It)
	{
		Sky = *It;
		SkyIntensity = It->GetLightComponent()->Intensity;
		break;
	}
	for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
	{
		Fog = *It;
		FogDensity = It->GetComponent()->FogDensity;
		FogInscatter = It->GetComponent()->FogInscatteringLuminance;
		break;
	}
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (It->ActorHasTag(TEXT("StreetLight")))
		{
			StreetLights.Add(*It);
		}
		else if (It->ActorHasTag(TEXT("NightLight")))
		{
			NightLights.Add(*It);
		}
	}
	UStaticMesh* Cyl = RainCurtainMesh ? RainCurtainMesh.Get() : LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cyl && RainMaterial)
	{
		for (int32 i = 0; i < 2; ++i)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
			C->SetStaticMesh(Cyl);
			C->SetupAttachment(RootComponent);
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			C->SetCastShadow(false);
			C->SetRelativeScale3D(i == 0 ? FVector(34.f, 34.f, 26.f) : FVector(11.f, 11.f, 14.f));
			C->RegisterComponent();
			UMaterialInstanceDynamic* MID = C->CreateDynamicMaterialInstance(0, RainMaterial);
			if (MID)
			{
				MID->SetScalarParameterValue(TEXT("Tiling"), i == 0 ? 9.f : 4.f);
			}
			C->SetVisibility(false);
			(i == 0 ? Curtain : CurtainInner) = C;
		}
	}
	if (RainLoop)
	{
		RainAudio = NewObject<UAudioComponent>(this);
		RainAudio->SetupAttachment(RootComponent);
		RainAudio->SetSound(RainLoop);
		RainAudio->bAutoActivate = false;
		RainAudio->bIsUISound = true;   // 2D bed around the listener
		RainAudio->RegisterComponent();
	}
	Apply();
}

void AGIWeather::SetRaining(bool bRain)
{
	bWantRain = bRain;
}

void AGIWeather::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Elapsed += DeltaSeconds;
	if (AutoRainAfter >= 0.f && Elapsed > AutoRainAfter && !bWantRain)
	{
		AutoRainAfter = -1.f;
		SetRaining(true);
	}
	const float Prev = Rain;
	Rain = FMath::FInterpConstantTo(Rain, bWantRain ? 1.f : 0.f, DeltaSeconds, 1.f / 8.f);
	if (const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		if (PC->PlayerCameraManager)
		{
			SetActorLocation(PC->PlayerCameraManager->GetCameraLocation());
		}
	}
	if (!FMath::IsNearlyEqual(Prev, Rain) || Rain > 0.f)
	{
		Apply();
	}
	if (Rain > 0.6f)
	{
		ThunderTimer -= DeltaSeconds;
		if (ThunderTimer <= 0.f)
		{
			ThunderTimer = FMath::FRandRange(14.f, 30.f);
			if (ThunderSound)
			{
				UGameplayStatics::PlaySound2D(this, ThunderSound, FMath::FRandRange(0.6f, 1.f), FMath::FRandRange(0.85f, 1.1f));
			}
		}
	}
}

void AGIWeather::SetHour(float InHour)
{
	Hour = InHour;
	if (Hour >= 0.f && !Moon.IsValid())
	{
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (ADirectionalLight* M = GetWorld()->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), FVector(0, 0, 20000.f), FRotator(-48.f, 230.f, 0.f), P))
		{
			if (UDirectionalLightComponent* L = Cast<UDirectionalLightComponent>(M->GetLightComponent()))
			{
				L->SetMobility(EComponentMobility::Movable);
				L->SetAtmosphereSunLight(false);
				L->SetUseTemperature(true);
				L->SetTemperature(9800.f);
				L->SetIntensity(0.f);
				L->SetCastShadows(true);
				L->SetLightColor(FLinearColor(0.7f, 0.8f, 1.f));
			}
			Moon = M;
		}
	}
	Apply();
}

void AGIWeather::Apply()
{
	const float R = FMath::SmoothStep(0.f, 1.f, Rain);
	float Day = 1.f;
	float Dusk = 0.f;
	Night = 0.f;
	if (Hour >= 0.f)
	{
		// sun: rises in the east at 6, peaks at noon (~72 deg), sets at 18:30
		const float T = (Hour - 6.f) / 12.5f;
		const float Elev = 72.f * FMath::Sin(T * PI);
		Day = FMath::Clamp(Elev / 14.f, 0.f, 1.f);
		Dusk = FMath::Clamp(1.f - FMath::Abs(Elev - 4.f) / 22.f, 0.f, 1.f) * (Elev > -6.f ? 1.f : 0.f);
		Night = 1.f - FMath::SmoothStep(-7.f, 3.f, Elev);
		if (ADirectionalLight* S = Sun.Get())
		{
			const float Yaw = 75.f + FMath::Clamp(T, -0.2f, 1.2f) * 170.f;
			// below the horizon the light points up so the sky goes dark blue
			S->SetActorRotation(FRotator(-FMath::Max(Elev, -4.f), Yaw, 0.f));
		}
	}
	if (ADirectionalLight* S = Sun.Get())
	{
		if (ULightComponent* L = S->GetLightComponent())
		{
			L->SetIntensity(FMath::Lerp(SunIntensity, SunIntensity * 0.08f, R) * Day);
			const float Temp = FMath::Lerp(SunTemp, 3100.f, Dusk);
			L->SetTemperature(FMath::Lerp(Temp, 7600.f, R));
		}
	}
	if (ADirectionalLight* M = Moon.Get())
	{
		M->GetLightComponent()->SetIntensity(0.55f * Night * (1.f - 0.6f * R));
	}
	if (ASkyLight* S = Sky.Get())
	{
		S->GetLightComponent()->SetIntensity(FMath::Lerp(SkyIntensity, SkyIntensity * 0.7f, R) * FMath::Lerp(0.16f, 1.f, FMath::Max(Day, 1.f - Night)));
	}
	if (AExponentialHeightFog* F = Fog.Get())
	{
		F->GetComponent()->SetFogDensity(FMath::Lerp(FogDensity, FogDensity * 3.f, R));
		FLinearColor In = FMath::Lerp(FogInscatter, FLinearColor(0.75f, 0.45f, 0.28f), Dusk * 0.6f);
		In = FMath::Lerp(In, FLinearColor(0.025f, 0.03f, 0.05f), Night);
		F->GetComponent()->SetFogInscatteringColor(FMath::Lerp(In, FLinearColor(0.16f, 0.2f, 0.26f) * FMath::Lerp(1.f, 0.25f, Night), R));
	}
	const float Lamps = FMath::Max(R, FMath::SmoothStep(0.25f, 0.8f, Night + 0.3f * Dusk));
	for (const TWeakObjectPtr<AActor>& A : StreetLights)
	{
		if (const ALight* L = Cast<ALight>(A.Get()))
		{
			L->GetLightComponent()->SetVisibility(Lamps > 0.05f);
			L->GetLightComponent()->SetIntensity(5000.f * Lamps);
		}
	}
	for (const TWeakObjectPtr<AActor>& A : NightLights)
	{
		if (const ALight* L = Cast<ALight>(A.Get()))
		{
			const float N = FMath::SmoothStep(0.3f, 0.9f, Night + 0.25f * Dusk);
			L->GetLightComponent()->SetVisibility(N > 0.05f);
			L->GetLightComponent()->SetIntensity(1800.f * N);
		}
	}
	if (WeatherCollection)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, WeatherCollection, TEXT("Wetness"), R);
		UKismetMaterialLibrary::SetScalarParameterValue(this, WeatherCollection, TEXT("NightGlow"), 0.25f + 0.75f * FMath::Max(R, Night));
	}
	const AGIStory* Story = AGIStory::Get(this);
	const bool bCine = Story && Story->IsCinematic();
	for (UStaticMeshComponent* C : { Curtain.Get(), CurtainInner.Get() })
	{
		if (C)
		{
			C->SetVisibility(R > 0.02f && !bCine);
			if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(C->GetMaterial(0)))
			{
				// at night the lamp-lit streaks read too hard: thinner curtain
				MID->SetScalarParameterValue(TEXT("Amount"), R * (1.f - 0.5f * Night));
			}
		}
	}
	if (RainAudio)
	{
		if (R > 0.02f && !RainAudio->IsPlaying())
		{
			RainAudio->Play();
		}
		else if (R <= 0.02f && RainAudio->IsPlaying())
		{
			RainAudio->Stop();
		}
		RainAudio->SetVolumeMultiplier(FMath::Max(0.01f, R));
	}
}

// --------------------------------------------------------------------------------- level profile
AGILevelProfile* AGILevelProfile::Get(const UObject* WorldContext)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGILevelProfile> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

// -------------------------------------------------------------------------------- scripted walker
AGIScriptedWalker::AGIScriptedWalker()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Movable);
}

void AGIScriptedWalker::BeginPlay()
{
	Super::BeginPlay();
	A = GetActorLocation();
	B = EndPoint;
	T = FMath::Clamp(StartAlpha, 0.f, 1.f);
	if (Mesh)
	{
		Body = NewPerson(this, Mesh, EGIPoseMode::Locomotion, FMath::FRand() * 4.f);
		Body->SetUsingAbsoluteLocation(true);
		Body->SetUsingAbsoluteRotation(true);
		Anim = Cast<UGIAnimInstance>(Body->GetAnimInstance());
	}
	Yaw = (B - A).Rotation().Yaw;
}

void AGIScriptedWalker::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!Body)
	{
		return;
	}
	const float Len = FMath::Max(FVector::Dist2D(A, B), 1.f);
	float Want = Speed;
	if (Pause > 0.f)
	{
		Pause -= DeltaSeconds;
		Want = 0.f;
	}
	// ease in / out so the stride blends smoothly from idle to walk and back
	CurSpeed = FMath::FInterpTo(CurSpeed, Want, DeltaSeconds, 2.5f);
	T += Dir * CurSpeed * DeltaSeconds / Len;
	if (T >= 1.f || T <= 0.f)
	{
		T = FMath::Clamp(T, 0.f, 1.f);
		Dir = -Dir;
		Pause = PauseAtEnds;
	}
	const FVector P = FMath::Lerp(A, B, T);
	const float WantYaw = ((Dir > 0.f ? B - A : A - B)).Rotation().Yaw;
	Yaw = FMath::FixedTurn(Yaw, WantYaw, 140.f * DeltaSeconds);
	// keep the feet on the ground
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(GIWalker), false, this);
	float Z = P.Z;
	if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0, 0, 150.f), P - FVector(0, 0, 300.f), ECC_Visibility, Q))
	{
		Z = Hit.ImpactPoint.Z;
	}
	Body->SetWorldLocationAndRotation(FVector(P.X, P.Y, Z), FRotator(0.f, Yaw - 90.f, 0.f));
	if (Anim)
	{
		Anim->Params.Speed = CurSpeed;
	}
}

#undef LOCTEXT_NAMESPACE
