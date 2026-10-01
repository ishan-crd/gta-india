#include "GIAssetSettings.h"
#include "Sound/SoundAttenuation.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

USoundAttenuation* UGIAssetSettings::MakeAttenuation(UObject* Outer, float Inner, float Falloff)
{
	USoundAttenuation* A = NewObject<USoundAttenuation>(Outer);
	A->Attenuation.bAttenuate = true;
	A->Attenuation.bSpatialize = true;
	A->Attenuation.AttenuationShape = EAttenuationShape::Sphere;
	A->Attenuation.AttenuationShapeExtents = FVector(Inner, 0.f, 0.f);
	A->Attenuation.FalloffDistance = Falloff;
	A->Attenuation.DistanceAlgorithm = EAttenuationDistanceModel::NaturalSound;
	return A;
}

void UGIAssetSettings::ApplyLookVariety(USkeletalMeshComponent* Comp, const FGICharacterLook& Look, FRandomStream& Rand)
{
	if (!Comp)
	{
		return;
	}
	// Typical Indian clothing colours: saffron, marigold, red, maroon, pink, green, royal blue, white, purple.
	static const FLinearColor Palette[] = {
		FLinearColor(1.f, 0.38f, 0.04f), FLinearColor(1.f, 0.72f, 0.06f), FLinearColor(0.85f, 0.06f, 0.05f),
		FLinearColor(0.45f, 0.04f, 0.08f), FLinearColor(0.95f, 0.3f, 0.55f), FLinearColor(0.1f, 0.55f, 0.2f),
		FLinearColor(0.1f, 0.25f, 0.8f), FLinearColor(0.95f, 0.93f, 0.88f), FLinearColor(0.45f, 0.15f, 0.6f) };
	if (Look.MaterialVariants.Num() > 0)
	{
		const int32 Pick = Rand.RandRange(-1, Look.MaterialVariants.Num() - 1); // -1 keeps the original
		if (Pick >= 0)
		{
			if (UMaterialInterface* M = Look.MaterialVariants[Pick].LoadSynchronous())
			{
				Comp->SetMaterial(0, M);
			}
		}
	}
	for (const FName& Slot : Look.TintSlots)
	{
		const int32 Idx = Comp->GetMaterialIndex(Slot);
		if (Idx == INDEX_NONE)
		{
			continue;
		}
		if (UMaterialInstanceDynamic* MID = Comp->CreateDynamicMaterialInstance(Idx))
		{
			const bool bTint = Rand.FRand() < 0.8f;
			MID->SetVectorParameterValue(TEXT("OutfitTint"), Palette[Rand.RandRange(0, UE_ARRAY_COUNT(Palette) - 1)]);
			MID->SetScalarParameterValue(TEXT("OutfitTintStrength"), bTint ? Rand.FRandRange(0.7f, 0.95f) : 0.f);
		}
	}
}
