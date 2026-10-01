#include "GIAnimInstance.h"
#include "GIAssetSettings.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeBase.h"
#include "AnimationRuntime.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "BonePose.h"
#include "TwoBoneIK.h"

namespace
{
	int32 FindBone(const FReferenceSkeleton& Ref, std::initializer_list<const TCHAR*> Names)
	{
		for (const TCHAR* N : Names)
		{
			const int32 Idx = Ref.FindBoneIndex(FName(N));
			if (Idx != INDEX_NONE)
			{
				return Idx;
			}
		}
		return INDEX_NONE;
	}

	FCompactPoseBoneIndex ToCompact(const FCompactPose& Pose, int32 MeshIdx)
	{
		if (MeshIdx == INDEX_NONE)
		{
			return FCompactPoseBoneIndex(INDEX_NONE);
		}
		return Pose.GetBoneContainer().MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIdx));
	}

	/** Rotate a bone by a component-space delta, keeping its children attached. */
	void RotateBoneCS(FCompactPose& Pose, int32 MeshIdx, const FVector& AxisCS, float AngleRad)
	{
		const FCompactPoseBoneIndex Bone = ToCompact(Pose, MeshIdx);
		if (!Bone.IsValid() || FMath::IsNearlyZero(AngleRad))
		{
			return;
		}
		FQuat ParentCS = FQuat::Identity;
		for (FCompactPoseBoneIndex P = Pose.GetParentBoneIndex(Bone); P.IsValid(); P = Pose.GetParentBoneIndex(P))
		{
			ParentCS = Pose[P].GetRotation() * ParentCS;
		}
		const FQuat Delta(AxisCS.GetSafeNormal(), AngleRad);
		FTransform& T = Pose[Bone];
		T.SetRotation((ParentCS.Inverse() * Delta * ParentCS * T.GetRotation()).GetNormalized());
	}

	float ClipLength(const UAnimSequence* Seq)
	{
		return Seq ? FMath::Max(Seq->GetPlayLength(), 0.01f) : 1.f;
	}
}

// ---------------------------------------------------------------------------------------------
// UGIAnimInstance

float UGIAnimInstance::GetSitPelvisHeight()
{
	return UGIAssetSettings::Get().Anims.Sit.IsNull() ? 95.f : 50.f;
}

bool UGIAnimInstance::HasSwimClip()
{
	return !UGIAssetSettings::Get().Anims.Swim.IsNull();
}

void UGIAnimInstance::NativeInitializeAnimation()
{
	Super::NativeInitializeAnimation();

	const FGIAnimSet& Set = UGIAssetSettings::Get().Anims;
	LoadedClips.SetNum(FGIAnimProxy::L_Num);
	LoadedClips[FGIAnimProxy::L_Idle] = OverrideIdle ? OverrideIdle.Get() : Set.Idle.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Walk] = Set.Walk.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Run] = Set.Run.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Jump] = Set.Jump.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Fall] = Set.Fall.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Land] = Set.Land.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Swim] = Set.Swim.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Sit] = Set.Sit.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Death] = Set.Death.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_PickUp] = Set.PickUp.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Tread] = Set.Tread.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_SitTalk] = Set.SitTalk.LoadSynchronous();
	LoadedClips[FGIAnimProxy::L_Wash] = LoadedClips[FGIAnimProxy::L_PickUp];
	WalkRefSpeed = Set.WalkSpeed;
	RunRefSpeed = Set.RunSpeed;
	WalkPlant = Set.WalkPlantPhase;
	RunPlant = Set.RunPlantPhase;

	// Drop clips that don't match this mesh's skeleton rather than producing garbage.
	if (const USkeletalMeshComponent* Comp = GetSkelMeshComponent())
	{
		if (const USkeletalMesh* Mesh = Comp->GetSkeletalMeshAsset())
		{
			for (TObjectPtr<UAnimSequence>& Clip : LoadedClips)
			{
				if (Clip && Clip->GetSkeleton() != Mesh->GetSkeleton())
				{
					Clip = nullptr;
				}
			}
		}
	}
}

FAnimInstanceProxy* UGIAnimInstance::CreateAnimInstanceProxy()
{
	return new FGIAnimProxy(this);
}

void UGIAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy)
{
	delete static_cast<FGIAnimProxy*>(InProxy);
}

// ---------------------------------------------------------------------------------------------
// FGIAnimProxy

void FGIAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);

	UGIAnimInstance* Inst = CastChecked<UGIAnimInstance>(InAnimInstance);
	Params = Inst->Params;
	WalkRefSpeed = FMath::Max(Inst->WalkRefSpeed, 1.f);
	RunRefSpeed = FMath::Max(Inst->RunRefSpeed, WalkRefSpeed + 1.f);
	WalkPlant = Inst->WalkPlant;
	RunPlant = Inst->RunPlant;
	for (int32 i = 0; i < L_Num; ++i)
	{
		Layers[i].Seq = Inst->LoadedClips.IsValidIndex(i) ? Inst->LoadedClips[i].Get() : nullptr;
	}
	Layers[L_Jump].bLoop = false;
	Layers[L_Land].bLoop = false;
	Layers[L_Death].bLoop = false;
	Layers[L_PickUp].bLoop = false;

	if (const USkeletalMeshComponent* Comp = Inst->GetSkelMeshComponent())
	{
		const USkeletalMesh* Mesh = Comp->GetSkeletalMeshAsset();
		if (Mesh != CachedMesh)
		{
			ResolveBones(Mesh);
		}
	}
}

void FGIAnimProxy::ResolveBones(const USkeletalMesh* Mesh)
{
	CachedMesh = Mesh;
	Bones = FBones();
	if (!Mesh)
	{
		return;
	}
	const FReferenceSkeleton& R = Mesh->GetRefSkeleton();
	Bones.Pelvis = FindBone(R, { TEXT("pelvis"), TEXT("mixamorig:Hips"), TEXT("Hips") });
	Bones.Spine1 = FindBone(R, { TEXT("spine_01"), TEXT("mixamorig:Spine"), TEXT("Spine") });
	Bones.Spine2 = FindBone(R, { TEXT("spine_03"), TEXT("mixamorig:Spine1"), TEXT("Spine1") });
	Bones.Spine3 = FindBone(R, { TEXT("spine_05"), TEXT("spine_04"), TEXT("mixamorig:Spine2"), TEXT("Spine2") });
	Bones.Neck = FindBone(R, { TEXT("neck_01"), TEXT("mixamorig:Neck"), TEXT("Neck") });
	Bones.Head = FindBone(R, { TEXT("head"), TEXT("mixamorig:Head"), TEXT("Head") });
	Bones.ClavL = FindBone(R, { TEXT("clavicle_l"), TEXT("mixamorig:LeftShoulder"), TEXT("LeftShoulder") });
	Bones.UpperArmL = FindBone(R, { TEXT("upperarm_l"), TEXT("mixamorig:LeftArm"), TEXT("LeftArm") });
	Bones.LowerArmL = FindBone(R, { TEXT("lowerarm_l"), TEXT("mixamorig:LeftForeArm"), TEXT("LeftForeArm") });
	Bones.HandL = FindBone(R, { TEXT("hand_l"), TEXT("mixamorig:LeftHand"), TEXT("LeftHand") });
	Bones.ClavR = FindBone(R, { TEXT("clavicle_r"), TEXT("mixamorig:RightShoulder"), TEXT("RightShoulder") });
	Bones.UpperArmR = FindBone(R, { TEXT("upperarm_r"), TEXT("mixamorig:RightArm"), TEXT("RightArm") });
	Bones.LowerArmR = FindBone(R, { TEXT("lowerarm_r"), TEXT("mixamorig:RightForeArm"), TEXT("RightForeArm") });
	Bones.HandR = FindBone(R, { TEXT("hand_r"), TEXT("mixamorig:RightHand"), TEXT("RightHand") });
	Bones.ThighL = FindBone(R, { TEXT("thigh_l"), TEXT("mixamorig:LeftUpLeg"), TEXT("LeftUpLeg") });
	Bones.CalfL = FindBone(R, { TEXT("calf_l"), TEXT("mixamorig:LeftLeg"), TEXT("LeftLeg") });
	Bones.FootL = FindBone(R, { TEXT("foot_l"), TEXT("mixamorig:LeftFoot"), TEXT("LeftFoot") });
	Bones.ThighR = FindBone(R, { TEXT("thigh_r"), TEXT("mixamorig:RightUpLeg"), TEXT("RightUpLeg") });
	Bones.CalfR = FindBone(R, { TEXT("calf_r"), TEXT("mixamorig:RightLeg"), TEXT("RightLeg") });
	Bones.FootR = FindBone(R, { TEXT("foot_r"), TEXT("mixamorig:RightFoot"), TEXT("RightFoot") });
}

void FGIAnimProxy::Update(float DeltaSeconds)
{
	FAnimInstanceProxy::Update(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.1f);
	ModeTime += Dt;

	for (FLayer& L : Layers)
	{
		L.Target = 0.f;
	}

	const EGIPoseMode Mode = Params.Mode;
	const float Speed = Params.Speed;

	// Jump / land edge detection.
	if (Params.bInAir && !bWasInAir)
	{
		JumpTimer = 0.f;
		bRealJump = Params.VerticalSpeed > 150.f;
	}
	if (!Params.bInAir && bWasInAir)
	{
		// Landing dip scaled by how hard we came down (stepping down a ghat step barely registers).
		LandDip = FMath::Clamp(-LastAirSpeed / 650.f, 0.f, 1.f);
	}
	if (Params.bInAir)
	{
		LastAirSpeed = Params.VerticalSpeed;
	}
	bWasInAir = Params.bInAir;
	JumpTimer += Dt;
	LandTimer = FMath::Max(0.f, LandTimer - Dt);
	const bool bAirborne = Params.bInAir && Mode == EGIPoseMode::Locomotion && (bRealJump || JumpTimer > 0.28f);
	AirAmount = FMath::FInterpTo(AirAmount, bAirborne ? 1.f : 0.f, Dt, bAirborne ? 8.f : 14.f);
	LandDip = FMath::Max(0.f, LandDip - Dt * 3.f);

	auto SpeedBlend = [&](float S)
	{
		if (S < 10.f)
		{
			Layers[L_Idle].Target = 1.f;
		}
		else if (S < WalkRefSpeed)
		{
			const float A = S / WalkRefSpeed;
			Layers[L_Idle].Target = 1.f - A;
			Layers[L_Walk].Target = A;
		}
		else if (S < RunRefSpeed)
		{
			const float A = (S - WalkRefSpeed) / (RunRefSpeed - WalkRefSpeed);
			Layers[L_Walk].Target = 1.f - A;
			Layers[L_Run].Target = A;
		}
		else
		{
			Layers[L_Run].Target = 1.f;
		}
	};

	switch (Mode)
	{
	case EGIPoseMode::Swim:
		if (Speed < 45.f && Layers[L_Tread].Seq)
		{
			Layers[L_Tread].Target = 1.f;   // treading water when not moving
		}
		else
		{
			(Layers[L_Swim].Seq ? Layers[L_Swim] : Layers[L_Idle]).Target = 1.f;
		}
		break;
	case EGIPoseMode::Sit:
	case EGIPoseMode::SitArmsOut:
	case EGIPoseMode::RideBike:
		(Layers[L_Sit].Seq ? Layers[L_Sit] : Layers[L_Idle]).Target = 1.f;
		break;
	case EGIPoseMode::Hang:
	case EGIPoseMode::StandArmsOut:
	case EGIPoseMode::ClimbOut:
	case EGIPoseMode::Angry:
	case EGIPoseMode::Talk:
		Layers[L_Idle].Target = 1.f;
		break;
	case EGIPoseMode::Dead:
		Layers[L_Death].Target = 1.f;
		break;
	case EGIPoseMode::PickUp:
		Layers[L_PickUp].Target = 1.f;
		break;
	case EGIPoseMode::Tread:
		Layers[L_Tread].Target = 1.f;
		break;
	case EGIPoseMode::SitTalk:
		(Layers[L_SitTalk].Seq ? Layers[L_SitTalk] : Layers[L_Sit]).Target = 1.f;
		break;
	case EGIPoseMode::Wash:
		Layers[L_Wash].Target = 1.f;
		break;
	case EGIPoseMode::Wade:
		SpeedBlend(FMath::Min(Speed, WalkRefSpeed));
		break;
	default:
		// Airborne: keep the locomotion pose (stride frozen below) and add a procedural tuck/arm
		// balance, instead of separate jump clips. Short drops off steps stay plain locomotion.
		SpeedBlend(Params.bInAir ? FMath::Max(Speed, WalkRefSpeed * 1.2f) : Speed);
		break;
	}

	// Redirect weight of missing clips to sensible fallbacks.
	auto Redirect = [&](int32 From, int32 To)
	{
		if (!Layers[From].Seq && Layers[From].Target > 0.f)
		{
			Layers[To].Target += Layers[From].Target;
			Layers[From].Target = 0.f;
		}
	};
	Layers[L_Jump].Target = Layers[L_Fall].Target = Layers[L_Land].Target = 0.f;
	Redirect(L_Run, L_Walk);
	Redirect(L_Walk, L_Idle);
	Redirect(L_Jump, L_Fall);
	Redirect(L_Land, L_Idle);
	Redirect(L_Fall, L_Idle);
	Redirect(L_Swim, L_Idle);
	Redirect(L_Sit, L_Idle);
	Redirect(L_Death, L_Idle);
	Redirect(L_PickUp, L_Idle);
	Redirect(L_Tread, L_Idle);
	Redirect(L_SitTalk, L_Sit);
	Redirect(L_Wash, L_Idle);

	// Smooth weights and advance clip time.
	const float BlendAlpha = FMath::Min(1.f, Dt * 9.f);
	for (int32 i = 0; i < L_Num; ++i)
	{
		FLayer& L = Layers[i];
		const bool bWasOff = L.Weight < 0.01f;
		L.Weight += (L.Target - L.Weight) * BlendAlpha;
		if (L.Target > 0.f && bWasOff && !L.bLoop)
		{
			L.Time = 0.f;
		}
		if (!L.Seq || (L.Weight < 0.001f && L.Target <= 0.f))
		{
			continue;
		}
		if (i == L_Walk || i == L_Run)
		{
			continue; // driven by the shared locomotion phase below
		}
		float Rate = 1.f;
		if (i == L_Swim)
		{
			Rate = FMath::Clamp(Speed / 260.f, 0.55f, 1.35f);
		}
		const float Len = ClipLength(L.Seq);
		L.Time += Dt * Rate;
		L.Time = L.bLoop ? FMath::Fmod(L.Time, Len) : FMath::Min(L.Time, Len);
	}

	// Walk / run share one stride clock so the legs never scissor while blending, and each clip plays
	// at exactly the rate that matches the ground speed (no foot sliding).
	{
		const float LenW = ClipLength(Layers[L_Walk].Seq);
		const float LenR = ClipLength(Layers[L_Run].Seq);
		const float WW = Layers[L_Walk].Seq ? Layers[L_Walk].Weight : 0.f;
		const float WR = Layers[L_Run].Seq ? Layers[L_Run].Weight : 0.f;
		const float RunFrac = (WW + WR) > 0.001f ? WR / (WW + WR) : (Speed > (WalkRefSpeed + RunRefSpeed) * 0.5f ? 1.f : 0.f);
		const float Stride = FMath::Lerp(WalkRefSpeed * LenW, RunRefSpeed * LenR, RunFrac);
		if (Stride > 1.f && AirAmount < 0.5f)
		{
			LocoPhase = FMath::Frac(LocoPhase + Dt * FMath::Max(Speed, 0.f) / Stride);
		}
		Layers[L_Walk].Time = FMath::Frac(LocoPhase + WalkPlant) * LenW;
		Layers[L_Run].Time = FMath::Frac(LocoPhase + RunPlant) * LenR;
	}

	// Procedural overlay fade (cross-fade between modes).
	if (Mode != OverlayMode)
	{
		ProcAlpha -= Dt * 6.f;
		if (ProcAlpha <= 0.f)
		{
			ProcAlpha = 0.f;
			OverlayMode = Mode;
		}
	}
	else
	{
		ProcAlpha = FMath::Min(1.f, ProcAlpha + Dt * (Mode == EGIPoseMode::ClimbOut ? 10.f : 4.f));
	}
	if (Mode != LastMode)
	{
		LastMode = Mode;
		ModeTime = 0.f;
	}
}

bool FGIAnimProxy::Evaluate(FPoseContext& Output)
{
	float TotalWeight = 0.f;
	for (const FLayer& L : Layers)
	{
		if (L.Seq && L.Weight > 0.001f)
		{
			TotalWeight += L.Weight;
		}
	}

	if (TotalWeight <= 0.f)
	{
		Output.ResetToRefPose();
	}
	else
	{
		float Accum = 0.f;
		bool bFirst = true;
		for (int32 i = 0; i < L_Num; ++i)
		{
			const FLayer& L = Layers[i];
			if (!L.Seq || L.Weight <= 0.001f)
			{
				continue;
			}
			const float Time = L.bLoop && i == L_Idle ? FMath::Fmod(L.Time + Params.TimeOffset, ClipLength(L.Seq)) : L.Time;
			const FAnimExtractContext Ctx(static_cast<double>(Time), false, FDeltaTimeRecord(), L.bLoop);
			if (bFirst)
			{
				FAnimationPoseData OutData(Output);
				L.Seq->GetAnimationPose(OutData, Ctx);
				Accum = L.Weight;
				bFirst = false;
				continue;
			}
			FPoseContext Sample(Output);
			FAnimationPoseData SampleData(Sample);
			L.Seq->GetAnimationPose(SampleData, Ctx);

			FPoseContext Blended(Output);
			FAnimationPoseData BlendedData(Blended);
			const FAnimationPoseData AccumData(Output);
			const float WeightOfAccum = Accum / (Accum + L.Weight);
			FAnimationRuntime::BlendTwoPosesTogether(AccumData, SampleData, WeightOfAccum, BlendedData);
			Output.Pose.CopyBonesFrom(Blended.Pose);
			Output.Curve.CopyFrom(Blended.Curve);
			Accum += L.Weight;
		}
		Output.Pose.NormalizeRotations();
	}

	ApplyProcedural(Output);
	ApplyFootIK(Output);
	return true;
}

void FGIAnimProxy::ApplyProcedural(FPoseContext& Output) const
{
	if (ProcAlpha <= 0.f || !CachedMesh)
	{
		return;
	}
	FCompactPose& Pose = Output.Pose;
	const float A = ProcAlpha;
	const FQuat Inv = Params.MeshBaseRotation.Inverse();
	const FVector F = Inv.RotateVector(FVector::ForwardVector);
	const FVector R = Inv.RotateVector(FVector::RightVector);
	const FVector U = Inv.RotateVector(FVector::UpVector);
	const float Deg = PI / 180.f;
	const float T = ModeTime + Params.TimeOffset;

	auto SitLegs = [&](float ThighDeg, float Spread)
	{
		// Thigh from pointing down (-U) towards forward (+F): negative rotation about R.
		RotateBoneCS(Pose, Bones.ThighL, R, -ThighDeg * Deg * A);
		RotateBoneCS(Pose, Bones.ThighR, R, -ThighDeg * Deg * A);
		RotateBoneCS(Pose, Bones.ThighL, F, -Spread * Deg * A);
		RotateBoneCS(Pose, Bones.ThighR, F, Spread * Deg * A);
		RotateBoneCS(Pose, Bones.CalfL, R, ThighDeg * Deg * A);
		RotateBoneCS(Pose, Bones.CalfR, R, ThighDeg * Deg * A);
	};
	auto ArmsOut = [&](float AngleDeg)
	{
		RotateBoneCS(Pose, Bones.UpperArmR, F, AngleDeg * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, F, -AngleDeg * Deg * A);
	};

	switch (OverlayMode)
	{
	case EGIPoseMode::Swim:
	{
		if (Layers[L_Swim].Seq)
		{
			break;
		}
		const float Moving = FMath::Clamp(Params.Speed / 250.f, 0.f, 1.f);
		const float Hz = FMath::Lerp(0.35f, 0.75f, Moving);
		const float Phase = T * 2.f * PI * Hz;
		const float Amp = FMath::Lerp(0.35f, 1.f, Moving);
		// Front crawl: arms circle about the body's right axis, half a cycle apart.
		RotateBoneCS(Pose, Bones.UpperArmL, R, -FMath::Fmod(Phase, 2.f * PI) * A * Amp);
		RotateBoneCS(Pose, Bones.UpperArmR, R, -FMath::Fmod(Phase + PI, 2.f * PI) * A * Amp);
		RotateBoneCS(Pose, Bones.LowerArmL, R, -0.35f * (1.f + FMath::Sin(Phase)) * A);
		RotateBoneCS(Pose, Bones.LowerArmR, R, -0.35f * (1.f + FMath::Sin(Phase + PI)) * A);
		// Flutter kick.
		const float Kick = 0.3f * FMath::Sin(Phase * 3.f) * A * FMath::Lerp(0.4f, 1.f, Moving);
		RotateBoneCS(Pose, Bones.ThighL, R, Kick);
		RotateBoneCS(Pose, Bones.ThighR, R, -Kick);
		RotateBoneCS(Pose, Bones.CalfL, R, 0.25f * A);
		RotateBoneCS(Pose, Bones.CalfR, R, 0.25f * A);
		// Body roll and head up out of the water.
		RotateBoneCS(Pose, Bones.Spine1, U, 0.3f * FMath::Sin(Phase) * A);
		RotateBoneCS(Pose, Bones.Neck, R, -45.f * Deg * A);
		RotateBoneCS(Pose, Bones.Head, R, -20.f * Deg * A);
		break;
	}
	case EGIPoseMode::Sit:
		if (Layers[L_Sit].Seq)
		{
			break;
		}
		SitLegs(90.f, 8.f);
		RotateBoneCS(Pose, Bones.Spine1, R, -6.f * Deg * A);
		break;
	case EGIPoseMode::SitArmsOut:
		if (!Layers[L_Sit].Seq)
		{
			SitLegs(85.f, 12.f);
		}
		ArmsOut(80.f + 6.f * FMath::Sin(T * 1.7f));
		break;
	case EGIPoseMode::RideBike:
		if (!Layers[L_Sit].Seq)
		{
			SitLegs(70.f, 14.f);
		}
		RotateBoneCS(Pose, Bones.Spine1, R, -12.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, R, -55.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmR, R, -55.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, F, -12.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmR, F, 12.f * Deg * A);
		RotateBoneCS(Pose, Bones.LowerArmL, R, -25.f * Deg * A);
		RotateBoneCS(Pose, Bones.LowerArmR, R, -25.f * Deg * A);
		break;
	case EGIPoseMode::StandArmsOut:
		ArmsOut(75.f + 8.f * FMath::Sin(T * 2.1f));
		RotateBoneCS(Pose, Bones.Spine1, F, 4.f * Deg * FMath::Sin(T * 1.3f) * A);
		break;
	case EGIPoseMode::Hang:
		RotateBoneCS(Pose, Bones.UpperArmR, R, -165.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, F, -35.f * Deg * A);
		RotateBoneCS(Pose, Bones.ThighL, R, -20.f * Deg * A);
		RotateBoneCS(Pose, Bones.CalfL, R, 25.f * Deg * A);
		break;
	case EGIPoseMode::Wade:
		ArmsOut(28.f);
		break;
	case EGIPoseMode::Locomotion:
	{
		// Lean into turns (spine + a touch of neck counter-rotation to keep the head level).
		RotateBoneCS(Pose, Bones.Spine1, F, Params.LeanRoll * 0.55f * Deg * A);
		RotateBoneCS(Pose, Bones.Spine2, F, Params.LeanRoll * 0.35f * Deg * A);
		RotateBoneCS(Pose, Bones.Neck, F, -Params.LeanRoll * 0.4f * Deg * A);
		// Jogging arms: the source run swings stiff, straight arms forward. Bend the elbows and
		// tuck the upper arms in, like a natural run.
		const float RunW = Layers[L_Run].Weight;
		if (RunW > 0.01f)
		{
			RotateBoneCS(Pose, Bones.UpperArmL, R, 14.f * Deg * A * RunW);
			RotateBoneCS(Pose, Bones.UpperArmR, R, 14.f * Deg * A * RunW);
			RotateBoneCS(Pose, Bones.LowerArmL, R, -38.f * Deg * A * RunW);
			RotateBoneCS(Pose, Bones.LowerArmR, R, -38.f * Deg * A * RunW);
			RotateBoneCS(Pose, Bones.Spine2, R, 9.f * Deg * A * RunW);
			RotateBoneCS(Pose, Bones.Neck, R, 6.f * Deg * A * RunW);
		}
		// Airborne: knees come up while rising, legs reach for the ground while falling; arms out for balance.
		if (AirAmount > 0.01f)
		{
			const float Rise = FMath::Clamp(Params.VerticalSpeed / 400.f, -1.f, 1.f);
			const float Tuck = (Rise > 0.f ? 35.f : 15.f) * AirAmount;
			RotateBoneCS(Pose, Bones.ThighL, R, -Tuck * Deg * A);
			RotateBoneCS(Pose, Bones.ThighR, R, -Tuck * 0.6f * Deg * A);
			RotateBoneCS(Pose, Bones.CalfL, R, Tuck * 1.3f * Deg * A);
			RotateBoneCS(Pose, Bones.CalfR, R, Tuck * 0.8f * Deg * A);
			RotateBoneCS(Pose, Bones.UpperArmL, F, -22.f * Deg * A * AirAmount);
			RotateBoneCS(Pose, Bones.UpperArmR, F, 22.f * Deg * A * AirAmount);
			RotateBoneCS(Pose, Bones.Spine1, R, -6.f * Deg * A * AirAmount);
		}
		// Landing: a quick knee dip.
		if (LandDip > 0.01f)
		{
			const float D = FMath::Sin(LandDip * PI * 0.5f) * 28.f;
			RotateBoneCS(Pose, Bones.ThighL, R, -D * Deg * A);
			RotateBoneCS(Pose, Bones.ThighR, R, -D * Deg * A);
			RotateBoneCS(Pose, Bones.CalfL, R, D * 1.8f * Deg * A);
			RotateBoneCS(Pose, Bones.CalfR, R, D * 1.8f * Deg * A);
			RotateBoneCS(Pose, Bones.Spine1, R, -D * 0.3f * Deg * A);
		}
		break;
	}
	case EGIPoseMode::Angry:
	{
		const float Shake = FMath::Sin(T * 9.f);
		RotateBoneCS(Pose, Bones.UpperArmR, R, (-70.f + 8.f * Shake) * Deg * A);   // pointing / gesturing
		RotateBoneCS(Pose, Bones.LowerArmR, R, -25.f * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, F, -32.f * Deg * A);                    // hand on hip
		RotateBoneCS(Pose, Bones.LowerArmL, U, 75.f * Deg * A);
		RotateBoneCS(Pose, Bones.Head, U, 12.f * Shake * Deg * A);
		RotateBoneCS(Pose, Bones.Spine2, R, 6.f * Deg * A);
		break;
	}
	case EGIPoseMode::Talk:
	{
		// Bursts of gesturing every few seconds, like people chatting on the ghats.
		const float Burst = FMath::Clamp(FMath::Sin(T * 0.7f) * 1.6f, 0.f, 1.f);
		const float G1 = FMath::Sin(T * 3.1f), G2 = FMath::Sin(T * 2.3f + 1.f);
		RotateBoneCS(Pose, Bones.UpperArmR, R, (-28.f - 10.f * G1) * Burst * Deg * A);
		RotateBoneCS(Pose, Bones.LowerArmR, R, (-45.f - 15.f * G2) * Burst * Deg * A);
		RotateBoneCS(Pose, Bones.UpperArmL, R, -12.f * Burst * (0.5f + 0.5f * G2) * Deg * A);
		RotateBoneCS(Pose, Bones.LowerArmL, R, -30.f * Burst * Deg * A);
		RotateBoneCS(Pose, Bones.Head, U, 10.f * FMath::Sin(T * 0.9f) * Deg * A);
		RotateBoneCS(Pose, Bones.Head, R, -4.f * G1 * Burst * Deg * A);
		break;
	}
	case EGIPoseMode::ClimbOut:
	{
		// Phase 1 (0..0.55): hands planted on the step, chest down, pulling up.
		// Phase 2 (0.55..1): one knee up onto the step, then straighten.
		const float P = Params.ActionAlpha;
		const float Pull = 1.f - FMath::SmoothStep(0.55f, 1.f, P);
		const float Knee = FMath::Sin(FMath::Clamp((P - 0.35f) / 0.65f, 0.f, 1.f) * PI);
		RotateBoneCS(Pose, Bones.Spine1, R, -35.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.Spine2, R, -15.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.UpperArmL, R, -75.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.UpperArmR, R, -75.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.LowerArmL, R, 30.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.LowerArmR, R, 30.f * Deg * A * Pull);
		RotateBoneCS(Pose, Bones.ThighR, R, -80.f * Deg * A * Knee);
		RotateBoneCS(Pose, Bones.CalfR, R, 95.f * Deg * A * Knee);
		RotateBoneCS(Pose, Bones.Neck, R, -20.f * Deg * A * Pull);
		break;
	}
	default:
		break;
	}
}

void FGIAnimProxy::ApplyFootIK(FPoseContext& Output) const
{
	const float A = FMath::Clamp(Params.IKAlpha, 0.f, 1.f);
	if (A <= 0.01f || !CachedMesh)
	{
		return;
	}
	FCompactPose& Pose = Output.Pose;
	const FCompactPoseBoneIndex Pel = ToCompact(Pose, Bones.Pelvis);
	const FCompactPoseBoneIndex TL = ToCompact(Pose, Bones.ThighL), CL = ToCompact(Pose, Bones.CalfL), FL = ToCompact(Pose, Bones.FootL);
	const FCompactPoseBoneIndex TR = ToCompact(Pose, Bones.ThighR), CR = ToCompact(Pose, Bones.CalfR), FR = ToCompact(Pose, Bones.FootR);
	if (!Pel.IsValid() || !TL.IsValid() || !CL.IsValid() || !FL.IsValid() || !TR.IsValid() || !CR.IsValid() || !FR.IsValid())
	{
		return;
	}
	const FVector Forward = Params.MeshBaseRotation.Inverse().RotateVector(FVector::ForwardVector);
	const float PelvisDrop = Params.PelvisOffset * A;

	FCSPose<FCompactPose> CS;
	CS.InitPose(Pose);
	{
		FTransform PelT = CS.GetComponentSpaceTransform(Pel);
		PelT.AddToTranslation(FVector(0.f, 0.f, PelvisDrop));
		TArray<FBoneTransform> Out;
		Out.Add(FBoneTransform(Pel, PelT));
		CS.SafeSetCSBoneTransforms(Out);
	}
	auto SolveLeg = [&](FCompactPoseBoneIndex T, FCompactPoseBoneIndex C, FCompactPoseBoneIndex F, float Offset)
	{
		FTransform RootT = CS.GetComponentSpaceTransform(T);
		FTransform JointT = CS.GetComponentSpaceTransform(C);
		FTransform EndT = CS.GetComponentSpaceTransform(F);
		const FVector Effector = EndT.GetLocation() + FVector(0.f, 0.f, Offset * A - PelvisDrop);
		const FVector JointTarget = JointT.GetLocation() + Forward * 60.f;
		AnimationCore::SolveTwoBoneIK(RootT, JointT, EndT, JointTarget, Effector, false, 1.0, 1.0);
		TArray<FBoneTransform> Out;
		Out.Add(FBoneTransform(T, RootT));
		Out.Add(FBoneTransform(C, JointT));
		Out.Add(FBoneTransform(F, EndT));
		CS.SafeSetCSBoneTransforms(Out);
	};
	SolveLeg(TL, CL, FL, Params.FootOffsetL);
	SolveLeg(TR, CR, FR, Params.FootOffsetR);
	FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(MoveTemp(CS), Pose);
}
