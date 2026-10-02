#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GIAnimInstance.h"
#include "GIStory.generated.h"

class ACameraActor;
class UAudioComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
class USoundBase;
class AGIPlayerCharacter;
class UGIAnimInstance;

UENUM(BlueprintType)
enum class EGIBeatKind : uint8
{
	Scene,       // a cutscene plays as soon as the beat starts
	TalkTo,      // walk up to Npc and press E: its scene plays
	Reach,       // get to Location (optional time limit), then the scene
	Follow,      // Npc leads along Path and waits for you
	Tail,        // Npc walks Path; keep your distance - too close or too far fails
	Chai,        // buy a cutting chai, then the scene
	ReturnBall,  // throw the kids' ball back, then the scene
	Finale,      // last scene, then the end card, credits and free roam
};

/** One spoken line of a scene. */
USTRUCT(BlueprintType)
struct FGIStoryLine
{
	GENERATED_BODY()

	/** Actor id of the speaker ("player", an NPC id, or "vo" for voice-over with no cut). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Speaker;
	/** Who the speaker talks to (defaults: player <-> the beat's NPC). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Listener;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString Text;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TObjectPtr<USoundBase> Voice;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") EGIPoseMode Gesture = EGIPoseMode::Talk;
	/** Camera: "" = over-the-shoulder onto the speaker, "two", "wide", "close", "follow", "high", "keep". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Shot;
	/** Hand-placed camera (world): set CamFrom to use it; the lens dollies to CamTo over the line. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector CamFrom = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector CamTo = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector CamLook = FVector::ZeroVector;
	/** Lens for this line (0 = the default 52 degrees). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float CamFov = 0.f;
};

/** A story character. */
USTRUCT(BlueprintType)
struct FGIStoryActorDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Id;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString Name;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TObjectPtr<USkeletalMesh> Mesh;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float Scale = 1.f;
};

/** Where a character stands (and what it does) while a beat runs. Id "player" places the player. */
USTRUCT(BlueprintType)
struct FGIStoryCast
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Id;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector Location = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float Yaw = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") EGIPoseMode Mode = EGIPoseMode::Locomotion;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") bool bVisible = true;
};

USTRUCT(BlueprintType)
struct FGIStoryBeat
{
	GENERATED_BODY()

	/** Chapter card shown as the beat starts ("" = none), with its subtitle. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString Chapter;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString ChapterSub;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString Objective;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") EGIBeatKind Kind = EGIBeatKind::Scene;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Npc;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector Location = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float Radius = 300.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FVector> Path;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float PathSpeed = 150.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FGIStoryCast> Cast;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FGIStoryLine> Lines;
	/** Jump the clock to this hour when the beat starts (< 0 keeps the time). Big jumps fade through black. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float Hour = -1.f;
	/** 1 = the monsoon breaks, 0 = it clears, -1 = leave the weather alone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") int32 Rain = -1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString FadeText;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float TimeLimit = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString DoneBanner;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") int32 Reward = 0;
	/** Where the player restarts when the beat fails. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FVector RetryLocation = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float RetryYaw = 0.f;
};

/**
 * A story mission told GTA-style: chapters, objectives, cutscenes (cinematic cuts, letterbox, voiced
 * subtitles, characters turning and gesturing), follow / tail sequences with fail and retry, the clock
 * running through the day and jumping at story beats, the monsoon, an end card and credits.
 */
UCLASS()
class GTAINDIA_API AGIStory : public AActor
{
	GENERATED_BODY()

public:
	AGIStory();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString Title;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString PlayerName = TEXT("Shankar");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FGIStoryActorDef> Actors;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FGIStoryBeat> Beats;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float StartHour = 7.f;
	/** Game minutes per real second while you play. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float MinutesPerSecond = 0.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString EndTitle;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString EndSubtitle;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TArray<FString> Credits;
	/** After the finale this character walks with you (free roam). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FName Companion;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString FreeRoamObjective;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TObjectPtr<USoundBase> StingerSound;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") TObjectPtr<USoundBase> FailSound;

	static AGIStory* Get(const UObject* WorldContext);

	// ---- HUD
	bool IsCinematic() const { return bInScene || EndCardTime > 0.f; }
	float GetLetterbox() const { return Letterbox; }
	float GetFade(FString& OutText) const { OutText = FadeText; return Fade; }
	bool GetSubtitle(FString& OutName, FString& OutText, FLinearColor& OutColor) const;
	bool GetChapterCard(FString& OutTitle, FString& OutSub, float& OutAlpha) const;
	bool GetEndCard(FString& OutTitle, FString& OutSub, TArray<FString>& OutCredits, float& OutAlpha, float& OutScroll) const;
	FText GetTitle() const;
	FText GetObjective() const;
	bool GetTarget(FVector& Out) const;
	/** Ground cylinder only for places, not for people. */
	bool WantsGroundMarker() const;
	float GetTimeLeft() const { return BeatTimeLeft; }
	FText GetBanner(float& OutAlpha) const;
	/** Distance warning while tailing ("" when fine). */
	FString GetWarning() const { return Warning; }
	float GetHour() const { return Hour; }
	bool HasStarted() const { return bStarted; }
	int32 GetBeatIndex() const { return BeatIndex; }
	int32 GetFailCount() const { return FailCount; }
	bool IsFreeRoam() const { return Phase == EPhase::FreeRoam; }
	bool IsPlaying() const { return Phase == EPhase::Playing && !bInScene; }
	FVector GetMoverPos() const { return MoverPos; }

	// ---- player
	bool CanTalk(const AGIPlayerCharacter* Player, FString& OutName) const;
	void Talk(AGIPlayerCharacter* Player);
	/** E / Enter during a scene: next line. */
	void SkipLine();
	/** Testing: jump to a beat (optionally freezing its scene on a line, at an hour). */
	void DebugJump(int32 Beat, int32 HoldLine, float InHour = -1.f);

protected:
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	struct FActorState
	{
		FName Id;
		FString Name;
		USkeletalMeshComponent* Comp = nullptr;
		UGIAnimInstance* Anim = nullptr;
		EGIPoseMode RestMode = EGIPoseMode::Locomotion;
		float RestYaw = 0.f;
		float Scale = 1.f;
	};

	enum class EPhase : uint8 { Waiting, FadeOut, FadeHold, FadeIn, Playing, Scene, EndCard, FreeRoam };

	AGIPlayerCharacter* GetPlayer() const;
	FActorState* FindActor(FName Id);
	const FActorState* FindActor(FName Id) const;
	FVector HeadOf(FName Id) const;
	FVector FeetOf(FName Id) const;
	void FaceTowards(FName Id, const FVector& Target);
	void SetActorMode(FName Id, EGIPoseMode Mode, float Speed = 0.f);

	void EnterBeat(int32 Index, bool bRetry = false);
	void ApplyBeatSetup();
	void BeginBeatPlay();
	void CompleteBeat();
	void Advance();
	void FailBeat(const FString& Reason);
	void StartScene(const TArray<FGIStoryLine>& Lines);
	void StartLine(int32 Index);
	void EndScene();
	void PlaceCamera(const FGIStoryLine& Line, float Alpha);
	void TickMover(float DeltaSeconds, bool bTail);
	void TickCompanion(float DeltaSeconds);
	void LockPlayer(bool bLock);
	void ShowBanner(const FString& Text, float Duration = 4.f);
	void ApplyHour();

	TArray<FActorState> ActorStates;
	UPROPERTY() TObjectPtr<ACameraActor> SceneCam;
	UPROPERTY() TObjectPtr<UAudioComponent> VoiceAudio;

	EPhase Phase = EPhase::Waiting;
	bool bStarted = false;
	bool bInScene = false;
	bool bSceneCompletesBeat = false;
	int32 BeatIndex = -1;
	int32 LineIndex = 0;
	float LineTime = 0.f;
	float LineDuration = 1.f;
	TArray<FGIStoryLine> SceneLines;
	FVector CamFrom = FVector::ZeroVector;
	FVector CamTo = FVector::ZeroVector;
	FVector CamLook = FVector::ZeroVector;

	float Hour = 7.f;
	float HourApplyTimer = 0.f;
	float Letterbox = 0.f;
	float Fade = 0.f;
	FString FadeText;
	float PhaseTime = 0.f;
	float ChapterTime = 0.f;
	float BannerTime = 0.f;
	float BannerDuration = 1.f;
	FString Banner;
	FString Warning;
	float BeatTimeLeft = -1.f;
	bool bPendingRetry = false;
	bool bPlayerLocked = false;
	int32 FailCount = 0;
	FString FailReason;
	float EndCardTime = 0.f;

	// follow / tail
	int32 PathIndex = 0;
	FVector MoverPos = FVector::ZeroVector;
	float MoverSpeed = 0.f;
	float WarnTime = 0.f;
	float TooFarTime = 0.f;

	// debug: GI_STORY=beat[:line]
	int32 DebugHoldLine = -1;
	float CompanionSpeed = 0.f;
};
