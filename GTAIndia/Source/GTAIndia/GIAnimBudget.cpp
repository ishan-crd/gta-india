#include "GIAnimBudget.h"
#include "SkeletalMeshComponentBudgeted.h"
#include "IAnimationBudgetAllocator.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"

namespace
{
	// Nearer and visible people matter more; off-screen ones barely tick.
	float CalcSignificance(USkeletalMeshComponentBudgeted* C)
	{
		const UWorld* World = C ? C->GetWorld() : nullptr;
		const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (!PC || !PC->PlayerCameraManager)
		{
			return 1.f;
		}
		const float Dist = FVector::Dist(C->GetComponentLocation(), PC->PlayerCameraManager->GetCameraLocation());
		float S = FMath::Clamp(1.f - Dist / 15000.f, 0.02f, 1.f);
		if (!C->WasRecentlyRendered(0.2f))
		{
			S *= 0.2f;
		}
		return S;
	}
}

USkeletalMeshComponent* GIAnimBudget::NewPersonComponent(UObject* Outer)
{
	static bool bBound = false;
	if (!bBound)
	{
		USkeletalMeshComponentBudgeted::OnCalculateSignificance().BindStatic(&CalcSignificance);
		bBound = true;
	}
	if (Outer)
	{
		EnableForWorld(Outer->GetWorld());   // before the component registers with the allocator
	}
	USkeletalMeshComponentBudgeted* C = NewObject<USkeletalMeshComponentBudgeted>(Outer);
	C->SetAutoCalculateSignificance(true);
	C->bUpdateOverlapsOnAnimationFinalize = false;
	return C;
}

void GIAnimBudget::EnableForWorld(UWorld* World)
{
	if (IAnimationBudgetAllocator* A = World ? IAnimationBudgetAllocator::Get(World) : nullptr)
	{
		if (!A->GetEnabled())
		{
			A->SetEnabled(true);
		}
	}
}
