#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GIAnimInstance.h"
#include "GICrowdManager.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;

/** A straight walking lane (people walk back and forth along it). */
USTRUCT(BlueprintType)
struct FGIWalkLane
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") FVector Start = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") FVector End = FVector::ZeroVector;
	/** Lateral spread (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float Width = 300.f;
	/** Relative share of walkers. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float Weight = 1.f;
};

/** A spot where someone stands / sits / bathes. */
USTRUCT(BlueprintType)
struct FGIStaticSpot
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") FVector Location = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float Yaw = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") EGIPoseMode Mode = EGIPoseMode::Locomotion;
	/** Spots with higher priority are filled first when the crowd budget is small. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float Priority = 0.5f;
	/** If true, Location.Z is used as is (no ground trace), e.g. bathers in the river. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") bool bFixedZ = false;
};

/**
 * Lightweight crowd: one actor drives many skeletal mesh components (no per-person actors or
 * character movement). Count scales with the Crowd Density setting.
 */
UCLASS()
class GTAINDIA_API AGICrowdManager : public AActor
{
	GENERATED_BODY()

public:
	AGICrowdManager();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") TArray<FGIWalkLane> Lanes;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") TArray<FGIStaticSpot> Spots;
	/** Fraction of the crowd budget used by this manager (the train uses the rest). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float BudgetShare = 0.7f;
	/** Share of this manager's budget that walks (rest fills static spots). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float WalkerShare = 0.6f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float CullDistance = 16000.f;
	/** The crowd follows the player: people further than this (and off screen) are moved to free lanes /
	 *  spots around the player, so the whole budget is spent where it is seen. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") float BubbleRadius = 8500.f;
	/** Voice-line category for background chatter (Varanasi: ambient, Mumbai: mumbai). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Crowd") FName AmbientCategory = TEXT("ambient");

	/** Rebuilds the crowd (called after the settings menu changes density). */
	void Rebuild();

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FPerson
	{
		USkeletalMeshComponent* Comp = nullptr;
		UGIAnimInstance* Anim = nullptr;
		int32 Lane = INDEX_NONE;
		float T = 0.f;
		float Dir = 1.f;
		float Lateral = 0.f;
		float Speed = 120.f;
		float GroundZ = 0.f;
		float NextTrace = 0.f;
		float PauseTime = 0.f;
		float Yaw = 0.f;
		float Dodge = 0.f;
		FName Gender;
		float SpeakCooldown = 0.f;
		float AngryTimer = 0.f;
		EGIPoseMode BaseMode = EGIPoseMode::Locomotion;
		float BaseYaw = 0.f;
		bool bSitting = false;
		int32 Spot = INDEX_NONE;
		UStaticMeshComponent* Umbrella = nullptr;
	};
	void UpdateUmbrellas();
	bool bUmbrellasOut = false;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> UmbrellaComps;

	struct FLaneCand
	{
		int32 Lane = 0;
		float T = 0.f;
		float HalfSpan = 0.f;
		float Weight = 0.f;
	};
	FVector BubbleCenter() const;
	void GatherLanes(const FVector& Center, TArray<FLaneCand>& Out) const;
	bool PickLanePoint(const TArray<FLaneCand>& Cands, const FVector& Center, const FVector* Cam, const FVector& CamFwd, FRandomStream& Rand,
		int32& OutLane, float& OutT, float& OutLat) const;
	static bool IsInView(const FVector& Pos, const FVector& Cam, const FVector& CamFwd);
	void PlaceWalker(FPerson& P, int32 Lane, float T, float Lat, FRandomStream& Rand);
	void PlaceStatic(FPerson& P, int32 SpotIdx, FRandomStream& Rand);
	void UpdateBubble();
	TArray<bool> SpotUsed;
	float BubbleTimer = 0.f;
	FRandomStream BubbleRand;

	void Clear();
	USkeletalMeshComponent* SpawnComp(FRandomStream& Rand, FName* OutGender = nullptr);
	void UpdateSpeech(float DeltaSeconds);
	bool Say(FPerson& P, FName Category, bool bSubtitle);
	void React(FPerson& P, const FVector& PlayerLoc);
	float AmbientTimer = 3.f;
	float BumpCooldown = 0.f;
	float BikeCooldown = 0.f;
	float SwimCooldown = 0.f;
	bool bPlayerWasSwimming = false;
	UPROPERTY() TObjectPtr<class USoundAttenuation> VoiceAttenuation;
	bool Ground(const FVector& P, float& OutZ) const;

	TArray<FPerson> People;
	float SignificanceTimer = 0.f;
	void UpdateSignificance();
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> Comps;
	float TotalLaneWeight = 0.f;
};
