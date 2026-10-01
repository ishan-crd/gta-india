#include "GIScatter.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"

AGIScatter::AGIScatter()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Static);
}

void AGIScatter::BuildInstances()
{
	TArray<UInstancedStaticMeshComponent*> Existing;
	GetComponents<UInstancedStaticMeshComponent>(Existing);
	for (UInstancedStaticMeshComponent* C : Existing)
	{
		RemoveInstanceComponent(C);
		C->DestroyComponent();
	}
	CreateComponents(true);
}

void AGIScatter::BeginPlay()
{
	Super::BeginPlay();
	// Safety net: if the saved level has no components (e.g. an older build), build them now.
	TArray<UInstancedStaticMeshComponent*> Existing;
	GetComponents<UInstancedStaticMeshComponent>(Existing);
	if (Existing.Num() == 0 && Items.Num() > 0)
	{
		CreateComponents(false);
	}
}

void AGIScatter::CreateComponents(bool bPersistent)
{
	for (int32 i = 0; i < Items.Num(); ++i)
	{
		const FGIScatterItem& Item = Items[i];
		if (!Item.Mesh || Item.Transforms.Num() == 0)
		{
			continue;
		}
		UInstancedStaticMeshComponent* ISM = NewObject<UInstancedStaticMeshComponent>(this, NAME_None, RF_Transactional);
		ISM->CreationMethod = bPersistent ? EComponentCreationMethod::Instance : EComponentCreationMethod::Native;
		ISM->SetMobility(bPersistent ? EComponentMobility::Static : EComponentMobility::Movable);
		ISM->SetupAttachment(RootComponent);
		ISM->SetStaticMesh(Item.Mesh);
		for (int32 m = 0; m < Item.Materials.Num(); ++m)
		{
			if (Item.Materials[m])
			{
				ISM->SetMaterial(m, Item.Materials[m]);
			}
		}
		ISM->SetCollisionEnabled(Item.bCollision ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		ISM->SetCollisionProfileName(Item.bCollision ? UCollisionProfile::BlockAll_ProfileName : UCollisionProfile::NoCollision_ProfileName);
		ISM->SetCastShadow(Item.bCastShadow);
		if (Item.CullDistance > 0.f)
		{
			ISM->SetCullDistances(FMath::RoundToInt(Item.CullDistance * 0.8f), FMath::RoundToInt(Item.CullDistance));
		}
		ISM->RegisterComponent();
		ISM->AddInstances(Item.Transforms, false, false);
		if (bPersistent)
		{
			AddInstanceComponent(ISM);
		}
	}
}
