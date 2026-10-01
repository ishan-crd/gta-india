#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GITraffic.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class USkeletalMeshComponent;

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
	/** Per-mesh yaw so the model's front faces the travel direction (same order as VehicleMeshes). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") TArray<float> VehicleMeshYaws;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float MinX = -52000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float MaxX = 52000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traffic") float Speed = 900.f;

	/** Is there a vehicle the player could take within MaxDist? */
	bool HasVehicleNear(const FVector& Location, float MaxDist) const;
	/** Pull the nearest vehicle out of traffic (its people get off) so the player can drive it. */
	bool TakeVehicle(const FVector& Location, float MaxDist, FTransform& OutTransform, UStaticMesh*& OutMesh, float& OutMeshYaw, bool& bOutFourWheeler);

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
		float MeshYaw = 0.f;
		float HalfLen = 150.f;
		bool bFourWheeler = false;
		TArray<USkeletalMeshComponent*> Riders;
		TArray<FVector> RiderOffsets;      // in the travel frame (X forward), from the ground under the vehicle
	};
	void AddRiders(FVehicle& V, FRandomStream& Rand);
	void AddRider(FVehicle& V, FRandomStream& Rand, const FVector& PelvisOffset, bool bDriver);
	float SignificanceTimer = 0.f;
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> RiderComps;
	TArray<FVehicle> Vehicles;
	float HitCooldown = 0.f;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Comps;
};
