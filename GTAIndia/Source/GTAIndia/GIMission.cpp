#include "GIMission.h"
#include "GIAssetSettings.h"
#include "GIPlayerCharacter.h"
#include "GIBike.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Sound/SoundBase.h"

#define LOCTEXT_NAMESPACE "GTAIndia"

AGIMission::AGIMission()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Marker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Marker"));
	Marker->SetupAttachment(RootComponent);
	Marker->SetUsingAbsoluteLocation(true);
	Marker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Marker->SetCastShadow(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cyl(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cyl.Succeeded())
	{
		Marker->SetStaticMesh(Cyl.Object);
	}
	Marker->SetWorldScale3D(FVector(2.4f, 2.4f, 1.6f));
}

AGIMission* AGIMission::Get(const UObject* WorldContext)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGIMission> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

AGIPlayerCharacter* AGIMission::GetPlayer() const
{
	// The player may be on the bike: look up the character either way.
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (AGIPlayerCharacter* C = Cast<AGIPlayerCharacter>(Pawn))
	{
		return C;
	}
	for (TActorIterator<AGIPlayerCharacter> It(GetWorld()); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

void AGIMission::BeginPlay()
{
	Super::BeginPlay();
	if (UMaterialInterface* Mat = UGIAssetSettings::Get().MarkerMaterial.LoadSynchronous())
	{
		Marker->SetMaterial(0, Mat);
	}
	else
	{
		Marker->SetVisibility(false);
	}
	SetStage(EGIMissionStage::ToPickup);
}

FText AGIMission::GetTitle() const
{
	return LOCTEXT("MissionTitle", "Mission: [Ganga Paar Delivery]");
}

FText AGIMission::GetObjective() const
{
	switch (Stage)
	{
	case EGIMissionStage::ToPickup: return LOCTEXT("ObjPickup", "Sharma Bhojnalaya se order uthao.");
	case EGIMissionStage::ToGhat: return LOCTEXT("ObjGhat", "Dashashwamedh Ghat pahuncho. Bike ya train, jaise marzi!");
	case EGIMissionStage::CrossRiver: return LOCTEXT("ObjCross", "Ganga paar karke Ramnagar Ghat pe order do.");
	case EGIMissionStage::Delivered: return LOCTEXT("ObjDone", "Order deliver ho gaya! Naya order Sharma Bhojnalaya pe...");
	}
	return FText::GetEmpty();
}

bool AGIMission::GetTarget(FVector& Out) const
{
	switch (Stage)
	{
	case EGIMissionStage::ToPickup: Out = PickupLocation; return true;
	case EGIMissionStage::ToGhat: Out = GhatLocation; return true;
	case EGIMissionStage::CrossRiver: Out = DropLocation; return true;
	default: return false;
	}
}

FText AGIMission::GetBanner(float& OutAlpha) const
{
	if (BannerTime <= 0.f)
	{
		OutAlpha = 0.f;
		return FText::GetEmpty();
	}
	const float Elapsed = BannerDuration - BannerTime;
	OutAlpha = FMath::Clamp(FMath::Min(Elapsed / 0.3f, BannerTime / 0.6f), 0.f, 1.f);
	return Banner;
}

void AGIMission::ShowBanner(const FText& Text, float Duration)
{
	Banner = Text;
	BannerTime = BannerDuration = Duration;
}

void AGIMission::SetStage(EGIMissionStage NewStage)
{
	Stage = NewStage;
	StageTimer = 0.f;
	FVector Target;
	const bool bHas = GetTarget(Target);
	Marker->SetVisibility(bHas && Marker->GetMaterial(0) != nullptr);
	if (bHas)
	{
		Marker->SetWorldLocation(Target - FVector(0, 0, 20.f));
	}
}

void AGIMission::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	BannerTime = FMath::Max(0.f, BannerTime - DeltaSeconds);
	StageTimer += DeltaSeconds;

	AGIPlayerCharacter* Player = GetPlayer();
	if (!Player || Player->IsDead())
	{
		return;
	}
	const FVector P = Player->IsRiding() ? Player->GetRidingBike()->GetActorLocation() : Player->GetActorLocation();

	if (bTimerRunning)
	{
		TimeLeft -= DeltaSeconds;
	}

	// Gentle pulse on the marker.
	const float Pulse = 1.f + 0.06f * FMath::Sin(GetWorld()->GetTimeSeconds() * 3.f);
	Marker->SetWorldScale3D(FVector(2.4f * Pulse, 2.4f * Pulse, 1.6f));

	switch (Stage)
	{
	case EGIMissionStage::ToPickup:
		if (FVector::Dist(P, PickupLocation) < 300.f)
		{
			TimeLeft = TimeLimit;
			bTimerRunning = true;
			bAnnouncedFarBank = false;
			ShowBanner(LOCTEXT("GotOrder", "Order mila! Ramnagar Ghat - jaldi!"));
			Player->RespawnTransform = Player->GetActorTransform();
			if (!Player->IsRiding())
			{
				Player->PlayPickUp();
			}
			SetStage(EGIMissionStage::ToGhat);
		}
		break;
	case EGIMissionStage::ToGhat:
		if (FVector::Dist2D(P, GhatLocation) < 900.f || Player->IsSwimming())
		{
			ShowBanner(LOCTEXT("AtGhat", "Dashashwamedh Ghat! Ab Ganga paar karo."), 3.5f);
			if (!Player->IsSwimming())
			{
				Player->RespawnTransform = Player->GetActorTransform();
			}
			SetStage(EGIMissionStage::CrossRiver);
		}
		break;
	case EGIMissionStage::CrossRiver:
		if (!bAnnouncedFarBank && P.Y < FarBankY && !Player->IsSwimming())
		{
			bAnnouncedFarBank = true;
			ShowBanner(LOCTEXT("FarBank", "Ganga paar pahunch gaye!"), 3.f);
		}
		if (FVector::Dist(P, DropLocation) < 350.f)
		{
			const int32 TimeBonus = TimeLeft > 0.f ? FMath::RoundToInt(TimeLeft / 3.f) : 0;
			const int32 Reward = TimeLeft > 0.f ? BaseReward + TimeBonus : BaseReward / 3;
			Player->AddMoney(Reward);
			if (USoundBase* S = UGIAssetSettings::Get().Cash.LoadSynchronous())
			{
				UGameplayStatics::PlaySound2D(this, S);
			}
			bTimerRunning = false;
			++OrdersDone;
			ShowBanner(TimeLeft > 0.f
				? FText::Format(LOCTEXT("Delivered", "ORDER DELIVERED!  +₹{0}"), FText::AsNumber(Reward))
				: FText::Format(LOCTEXT("DeliveredLate", "Late delivery... sirf +₹{0}"), FText::AsNumber(Reward)), 5.f);
			Player->RestoreHealth();
			SetStage(EGIMissionStage::Delivered);
		}
		break;
	case EGIMissionStage::Delivered:
		if (StageTimer > 8.f)
		{
			// Next order: back to Sharma Bhojnalaya (boat back or swim, your call).
			SetStage(EGIMissionStage::ToPickup);
		}
		break;
	}
}

#undef LOCTEXT_NAMESPACE
