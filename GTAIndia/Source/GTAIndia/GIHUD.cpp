#include "GIHUD.h"
#include "GIRiver.h"
#include "GIAssetSettings.h"
#include "GIBike.h"
#include "GIGameUserSettings.h"
#include "GIMission.h"
#include "GIPlayerCharacter.h"
#include "CanvasItem.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TextureResource.h"
#include "GlobalRenderResources.h"

namespace
{
	const FLinearColor Gold(1.f, 0.78f, 0.12f, 1.f);
	const FLinearColor PanelBg(0.f, 0.f, 0.f, 0.55f);
	const FLinearColor MoneyGreen(0.45f, 0.95f, 0.45f, 1.f);
	constexpr float MinimapOrthoWidth = 9000.f;

	FString FormatRupees(int32 Amount)
	{
		// Indian grouping: 12,34,567
		FString Digits = FString::FromInt(FMath::Abs(Amount));
		FString Out;
		const int32 Len = Digits.Len();
		for (int32 i = 0; i < Len; ++i)
		{
			const int32 FromRight = Len - i;
			Out.AppendChar(Digits[i]);
			if (FromRight > 1 && (FromRight == 4 || (FromRight > 4 && (FromRight - 4) % 2 == 0)))
			{
				Out.AppendChar(TEXT(','));
			}
		}
		return (Amount < 0 ? TEXT("-") : TEXT("")) + FString(TEXT("₹ ")) + Out;
	}
}

AGIHUD::AGIHUD()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AGIHUD::BeginPlay()
{
	Super::BeginPlay();
	BigFont = GEngine->GetLargeFont();
	MedFont = GEngine->GetMediumFont();
	SmallFont = GEngine->GetSmallFont();
}

AGIPlayerCharacter* AGIHUD::GetPlayerCharacter() const
{
	if (BoundPlayer.IsValid())
	{
		return BoundPlayer.Get();
	}
	for (TActorIterator<AGIPlayerCharacter> It(GetWorld()); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

void AGIHUD::BindPlayer()
{
	if (BoundPlayer.IsValid())
	{
		return;
	}
	if (AGIPlayerCharacter* P = GetPlayerCharacter())
	{
		BoundPlayer = P;
		PopupHandle = P->OnPopup.AddUObject(this, &AGIHUD::AddPopup);
	}
}

void AGIHUD::AddPopup(const FText& InText)
{
	if (InText.ToString().StartsWith(TEXT("\"")))
	{
		Subtitle = InText.ToString();
		SubtitleTime = 2.8f;
		return;
	}
	FPopup P;
	P.Text = InText;
	Popups.Insert(P, 0);
	if (Popups.Num() > 5)
	{
		Popups.SetNum(5);
	}
}

void AGIHUD::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	BindPlayer();
	for (FPopup& P : Popups)
	{
		P.Age += DeltaSeconds;
	}
	Popups.RemoveAll([](const FPopup& P) { return P.Age > 2.6f; });
	SubtitleTime = FMath::Max(0.f, SubtitleTime - DeltaSeconds);
	if (DeltaSeconds > 0.f)
	{
		SmoothedFPS = FMath::Lerp(SmoothedFPS, 1.f / DeltaSeconds, 0.05f);
	}
	if (const AGIPlayerCharacter* P = GetPlayerCharacter())
	{
		DisplayedHealth = FMath::FInterpTo(DisplayedHealth, P->Health, DeltaSeconds, 6.f);
	}
}

// ---------------------------------------------------------------------------------------------
// Drawing primitives

void AGIHUD::Rect(float X, float Y, float W, float H, const FLinearColor& C)
{
	FCanvasTileItem Tile(FVector2D(X, Y), FVector2D(W, H), C);
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

FVector2D AGIHUD::TextSize(const FString& Str, UFont* Font, float Scale)
{
	float W = 0.f, H = 0.f;
	Canvas->TextSize(Font, Str, W, H, Scale, Scale);
	return FVector2D(W, H);
}

void AGIHUD::Text(const FString& Str, float X, float Y, UFont* Font, float Scale, const FLinearColor& C, bool bCenterX, bool bShadow)
{
	FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(Str), Font, C);
	Item.Scale = FVector2D(Scale, Scale);
	Item.bCentreX = bCenterX;
	if (bShadow)
	{
		Item.EnableShadow(FLinearColor(0.f, 0.f, 0.f, 0.85f * C.A), FVector2D(1.5f, 1.5f));
	}
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

void AGIHUD::Disc(const FVector2D& Center, float Radius, const FLinearColor& C, int32 Sides)
{
	FCanvasNGonItem Item(Center, FVector2D(Radius, Radius), Sides, C);
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

void AGIHUD::Triangle(const FVector2D& A, const FVector2D& B, const FVector2D& C, const FLinearColor& Color)
{
	FCanvasTriangleItem Item(A, B, C, GWhiteTexture);
	Item.SetColor(Color);
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

// ---------------------------------------------------------------------------------------------

void AGIHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas)
	{
		return;
	}
	const float S = Canvas->ClipY / 1080.f;

	const UGIGameUserSettings* GS = UGIGameUserSettings::Get();
	if (GS && GS->bShowFPS)
	{
		DrawFPS(S);
	}

	if (!bGameplayHUDVisible)
	{
		return;
	}

	const AGIPlayerCharacter* Player = GetPlayerCharacter();
	DrawMissionBox(S);
	if (Player)
	{
		DrawStats(Player, S);
		DrawMinimap(Player, S);
		DrawWorldMarker(S);
		DrawPrompt(Player, S);
	}
	DrawBanner(S);
	if (SubtitleTime > 0.f && !Subtitle.IsEmpty())
	{
		const float Alpha = FMath::Clamp(SubtitleTime / 0.4f, 0.f, 1.f);
		const FVector2D TS = TextSize(Subtitle, MedFont, 1.0f * S);
		const float Y = Canvas->ClipY * 0.86f;
		Rect(Canvas->ClipX * 0.5f - TS.X * 0.5f - 14.f * S, Y - 6.f * S, TS.X + 28.f * S, TS.Y + 12.f * S, FLinearColor(0.f, 0.f, 0.f, 0.5f * Alpha));
		Text(Subtitle, Canvas->ClipX * 0.5f, Y, MedFont, 1.0f * S, FLinearColor(1.f, 1.f, 1.f, Alpha), true);
	}
	if (Player && Player->IsDead())
	{
		DrawDeath(S);
	}
}

void AGIHUD::DrawMissionBox(float S)
{
	const AGIMission* Mission = AGIMission::Get(this);
	if (!Mission)
	{
		return;
	}
	const float X = 28.f * S, Y = 28.f * S, W = 470.f * S;
	const FString Title = Mission->GetTitle().ToString();
	const FString Obj = Mission->GetObjective().ToString();
	const float TitleScale = 1.05f * S, ObjScale = 0.95f * S;
	const float H = 92.f * S;
	Rect(X, Y, W, H, PanelBg);
	Rect(X, Y, 5.f * S, H, Gold);
	Text(Title, X + 18.f * S, Y + 10.f * S, MedFont, TitleScale, Gold);
	Text(Obj, X + 18.f * S, Y + 44.f * S, SmallFont, ObjScale * 1.25f, FLinearColor::White);

	const float TimeLeft = Mission->GetTimeLeft();
	if (TimeLeft >= 0.f)
	{
		const int32 Secs = FMath::Max(0, FMath::CeilToInt(TimeLeft));
		const FString T = FString::Printf(TEXT("%02d:%02d"), Secs / 60, Secs % 60);
		const FLinearColor TC = TimeLeft < 60.f ? FLinearColor(1.f, 0.3f, 0.25f) : FLinearColor::White;
		const FVector2D TS = TextSize(T, MedFont, 1.1f * S);
		Text(T, X + W - TS.X - 14.f * S, Y + 10.f * S, MedFont, 1.1f * S, TC);
	}
}

void AGIHUD::DrawStats(const AGIPlayerCharacter* Player, float S)
{
	const float W = 250.f * S;
	const float X = Canvas->ClipX - W - 32.f * S;
	float Y = 30.f * S;

	// Clock (GTA style): the day starts at 09:30 and runs one game minute every 4 seconds.
	{
		const int32 Minutes = 9 * 60 + 30 + FMath::FloorToInt(GetWorld()->GetTimeSeconds() / 4.f);
		const FString Clock = FString::Printf(TEXT("%02d:%02d"), (Minutes / 60) % 24, Minutes % 60);
		const FVector2D CS = TextSize(Clock, BigFont, 1.0f * S);
		Text(Clock, X + W - CS.X, Y - 4.f * S, BigFont, 1.0f * S, FLinearColor::White);
		Y += CS.Y + 6.f * S;
	}

	// Health bar.
	const float Frac = FMath::Clamp(DisplayedHealth / FMath::Max(Player->MaxHealth, 1.f), 0.f, 1.f);
	const bool bPoisoned = Player->IsSwimming();
	const FLinearColor Fill = bPoisoned ? FLinearColor(0.9f, 0.12f, 0.1f)
		: (Frac > 0.5f ? FLinearColor(0.25f, 0.85f, 0.3f) : (Frac > 0.25f ? FLinearColor(0.95f, 0.65f, 0.15f) : FLinearColor(0.9f, 0.18f, 0.15f)));
	if (bPoisoned)
	{
		// Status line like the reference: "Status: Poisoned"
		const FString Status = TEXT("Haalat: ZEHER  (Ganga ka paani)");
		const float Pulse = 0.65f + 0.35f * FMath::Sin(GetWorld()->GetTimeSeconds() * 5.f);
		const FVector2D SS = TextSize(Status, SmallFont, 1.05f * S);
		Rect(Canvas->ClipX * 0.5f - SS.X * 0.5f - 12.f * S, 18.f * S, SS.X + 24.f * S, SS.Y + 8.f * S, FLinearColor(0.f, 0.f, 0.f, 0.55f));
		Text(Status, Canvas->ClipX * 0.5f, 22.f * S, SmallFont, 1.05f * S, FLinearColor(1.f, 0.3f * Pulse + 0.2f, 0.2f, 1.f), true);
	}
	Rect(X - 4.f * S, Y - 4.f * S, W + 8.f * S, 22.f * S, PanelBg);
	Rect(X, Y, W * Frac, 14.f * S, Fill);
	const FString HP = FString::Printf(TEXT("%d/%d"), FMath::CeilToInt(Player->Health), FMath::RoundToInt(Player->MaxHealth));
	const FVector2D HS = TextSize(HP, SmallFont, 1.05f * S);
	Text(HP, X + W - HS.X - 4.f * S, Y - 1.f * S, SmallFont, 1.05f * S, FLinearColor::White);
	Y += 30.f * S;

	// Money.
	const FString Money = FormatRupees(Player->Money);
	const FVector2D MS = TextSize(Money, BigFont, 1.1f * S);
	Rect(X + W - MS.X - 20.f * S, Y, MS.X + 20.f * S, MS.Y + 6.f * S, PanelBg);
	Text(Money, X + W - MS.X - 10.f * S, Y + 3.f * S, BigFont, 1.1f * S, MoneyGreen);
	Y += MS.Y + 16.f * S;

	// Popups under the money.
	for (const FPopup& P : Popups)
	{
		const float Alpha = FMath::Clamp(2.6f - P.Age, 0.f, 1.f);
		const FString Str = P.Text.ToString();
		FLinearColor C = Gold;
		if (Str.StartsWith(TEXT("+")))
		{
			C = MoneyGreen;
		}
		else if (Str.StartsWith(TEXT("HP")) || Str.StartsWith(TEXT("-")) || Str.Contains(TEXT("bill")))
		{
			C = FLinearColor(1.f, 0.35f, 0.3f);
		}
		C.A = Alpha;
		const FVector2D PS = TextSize(Str, MedFont, 0.95f * S);
		const float Rise = FMath::Min(P.Age, 0.3f) * 30.f * S;
		Rect(X + W - PS.X - 16.f * S, Y - Rise, PS.X + 16.f * S, PS.Y + 4.f * S, FLinearColor(0.f, 0.f, 0.f, 0.45f * Alpha));
		Text(Str, X + W - PS.X - 8.f * S, Y + 2.f * S - Rise, MedFont, 0.95f * S, C);
		Y += PS.Y + 10.f * S;
	}

	// Speedometer when riding.
	if (const AGIBike* Bike = Player->GetRidingBike())
	{
		const FString Spd = FString::Printf(TEXT("%d km/h"), FMath::RoundToInt(Bike->GetSpeedKmh()));
		const FVector2D SS = TextSize(Spd, BigFont, 1.2f * S);
		Text(Spd, Canvas->ClipX - SS.X - 40.f * S, Canvas->ClipY - SS.Y - 40.f * S, BigFont, 1.2f * S, FLinearColor::White);
	}
}

void AGIHUD::EnsureMinimap()
{
	if (MinimapCapture)
	{
		return;
	}
	MinimapRT = UKismetRenderingLibrary::CreateRenderTarget2D(this, 384, 384, RTF_RGBA8);
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	MinimapCapture = GetWorld()->SpawnActor<ASceneCapture2D>(FVector(0, 0, 30000.f), FRotator(-90.f, 0.f, 0.f), Params);
	if (!MinimapCapture)
	{
		return;
	}
	USceneCaptureComponent2D* C = MinimapCapture->GetCaptureComponent2D();
	C->ProjectionType = ECameraProjectionMode::Orthographic;
	C->OrthoWidth = MinimapOrthoWidth;
	C->CaptureSource = ESceneCaptureSource::SCS_BaseColor;
	C->bCaptureEveryFrame = false;
	C->bCaptureOnMovement = false;
	C->bAlwaysPersistRenderingState = true;
	C->TextureTarget = MinimapRT;
	C->ShowFlags.SetSkeletalMeshes(false);
	C->ShowFlags.SetParticles(false);
	C->ShowFlags.SetFog(false);
	C->ShowFlags.SetVolumetricFog(false);
	C->ShowFlags.SetAtmosphere(false);
	C->ShowFlags.SetCloud(false);

	if (UMaterialInterface* Mat = UGIAssetSettings::Get().MinimapMaterial.LoadSynchronous())
	{
		MinimapMID = UMaterialInstanceDynamic::Create(Mat, this);
		MinimapMID->SetTextureParameterValue(TEXT("Map"), MinimapRT);
	}
}

void AGIHUD::DrawMinimap(const AGIPlayerCharacter* Player, float S)
{
	EnsureMinimap();
	if (!MinimapCapture)
	{
		return;
	}
	const float Radius = 125.f * S;
	const FVector2D Center(40.f * S + Radius, Canvas->ClipY - 40.f * S - Radius);

	const FVector PLoc = Player->IsRiding() ? Player->GetRidingBike()->GetActorLocation() : Player->GetActorLocation();
	const float CamYaw = PlayerOwner ? PlayerOwner->GetControlRotation().Yaw : 0.f;

	MinimapTimer -= GetWorld()->GetDeltaSeconds();
	if (MinimapTimer <= 0.f)
	{
		MinimapTimer = 0.1f;
		MinimapCapture->SetActorLocationAndRotation(FVector(PLoc.X, PLoc.Y, PLoc.Z + 15000.f), FRotator(-90.f, CamYaw, 0.f));
		MinimapCapture->GetCaptureComponent2D()->CaptureScene();
	}

	// Ring + map.
	Disc(Center, Radius + 5.f * S, FLinearColor(0.f, 0.f, 0.f, 0.7f), 48);
	// River blue under the map in Varanasi (the river is transparent in the capture); concrete grey elsewhere.
	const bool bRiverMap = AGIRiver::Get(this) != nullptr;
	Disc(Center, Radius, bRiverMap ? FLinearColor(0.1f, 0.24f, 0.36f, 0.95f) : FLinearColor(0.22f, 0.22f, 0.22f, 0.95f), 48);
	if (MinimapMID)
	{
		FCanvasTileItem Tile(Center - FVector2D(Radius, Radius), MinimapMID->GetRenderProxy(), FVector2D(Radius * 2.f, Radius * 2.f));
		Canvas->DrawItem(Tile);
	}
	else if (MinimapRT)
	{
		const float Half = Radius * 0.72f;
		FCanvasTileItem Tile(Center - FVector2D(Half, Half), MinimapRT->GetResource(), FVector2D(Half * 2.f, Half * 2.f), FLinearColor::White);
		Canvas->DrawItem(Tile);
	}

	const FVector Fwd = FRotator(0.f, CamYaw, 0.f).Vector();
	const FVector Right = FRotator(0.f, CamYaw + 90.f, 0.f).Vector();
	const float PxPerCm = Radius / (MinimapOrthoWidth * 0.5f);
	auto ToMap = [&](const FVector& World, bool bClamp, float Margin) -> FVector2D
	{
		const FVector D = World - PLoc;
		FVector2D M(FVector::DotProduct(D, Right) * PxPerCm, -FVector::DotProduct(D, Fwd) * PxPerCm);
		if (bClamp && M.Size() > Radius - Margin)
		{
			M = M.GetSafeNormal() * (Radius - Margin);
		}
		return Center + M;
	};

	// North marker.
	const FVector2D N = ToMap(PLoc + FVector(1e6f, 0, 0), true, 2.f);
	Disc(N, 10.f * S, FLinearColor(0.f, 0.f, 0.f, 0.8f), 16);
	Text(TEXT("N"), N.X, N.Y - 9.f * S, SmallFont, 0.95f * S, FLinearColor::White, true, false);

	// Objective.
	if (const AGIMission* Mission = AGIMission::Get(this))
	{
		FVector Target;
		if (Mission->GetTarget(Target))
		{
			const FVector2D T = ToMap(Target, true, 10.f * S);
			Disc(T, 9.f * S, FLinearColor(0.f, 0.f, 0.f, 0.8f), 16);
			Disc(T, 6.5f * S, Gold, 16);
		}
	}

	// Player arrow.
	const float Yaw = FMath::DegreesToRadians((Player->IsRiding() ? Player->GetRidingBike()->GetActorRotation().Yaw : Player->GetActorRotation().Yaw) - CamYaw);
	auto Rot = [&](float X, float Y) { return Center + FVector2D(X * FMath::Cos(Yaw) - Y * FMath::Sin(Yaw), X * FMath::Sin(Yaw) + Y * FMath::Cos(Yaw)) * S; };
	Triangle(Rot(0.f, -12.f), Rot(8.f, 9.f), Rot(-8.f, 9.f), FLinearColor(0.f, 0.f, 0.f, 0.6f));
	Triangle(Rot(0.f, -10.f), Rot(6.5f, 7.f), Rot(0.f, 3.f), FLinearColor::White);
	Triangle(Rot(0.f, -10.f), Rot(0.f, 3.f), Rot(-6.5f, 7.f), FLinearColor(0.85f, 0.85f, 0.85f));
}

void AGIHUD::DrawWorldMarker(float S)
{
	const AGIMission* Mission = AGIMission::Get(this);
	FVector Target;
	if (!Mission || !PlayerOwner || !Mission->GetTarget(Target))
	{
		return;
	}
	FVector2D Screen;
	const FVector Pin = Target + FVector(0, 0, 250.f);
	const bool bOnScreen = PlayerOwner->ProjectWorldLocationToScreen(Pin, Screen, false);
	const float Margin = 50.f * S;
	if (!bOnScreen)
	{
		return;
	}
	Screen.X = FMath::Clamp(Screen.X, Margin, Canvas->ClipX - Margin);
	Screen.Y = FMath::Clamp(Screen.Y, Margin, Canvas->ClipY - Margin);

	const float Bob = 4.f * FMath::Sin(GetWorld()->GetTimeSeconds() * 3.f) * S;
	const FVector2D P(Screen.X, Screen.Y + Bob);
	Disc(P, 15.f * S, FLinearColor(0.f, 0.f, 0.f, 0.6f), 24);
	Disc(P, 12.f * S, Gold, 24);
	Disc(P, 5.f * S, FLinearColor(0.35f, 0.2f, 0.f), 16);
	Triangle(P + FVector2D(-10.f, 6.f) * S, P + FVector2D(10.f, 6.f) * S, P + FVector2D(0.f, 24.f) * S, Gold);

	const APawn* Pawn = PlayerOwner->GetPawn();
	if (Pawn)
	{
		const int32 Meters = FMath::RoundToInt(FVector::Dist(Pawn->GetActorLocation(), Target) / 100.f);
		Text(FString::Printf(TEXT("%d m"), Meters), P.X, P.Y + 26.f * S, SmallFont, 1.1f * S, FLinearColor::White, true);
	}
}

void AGIHUD::DrawPrompt(const AGIPlayerCharacter* Player, float S)
{
	const FText Prompt = Player->GetPrompt();
	if (Prompt.IsEmpty())
	{
		return;
	}
	const FString Str = Prompt.ToString();
	const FVector2D TS = TextSize(Str, MedFont, 1.0f * S);
	const float X = Canvas->ClipX * 0.5f;
	const float Y = Canvas->ClipY * 0.78f;
	Rect(X - TS.X * 0.5f - 16.f * S, Y - 6.f * S, TS.X + 32.f * S, TS.Y + 12.f * S, PanelBg);
	Text(Str, X, Y, MedFont, 1.0f * S, FLinearColor::White, true);
}

void AGIHUD::DrawBanner(float S)
{
	const AGIMission* Mission = AGIMission::Get(this);
	if (!Mission)
	{
		return;
	}
	float Alpha = 0.f;
	const FText Banner = Mission->GetBanner(Alpha);
	if (Banner.IsEmpty() || Alpha <= 0.f)
	{
		return;
	}
	const FString Str = Banner.ToString();
	const float Scale = 1.6f * S;
	const FVector2D TS = TextSize(Str, BigFont, Scale);
	const float Y = Canvas->ClipY * 0.28f;
	Rect(0.f, Y - 14.f * S, Canvas->ClipX, TS.Y + 28.f * S, FLinearColor(0.f, 0.f, 0.f, 0.45f * Alpha));
	FLinearColor C = Gold;
	C.A = Alpha;
	Text(Str, Canvas->ClipX * 0.5f, Y, BigFont, Scale, C, true);
}

void AGIHUD::DrawDeath(float S)
{
	Rect(0.f, 0.f, Canvas->ClipX, Canvas->ClipY, FLinearColor(0.35f, 0.f, 0.f, 0.35f));
	const FString Str = TEXT("KHATAM");
	Text(Str, Canvas->ClipX * 0.5f, Canvas->ClipY * 0.42f, BigFont, 3.2f * S, FLinearColor(0.85f, 0.1f, 0.08f), true);
	Text(TEXT("Ganga maiya ne bacha liya... hospital le ja rahe hain"), Canvas->ClipX * 0.5f, Canvas->ClipY * 0.42f + 90.f * S, MedFont, 1.0f * S, FLinearColor::White, true);
}

void AGIHUD::DrawFPS(float S)
{
	const FString Str = FString::Printf(TEXT("%d FPS"), FMath::RoundToInt(SmoothedFPS));
	Text(Str, Canvas->ClipX * 0.5f, 8.f * S, SmallFont, 1.0f * S, FLinearColor(0.7f, 1.f, 0.7f), true);
}
