#pragma once

#include "CoreMinimal.h"

class UObject;
class UWorld;
class USkeletalMeshComponent;

/**
 * Crowd animation budgeting (Animation Budget Allocator plugin): every person mesh (crowd, train roof,
 * traffic riders, pillions) is a USkeletalMeshComponentBudgeted whose tick rate is throttled to keep the
 * total animation cost inside a fixed per-frame budget (a.Budget.BudgetMs), nearest / on-screen first.
 */
namespace GIAnimBudget
{
	/** Create a person mesh component (budgeted, auto significance, no overlap updates). Register it yourself. */
	USkeletalMeshComponent* NewPersonComponent(UObject* Outer);
	/** Turn the allocator on for this world (safe to call repeatedly). */
	void EnableForWorld(UWorld* World);
}
