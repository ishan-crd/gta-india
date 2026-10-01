#include "GIRiver.h"
#include "GIAssetSettings.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "UObject/ConstructorHelpers.h"

TWeakObjectPtr<AGIRiver> AGIRiver::Cached;

AGIRiver::AGIRiver()
{
	PrimaryActorTick.bCanEverTick = false;

	Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Surface"));
	RootComponent = Surface;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> PlaneMesh(TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (PlaneMesh.Succeeded())
	{
		Surface->SetStaticMesh(PlaneMesh.Object);
	}
	Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Surface->SetCastShadow(false);
	Surface->bAffectDistanceFieldLighting = false;
}

void AGIRiver::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	UpdateSurface();
}

void AGIRiver::UpdateSurface()
{
	// Engine plane is 100x100 cm.
	Surface->SetWorldScale3D(FVector(HalfExtent.X / 50.f, HalfExtent.Y / 50.f, 1.f));
	if (UMaterialInterface* Mat = UGIAssetSettings::Get().WaterMaterial.LoadSynchronous())
	{
		Surface->SetMaterial(0, Mat);
	}
}

void AGIRiver::BeginPlay()
{
	Super::BeginPlay();
	Cached = this;
	UpdateSurface();
}

void AGIRiver::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Cached.Get() == this)
	{
		Cached.Reset();
	}
	Super::EndPlay(Reason);
}

bool AGIRiver::IsInWaterArea(const FVector& WorldPos) const
{
	const FVector Local = WorldPos - GetActorLocation();
	return FMath::Abs(Local.X) <= HalfExtent.X && FMath::Abs(Local.Y) <= HalfExtent.Y;
}

float AGIRiver::GetDepth(const FVector& WorldPos, float GroundZ) const
{
	if (!IsInWaterArea(WorldPos))
	{
		return 0.f;
	}
	return GetWaterZ() - GroundZ;
}

AGIRiver* AGIRiver::Get(const UObject* WorldContext)
{
	if (Cached.IsValid())
	{
		return Cached.Get();
	}
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGIRiver> It(World); It; ++It)
	{
		Cached = *It;
		return *It;
	}
	return nullptr;
}
