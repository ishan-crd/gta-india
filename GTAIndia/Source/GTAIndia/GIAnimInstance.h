#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "GIAnimInstance.generated.h"

class UAnimSequence;

/** High-level pose the character should be in. */
UENUM(BlueprintType)
enum class EGIPoseMode : uint8
{
	Locomotion,   // idle / walk / run / jump / fall
	Swim,         // front crawl (procedural if there is no swim clip)
	Sit,          // sitting (train roof, bike passenger)
	SitArmsOut,   // sitting with arms spread (top of the bike stack)
	StandArmsOut, // standing, arms spread for balance (train roof surfing)
	RideBike,     // sitting, hands forward on the handlebar
	Hang,         // hanging off a train door, one arm up
	Wade,         // waist-deep in water: slow walk with arms raised a bit
	Dead,         // death clip, holds the last frame
	PickUp,       // pick-up clip (collecting the order)
	Tread,        // treading water (bathers)
	SitTalk,      // seated, chatting with gestures
	Wash,         // bending at the water's edge (washing clothes / filling pots), looped
	ClimbOut,     // hauling out of the river onto the steps (procedural, uses ClimbAlpha)
	Angry,        // standing, telling someone off: pointing arm, hand on hip, head shake
	Talk,         // standing and chatting: relaxed hand gestures, head movement
	Drink,        // standing, glass of chai to the mouth (sips)
	Throw,        // one-shot overarm throw (ActionAlpha 0..1)
	Cheer,        // both arms up, waving (kids: "Yay!")
	Bat,          // batsman stance, swings when ActionAlpha runs 0..1
	Bowl,         // bowler: locomotion + windmill arm when ActionAlpha runs 0..1
	Pour,         // chai-wallah pouring from a raised kettle into a glass
};

/** Game-thread inputs copied to the proxy every frame. */
USTRUCT()
struct FGIAnimParams
{
	GENERATED_BODY()

	float Speed = 0.f;
	float VerticalSpeed = 0.f;
	bool bInAir = false;
	EGIPoseMode Mode = EGIPoseMode::Locomotion;
	/** Idle variation phase so a crowd doesn't move in lock-step. */
	float TimeOffset = 0.f;
	/** 0..1 progress for one-shot procedural moves (climb-out). */
	float ActionAlpha = 0.f;
	/** Upper-body lean into turns (degrees, + = lean right). */
	float LeanRoll = 0.f;
	/** Foot IK: ground height under each foot relative to the capsule bottom (cm), pelvis drop (cm). */
	float FootOffsetL = 0.f;
	float FootOffsetR = 0.f;
	float PelvisOffset = 0.f;
	float IKAlpha = 0.f;
	/** Mesh base rotation (component relative, without swim pitch). Used to find body axes. */
	FQuat MeshBaseRotation = FQuat::Identity;
	/** Right hand holds an umbrella up (any standing / walking mode). */
	bool bHoldUmbrella = false;
};

/** Evaluates the pose natively: blended clips + procedural bone overlays. No anim graph needed. */
USTRUCT()
struct FGIAnimProxy : public FAnimInstanceProxy
{
	GENERATED_BODY()

	FGIAnimProxy() = default;
	explicit FGIAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	enum ELayer { L_Idle, L_Walk, L_Run, L_Jump, L_Fall, L_Land, L_Swim, L_Sit, L_Death, L_PickUp, L_Tread, L_SitTalk, L_Wash, L_Num };

	struct FLayer
	{
		UAnimSequence* Seq = nullptr;
		float Time = 0.f;
		float Weight = 0.f;
		float Target = 0.f;
		bool bLoop = true;
	};

	FLayer Layers[L_Num];
	FGIAnimParams Params;
	float WalkRefSpeed = 150.f;
	float RunRefSpeed = 400.f;
	float WalkPlant = 0.f;
	float RunPlant = 0.f;
	float LocoPhase = 0.f;
	float ModeTime = 0.f;
	float ProcAlpha = 0.f;      // blend-in of the procedural overlay for the current mode
	EGIPoseMode LastMode = EGIPoseMode::Locomotion;
	EGIPoseMode OverlayMode = EGIPoseMode::Locomotion;
	bool bWasInAir = false;
	bool bRealJump = false;      // took off with upward speed (not just stepped off a ledge)
	float AirAmount = 0.f;       // 0..1 blend of the airborne overlay
	float LandDip = 0.f;         // 0..1 landing knee dip
	float LastAirSpeed = 0.f;
	float LandTimer = 0.f;
	float JumpTimer = 0.f;

	// Cached bone lookup
	const USkeletalMesh* CachedMesh = nullptr;
	struct FBones
	{
		int32 Pelvis = INDEX_NONE, Spine1 = INDEX_NONE, Spine2 = INDEX_NONE, Spine3 = INDEX_NONE, Neck = INDEX_NONE, Head = INDEX_NONE;
		int32 ClavL = INDEX_NONE, UpperArmL = INDEX_NONE, LowerArmL = INDEX_NONE, HandL = INDEX_NONE;
		int32 ClavR = INDEX_NONE, UpperArmR = INDEX_NONE, LowerArmR = INDEX_NONE, HandR = INDEX_NONE;
		int32 ThighL = INDEX_NONE, CalfL = INDEX_NONE, FootL = INDEX_NONE;
		int32 ThighR = INDEX_NONE, CalfR = INDEX_NONE, FootR = INDEX_NONE;
	} Bones; // mesh-pose indices

protected:
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual void Update(float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

private:
	void ResolveBones(const USkeletalMesh* Mesh);
	void ApplyProcedural(FPoseContext& Output) const;
	void ApplyFootIK(FPoseContext& Output) const;
};

UCLASS(Transient)
class GTAINDIA_API UGIAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	/** Set by the owning actor every frame. */
	FGIAnimParams Params;

	/** Optional per-instance clip overrides (e.g. a mesh that ships its own idle). */
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> OverrideIdle;

	void SetMode(EGIPoseMode InMode) { Params.Mode = InMode; }

	/** Height of the pelvis above the mesh origin when sitting (clip or procedural pose). */
	static float GetSitPelvisHeight();
	/** True if a swim clip is configured (then the clip itself lies prone). */
	static bool HasSwimClip();

protected:
	virtual void NativeInitializeAnimation() override;
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;

	friend struct FGIAnimProxy;

	UPROPERTY(Transient) TArray<TObjectPtr<UAnimSequence>> LoadedClips;
	float WalkRefSpeed = 150.f;
	float RunRefSpeed = 400.f;
	float WalkPlant = 0.f;
	float RunPlant = 0.f;
};
