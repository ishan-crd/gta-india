#include "GIEditorLib.h"
#include "Animation/Skeleton.h"

bool UGIEditorLib::SetupSharedSkeleton(USkeleton* Skeleton, FName RootBone, FName HipsBone)
{
#if WITH_EDITOR
	if (!Skeleton)
	{
		return false;
	}
	const FReferenceSkeleton& Ref = Skeleton->GetReferenceSkeleton();
	const int32 RootIdx = Ref.FindBoneIndex(RootBone);
	const int32 HipsIdx = Ref.FindBoneIndex(HipsBone);
	if (HipsIdx == INDEX_NONE)
	{
		return false;
	}
	Skeleton->Modify();
	// Everything under the hips uses the target mesh's proportions.
	Skeleton->SetBoneTranslationRetargetingMode(HipsIdx, EBoneTranslationRetargetingMode::Skeleton, true);
	Skeleton->SetBoneTranslationRetargetingMode(HipsIdx, EBoneTranslationRetargetingMode::AnimationScaled, false);
	if (RootIdx != INDEX_NONE)
	{
		Skeleton->SetBoneTranslationRetargetingMode(RootIdx, EBoneTranslationRetargetingMode::Animation, false);
	}
	Skeleton->MarkPackageDirty();
	return true;
#else
	return false;
#endif
}

TArray<FName> UGIEditorLib::GetSkeletonBoneNames(USkeleton* Skeleton)
{
	TArray<FName> Names;
	if (Skeleton)
	{
		const FReferenceSkeleton& Ref = Skeleton->GetReferenceSkeleton();
		for (int32 i = 0; i < Ref.GetNum(); ++i)
		{
			Names.Add(Ref.GetBoneName(i));
		}
	}
	return Names;
}
