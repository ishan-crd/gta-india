#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GIMission.generated.h"

class UStaticMeshComponent;
class AGIPlayerCharacter;

UENUM(BlueprintType)
enum class EGIMissionStage : uint8
{
	ToPickup,
	ToGhat,
	CrossRiver,
	Delivered,
};

/** "Ganga Paar Delivery": pick up food in town, cross the Ganga, deliver at Ramnagar Ghat. */
UCLASS()
class GTAINDIA_API AGIMission : public AActor
{
	GENERATED_BODY()

public:
	AGIMission();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FVector PickupLocation = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FVector GhatLocation = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FVector DropLocation = FVector::ZeroVector;
	/** Y below which the player counts as being on the far (east) bank. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") float FarBankY = -15000.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") float TimeLimit = 420.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") int32 BaseReward = 150;

	/** Slow dolly shot behind the title menu. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Title") FVector TitleCamStart = FVector(-6000.f, -9000.f, 2500.f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Title") FVector TitleCamEnd = FVector(6000.f, -9000.f, 2200.f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Title") FVector TitleCamLookAt = FVector(0.f, 3000.f, 1200.f);

	UPROPERTY(VisibleAnywhere, Category = "Mission") TObjectPtr<UStaticMeshComponent> Marker;

	EGIMissionStage GetStage() const { return Stage; }
	FText GetTitle() const;
	FText GetObjective() const;
	bool GetTarget(FVector& Out) const;
	/** Seconds left on the delivery timer, < 0 when no timer runs. */
	float GetTimeLeft() const { return bTimerRunning ? TimeLeft : -1.f; }
	/** Big centre-screen banner (e.g. "ORDER DELIVERED!"), empty when none. */
	FText GetBanner(float& OutAlpha) const;

	static AGIMission* Get(const UObject* WorldContext);

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void SetStage(EGIMissionStage NewStage);
	void ShowBanner(const FText& Text, float Duration = 4.f);
	AGIPlayerCharacter* GetPlayer() const;

	EGIMissionStage Stage = EGIMissionStage::ToPickup;
	bool bTimerRunning = false;
	bool bAnnouncedFarBank = false;
	float TimeLeft = 0.f;
	float StageTimer = 0.f;
	FText Banner;
	float BannerTime = 0.f;
	float BannerDuration = 1.f;
	int32 OrdersDone = 0;
};
