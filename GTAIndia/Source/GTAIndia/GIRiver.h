#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GIRiver.generated.h"

class UStaticMeshComponent;

/**
 * The Ganga. Defines the water surface height and the XY area where water exists, and renders the
 * surface as a large plane. Swimming / wading logic queries this actor.
 */
UCLASS()
class GTAINDIA_API AGIRiver : public AActor
{
	GENERATED_BODY()

public:
	AGIRiver();

	/** Water surface height (world Z). Taken from the actor location. */
	float GetWaterZ() const { return GetActorLocation().Z; }

	/** True if the XY position lies inside the water area. Terrain above the surface is handled by depth checks. */
	bool IsInWaterArea(const FVector& WorldPos) const;

	/** Water depth at a point given the ground height below it (<= 0 means dry). */
	float GetDepth(const FVector& WorldPos, float GroundZ) const;

	/** Returns the river in this world (cached). */
	static AGIRiver* Get(const UObject* WorldContext);

	/** Half size of the water area in X / Y (cm), centred on the actor. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "River")
	FVector2D HalfExtent = FVector2D(60000.f, 11000.f);

	UPROPERTY(VisibleAnywhere, Category = "River")
	TObjectPtr<UStaticMeshComponent> Surface;

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	static TWeakObjectPtr<AGIRiver> Cached;
	void UpdateSurface();
};
