#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GITrain.generated.h"

class UStaticMeshComponent;
class USkeletalMeshComponent;
class UAudioComponent;

/**
 * Overcrowded passenger train running along the riverfront line (straight track along X).
 * Cars are solid so the player can stand on the roof; people sit on the roof edges and hang
 * from the doors.
 */
UCLASS()
class GTAINDIA_API AGITrain : public AActor
{
	GENERATED_BODY()

public:
	AGITrain();

	UPROPERTY(EditAnywhere, Category = "Train") int32 NumCars = 9;
	/** cm/s along +X (negative runs the other way). */
	UPROPERTY(EditAnywhere, Category = "Train") float Speed = 1100.f;
	UPROPERTY(EditAnywhere, Category = "Train") float TrackStartX = -70000.f;
	UPROPERTY(EditAnywhere, Category = "Train") float TrackEndX = 70000.f;
	UPROPERTY(EditAnywhere, Category = "Train") float CarGap = 80.f;
	/** Fraction of the crowd budget that rides on this train. */
	UPROPERTY(EditAnywhere, Category = "Train") float CrowdShare = 0.85f;
	/** Door centres along each car, cm from the car centre (EMU: three doors per side). */
	UPROPERTY(EditAnywhere, Category = "Train") TArray<float> DoorOffsets = { -700.f, 0.f, 700.f };
	/** Mumbai local: riders only hang out of / stand in the doors, nobody on the roof. */
	UPROPERTY(EditAnywhere, Category = "Train") bool bDoorRidersOnly = false;

	/** Closest point on a car roof within MaxDist (XY) of Location. */
	bool GetRoofPointNear(const FVector& Location, float MaxDist, FVector& OutPoint) const;

	/** Returns true if the component belongs to this train (used for "on the train" checks). */
	bool OwnsComponent(const UPrimitiveComponent* Comp) const;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void BuildCars();
	void BuildRiders();

	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Cars;
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> Riders;
	UPROPERTY() TObjectPtr<UAudioComponent> Rumble;
	float HornTimer = 5.f;
	float SignificanceTimer = 0.f;
	float HitCooldown = 0.f;
	void CheckPlayerHit(float DeltaSeconds);

	float CarLength = 2400.f;
	float CarWidth = 320.f;
	float CarHeight = 420.f;
	float TrainLength = 0.f;
};
