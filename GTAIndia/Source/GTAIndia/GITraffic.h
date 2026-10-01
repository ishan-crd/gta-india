#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GITraffic.generated.h"

class UStaticMesh;
class UStaticMeshComponent;

/** One straight traffic lane along X (vehicles wrap around at the ends). */
USTRUCT(BlueprintType)
struct FGITrafficLane
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float Y = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float Z = 0.f;
	/** +1 drives towards +X, -1 towards -X. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float Direction = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") int32 Count = 6;
};

/**
 * Kinematic road traffic (autos, bikes): vehicles glide along lanes, slow down behind each other
 * and for the player, and honk. Solid, so they can knock the player around.
 */
UCLASS()
class GTAINDIA_API AGITraffic : public AActor
{
	GENERATED_BODY()

public:
	AGITraffic();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") TArray<FGITrafficLane> Lanes;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") TArray<TObjectPtr<UStaticMesh>> VehicleMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float MinX = -52000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float MaxX = 52000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float Speed = 900.f;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FVehicle
	{
		UStaticMeshComponent* Comp = nullptr;
		int32 Lane = 0;
		float X = 0.f;
		float Speed = 0.f;
		float MaxSpeed = 0.f;
		float Wobble = 0.f;
	};
	TArray<FVehicle> Vehicles;
	float HitCooldown = 0.f;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Comps;
};
