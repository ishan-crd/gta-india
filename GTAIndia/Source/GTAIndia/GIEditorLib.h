#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GIEditorLib.generated.h"

class USkeleton;

/** Small editor helpers called from the Python build scripts. */
UCLASS()
class GTAINDIA_API UGIEditorLib : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Make one skeleton usable by many body shapes: bones below the hips take translation from the
	 * mesh (Skeleton mode), the hips are scaled by height, the root keeps animation translation.
	 */
	UFUNCTION(BlueprintCallable, Category = "GTAIndia|Editor")
	static bool SetupSharedSkeleton(USkeleton* Skeleton, FName RootBone, FName HipsBone);

	/** Returns the bone names of a skeleton (debug helper for scripts). */
	UFUNCTION(BlueprintCallable, Category = "GTAIndia|Editor")
	static TArray<FName> GetSkeletonBoneNames(USkeleton* Skeleton);
};
