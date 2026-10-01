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

UENUM(BlueprintType)
enum class EGIObjectiveKind : uint8
{
	Reach,        // walk to Location (Radius)
	Chai,         // buy a cutting chai at a tapri
	ReturnBall,   // throw the kids' cricket ball back
	Monsoon,      // reach Location: the monsoon breaks
};

/** One step of a walk-around mission (used by the Dharavi map). */
USTRUCT(BlueprintType)
struct FGIObjective
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FString Text;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FString DoneBanner;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") EGIObjectiveKind Kind = EGIObjectiveKind::Reach;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FVector Location = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") float Radius = 400.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") int32 Reward = 0;
};

/** "Ganga Paar Delivery" (Varanasi), or - when Objectives is filled - a chain of walk-around objectives
 *  (Dharavi: chai at the tapri, the kids' ball, the main road as the monsoon breaks). */
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
	/** Walk-around mode: title + objective chain instead of the delivery. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") FString TourTitle;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mission") TArray<FGIObjective> Objectives;

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
	int32 ObjectiveIndex = 0;
	bool IsTour() const { return Objectives.Num() > 0; }
	void TickTour(class AGIPlayerCharacter* Player, const FVector& P);
	void RefreshMarker();
};
