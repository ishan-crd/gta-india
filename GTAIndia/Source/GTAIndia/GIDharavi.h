#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GIDharavi.generated.h"

class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialParameterCollection;
class UAudioComponent;
class USoundBase;
class AGIPlayerCharacter;
class ADirectionalLight;
class ASkyLight;
class AExponentialHeightFog;
class APostProcessVolume;

/** Plays a random voice line of a category at a location, with a subtitle popup for the player. */
namespace GIVoice
{
	bool Say(UObject* WorldContext, FName Category, const FVector& Location, bool bSubtitle = true, FName Gender = NAME_None);
}

/**
 * Mumbai "tapri" chai stall: a chai-wallah pours from a raised kettle all day; the player can buy a
 * cutting chai (E) for Rs 10: he sips it (+10 HP) while the vendor chats - like the reference clip.
 */
UCLASS()
class GTAINDIA_API AGIChaiStall : public AActor
{
	GENERATED_BODY()

public:
	AGIChaiStall();

	/** Vendor stands this far behind the counter (+Y of the actor), facing the customer (-Y). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") TObjectPtr<USkeletalMesh> VendorMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") FVector VendorOffset = FVector(150.f, 70.f, 0.f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") TObjectPtr<UStaticMesh> KettleMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") TObjectPtr<UStaticMesh> GlassMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") int32 Price = 10;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Chai") float HealAmount = 10.f;

	bool CanServe(const AGIPlayerCharacter* Player) const;
	void Serve(AGIPlayerCharacter* Player);

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Vendor;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Kettle;
	float Cooldown = 0.f;
	float ReplyTimer = -1.f;
	float AmbientTimer = 6.f;
};

/**
 * Kids playing gully cricket in a lane: bowler runs in and bowls, the batsman swings, the ball flies to
 * the fielders - and sometimes rolls to the player: "Bhaiya, ball wapas do!". The player picks it up and
 * throws it back (E); the kids cheer.  Pitch runs along the actor's +X from the batsman's stumps.
 */
UCLASS()
class GTAINDIA_API AGICricketGame : public AActor
{
	GENERATED_BODY()

public:
	AGICricketGame();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") TArray<TObjectPtr<USkeletalMesh>> KidMeshes;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") TObjectPtr<UStaticMesh> StumpsMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") TObjectPtr<UStaticMesh> BatMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") TObjectPtr<UStaticMesh> BallMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") float PitchLength = 1500.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") float LaneHalfWidth = 380.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cricket") int32 NumFielders = 5;

	bool WantsBallFromPlayer(const AGIPlayerCharacter* Player) const;
	void PlayerReturnsBall(AGIPlayerCharacter* Player);

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	enum class EState : uint8 { WalkBack, RunUp, Deliver, Flight, Hit, Return, WaitPlayer, PlayerThrow, Cheer };

	struct FKid
	{
		USkeletalMeshComponent* Comp = nullptr;
		class UGIAnimInstance* Anim = nullptr;
		FVector Home = FVector::ZeroVector;    // actor space
		float Yaw = 0.f;                        // actor space, facing
	};

	FKid MakeKid(FRandomStream& Rand, const FVector& LocalPos, float Yaw, float Scale);
	void PlaceKid(FKid& K, const FVector& LocalPos, float Yaw, float Speed);
	void SetState(EState S);
	void LaunchBall(const FVector& FromWorld, const FVector& ToWorld, float Duration, float ArcHeight, bool bBounce);
	FVector BallTargetNearPlayer() const;

	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> PropComps;
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> KidComps;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Ball;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Bat;

	FKid Batsman, Bowler, Keeper;
	TArray<FKid> Fielders;
	EState State = EState::WalkBack;
	float StateTime = 0.f;
	int32 CatcherIdx = 0;
	// Ball flight (world space)
	FVector BallFrom = FVector::ZeroVector, BallTo = FVector::ZeroVector;
	float BallDur = 1.f, BallT = 0.f, BallArc = 0.f;
	bool bBallBounce = false;
	bool bBallToPlayer = false;
	float ToPlayerCooldown = 8.f;
	float ShoutTimer = 0.f;
	TWeakObjectPtr<AGIPlayerCharacter> Thrower;
};

/**
 * Mumbai weather: sunny morning by default; the monsoon rolls in (rain curtain around the camera, dark
 * overcast light, wet / mirror-like streets via MPC_Weather.Wetness, street lights and neon glowing,
 * people opening umbrellas, rain + thunder audio) and clears again.
 */
UCLASS()
class GTAINDIA_API AGIWeather : public AActor
{
	GENERATED_BODY()

public:
	AGIWeather();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TObjectPtr<UStaticMesh> RainCurtainMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TObjectPtr<UMaterialInterface> RainMaterial;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TObjectPtr<UMaterialParameterCollection> WeatherCollection;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TObjectPtr<USoundBase> RainLoop;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TObjectPtr<USoundBase> ThunderSound;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") TArray<TObjectPtr<UStaticMesh>> UmbrellaMeshes;
	/** Start raining this many seconds into the game (< 0: only when the mission / menu asks). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather") float AutoRainAfter = -1.f;

	static AGIWeather* Get(const UObject* WorldContext);
	void SetRaining(bool bRain);
	void SetRainingInstant(bool bRain) { bWantRain = bRain; Rain = bRain ? 1.f : 0.f; Apply(); }
	bool IsRaining() const { return bWantRain; }
	float GetRainAmount() const { return Rain; }
	UStaticMesh* PickUmbrella(int32 Seed) const;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void Apply();

	UPROPERTY() TObjectPtr<UStaticMeshComponent> Curtain;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> CurtainInner;
	UPROPERTY() TObjectPtr<UAudioComponent> RainAudio;
	TWeakObjectPtr<ADirectionalLight> Sun;
	TWeakObjectPtr<ASkyLight> Sky;
	TWeakObjectPtr<AExponentialHeightFog> Fog;
	TArray<TWeakObjectPtr<AActor>> StreetLights;
	float SunIntensity = 9.f, SkyIntensity = 1.f, FogDensity = 0.03f, SunTemp = 4600.f;
	FLinearColor FogInscatter = FLinearColor::White;
	bool bWantRain = false;
	float Rain = 0.f;
	float Elapsed = 0.f;
	float ThunderTimer = 12.f;
};

/**
 * Per-map presentation overrides (the Trial scene): chase-camera framing, lens, player model, no bag.
 * The player reads the first one found in the level at BeginPlay.
 */
UCLASS()
class GTAINDIA_API AGILevelProfile : public AActor
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") float ArmLength = 270.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") FVector SocketOffset = FVector(0.f, 8.f, 26.f);
	/** Horizontal FOV forced for this map (0 = use the player's setting). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") float FieldOfView = 75.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") float StartPitch = -5.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") float CameraLagSpeed = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera") float RotationLagSpeed = 14.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player") TObjectPtr<USkeletalMesh> PlayerMesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player") bool bHideBag = true;
	/** Walking pace for this scene (cm/s); 0 = default. A relaxed stroll reads more natural in a narrow lane. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Player") float WalkSpeed = 0.f;

	static AGILevelProfile* Get(const UObject* WorldContext);
};

/** An NPC that strolls back and forth between two points (e.g. the woman in the sari walking down the lane). */
UCLASS()
class GTAINDIA_API AGIScriptedWalker : public AActor
{
	GENERATED_BODY()

public:
	AGIScriptedWalker();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Walker") TObjectPtr<USkeletalMesh> Mesh;
	/** Second end of the walk, world space (the first end is the actor location). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Walker") FVector EndPoint = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Walker") float Speed = 105.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Walker") float PauseAtEnds = 4.f;
	/** Start part-way along the path (0..1), walking towards EndPoint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Walker") float StartAlpha = 0.f;

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Body;
	class UGIAnimInstance* Anim = nullptr;
	FVector A = FVector::ZeroVector, B = FVector::ZeroVector;
	float T = 0.f;
	float Dir = 1.f;
	float Pause = 0.f;
	float Yaw = 0.f;
	float CurSpeed = 0.f;
};
