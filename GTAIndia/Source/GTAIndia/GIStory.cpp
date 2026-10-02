#include "GIStory.h"
#include "GIAnimInstance.h"
#include "GIAssetSettings.h"
#include "GIBike.h"
#include "GIDharavi.h"
#include "GIPlayerCharacter.h"
#include "GIPlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Sound/SoundBase.h"

namespace
{
	const FName PlayerId(TEXT("player"));
	const FName VoiceOverId(TEXT("vo"));
	constexpr float FadeOutTime = 0.9f;
	constexpr float FadeHoldTime = 2.4f;
	constexpr float FadeInTime = 1.2f;
	constexpr float ChapterCardTime = 5.f;

	float YawTo(const FVector& From, const FVector& To)
	{
		return (To - From).GetSafeNormal2D().Rotation().Yaw;
	}
}

AGIStory::AGIStory()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

AGIStory* AGIStory::Get(const UObject* WorldContext)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AGIStory> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

AGIPlayerCharacter* AGIStory::GetPlayer() const
{
	for (TActorIterator<AGIPlayerCharacter> It(GetWorld()); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

// ------------------------------------------------------------------------------------------ setup

void AGIStory::BeginPlay()
{
	Super::BeginPlay();
	Hour = StartHour;
	for (const FGIStoryActorDef& Def : Actors)
	{
		FActorState S;
		S.Id = Def.Id;
		S.Name = Def.Name;
		S.Scale = Def.Scale;
		if (Def.Mesh)
		{
			// Full-rate animation for the story cast (no budget throttling on the people you talk to).
			USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(this);
			C->SetupAttachment(RootComponent);
			C->SetUsingAbsoluteLocation(true);
			C->SetUsingAbsoluteRotation(true);
			C->RegisterComponent();
			C->SetSkeletalMesh(Def.Mesh);
			C->SetAnimInstanceClass(UGIAnimInstance::StaticClass());
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			C->SetWorldScale3D(FVector(Def.Scale));
			C->SetVisibility(false);
			C->bCastDynamicShadow = true;
			S.Comp = C;
			S.Anim = Cast<UGIAnimInstance>(C->GetAnimInstance());
			if (S.Anim)
			{
				S.Anim->Params.MeshBaseRotation = FRotator(0.f, -90.f, 0.f).Quaternion();
				S.Anim->Params.TimeOffset = FMath::FRandRange(0.f, 5.f);
			}
		}
		ActorStates.Add(S);
	}
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	SceneCam = GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity, P);
	if (SceneCam)
	{
		SceneCam->GetCameraComponent()->SetFieldOfView(52.f);
		SceneCam->GetCameraComponent()->bConstrainAspectRatio = false;
	}
	VoiceAudio = NewObject<UAudioComponent>(this);
	VoiceAudio->SetupAttachment(RootComponent);
	VoiceAudio->bAutoActivate = false;
	VoiceAudio->bIsUISound = true;
	VoiceAudio->RegisterComponent();
	ApplyHour();
}

AGIStory::FActorState* AGIStory::FindActor(FName Id)
{
	return ActorStates.FindByPredicate([Id](const FActorState& S) { return S.Id == Id; });
}

const AGIStory::FActorState* AGIStory::FindActor(FName Id) const
{
	return ActorStates.FindByPredicate([Id](const FActorState& S) { return S.Id == Id; });
}

FVector AGIStory::FeetOf(FName Id) const
{
	if (Id == PlayerId || Id.IsNone())
	{
		if (const AGIPlayerCharacter* P = GetPlayer())
		{
			return P->GetActorLocation() - FVector(0.f, 0.f, P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
		}
		return FVector::ZeroVector;
	}
	const FActorState* S = FindActor(Id);
	return S && S->Comp ? S->Comp->GetComponentLocation() : FVector::ZeroVector;
}

FVector AGIStory::HeadOf(FName Id) const
{
	static const FName HeadBone(TEXT("Head"));
	if (Id == PlayerId || Id.IsNone())
	{
		const AGIPlayerCharacter* P = GetPlayer();
		if (P && P->GetMesh() && P->GetMesh()->GetBoneIndex(HeadBone) != INDEX_NONE)
		{
			return P->GetMesh()->GetSocketLocation(HeadBone) + FVector(0.f, 0.f, 6.f);
		}
		return FeetOf(Id) + FVector(0.f, 0.f, 158.f);
	}
	const FActorState* S = FindActor(Id);
	if (S && S->Comp && S->Comp->GetBoneIndex(HeadBone) != INDEX_NONE)
	{
		return S->Comp->GetSocketLocation(HeadBone) + FVector(0.f, 0.f, 6.f * S->Scale);
	}
	return FeetOf(Id) + FVector(0.f, 0.f, 158.f * (S ? S->Scale : 1.f));
}

void AGIStory::FaceTowards(FName Id, const FVector& Target)
{
	if (Id == PlayerId)
	{
		if (AGIPlayerCharacter* P = GetPlayer())
		{
			P->SetActorRotation(FRotator(0.f, YawTo(P->GetActorLocation(), Target), 0.f));
		}
		return;
	}
	if (FActorState* S = FindActor(Id))
	{
		if (S->Comp)
		{
			S->Comp->SetWorldRotation(FRotator(0.f, YawTo(S->Comp->GetComponentLocation(), Target) - 90.f, 0.f));
		}
	}
}

void AGIStory::SetActorMode(FName Id, EGIPoseMode Mode, float Speed)
{
	if (FActorState* S = FindActor(Id))
	{
		if (S->Anim)
		{
			S->Anim->Params.Mode = Mode;
			S->Anim->Params.Speed = Speed;
		}
	}
}

// ------------------------------------------------------------------------------------------ queries

bool AGIStory::GetSubtitle(FString& OutName, FString& OutText, FLinearColor& OutColor) const
{
	if (!bInScene || !SceneLines.IsValidIndex(LineIndex))
	{
		return false;
	}
	const FGIStoryLine& L = SceneLines[LineIndex];
	OutText = L.Text;
	if (L.Speaker == PlayerId)
	{
		OutName = PlayerName;
		OutColor = FLinearColor(0.45f, 0.8f, 1.f);
	}
	else if (L.Speaker == VoiceOverId)
	{
		OutName = PlayerName;
		OutColor = FLinearColor(0.75f, 0.75f, 0.75f);
	}
	else
	{
		const FActorState* S = FindActor(L.Speaker);
		OutName = S ? S->Name : L.Speaker.ToString();
		OutColor = FLinearColor(1.f, 0.78f, 0.25f);
	}
	return true;
}

bool AGIStory::GetChapterCard(FString& OutTitle, FString& OutSub, float& OutAlpha) const
{
	if (ChapterTime <= 0.f || !Beats.IsValidIndex(BeatIndex) || Beats[BeatIndex].Chapter.IsEmpty())
	{
		return false;
	}
	OutTitle = Beats[BeatIndex].Chapter;
	OutSub = Beats[BeatIndex].ChapterSub;
	const float Elapsed = ChapterCardTime - ChapterTime;
	OutAlpha = FMath::Clamp(FMath::Min(Elapsed / 0.8f, ChapterTime / 1.0f), 0.f, 1.f);
	return true;
}

bool AGIStory::GetEndCard(FString& OutTitle, FString& OutSub, TArray<FString>& OutCredits, float& OutAlpha, float& OutScroll) const
{
	if (EndCardTime <= 0.f)
	{
		return false;
	}
	OutTitle = EndTitle;
	OutSub = EndSubtitle;
	OutCredits = Credits;
	const float Total = 16.f;
	const float Elapsed = Total - EndCardTime;
	OutAlpha = FMath::Clamp(FMath::Min(Elapsed / 1.5f, EndCardTime / 1.5f), 0.f, 1.f);
	OutScroll = Elapsed / Total;
	return true;
}

FText AGIStory::GetTitle() const
{
	return FText::FromString(Title);
}

FText AGIStory::GetObjective() const
{
	if (Phase == EPhase::FreeRoam)
	{
		return FText::FromString(FreeRoamObjective);
	}
	if (!Beats.IsValidIndex(BeatIndex) || bInScene || Phase != EPhase::Playing)
	{
		return FText::GetEmpty();
	}
	return FText::FromString(Beats[BeatIndex].Objective);
}

bool AGIStory::GetTarget(FVector& Out) const
{
	if (Phase != EPhase::Playing || bInScene || !Beats.IsValidIndex(BeatIndex))
	{
		return false;
	}
	const FGIStoryBeat& B = Beats[BeatIndex];
	switch (B.Kind)
	{
	case EGIBeatKind::TalkTo:
		Out = FeetOf(B.Npc);
		return true;
	case EGIBeatKind::Follow:
	case EGIBeatKind::Tail:
		Out = MoverPos;
		return true;
	case EGIBeatKind::ReturnBall:
		for (TActorIterator<AGICricketGame> It(GetWorld()); It; ++It)
		{
			if (It->GetWaitingBall(Out))
			{
				return true;
			}
		}
		Out = B.Location;
		return true;
	case EGIBeatKind::Reach:
	case EGIBeatKind::Chai:
		Out = B.Location;
		return true;
	default:
		return false;
	}
}

bool AGIStory::WantsGroundMarker() const
{
	if (!Beats.IsValidIndex(BeatIndex))
	{
		return false;
	}
	const EGIBeatKind K = Beats[BeatIndex].Kind;
	return K == EGIBeatKind::Reach || K == EGIBeatKind::Chai || K == EGIBeatKind::ReturnBall;
}

FText AGIStory::GetBanner(float& OutAlpha) const
{
	if (BannerTime <= 0.f)
	{
		OutAlpha = 0.f;
		return FText::GetEmpty();
	}
	const float Elapsed = BannerDuration - BannerTime;
	OutAlpha = FMath::Clamp(FMath::Min(Elapsed / 0.3f, BannerTime / 0.6f), 0.f, 1.f);
	return FText::FromString(Banner);
}

void AGIStory::ShowBanner(const FString& Text, float Duration)
{
	Banner = Text;
	BannerTime = BannerDuration = Duration;
}

bool AGIStory::CanTalk(const AGIPlayerCharacter* Player, FString& OutName) const
{
	if (!Player || Phase != EPhase::Playing || bInScene || !Beats.IsValidIndex(BeatIndex))
	{
		return false;
	}
	const FGIStoryBeat& B = Beats[BeatIndex];
	if (B.Kind != EGIBeatKind::TalkTo)
	{
		return false;
	}
	const FActorState* S = FindActor(B.Npc);
	if (!S || !S->Comp || FVector::Dist2D(S->Comp->GetComponentLocation(), Player->GetActorLocation()) > 260.f)
	{
		return false;
	}
	OutName = S->Name;
	return true;
}

void AGIStory::Talk(AGIPlayerCharacter* Player)
{
	FString Name;
	if (CanTalk(Player, Name))
	{
		bSceneCompletesBeat = true;
		StartScene(Beats[BeatIndex].Lines);
	}
}

void AGIStory::SkipLine()
{
	if (bInScene && DebugHoldLine < 0 && LineTime > 0.35f)
	{
		StartLine(LineIndex + 1);
	}
}

// ------------------------------------------------------------------------------------------ flow

void AGIStory::LockPlayer(bool bLock)
{
	// the engine's ignore-input flags are counters: only touch them when the state really changes
	if (bLock != bPlayerLocked)
	{
		bPlayerLocked = bLock;
		if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
		{
			PC->SetIgnoreMoveInput(bLock);
			PC->SetIgnoreLookInput(bLock);
		}
	}
	if (AGIPlayerCharacter* P = GetPlayer())
	{
		P->GetCharacterMovement()->StopMovementImmediately();
	}
}

void AGIStory::EnterBeat(int32 Index, bool bRetry)
{
	BeatIndex = Index;
	Warning.Reset();
	BeatTimeLeft = -1.f;
	if (!Beats.IsValidIndex(Index))
	{
		return;
	}
	const FGIStoryBeat& B = Beats[Index];
	const bool bTimeJump = B.Hour >= 0.f && FMath::Abs(B.Hour - Hour) > 0.4f;
	if (bRetry || bTimeJump || !B.FadeText.IsEmpty())
	{
		// Fade through black: the setup (time, weather, cast) is applied while the screen is dark.
		FadeText = bRetry ? FailReason : B.FadeText;
		bPendingRetry = bRetry;
		Phase = EPhase::FadeOut;
		PhaseTime = 0.f;
		LockPlayer(true);
		return;
	}
	ApplyBeatSetup();
	BeginBeatPlay();
}

void AGIStory::ApplyBeatSetup()
{
	const FGIStoryBeat& B = Beats[BeatIndex];
	if (B.Hour >= 0.f && !bPendingRetry)
	{
		Hour = B.Hour;
		ApplyHour();
	}
	if (B.Rain >= 0)
	{
		if (AGIWeather* W = AGIWeather::Get(this))
		{
			if (bPendingRetry || Fade > 0.5f)
			{
				W->SetRainingInstant(B.Rain > 0);
			}
			else
			{
				W->SetRaining(B.Rain > 0);
			}
		}
	}
	for (const FGIStoryCast& C : B.Cast)
	{
		if (C.Id == PlayerId)
		{
			if (AGIPlayerCharacter* P = GetPlayer())
			{
				P->SetActorHiddenInGame(!C.bVisible);
				const float Half = P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
				P->SetActorLocationAndRotation(C.Location + FVector(0.f, 0.f, Half + 5.f), FRotator(0.f, C.Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
				if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
				{
					PC->SetControlRotation(FRotator(-8.f, C.Yaw, 0.f));
				}
			}
			continue;
		}
		if (FActorState* S = FindActor(C.Id))
		{
			S->RestMode = C.Mode;
			S->RestYaw = C.Yaw;
			if (S->Comp)
			{
				S->Comp->SetWorldLocationAndRotation(C.Location, FRotator(0.f, C.Yaw - 90.f, 0.f));
				S->Comp->SetVisibility(C.bVisible, true);
			}
			SetActorMode(C.Id, C.Mode);
		}
	}
	if (bPendingRetry && !B.RetryLocation.IsZero())
	{
		if (AGIPlayerCharacter* P = GetPlayer())
		{
			const float Half = P->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			P->SetActorLocationAndRotation(B.RetryLocation + FVector(0.f, 0.f, Half + 5.f), FRotator(0.f, B.RetryYaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
			if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
			{
				PC->SetControlRotation(FRotator(-8.f, B.RetryYaw, 0.f));
			}
		}
	}
	// movers start at the head of their path
	PathIndex = 0;
	TooFarTime = 0.f;
	if ((B.Kind == EGIBeatKind::Follow || B.Kind == EGIBeatKind::Tail) && B.Path.Num() > 0)
	{
		MoverPos = B.Path[0];
		if (FActorState* S = FindActor(B.Npc))
		{
			if (S->Comp)
			{
				S->Comp->SetWorldLocation(MoverPos);
				S->Comp->SetVisibility(true, true);
			}
		}
	}
	if (AGIPlayerCharacter* P = GetPlayer())
	{
		P->bDidChai = false;
		P->bReturnedBall = false;
	}
}

void AGIStory::BeginBeatPlay()
{
	const FGIStoryBeat& B = Beats[BeatIndex];
	bPendingRetry = false;
	Phase = EPhase::Playing;
	PhaseTime = 0.f;
	if (!B.Chapter.IsEmpty())
	{
		ChapterTime = ChapterCardTime;
		if (StingerSound)
		{
			UGameplayStatics::PlaySound2D(this, StingerSound, 0.8f);
		}
	}
	BeatTimeLeft = B.TimeLimit > 0.f ? B.TimeLimit : -1.f;
	if (B.Kind == EGIBeatKind::Scene || B.Kind == EGIBeatKind::Finale)
	{
		bSceneCompletesBeat = true;
		StartScene(B.Lines);
		return;
	}
	LockPlayer(false);
}

void AGIStory::CompleteBeat()
{
	const FGIStoryBeat& B = Beats[BeatIndex];
	BeatTimeLeft = -1.f;
	Warning.Reset();
	if (B.Lines.Num() > 0 && B.Kind != EGIBeatKind::TalkTo)
	{
		bSceneCompletesBeat = true;
		StartScene(B.Lines);
		return;
	}
	Advance();
}

void AGIStory::Advance()
{
	const FGIStoryBeat& B = Beats[BeatIndex];
	if (!B.DoneBanner.IsEmpty())
	{
		ShowBanner(B.DoneBanner, 4.f);
	}
	if (B.Reward != 0)
	{
		if (AGIPlayerCharacter* P = GetPlayer())
		{
			P->AddMoney(B.Reward);
		}
	}
	if (B.Kind == EGIBeatKind::Finale)
	{
		Phase = EPhase::EndCard;
		EndCardTime = 16.f;
		LockPlayer(true);
		if (StingerSound)
		{
			UGameplayStatics::PlaySound2D(this, StingerSound, 1.f, 0.8f);
		}
		return;
	}
	EnterBeat(BeatIndex + 1);
}

void AGIStory::FailBeat(const FString& Reason)
{
	if (FailSound)
	{
		UGameplayStatics::PlaySound2D(this, FailSound);
	}
	FailReason = FString::Printf(TEXT("MISSION FAILED\n%s"), *Reason);
	++FailCount;
	EnterBeat(BeatIndex, true);
}

// ------------------------------------------------------------------------------------------ scenes

void AGIStory::StartScene(const TArray<FGIStoryLine>& Lines)
{
	if (Lines.Num() == 0)
	{
		if (bSceneCompletesBeat)
		{
			bSceneCompletesBeat = false;
			Advance();
		}
		return;
	}
	SceneLines = Lines;
	bInScene = true;
	Phase = EPhase::Scene;
	LockPlayer(true);
	AGIPlayerCharacter* Player = GetPlayer();
	const FGIStoryBeat& B = Beats[BeatIndex];
	// Talking to someone: stand a step in front of them, facing each other.
	if (Player && !B.Npc.IsNone() && B.Kind != EGIBeatKind::Scene && B.Kind != EGIBeatKind::Finale)
	{
		if (const FActorState* S = FindActor(B.Npc))
		{
			if (S->Comp)
			{
				const FVector N = S->Comp->GetComponentLocation();
				// stand in front of them (the way they face on their mark), so the camera has room behind you
				FVector Dir = FRotator(0.f, S->RestYaw, 0.f).Vector();
				FHitResult Hit;
				FCollisionQueryParams TQ(SCENE_QUERY_STAT(GIStoryTalkSpot), false, Player);
				if (GetWorld()->LineTraceSingleByObjectType(Hit, N + FVector(0, 0, 100.f), N + Dir * 300.f + FVector(0, 0, 100.f),
					FCollisionObjectQueryParams(ECC_WorldStatic), TQ))
				{
					// blocked: fall back to the side you walked up from
					Dir = (Player->GetActorLocation() - N).GetSafeNormal2D();
				}
				if (Dir.IsNearlyZero())
				{
					Dir = FVector::ForwardVector;
				}
				const FVector Feet = N + Dir * 165.f;
				Player->SetActorLocation(FVector(Feet.X, Feet.Y, Player->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
				FaceTowards(PlayerId, N);
				FaceTowards(B.Npc, Player->GetActorLocation());
			}
		}
	}
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		if (SceneCam)
		{
			PC->SetViewTargetWithBlend(SceneCam, 0.f);
		}
	}
	StartLine(0);
}

void AGIStory::StartLine(int32 Index)
{
	if (VoiceAudio && VoiceAudio->IsPlaying())
	{
		VoiceAudio->Stop();
	}
	// the previous speaker goes back to their resting pose
	if (SceneLines.IsValidIndex(LineIndex))
	{
		const FName Prev = SceneLines[LineIndex].Speaker;
		if (Prev != PlayerId && Prev != VoiceOverId)
		{
			if (const FActorState* S = FindActor(Prev))
			{
				SetActorMode(Prev, S->RestMode);
			}
		}
	}
	LineIndex = Index;
	LineTime = 0.f;
	if (!SceneLines.IsValidIndex(Index))
	{
		EndScene();
		return;
	}
	const FGIStoryLine& L = SceneLines[Index];
	LineDuration = 1.6f + L.Text.Len() * 0.055f;
	if (L.Voice)
	{
		const float D = L.Voice->GetDuration();
		if (D > 0.1f && D < 60.f)
		{
			LineDuration = D + 0.45f;
		}
		VoiceAudio->SetSound(L.Voice);
		VoiceAudio->Play();
	}
	const FName Listener = !L.Listener.IsNone() ? L.Listener
		: (L.Speaker == PlayerId ? Beats[BeatIndex].Npc : PlayerId);
	if (L.Speaker != VoiceOverId && !Listener.IsNone())
	{
		FaceTowards(L.Speaker, FeetOf(Listener));
		if (L.Shot != TEXT("keep"))
		{
			FaceTowards(Listener, FeetOf(L.Speaker));
		}
	}
	if (L.Speaker == PlayerId)
	{
		if (AGIPlayerCharacter* P = GetPlayer())
		{
			P->PlayAction(L.Gesture, LineDuration);
		}
	}
	else if (L.Speaker != VoiceOverId)
	{
		SetActorMode(L.Speaker, L.Gesture);
	}
	if (SceneCam)
	{
		SceneCam->GetCameraComponent()->SetFieldOfView(L.CamFov > 1.f ? L.CamFov : 52.f);
	}
	PlaceCamera(L, 0.f);
}

void AGIStory::PlaceCamera(const FGIStoryLine& L, float Alpha)
{
	if (!SceneCam)
	{
		return;
	}
	if (Alpha <= 0.f && !L.CamFrom.IsZero())
	{
		CamFrom = L.CamFrom;
		CamTo = L.CamTo.IsZero() ? L.CamFrom : L.CamTo;
		CamLook = L.CamLook;
	}
	else if (Alpha <= 0.f)
	{
		const FName Speaker = L.Speaker == VoiceOverId ? PlayerId : L.Speaker;
		const FName Listener = !L.Listener.IsNone() ? L.Listener
			: (Speaker == PlayerId ? (Beats[BeatIndex].Npc.IsNone() ? PlayerId : Beats[BeatIndex].Npc) : PlayerId);
		const FVector S = HeadOf(Speaker);
		const FVector O = Listener == Speaker ? S + FVector(200.f, 0.f, 0.f) : HeadOf(Listener);
		const FVector Mid = (S + O) * 0.5f;
		FVector Axis = (S - O).GetSafeNormal2D();
		if (Axis.IsNearlyZero())
		{
			Axis = FVector::ForwardVector;
		}
		// stay on one side of the line of action (from the player's point of view)
		FVector Side = FVector::CrossProduct(FVector::UpVector, Axis);
		if (Speaker != PlayerId)
		{
			Side = -Side;
		}
		FCollisionQueryParams Q(SCENE_QUERY_STAT(GIStoryCam), false);
		if (AGIPlayerCharacter* P = GetPlayer())
		{
			Q.AddIgnoredActor(P);
		}
		// fraction of the way from Anchor to To that is free of static geometry
		auto Room = [&](const FVector& AnchorPt, const FVector& To) -> float
		{
			FHitResult H;
			if (GetWorld()->LineTraceSingleByObjectType(H, AnchorPt, To, FCollisionObjectQueryParams(ECC_WorldStatic), Q))
			{
				return H.Time;
			}
			return 1.f;
		};
		const float Sep = FVector::Dist2D(S, O);
		FName Shot = L.Shot;
		if (Shot == TEXT("keep") && LineIndex > 0)
		{
			return;
		}
		// wide / high on a big stage: a deep over-the-shoulder takes in the whole group instead
		if (Shot == TEXT("wide") && Sep > 700.f)
		{
			Shot = TEXT("deep");
		}
		FVector From, Look;
		FVector Anchor = S;   // the wall check runs from the subject out to the lens
		auto SidePick = [&](const FVector& Base, float Dist, const FVector& Extra) -> FVector
		{
			// the side of the line with more room (default side first)
			const FVector A = Base + Side * Dist + Extra;
			const FVector B = Base - Side * Dist + Extra;
			const float RA = Room(Base, A);
			const float RB = Room(Base, B);
			return (RA >= 0.85f || RA >= RB) ? A : B;
		};
		if (Shot == TEXT("high") && Room(Mid, Mid + FVector(0.f, 0.f, 700.f)) < 0.9f)
		{
			Shot = TEXT("two");   // under a roof
		}
		if (Shot == TEXT("two"))
		{
			Anchor = Mid;
			From = SidePick(Mid, FMath::Max(320.f, Sep * 1.05f), -FVector(0.f, 0.f, 10.f));
			Look = Mid - FVector(0.f, 0.f, 15.f);
		}
		else if (Shot == TEXT("wide"))
		{
			Anchor = Mid;
			From = SidePick(Mid, 650.f, Axis * 180.f + FVector(0.f, 0.f, 220.f));
			Look = Mid - FVector(0.f, 0.f, 40.f);
		}
		else if (Shot == TEXT("deep"))
		{
			// behind the listener, looking down the stage; slide sideways until no pillar is in the way
			Look = S - FVector(0.f, 0.f, 25.f);
			float Best = -1.f;
			for (const float Off : { 110.f, -110.f, 240.f, -240.f, 380.f, -380.f })
			{
				const FVector Cand = O - Axis * 320.f + Side * Off + FVector(0.f, 0.f, 70.f);
				const float R = Room(S, Cand);
				if (R > Best + 0.05f)
				{
					Best = R;
					From = Cand;
				}
				if (R >= 0.99f)
				{
					break;
				}
			}
			if (Best < 0.5f)
			{
				Anchor = Mid;
				From = SidePick(Mid, FMath::Max(320.f, Sep * 1.05f), -FVector(0.f, 0.f, 10.f));
				Look = Mid - FVector(0.f, 0.f, 15.f);
			}
		}
		else if (Shot == TEXT("high"))
		{
			Anchor = Mid;
			From = SidePick(Mid, FMath::Max(500.f, Sep), FVector(0.f, 0.f, 900.f));
			Look = Mid - FVector(0.f, 0.f, 120.f);
		}
		else if (Shot == TEXT("close"))
		{
			const FVector Fwd = (O - S).GetSafeNormal2D();
			From = S + Fwd * 105.f + Side * 30.f - FVector(0.f, 0.f, 4.f);
			Look = S - FVector(0.f, 0.f, 6.f);
		}
		else if (Shot == TEXT("follow"))
		{
			const AGIPlayerCharacter* P = GetPlayer();
			const FVector Fwd = P ? P->GetActorForwardVector() : FVector::ForwardVector;
			const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd);
			From = S - Fwd * 210.f + Right * 55.f + FVector(0.f, 0.f, 12.f);
			Look = S + Fwd * 600.f - FVector(0.f, 0.f, 25.f);
		}
		else
		{
			// over the listener's shoulder onto the speaker
			From = O - Axis * 95.f + Side * 48.f + FVector(0.f, 0.f, 12.f);
			Look = S - FVector(0.f, 0.f, 8.f);
		}
		// keep the lens out of walls in the narrow gallis
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByObjectType(Hit, Anchor, From, FCollisionObjectQueryParams(ECC_WorldStatic), Q))
		{
			From = Hit.Location + (Anchor - From).GetSafeNormal() * 25.f;
		}
		UE_LOG(LogTemp, Verbose, TEXT("GIStory: line %d shot %s speaker %s at %s listener %s at %s cam %s look %s"), LineIndex, *Shot.ToString(),
			*Speaker.ToString(), *S.ToCompactString(), *Listener.ToString(), *O.ToCompactString(), *From.ToCompactString(), *Look.ToCompactString());
		CamFrom = From;
		CamTo = From + (Look - From).GetSafeNormal() * FMath::Min(60.f, FVector::Dist(From, Look) * 0.12f);
		CamLook = Look;
	}
	const float A = FMath::InterpEaseInOut(0.f, 1.f, FMath::Clamp(Alpha, 0.f, 1.f), 2.f);
	const FVector Pos = FMath::Lerp(CamFrom, CamTo, A);
	SceneCam->SetActorLocationAndRotation(Pos, (CamLook - Pos).Rotation());
}

void AGIStory::EndScene()
{
	bInScene = false;
	if (VoiceAudio && VoiceAudio->IsPlaying())
	{
		VoiceAudio->Stop();
	}
	for (const FActorState& S : ActorStates)
	{
		SetActorMode(S.Id, S.RestMode);
	}
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		if (APawn* Pawn = PC->GetPawn())
		{
			PC->SetViewTargetWithBlend(Pawn, 0.6f, VTBlend_EaseInOut, 2.f);
			PC->SetControlRotation(FRotator(-8.f, Pawn->GetActorRotation().Yaw, 0.f));
		}
	}
	Phase = EPhase::Playing;
	LockPlayer(false);
	if (bSceneCompletesBeat)
	{
		bSceneCompletesBeat = false;
		Advance();
	}
}

// ------------------------------------------------------------------------------------------ tick

void AGIStory::TickMover(float DeltaSeconds, bool bTail)
{
	const FGIStoryBeat& B = Beats[BeatIndex];
	AGIPlayerCharacter* Player = GetPlayer();
	FActorState* S = FindActor(B.Npc);
	if (!Player || !S || !S->Comp || B.Path.Num() == 0)
	{
		return;
	}
	const FVector P = Player->GetActorLocation();
	const float Dist = FVector::Dist2D(P, MoverPos);
	float Want = B.PathSpeed;
	Warning.Reset();
	if (bTail)
	{
		if (Dist < 380.f && PhaseTime > 6.f)
		{
			FailBeat(FString::Printf(TEXT("%s ne tumhe dekh liya!"), *S->Name));
			return;
		}
		if (Dist < 650.f)
		{
			Warning = TEXT("Bahut paas! Peeche raho...");
		}
		if (Dist > 2600.f)
		{
			TooFarTime += DeltaSeconds;
			Warning = FString::Printf(TEXT("%s nazar se door ja raha hai!"), *S->Name);
			if (TooFarTime > 6.f)
			{
				FailBeat(FString::Printf(TEXT("%s nazar se ojhal ho gaya."), *S->Name));
				return;
			}
		}
		else
		{
			TooFarTime = 0.f;
		}
	}
	else
	{
		// lead the way, waiting (and looking back) when you fall behind
		if (Dist > 900.f)
		{
			Want = 0.f;
			Warning = FString::Printf(TEXT("%s tumhara intezaar kar raha hai"), *S->Name);
		}
		else if (Dist > 600.f)
		{
			Want = B.PathSpeed * 0.45f;
		}
	}
	MoverSpeed = FMath::FInterpTo(MoverSpeed, Want, DeltaSeconds, 4.f);
	float Step = MoverSpeed * DeltaSeconds;
	while (Step > 0.f && PathIndex + 1 < B.Path.Num())
	{
		const FVector Next = B.Path[PathIndex + 1];
		const FVector To = Next - MoverPos;
		const float Len = To.Size2D();
		if (Len <= Step)
		{
			MoverPos = Next;
			Step -= Len;
			++PathIndex;
		}
		else
		{
			MoverPos += To / Len * Step;
			Step = 0.f;
		}
	}
	S->Comp->SetWorldLocation(MoverPos);
	if (PathIndex + 1 < B.Path.Num())
	{
		if (MoverSpeed > 5.f)
		{
			const float Yaw = YawTo(MoverPos, B.Path[PathIndex + 1]) - 90.f;
			const FRotator Cur = S->Comp->GetComponentRotation();
			S->Comp->SetWorldRotation(FMath::RInterpTo(Cur, FRotator(0.f, Yaw, 0.f), DeltaSeconds, 8.f));
		}
		else if (!bTail)
		{
			const FRotator Cur = S->Comp->GetComponentRotation();
			S->Comp->SetWorldRotation(FMath::RInterpTo(Cur, FRotator(0.f, YawTo(MoverPos, P) - 90.f, 0.f), DeltaSeconds, 4.f));
		}
		SetActorMode(B.Npc, EGIPoseMode::Locomotion, MoverSpeed);
	}
	else
	{
		SetActorMode(B.Npc, EGIPoseMode::Locomotion, 0.f);
		if (!bTail || Dist < 3000.f)
		{
			// arrived: the follow ends when you catch up; the tail ends as soon as he gets there
			if (bTail || Dist < 450.f)
			{
				CompleteBeat();
			}
		}
	}
}

void AGIStory::TickCompanion(float DeltaSeconds)
{
	FActorState* S = FindActor(Companion);
	AGIPlayerCharacter* Player = GetPlayer();
	if (!S || !S->Comp || !Player || Player->IsRiding())
	{
		return;
	}
	const FVector P = Player->GetActorLocation() - FVector(0.f, 0.f, Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	FVector C = S->Comp->GetComponentLocation();
	const float Dist = FVector::Dist2D(P, C);
	if (Dist > 3000.f)
	{
		// lost: catch up behind you
		C = P - Player->GetActorForwardVector() * 200.f;
		S->Comp->SetWorldLocation(C);
		return;
	}
	const float Want = Dist > 600.f ? 420.f : (Dist > 220.f ? FMath::Min(Player->GetVelocity().Size2D() + 40.f, 380.f) : 0.f);
	CompanionSpeed = FMath::FInterpTo(CompanionSpeed, Want, DeltaSeconds, 5.f);
	if (CompanionSpeed > 1.f)
	{
		const FVector Dir = (P - C).GetSafeNormal2D();
		C += Dir * CompanionSpeed * DeltaSeconds;
		// stay on the ground
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(GIStoryGround), false, Player);
		if (GetWorld()->LineTraceSingleByChannel(Hit, C + FVector(0, 0, 150.f), C - FVector(0, 0, 300.f), ECC_Visibility, Q))
		{
			C.Z = Hit.Location.Z;
		}
		S->Comp->SetWorldLocation(C);
		S->Comp->SetWorldRotation(FMath::RInterpTo(S->Comp->GetComponentRotation(), FRotator(0.f, Dir.Rotation().Yaw - 90.f, 0.f), DeltaSeconds, 6.f));
	}
	SetActorMode(Companion, EGIPoseMode::Locomotion, CompanionSpeed);
}

void AGIStory::ApplyHour()
{
	if (AGIWeather* W = AGIWeather::Get(this))
	{
		W->SetHour(Hour);
	}
}

void AGIStory::DebugJump(int32 Beat, int32 HoldLine, float InHour)
{
	if (Beats.Num() == 0)
	{
		return;
	}
	bStarted = true;
	if (VoiceAudio && VoiceAudio->IsPlaying())
	{
		VoiceAudio->Stop();
	}
	bInScene = false;
	bSceneCompletesBeat = false;
	Fade = 0.f;
	FadeText.Reset();
	EndCardTime = 0.f;
	const int32 First = FMath::Clamp(Beat, 0, Beats.Num() - 1);
	// replay the clock and the weather of the beats skipped over, and their cast placements
	bool bRain = false;
	for (int32 i = 0; i < First; ++i)
	{
		if (Beats[i].Hour >= 0.f)
		{
			Hour = Beats[i].Hour;
		}
		if (Beats[i].Rain >= 0)
		{
			bRain = Beats[i].Rain > 0;
		}
		BeatIndex = i;
		ApplyBeatSetup();
	}
	if (AGIWeather* W = AGIWeather::Get(this))
	{
		W->SetRainingInstant(bRain);
	}
	if (InHour >= 0.f)
	{
		Hour = InHour;
	}
	DebugHoldLine = HoldLine;
	BeatIndex = First;
	ApplyBeatSetup();
	if (InHour >= 0.f)
	{
		Hour = InHour;
	}
	ApplyHour();
	BeginBeatPlay();
	if (HoldLine >= 0)
	{
		if (!bInScene)
		{
			StartScene(Beats[First].Lines);
		}
		StartLine(FMath::Clamp(HoldLine, 0, FMath::Max(0, SceneLines.Num() - 1)));
	}
	if (const AGIPlayerCharacter* P = GetPlayer())
	{
		const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
		UE_LOG(LogTemp, Display, TEXT("GIStory: jump %d actor yaw %.1f control yaw %.1f mesh yaw %.1f"), First, P->GetActorRotation().Yaw,
			PC ? PC->GetControlRotation().Yaw : 0.f, P->GetMesh()->GetComponentRotation().Yaw);
	}
}

void AGIStory::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ChapterTime = FMath::Max(0.f, ChapterTime - DeltaSeconds);
	BannerTime = FMath::Max(0.f, BannerTime - DeltaSeconds);
	Letterbox = FMath::FInterpConstantTo(Letterbox, IsCinematic() ? 1.f : 0.f, DeltaSeconds, 2.5f);

	// the clock
	if (Phase == EPhase::Playing || Phase == EPhase::FreeRoam || Phase == EPhase::Waiting)
	{
		Hour = FMath::Fmod(Hour + MinutesPerSecond * DeltaSeconds / 60.f, 24.f);
	}
	HourApplyTimer -= DeltaSeconds;
	if (HourApplyTimer <= 0.f)
	{
		HourApplyTimer = 0.2f;
		ApplyHour();
	}

	if (!bStarted)
	{
		// screenshot runs only start the story through a "story" shot
		static const bool bShotRun = FString(FCommandLine::Get()).Contains(TEXT("GIShots="));
		if (bShotRun)
		{
			return;
		}
		const AGIPlayerController* PC = Cast<AGIPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
		if (!PC || !PC->IsInGame() || Beats.Num() == 0)
		{
			return;
		}
		bStarted = true;
		int32 First = 0;
		int32 Hold = -1;
		float H = -1.f;
		const FString Debug = FPlatformMisc::GetEnvironmentVariable(TEXT("GI_STORY"));
		if (!Debug.IsEmpty())
		{
			FString A, Bs;
			if (Debug.Split(TEXT(":"), &A, &Bs))
			{
				First = FCString::Atoi(*A);
				Hold = FCString::Atoi(*Bs);
			}
			else
			{
				First = FCString::Atoi(*Debug);
			}
			const FString HS = FPlatformMisc::GetEnvironmentVariable(TEXT("GI_STORY_HOUR"));
			H = HS.IsEmpty() ? -1.f : FCString::Atof(*HS);
		}
		DebugJump(First, Hold, H);
		return;
	}

	switch (Phase)
	{
	case EPhase::FadeOut:
		PhaseTime += DeltaSeconds;
		Fade = FMath::Clamp(PhaseTime / FadeOutTime, 0.f, 1.f);
		if (PhaseTime >= FadeOutTime)
		{
			Phase = EPhase::FadeHold;
			PhaseTime = 0.f;
			ApplyBeatSetup();
		}
		return;
	case EPhase::FadeHold:
		PhaseTime += DeltaSeconds;
		Fade = 1.f;
		if (PhaseTime >= (FadeText.IsEmpty() ? 0.6f : FadeHoldTime))
		{
			Phase = EPhase::FadeIn;
			PhaseTime = 0.f;
		}
		return;
	case EPhase::FadeIn:
		PhaseTime += DeltaSeconds;
		Fade = 1.f - FMath::Clamp(PhaseTime / FadeInTime, 0.f, 1.f);
		if (PhaseTime >= FadeInTime * 0.35f && Phase == EPhase::FadeIn)
		{
			FadeText.Reset();
		}
		if (PhaseTime >= FadeInTime)
		{
			Fade = 0.f;
			BeginBeatPlay();
		}
		return;
	case EPhase::Scene:
	{
		if (!SceneLines.IsValidIndex(LineIndex))
		{
			EndScene();
			return;
		}
		LineTime += DeltaSeconds;
		PlaceCamera(SceneLines[LineIndex], LineTime / FMath::Max(LineDuration, 0.1f));
		if (DebugHoldLine < 0 && LineTime >= LineDuration)
		{
			StartLine(LineIndex + 1);
		}
		return;
	}
	case EPhase::EndCard:
		EndCardTime -= DeltaSeconds;
		if (EndCardTime <= 0.f)
		{
			EndCardTime = 0.f;
			Phase = EPhase::FreeRoam;
			LockPlayer(false);
			// everyone goes home; Saraswati walks with you
			for (FActorState& A : ActorStates)
			{
				if (A.Comp && A.Id != Companion)
				{
					A.Comp->SetVisibility(false, true);
				}
			}
			if (FActorState* S = FindActor(Companion))
			{
				if (S->Comp)
				{
					S->Comp->SetVisibility(true, true);
				}
			}
		}
		return;
	case EPhase::FreeRoam:
		TickCompanion(DeltaSeconds);
		return;
	case EPhase::Playing:
		PhaseTime += DeltaSeconds;
		break;
	default:
		return;
	}

	if (!Beats.IsValidIndex(BeatIndex))
	{
		return;
	}
	AGIPlayerCharacter* Player = GetPlayer();
	if (!Player || Player->IsDead())
	{
		return;
	}
	const FGIStoryBeat& B = Beats[BeatIndex];
	const FVector P = Player->IsRiding() ? Player->GetRidingBike()->GetActorLocation() : Player->GetActorLocation();
	if (BeatTimeLeft > 0.f)
	{
		BeatTimeLeft -= DeltaSeconds;
		if (BeatTimeLeft <= 0.f)
		{
			BeatTimeLeft = -1.f;
			FailBeat(TEXT("Der ho gayi..."));
			return;
		}
	}
	// the person you need to talk to idles facing you when you are close
	if (B.Kind == EGIBeatKind::TalkTo)
	{
		if (FActorState* S = FindActor(B.Npc))
		{
			if (S->Comp && FVector::Dist2D(S->Comp->GetComponentLocation(), P) < 700.f)
			{
				const FRotator Cur = S->Comp->GetComponentRotation();
				S->Comp->SetWorldRotation(FMath::RInterpTo(Cur, FRotator(0.f, YawTo(S->Comp->GetComponentLocation(), P) - 90.f, 0.f), DeltaSeconds, 3.f));
			}
		}
	}
	switch (B.Kind)
	{
	case EGIBeatKind::Reach:
		if (FVector::Dist2D(P, B.Location) < B.Radius && FMath::Abs(P.Z - B.Location.Z) < 400.f)
		{
			CompleteBeat();
		}
		break;
	case EGIBeatKind::Chai:
		if (Player->bDidChai)
		{
			CompleteBeat();
		}
		break;
	case EGIBeatKind::ReturnBall:
		if (Player->bReturnedBall)
		{
			CompleteBeat();
			break;
		}
		{
			// make it happen: once you're at the pitch the next shot comes your way; the ball gets the marker
			bool bWaiting = false;
			for (TActorIterator<AGICricketGame> It(GetWorld()); It; ++It)
			{
				FVector Ball;
				if (It->GetWaitingBall(Ball))
				{
					bWaiting = true;
				}
				else if (FVector::Dist2D(P, B.Location) < B.Radius + 300.f && FVector::Dist2D(P, It->GetActorLocation()) < 2400.f)
				{
					It->ForceNextToPlayer();
				}
			}
			if (bWaiting)
			{
				Warning = TEXT("Ball tumhari taraf aayi! Uske paas jao aur wapas phenko (E)");
			}
			else if (FVector::Dist2D(P, B.Location) < B.Radius + 300.f)
			{
				Warning = TEXT("Ruko... agla shot tumhari taraf aayega");
			}
			else
			{
				Warning.Reset();
			}
		}
		break;
	case EGIBeatKind::Follow:
		TickMover(DeltaSeconds, false);
		break;
	case EGIBeatKind::Tail:
		TickMover(DeltaSeconds, true);
		break;
	default:
		break;
	}
}
