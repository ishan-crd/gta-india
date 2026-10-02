#include "GIPlayerController.h"
#include "GIBike.h"
#include "GICrowdManager.h"
#include "GIGameUserSettings.h"
#include "GIHUD.h"
#include "GIInput.h"
#include "GIMission.h"
#include "GIPlayerCharacter.h"
#include "GITrain.h"
#include "GIDharavi.h"
#include "GIStory.h"
#include "GameFramework/GameModeBase.h"
#include "GICharacterMovement.h"
#include "SGIMenu.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "EngineUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Widgets/SWeakWidget.h"
#include "Misc/App.h"
#include "GIAssetSettings.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#include "UnrealEngine.h"
#include "RenderCore.h"
#include "RHI.h"
#include "HAL/FileManager.h"

AGIPlayerController::AGIPlayerController()
{
	bShowMouseCursor = false;
	bShouldPerformFullTickWhenPaused = true;
}

AGIPlayerCharacter* AGIPlayerController::GetCharacter() const
{
	return Cast<AGIPlayerCharacter>(GetPawn());
}

AGIBike* AGIPlayerController::GetBike() const
{
	return Cast<AGIBike>(GetPawn());
}

void AGIPlayerController::BeginPlay()
{
	Super::BeginPlay();
	if (!IsLocalController())
	{
		return;
	}

	if (UGIGameUserSettings* S = UGIGameUserSettings::Get())
	{
		S->AutoDetectIfFirstRun();
		S->ApplyGameSettings();
	}

	UpdateMappingContexts();

	// Title camera: slow dolly along the river.
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	TitleCamera = GetWorld()->SpawnActor<ACameraActor>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
	if (TitleCamera)
	{
		TitleCamera->GetCameraComponent()->SetFieldOfView(62.f);
		TitleCamera->GetCameraComponent()->bConstrainAspectRatio = false;
		UpdateTitleCamera(0.f);
		SetViewTarget(TitleCamera);
	}
	ShowMenu(EGIMenuPage::Title);
	LoadShots();
	// Arrived here from the city picker: skip the title and play.
	if (const AGameModeBase* GM = GetWorld()->GetAuthGameMode())
	{
		if (UGameplayStatics::HasOption(GM->OptionsString, TEXT("autostart")))
		{
			StartGame();
		}
	}

	const UGIAssetSettings& AS = UGIAssetSettings::Get();
	auto Amb = [this](USoundBase* S) -> UAudioComponent*
	{
		return S ? UGameplayStatics::SpawnSound2D(this, S, 0.f, 1.f, 0.f, nullptr, false, false) : nullptr;
	};
	AmbCity = Amb(AS.AmbCity.LoadSynchronous());
	if (!IsMumbai())
	{
		AmbRiver = Amb(AS.AmbRiver.LoadSynchronous());
		AmbBells = Amb(AS.TempleBells.LoadSynchronous());
	}
}

void AGIPlayerController::LoadShots()
{
	FString File;
	if (!FParse::Value(FCommandLine::Get(), TEXT("GIShots="), File))
	{
		return;
	}
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *File))
	{
		UE_LOG(LogTemp, Error, TEXT("GIShots: cannot read %s"), *File);
		QuitGame();
		return;
	}
	ShotDir = FPaths::Combine(FPaths::GetPath(File), TEXT("out"));
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	for (const FString& Line : Lines)
	{
		TArray<FString> T;
		Line.TrimStartAndEnd().ParseIntoArrayWS(T);
		if (T.Num() < 2 || T[0].StartsWith(TEXT("#")))
		{
			continue;
		}
		FGIShot S;
		S.Name = T[0];
		S.Kind = T[1];
		auto F = [&T](int32 i, float Def) { return T.IsValidIndex(i) ? FCString::Atof(*T[i]) : Def; };
		if (S.Kind == TEXT("cam"))
		{
			S.Loc = FVector(F(2, 0), F(3, 0), F(4, 0));
			S.Rot = FRotator(F(5, 0), F(6, 0), 0.f);
		}
		else if (S.Kind == TEXT("seq"))
		{
			S.Loc = FVector(F(2, 0), F(3, 0), F(4, 0));
			S.Rot = FRotator(0.f, F(5, 0), 0.f);
			S.Program = T.IsValidIndex(6) ? T[6] : TEXT("walkrun");
		}
		else if (S.Kind == TEXT("preset"))
		{
			S.Loc.X = F(2, 3);
		}
		else if (S.Kind == TEXT("city"))
		{
			S.Program = T.IsValidIndex(2) ? T[2] : TEXT("Mumbai");
		}
		else if (S.Kind == TEXT("story"))
		{
			// story <beat> <line or -1> [hour]
			S.Loc = FVector(F(2, 0), F(3, -1), F(4, -1));
		}
		else if (S.Kind == TEXT("player") || S.Kind == TEXT("climb") || S.Kind == TEXT("dive"))
		{
			S.Loc = FVector(F(2, 0), F(3, 0), F(4, 0));
			S.Rot = FRotator(F(6, -12.f), F(5, 0), 0.f);
		}
		Shots.Add(S);
	}
	UE_LOG(LogTemp, Display, TEXT("GIShots: loaded %d shots from %s"), Shots.Num(), *File);
	// After a "city" shot travelled here, carry on with the shots that follow it.
	int32 From = 0;
	if (const AGameModeBase* GM = GetWorld()->GetAuthGameMode())
	{
		From = UGameplayStatics::GetIntOption(GM->OptionsString, TEXT("shotsfrom"), 0);
	}
	if (Shots.IsValidIndex(From))
	{
		ShotIndex = From;
		ShotTimer = 0.f;
		BeginShot(Shots[From]);
	}
}

void AGIPlayerController::BeginShot(const FGIShot& Shot)
{
	bShotTaken = false;
	ShotTimer = 0.f;
	if (Shot.Kind == TEXT("cam"))
	{
		if (bInGame)
		{
			QuitToTitle();
		}
		HideMenu();
		bInGame = false;
		if (TitleCamera)
		{
			TitleCamera->SetActorLocationAndRotation(Shot.Loc, Shot.Rot);
			SetViewTarget(TitleCamera);
		}
	}
	else if (Shot.Kind == TEXT("story"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		if (AGIStory* Story = AGIStory::Get(this))
		{
			Story->DebugJump(FMath::RoundToInt(Shot.Loc.X), FMath::RoundToInt(Shot.Loc.Y), Shot.Loc.Z);
		}
	}
	else if (Shot.Kind == TEXT("player"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		if (APawn* P = GetPawn())
		{
			P->TeleportTo(Shot.Loc, FRotator(0.f, Shot.Rot.Yaw, 0.f));
			SetViewTarget(P);
		}
		SetControlRotation(Shot.Rot);
	}
	else if (Shot.Kind == TEXT("seq"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		if (AGIBike* B = GetBike())
		{
			B->Dismount();
		}
		if (AGIPlayerCharacter* C = GetCharacter())
		{
			C->TeleportTo(Shot.Loc, Shot.Rot);
			C->InputWalk(false);
			C->InputSprint(false);
		}
		SeqFrame = 0;
		SeqNext = 1.f;
		RouteIndex = 0;
		RouteStuckTimer = 0.f;
		if (TitleCamera)
		{
			SetViewTarget(TitleCamera);
		}
	}
	else if (Shot.Kind == TEXT("climb") || Shot.Kind == TEXT("dive"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		if (AGIBike* B = GetBike())
		{
			B->Dismount();
		}
		if (AGIPlayerCharacter* C = GetCharacter())
		{
			C->TeleportTo(Shot.Loc, FRotator(0.f, Shot.Rot.Yaw, 0.f));
			C->InputDive(Shot.Kind == TEXT("dive"));
			SetViewTarget(C);
		}
		SetControlRotation(Shot.Rot);
	}
	else if (Shot.Kind == TEXT("preset"))
	{
		// Apply a graphics preset, then keep the current view for the capture.
		if (UGIGameUserSettings* S = UGIGameUserSettings::Get())
		{
			const int32 Q = FMath::Clamp(FMath::RoundToInt(Shot.Loc.X), 0, 3);
			S->SetOverallScalabilityLevel(Q);
			S->CrowdDensity = Q;
			S->ScreenPercentage = Q == 0 ? 67.f : (Q == 1 ? 80.f : 100.f);
			S->bVolumetricFog = Q >= 2;
			S->ApplySettings(false);
		}
	}
	else if (Shot.Kind == TEXT("ride"))
	{
		// Mount the nearest bike and ride forward with a little steering.
		if (!bInGame)
		{
			StartGame();
		}
		AGIPlayerCharacter* C = GetCharacter();
		AGIBike* Bike = nullptr;
		for (TActorIterator<AGIBike> It(GetWorld()); It; ++It)
		{
			Bike = *It;
			break;
		}
		if (C && Bike)
		{
			C->TeleportTo(Bike->GetActorLocation() - Bike->GetActorRightVector() * 120.f + FVector(0, 0, 60.f), Bike->GetActorRotation());
			Bike->Mount(C);
			Bike->SetThrottle(1.f);
			Bike->SetSteer(0.15f);
		}
	}
	else if (Shot.Kind == TEXT("train"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		if (AGIBike* B = GetBike())
		{
			B->Dismount();
		}
		AGIPlayerCharacter* C = GetCharacter();
		for (TActorIterator<AGITrain> It(GetWorld()); It && C; ++It)
		{
			FVector Roof;
			const FVector Near = It->GetActorLocation() - FVector(3000.f, 0.f, 0.f);
			if (It->GetRoofPointNear(Near, 5000.f, Roof))
			{
				C->TeleportTo(Roof + FVector(0, 0, 100.f), FRotator(0.f, 0.f, 0.f));
				SetControlRotation(FRotator(-12.f, -35.f, 0.f));   // ahead and towards the river, like the clip
			}
			break;
		}
	}
	else if (Shot.Kind == TEXT("title"))
	{
		QuitToTitle();
	}
	else if (Shot.Kind == TEXT("city"))
	{
		// Travel like the menu's city picker does, then continue the list there.
		UGameplayStatics::OpenLevel(this, FName(*Shot.Program), true, FString::Printf(TEXT("autostart?shotsfrom=%d"), ShotIndex + 1));
	}
	else if (Shot.Kind == TEXT("rain") || Shot.Kind == TEXT("sun"))
	{
		// Same view as the previous shot, with the weather switched instantly.
		if (AGIWeather* W = AGIWeather::Get(this))
		{
			W->SetRainingInstant(Shot.Kind == TEXT("rain"));
		}
	}
	else if (Shot.Kind == TEXT("pause") || Shot.Kind == TEXT("settings"))
	{
		if (!bInGame)
		{
			StartGame();
		}
		SetPause(true);
		ShowMenu(Shot.Kind == TEXT("pause") ? EGIMenuPage::Pause : EGIMenuPage::Settings);
	}
}

void AGIPlayerController::TickShots(float DeltaTime)
{
	if (ShotIndex < 0 || ShotIndex >= Shots.Num())
	{
		return;
	}
	ShotTimer += FApp::GetDeltaTime();
	if (ShotTimer > 3.f && !bShotTaken)
	{
		PerfFrame.Add(FApp::GetDeltaTime() * 1000.f);
		PerfGame.Add(FPlatformTime::ToMilliseconds(GGameThreadTime));
		PerfRender.Add(FPlatformTime::ToMilliseconds(GRenderThreadTime));
		PerfGPU.Add(FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)));
	}
	static double LastLog = 0.0;
	if (FPlatformTime::Seconds() - LastLog > 5.0)
	{
		LastLog = FPlatformTime::Seconds();
		UE_LOG(LogTemp, Display, TEXT("GIShots: shot %d/%d timer %.2f dt %.4f"), ShotIndex, Shots.Num(), ShotTimer, FApp::GetDeltaTime());
	}
	// Scripted input for the climb test: swim forward until the climb-out is half way, then capture.
	const FGIShot& Cur = Shots[ShotIndex];
	if (Cur.Kind == TEXT("seq"))
	{
		TickSequence(Cur);
		return;
	}
	bool bCaptureNow = false;
	if (Cur.Kind == TEXT("climb") || Cur.Kind == TEXT("dive"))
	{
		if (AGIPlayerCharacter* C = GetCharacter())
		{
			if (Cur.Kind == TEXT("climb") && ShotTimer > 2.f)
			{
				C->AddMovementInput(FRotator(0.f, Cur.Rot.Yaw, 0.f).Vector(), 1.f);
			}
			if (Cur.Kind == TEXT("dive") && ShotTimer > 1.f)
			{
				C->AddMovementInput(FRotator(0.f, Cur.Rot.Yaw, 0.f).Vector(), 0.5f);
			}
			const UGICharacterMovement* M = C->GetGIMovement();
			bCaptureNow = Cur.Kind == TEXT("climb") && M && M->IsClimbingOut() && M->GetClimbAlpha() > 0.4f;
		}
	}
	// Let Lumen / streaming settle before capturing.
	if (!bShotTaken && (ShotTimer > 9.f || (bCaptureNow && ShotTimer > 3.f)))
	{
		const FString Path = FPaths::Combine(ShotDir, Shots[ShotIndex].Name + TEXT(".png"));
		FScreenshotRequest::RequestScreenshot(Path, true, false);
		WritePerf(Shots[ShotIndex].Name);
		UE_LOG(LogTemp, Display, TEXT("GIShots: requested %s"), *Path);
		ShotTakenAt = ShotTimer;
		bShotTaken = true;
	}
	if (bShotTaken && ShotTimer > ShotTakenAt + 1.0f)
	{
		++ShotIndex;
		if (ShotIndex >= Shots.Num())
		{
			QuitGame();
			return;
		}
		SetPause(false);
		BeginShot(Shots[ShotIndex]);
	}
}

void AGIPlayerController::TickSequence(const FGIShot& Shot)
{
	// Scripted movement for animation review; a side-tracking camera captures a frame every 0.2 s.
	AGIPlayerCharacter* C = GetCharacter();
	if (!C || !TitleCamera)
	{
		return;
	}
	const float T = ShotTimer;
	const FVector Base = FRotator(0.f, Shot.Rot.Yaw, 0.f).Vector();
	FVector Dir = Base;
	float Input = 0.f;
	bool bWalk = false, bSprint = false;
	if (Shot.Program == TEXT("walkrun"))
	{
		Input = (T > 1.f && T < 8.f) ? 1.f : 0.f;
		bWalk = T < 3.5f;
		bSprint = T > 6.f;
	}
	else if (Shot.Program == TEXT("turns"))
	{
		Input = T > 0.5f ? 1.f : 0.f;
		Dir = FRotator(0.f, Shot.Rot.Yaw + 70.f * FMath::Sin(T * 1.3f), 0.f).Vector();
	}
	else if (Shot.Program == TEXT("jump"))
	{
		Input = T > 0.5f ? 1.f : 0.f;
		if ((T > 3.f && T < 3.1f) || (T > 6.f && T < 6.1f))
		{
			C->Jump();
		}
		else
		{
			C->StopJumping();
		}
	}
	else if (Shot.Program == TEXT("route"))
	{
		// Full mission playthrough: steer through waypoints, log progress, detect getting stuck.
		static const FVector Route[] = {
			FVector(-12000, 13600, 0), FVector(-12000, 12500, 0), FVector(0, 12500, 0), FVector(0, 9700, 0),
			FVector(0, 6200, 0), FVector(0, 4300, 0), FVector(0, 600, 0), FVector(0, -14700, 0),
			FVector(0, -17200, 0), FVector(0, -18600, 0) };
		const int32 N = UE_ARRAY_COUNT(Route);
		const FVector P = C->GetActorLocation();
		if (RouteIndex < N)
		{
			const FVector To = Route[RouteIndex] - FVector(P.X, P.Y, 0.f);
			Dir = FVector(To.X, To.Y, 0.f).GetSafeNormal();
			Input = 1.f;
			bSprint = !C->IsSwimming();
			if (FVector::Dist2D(P, Route[RouteIndex]) < 260.f)
			{
				LogLine(FString::Printf(TEXT("route,waypoint=%d,t=%.1f,pos=(%.0f %.0f %.0f),hp=%.0f,money=%d"), RouteIndex, T, P.X, P.Y, P.Z, C->Health, C->Money));
				++RouteIndex;
			}
			RouteStuckTimer = FVector::Dist2D(P, RouteLastPos) < 15.f ? RouteStuckTimer + FApp::GetDeltaTime() : 0.f;
			RouteLastPos = P;
			if (RouteStuckTimer > 4.f)
			{
				LogLine(FString::Printf(TEXT("route,STUCK,waypoint=%d,t=%.1f,pos=(%.0f %.0f %.0f)"), RouteIndex, T, P.X, P.Y, P.Z));
				C->Jump();  // try to hop over small obstacles
				RouteStuckTimer = -2.f;
			}
		}
		if (const AGIMission* M = AGIMission::Get(this))
		{
			static int32 LastStage = -1;
			if ((int32)M->GetStage() != LastStage)
			{
				LastStage = (int32)M->GetStage();
				LogLine(FString::Printf(TEXT("route,stage=%d,t=%.1f,objective=%s"), LastStage, T, *M->GetObjective().ToString()));
			}
		}
	}
	else if (Shot.Program == TEXT("story"))
	{
		// Story autopilot: plays the whole mission - walks to each objective (with hints through the gallis),
		// presses E, follows / tails along the beat's path, races to the station; logs beats and failures.
		AGIStory* St = AGIStory::Get(this);
		const FVector P = C->GetActorLocation();
		static int32 LastBeat = -2, LastFails = 0, PathK = 0;
		static float SkipT = 0.f, DoneT = -1.f;
		if (!St)
		{
			return;
		}
		if (!St->HasStarted())
		{
			St->DebugJump(0, -1);
			LastBeat = -2; LastFails = 0; PathK = 0; DoneT = -1.f;
		}
		if (St->GetBeatIndex() != LastBeat || St->GetFailCount() != LastFails)
		{
			LogLine(FString::Printf(TEXT("story,beat=%d,fails=%d,t=%.1f,pos=(%.0f %.0f %.0f),hour=%.2f,objective=%s"), St->GetBeatIndex(),
				St->GetFailCount(), T, P.X, P.Y, P.Z, St->GetHour(), *St->GetObjective().ToString()));
			LastBeat = St->GetBeatIndex();
			LastFails = St->GetFailCount();
			RouteIndex = 0;
			PathK = 0;
		}
		if (St->IsFreeRoam())
		{
			if (DoneT < 0.f)
			{
				DoneT = T;
				LogLine(FString::Printf(TEXT("story,COMPLETE,t=%.1f"), T));
			}
		}
		else if (St->IsCinematic())
		{
			SkipT += FApp::GetDeltaTime();
			if (SkipT > 0.6f)
			{
				SkipT = 0.f;
				St->SkipLine();
			}
		}
		else if (St->IsPlaying() && St->Beats.IsValidIndex(St->GetBeatIndex()))
		{
			const FGIStoryBeat& B = St->Beats[St->GetBeatIndex()];
			FVector Goal;
			bool bGoal = St->GetTarget(Goal);
			// hints so the straight-line walker doesn't run into the houses
			TArray<FVector> Hints;
			switch (St->GetBeatIndex())
			{
			case 6: Hints = { FVector(6000, 3350, 0), FVector(6000, -6600, 0) }; break;
			case 9: Hints = { FVector(-500, 7120, 0), FVector(18500, 7120, 0), FVector(18500, 9300, 0), FVector(18500, 9850, 0),
				FVector(17700, 10650, 0), FVector(18300, 10650, 0) }; break;
			default: break;
			}
			if (RouteIndex < Hints.Num())
			{
				Goal = Hints[RouteIndex];
				bGoal = true;
				if (FVector::Dist2D(P, Goal) < 220.f)
				{
					++RouteIndex;
				}
			}
			else if ((B.Kind == EGIBeatKind::Follow || B.Kind == EGIBeatKind::Tail) && B.Path.Num() > 0)
			{
				// walk the beat's own path, never past the person you're with
				while (PathK < B.Path.Num() - 1 && FVector::Dist2D(P, B.Path[PathK]) < 200.f)
				{
					++PathK;
				}
				Goal = B.Path[PathK];
				const float D = FVector::Dist2D(P, St->GetMoverPos());
				const float Keep = B.Kind == EGIBeatKind::Tail ? 1100.f : 250.f;
				bGoal = D > Keep;
			}
			else if (B.Kind == EGIBeatKind::ReturnBall)
			{
				for (TActorIterator<AGICricketGame> It(GetWorld()); It; ++It)
				{
					FVector Ball;
					if (It->GetWaitingBall(Ball))
					{
						Goal = Ball;
						bGoal = true;
					}
					if (It->WantsBallFromPlayer(C))
					{
						It->PlayerReturnsBall(C);
					}
				}
				if (bGoal && FVector::Dist2D(P, Goal) < 120.f)
				{
					bGoal = false;
				}
			}
			FString Who;
			if (St->CanTalk(C, Who))
			{
				St->Talk(C);
				bGoal = false;
			}
			for (TActorIterator<AGIChaiStall> It(GetWorld()); It; ++It)
			{
				if (B.Kind == EGIBeatKind::Chai && It->CanServe(C) && !C->IsInAction())
				{
					It->Serve(C);
				}
			}
			if (bGoal && FVector::Dist2D(P, Goal) > 90.f)
			{
				const FVector To = Goal - FVector(P.X, P.Y, 0.f);
				Dir = FVector(To.X, To.Y, 0.f).GetSafeNormal();
				Input = 1.f;
				bSprint = B.Kind == EGIBeatKind::Reach || B.Kind == EGIBeatKind::Follow;
				RouteStuckTimer = FVector::Dist2D(P, RouteLastPos) < 10.f ? RouteStuckTimer + FApp::GetDeltaTime() : 0.f;
				RouteLastPos = P;
				if (RouteStuckTimer > 5.f)
				{
					LogLine(FString::Printf(TEXT("story,STUCK,beat=%d,t=%.1f,pos=(%.0f %.0f %.0f),goal=(%.0f %.0f)"), St->GetBeatIndex(), T,
						P.X, P.Y, P.Z, Goal.X, Goal.Y));
					C->Jump();
					RouteStuckTimer = -3.f;
				}
			}
		}
		if (DoneT >= 0.f && T > DoneT + 25.f)
		{
			RouteIndex = 999;   // finished: the shot ends below
		}
	}
	else if (Shot.Program == TEXT("steps"))
	{
		Input = (T > 1.f && T < 8.5f) ? 1.f : 0.f;
		bWalk = true;
	}
	C->InputWalk(bWalk);
	C->InputSprint(bSprint);
	if (Input > 0.f)
	{
		C->AddMovementInput(Dir, Input);
	}
	const bool bRoute = Shot.Program == TEXT("route") || Shot.Program == TEXT("story");
	const bool bStory = Shot.Program == TEXT("story");
	if (bRoute)
	{
		const AGIStory* StoryNow = AGIStory::Get(this);
		if (GetViewTarget() != C && !(StoryNow && StoryNow->IsCinematic()))
		{
			SetViewTarget(C);
		}
		SetControlRotation(FRotator(-12.f, FMath::FixedTurn(GetControlRotation().Yaw, Dir.Rotation().Yaw, 120.f * FApp::GetDeltaTime()), 0.f));
	}
	else
	{
		// Side camera: 4.5 m to the character's right, slightly above, looking at the hips.
		const FVector P = C->GetActorLocation();
		const FVector Right = FRotator(0.f, Shot.Rot.Yaw + 90.f, 0.f).Vector();
		const FVector CamPos = P + Right * 420.f + Base * 60.f + FVector(0.f, 0.f, 30.f);
		TitleCamera->SetActorLocationAndRotation(CamPos, (P - FVector(0, 0, 10.f) - CamPos).Rotation());
	}

	if (T >= SeqNext && SeqFrame < (bStory ? 90 : (bRoute ? 60 : 45)))
	{
		SeqNext = T + (bStory ? 12.f : (bRoute ? 4.f : 0.2f));
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(ShotDir, FString::Printf(TEXT("%s_%03d.png"), *Shot.Name, SeqFrame++)), false, false);
	}
	if (T > (bStory ? 1500.f : (bRoute ? 240.f : 10.f)) || (bStory && RouteIndex >= 999) || (!bStory && bRoute && RouteIndex >= 10 && T > SeqNext - 3.f))
	{
		++ShotIndex;
		if (ShotIndex >= Shots.Num())
		{
			QuitGame();
			return;
		}
		BeginShot(Shots[ShotIndex]);
	}
}

void AGIPlayerController::LogLine(const FString& Line)
{
	FFileHelper::SaveStringToFile(Line + TEXT("\n"), *FPaths::Combine(ShotDir, TEXT("perf.csv")), FFileHelper::EEncodingOptions::AutoDetect,
		&IFileManager::Get(), FILEWRITE_Append);
}

void AGIPlayerController::WritePerf(const FString& ShotName)
{
	auto Avg = [](const TArray<float>& A) { float S = 0.f; for (float V : A) { S += V; } return A.Num() ? S / A.Num() : 0.f; };
	auto Worst = [](TArray<float> A) { A.Sort(); return A.Num() ? A[FMath::Clamp(int32(A.Num() * 0.99f), 0, A.Num() - 1)] : 0.f; };
	const float F = Avg(PerfFrame);
	const FString Line = FString::Printf(TEXT("%s,fps=%.1f,frame_ms=%.2f,p99_ms=%.2f,game_ms=%.2f,render_ms=%.2f,gpu_ms=%.2f,samples=%d\n"),
		*ShotName, F > 0.f ? 1000.f / F : 0.f, F, Worst(PerfFrame), Avg(PerfGame), Avg(PerfRender), Avg(PerfGPU), PerfFrame.Num());
	FFileHelper::SaveStringToFile(Line, *FPaths::Combine(ShotDir, TEXT("perf.csv")), FFileHelper::EEncodingOptions::AutoDetect,
		&IFileManager::Get(), FILEWRITE_Append);
	PerfFrame.Reset();
	PerfGame.Reset();
	PerfRender.Reset();
	PerfGPU.Reset();
}

void AGIPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
	HideMenu();
	Super::EndPlay(Reason);
}

void AGIPlayerController::UpdateMappingContexts()
{
	ULocalPlayer* LP = GetLocalPlayer();
	UEnhancedInputLocalPlayerSubsystem* Sub = LP ? LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
	if (!Sub)
	{
		return;
	}
	UGIInput& In = UGIInput::Get();
	Sub->ClearAllMappings();
	Sub->AddMappingContext(In.Common, 1);
	Sub->AddMappingContext(GetBike() ? In.Driving : In.OnFoot, 0);
}

void AGIPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	UpdateMappingContexts();
}

void AGIPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(InputComponent);
	if (!EIC)
	{
		return;
	}
	UGIInput& In = UGIInput::Get();
	EIC->BindAction(In.Move, ETriggerEvent::Triggered, this, &AGIPlayerController::OnMove);
	EIC->BindAction(In.Look, ETriggerEvent::Triggered, this, &AGIPlayerController::OnLook);
	EIC->BindAction(In.Jump, ETriggerEvent::Started, this, &AGIPlayerController::OnJumpStarted);
	EIC->BindAction(In.Jump, ETriggerEvent::Completed, this, &AGIPlayerController::OnJumpCompleted);
	EIC->BindAction(In.Sprint, ETriggerEvent::Started, this, &AGIPlayerController::OnSprintStarted);
	EIC->BindAction(In.Sprint, ETriggerEvent::Completed, this, &AGIPlayerController::OnSprintCompleted);
	EIC->BindAction(In.Interact, ETriggerEvent::Started, this, &AGIPlayerController::OnInteract);
	EIC->BindAction(In.Vehicle, ETriggerEvent::Started, this, &AGIPlayerController::OnVehicle);
	EIC->BindAction(In.Pause, ETriggerEvent::Started, this, &AGIPlayerController::OnPause);
	EIC->BindAction(In.Throttle, ETriggerEvent::Triggered, this, &AGIPlayerController::OnThrottle);
	EIC->BindAction(In.Throttle, ETriggerEvent::Completed, this, &AGIPlayerController::OnThrottleCompleted);
	EIC->BindAction(In.Steer, ETriggerEvent::Triggered, this, &AGIPlayerController::OnSteer);
	EIC->BindAction(In.Steer, ETriggerEvent::Completed, this, &AGIPlayerController::OnSteerCompleted);
	EIC->BindAction(In.Brake, ETriggerEvent::Started, this, &AGIPlayerController::OnBrakeStarted);
	EIC->BindAction(In.Brake, ETriggerEvent::Completed, this, &AGIPlayerController::OnBrakeCompleted);
	EIC->BindAction(In.Horn, ETriggerEvent::Started, this, &AGIPlayerController::OnHorn);
	EIC->BindAction(In.Dive, ETriggerEvent::Started, this, &AGIPlayerController::OnDiveStarted);
	EIC->BindAction(In.Walk, ETriggerEvent::Started, this, &AGIPlayerController::OnWalkStarted);
	EIC->BindAction(In.Walk, ETriggerEvent::Completed, this, &AGIPlayerController::OnWalkCompleted);
	EIC->BindAction(In.Dive, ETriggerEvent::Completed, this, &AGIPlayerController::OnDiveCompleted);
}

void AGIPlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	TickShots(DeltaTime);
	UpdateAmbience();
	if (!bInGame && ShotIndex < 0)
	{
		UpdateTitleCamera(DeltaTime);
	}
}

void AGIPlayerController::UpdateAmbience()
{
	if (!PlayerCameraManager)
	{
		return;
	}
	// River ambience near the water, city bustle inland, temple bells around the ghats.
	const FVector Cam = PlayerCameraManager->GetCameraLocation();
	const float DistToWater = Cam.Y > 0.f ? Cam.Y : (Cam.Y < -15000.f ? -15000.f - Cam.Y : 0.f);
	const float RiverVol = FMath::Clamp(1.f - DistToWater / 9000.f, 0.12f, 1.f);
	const float CityVol = FMath::Clamp((Cam.Y - 1500.f) / 9000.f, 0.08f, 1.f) * (Cam.Y < -15000.f ? 0.3f : 1.f);
	const float BellVol = FMath::Clamp(1.f - FMath::Abs(Cam.Y - 2500.f) / 7000.f, 0.f, 1.f) * FMath::Clamp(1.f - FMath::Abs(Cam.X) / 30000.f, 0.2f, 1.f);
	if (AmbRiver) { AmbRiver->SetVolumeMultiplier(0.8f * RiverVol); }
	if (AmbCity) { AmbCity->SetVolumeMultiplier(0.45f * CityVol); }
	if (AmbBells) { AmbBells->SetVolumeMultiplier(0.35f * BellVol); }
}

void AGIPlayerController::UpdateTitleCamera(float DeltaTime)
{
	if (!TitleCamera)
	{
		return;
	}
	TitleTime += DeltaTime;
	FVector Start(-6000.f, -9000.f, 2500.f), End(6000.f, -9000.f, 2200.f), LookAt(0.f, 3000.f, 1200.f);
	if (const AGIMission* M = AGIMission::Get(this))
	{
		Start = M->TitleCamStart;
		End = M->TitleCamEnd;
		LookAt = M->TitleCamLookAt;
	}
	const float Alpha = 0.5f - 0.5f * FMath::Cos(TitleTime * 2.f * PI / 70.f);
	const FVector Pos = FMath::Lerp(Start, End, Alpha);
	const FVector Look = LookAt + (End - Start) * (Alpha - 0.5f) * 0.6f;
	TitleCamera->SetActorLocationAndRotation(Pos, (Look - Pos).Rotation());
}

// ---------------------------------------------------------------------------------------------
// Menus

void AGIPlayerController::ShowMenu(EGIMenuPage Page)
{
	if (!GEngine || !GEngine->GameViewport)
	{
		return;
	}
	if (!Menu.IsValid())
	{
		SAssignNew(Menu, SGIMenu).Owner(this);
		MenuContainer = SNew(SWeakWidget).PossiblyNullContent(Menu.ToSharedRef());
		GEngine->GameViewport->AddViewportWidgetContent(MenuContainer.ToSharedRef(), 50);
	}
	CurrentPage = Page;
	Menu->ShowPage(Page);
	// The title screen idles at 30 fps to be gentle on the shared GPU.
	if (Page == EGIMenuPage::Title && GEngine)
	{
		GEngine->SetMaxFPS(30.f);
	}

	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(Menu);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(Mode);
	bShowMouseCursor = true;
	Menu->FocusFirst();

	if (AGIHUD* H = Cast<AGIHUD>(GetHUD()))
	{
		H->bGameplayHUDVisible = false;
	}
}

void AGIPlayerController::HideMenu()
{
	if (MenuContainer.IsValid() && GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(MenuContainer.ToSharedRef());
	}
	Menu.Reset();
	MenuContainer.Reset();
	CurrentPage = EGIMenuPage::None;

	if (bInGame)
	{
		SetInputMode(FInputModeGameOnly());
		bShowMouseCursor = false;
		if (AGIHUD* H = Cast<AGIHUD>(GetHUD()))
		{
			H->bGameplayHUDVisible = true;
		}
	}
}

void AGIPlayerController::StartGame()
{
	bInGame = true;
	if (GEngine)
	{
		const UGIGameUserSettings* S = UGIGameUserSettings::Get();
		GEngine->SetMaxFPS(S ? S->GetFrameRateLimit() : 0.f);
	}
	HideMenu();
	SetPause(false);
	if (APawn* P = GetPawn())
	{
		SetViewTargetWithBlend(P, 1.6f, VTBlend_EaseInOut, 2.f);
		const AGILevelProfile* Profile = AGILevelProfile::Get(this);
		SetControlRotation(FRotator(Profile ? Profile->StartPitch : -10.f, P->GetActorRotation().Yaw, 0.f));
	}
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->ApplyUserSettings();
	}
}

bool AGIPlayerController::IsMumbai() const
{
	return GetWorld() && GetWorld()->GetMapName().Contains(TEXT("Mumbai"));
}

void AGIPlayerController::StartCity(FName MapName)
{
	const bool bHere = GetWorld()->GetMapName().EndsWith(MapName.ToString());
	if (bHere)
	{
		StartGame();
		return;
	}
	SetPause(false);
	UGameplayStatics::OpenLevel(this, MapName, true, TEXT("autostart"));
}

void AGIPlayerController::ToggleWeather()
{
	if (AGIWeather* W = AGIWeather::Get(this))
	{
		W->SetRaining(!W->IsRaining());
	}
	ResumeGame();
}

void AGIPlayerController::ResumeGame()
{
	HideMenu();
	SetPause(false);
}

void AGIPlayerController::QuitToTitle()
{
	SetPause(false);
	bInGame = false;
	if (TitleCamera)
	{
		SetViewTargetWithBlend(TitleCamera, 1.f);
	}
	ShowMenu(EGIMenuPage::Title);
}

void AGIPlayerController::QuitGame()
{
	UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false);
}

void AGIPlayerController::OpenPage(EGIMenuPage Page)
{
	if (Page == EGIMenuPage::None)
	{
		Page = bInGame ? EGIMenuPage::Pause : EGIMenuPage::Title;
	}
	if (Page == EGIMenuPage::Settings)
	{
		SettingsReturnPage = bInGame ? EGIMenuPage::Pause : EGIMenuPage::Title;
	}
	ShowMenu(Page);
}

void AGIPlayerController::CloseSettings()
{
	if (UGIGameUserSettings* S = UGIGameUserSettings::Get())
	{
		S->ApplySettings(false);
		S->SaveSettings();
	}
	ShowMenu(SettingsReturnPage);
}

void AGIPlayerController::OnSettingsChanged(bool bCrowdChanged)
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->ApplyUserSettings();
	}
	for (TActorIterator<AGIPlayerCharacter> It(GetWorld()); It; ++It)
	{
		It->ApplyUserSettings();
	}
	if (bCrowdChanged)
	{
		for (TActorIterator<AGICrowdManager> It(GetWorld()); It; ++It)
		{
			It->Rebuild();
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Input routing

void AGIPlayerController::OnMove(const FInputActionValue& V)
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputMove(V);
	}
}

void AGIPlayerController::OnLook(const FInputActionValue& V)
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputLook(V);
	}
	else if (AGIBike* B = GetBike())
	{
		const FVector2D Raw = V.Get<FVector2D>();
		const FVector2D L(FMath::Clamp(Raw.X, -20.f, 20.f), FMath::Clamp(Raw.Y, -20.f, 20.f));
		const UGIGameUserSettings* S = UGIGameUserSettings::Get();
		const float Sens = S ? S->MouseSensitivity : 1.f;
		AddYawInput(L.X * Sens);
		AddPitchInput((S && S->bInvertY ? -L.Y : L.Y) * Sens);
		if (!L.IsNearlyZero(0.05f))
		{
			B->NotifyLookInput();
		}
	}
}

void AGIPlayerController::OnJumpStarted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputJumpStart();
	}
}

void AGIPlayerController::OnJumpCompleted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputJumpStop();
	}
}

void AGIPlayerController::OnSprintStarted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputSprint(true);
	}
}

void AGIPlayerController::OnSprintCompleted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputSprint(false);
	}
}

void AGIPlayerController::OnInteract()
{
	if (AGIStory* Story = AGIStory::Get(this))
	{
		if (Story->IsCinematic())
		{
			Story->SkipLine();
			return;
		}
	}
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputInteract();
	}
}

void AGIPlayerController::OnVehicle()
{
	if (AGIBike* B = GetBike())
	{
		B->Dismount();
	}
	else if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputVehicle();
	}
}

void AGIPlayerController::OnPause()
{
	if (bInGame && !IsInMenu())
	{
		SetPause(true);
		ShowMenu(EGIMenuPage::Pause);
	}
}

void AGIPlayerController::OnThrottle(const FInputActionValue& V)
{
	if (AGIBike* B = GetBike())
	{
		B->SetThrottle(V.Get<float>());
	}
}

void AGIPlayerController::OnThrottleCompleted()
{
	if (AGIBike* B = GetBike())
	{
		B->SetThrottle(0.f);
	}
}

void AGIPlayerController::OnSteer(const FInputActionValue& V)
{
	if (AGIBike* B = GetBike())
	{
		B->SetSteer(V.Get<float>());
	}
}

void AGIPlayerController::OnSteerCompleted()
{
	if (AGIBike* B = GetBike())
	{
		B->SetSteer(0.f);
	}
}

void AGIPlayerController::OnBrakeStarted()
{
	if (AGIBike* B = GetBike())
	{
		B->SetBrake(true);
	}
}

void AGIPlayerController::OnBrakeCompleted()
{
	if (AGIBike* B = GetBike())
	{
		B->SetBrake(false);
	}
}

void AGIPlayerController::OnHorn()
{
	if (AGIBike* B = GetBike())
	{
		B->Honk();
	}
}

void AGIPlayerController::OnDiveStarted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputDive(true);
	}
}

void AGIPlayerController::OnDiveCompleted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputDive(false);
	}
}

void AGIPlayerController::OnWalkStarted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputWalk(true);
	}
}

void AGIPlayerController::OnWalkCompleted()
{
	if (AGIPlayerCharacter* C = GetCharacter())
	{
		C->InputWalk(false);
	}
}
