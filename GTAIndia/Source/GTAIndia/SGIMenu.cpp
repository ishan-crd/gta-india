#include "SGIMenu.h"
#include "GIAssetSettings.h"
#include "GIGameUserSettings.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "GTAIndiaMenu"

namespace GIMenuStyle
{
	const FLinearColor ColSaffron(1.f, 0.45f, 0.05f, 1.f);
	const FLinearColor ColGold(1.f, 0.78f, 0.12f, 1.f);
	const FLinearColor ColGreen(0.07f, 0.53f, 0.03f, 1.f);
	const FLinearColor ColPanel(0.f, 0.f, 0.f, 0.72f);
	const FLinearColor ColButtonIdle(0.f, 0.f, 0.f, 0.35f);

	FSlateFontInfo Font(int32 Size, const FName Weight = TEXT("Bold"))
	{
		return FCoreStyle::GetDefaultFontStyle(Weight, Size);
	}

	const FButtonStyle& ButtonStyle()
	{
		static FButtonStyle Style = []
		{
			FButtonStyle S;
			const FSlateColorBrush White(FLinearColor::White);
			S.SetNormal(White);
			S.SetHovered(White);
			S.SetPressed(White);
			S.SetDisabled(White);
			S.SetNormalPadding(FMargin(0));
			S.SetPressedPadding(FMargin(0));
			return S;
		}();
		return Style;
	}

	const FSlateBrush* WhiteBrush()
	{
		static FSlateColorBrush Brush(FLinearColor::White);
		return &Brush;
	}
}

using namespace GIMenuStyle;

static const TCHAR* QualityNames[] = { TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Ultra") };

static FText QualityText(int32 Q)
{
	return FText::FromString(QualityNames[FMath::Clamp(Q, 0, 3)]);
}

void SGIMenu::Construct(const FArguments& InArgs)
{
	Owner = InArgs._Owner;
	UKismetSystemLibrary::GetSupportedFullscreenResolutions(Resolutions);
	if (Resolutions.Num() == 0)
	{
		Resolutions = { FIntPoint(1280, 720), FIntPoint(1600, 900), FIntPoint(1920, 1080), FIntPoint(2560, 1440), FIntPoint(3840, 2160) };
	}

	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()
		[
			SAssignNew(Content, SBox)
		]
	];
}

void SGIMenu::Changed(bool bCrowd)
{
	if (UGIGameUserSettings* S = UGIGameUserSettings::Get())
	{
		S->ApplySettings(false);
	}
	if (Owner.IsValid())
	{
		Owner->OnSettingsChanged(bCrowd);
	}
}

void SGIMenu::FocusFirst()
{
	if (FirstFocus.IsValid())
	{
		FSlateApplication::Get().SetAllUserFocus(FirstFocus, EFocusCause::SetDirectly);
	}
	else
	{
		FSlateApplication::Get().SetAllUserFocus(SharedThis(this), EFocusCause::SetDirectly);
	}
}

void SGIMenu::ShowPage(EGIMenuPage InPage)
{
	Page = InPage;
	FirstFocus.Reset();
	TSharedRef<SWidget> W = SNullWidget::NullWidget;
	switch (Page)
	{
	case EGIMenuPage::Title: W = BuildTitle(); break;
	case EGIMenuPage::Pause: W = BuildPause(); break;
	case EGIMenuPage::Settings: W = BuildSettings(); break;
	case EGIMenuPage::Controls: W = BuildControls(); break;
	case EGIMenuPage::Credits: W = BuildCredits(); break;
	default: break;
	}
	Content->SetContent(W);
	FocusFirst();
}

FReply SGIMenu::OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Gamepad_Special_Right)
	{
		if (!Owner.IsValid())
		{
			return FReply::Handled();
		}
		switch (Page)
		{
		case EGIMenuPage::Pause: Owner->ResumeGame(); break;
		case EGIMenuPage::Settings: Owner->CloseSettings(); break;
		case EGIMenuPage::Controls:
		case EGIMenuPage::Credits: Owner->OpenPage(EGIMenuPage::None); break;
		default: break;
		}
		return FReply::Handled();
	}
	return SCompoundWidget::OnKeyDown(MyGeometry, InKeyEvent);
}

// ---------------------------------------------------------------------------------------------
// Building blocks

TSharedRef<SButton> SGIMenu::MakeButton(const FText& Label, TFunction<void()> OnClick, int32 FontSize, bool bRegisterFirst)
{
	TSharedRef<SButton> Btn = SNew(SButton)
		.ButtonStyle(&ButtonStyle())
		.ContentPadding(FMargin(20.f, 9.f))
		.IsFocusable(true)
		.OnClicked_Lambda([OnClick]() { OnClick(); return FReply::Handled(); });

	TWeakPtr<SButton> Weak = Btn;
	Btn->SetBorderBackgroundColor(TAttribute<FSlateColor>::CreateLambda([Weak]()
	{
		const TSharedPtr<SButton> B = Weak.Pin();
		const bool bActive = B.IsValid() && (B->IsHovered() || B->HasKeyboardFocus());
		return FSlateColor(bActive ? ColGold : ColButtonIdle);
	}));
	Btn->SetContent(
		SNew(STextBlock)
		.Text(Label)
		.Font(Font(FontSize))
		.ColorAndOpacity(TAttribute<FSlateColor>::CreateLambda([Weak]()
		{
			const TSharedPtr<SButton> B = Weak.Pin();
			const bool bActive = B.IsValid() && (B->IsHovered() || B->HasKeyboardFocus());
			return FSlateColor(bActive ? FLinearColor::Black : FLinearColor::White);
		})));
	if (bRegisterFirst && !FirstFocus.IsValid())
	{
		FirstFocus = Btn;
	}
	return Btn;
}

TSharedRef<SWidget> SGIMenu::MakeCycler(const FText& Label, TFunction<FText()> GetValue, TFunction<void(int32)> OnStep, int32 Impact)
{
	static const FLinearColor ImpactColors[] = { FLinearColor::Transparent, FLinearColor(0.35f, 0.85f, 0.4f), FLinearColor(1.f, 0.7f, 0.15f), FLinearColor(1.f, 0.32f, 0.25f) };
	static const TCHAR* ImpactNames[] = { TEXT(""), TEXT("FPS: low"), TEXT("FPS: medium"), TEXT("FPS: high") };
	const int32 I = FMath::Clamp(Impact, 0, 3);
	return SNew(SBox).Padding(FMargin(0.f, 3.f))
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
		[
			SNew(STextBlock).Text(Label).Font(Font(18, TEXT("Regular"))).ColorAndOpacity(FLinearColor(0.92f, 0.92f, 0.92f))
		]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 14.f, 0.f)
		[
			SNew(STextBlock).Text(FText::FromString(ImpactNames[I])).Font(Font(12)).ColorAndOpacity(ImpactColors[I])
		]
		+ SHorizontalBox::Slot().AutoWidth()
		[
			MakeButton(FText::FromString(TEXT("<")), [OnStep]() { OnStep(-1); }, 18)
		]
		+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(230.f).HAlign(HAlign_Center)
			[
				SNew(STextBlock).Text_Lambda([GetValue]() { return GetValue(); }).Font(Font(18)).ColorAndOpacity(ColGold)
			]
		]
		+ SHorizontalBox::Slot().AutoWidth()
		[
			MakeButton(FText::FromString(TEXT(">")), [OnStep]() { OnStep(1); }, 18, false)
		]
	];
}

TSharedRef<SWidget> SGIMenu::MakeSectionHeader(const FText& Label)
{
	return SNew(SBox).Padding(FMargin(0.f, 16.f, 0.f, 6.f))
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(STextBlock).Text(Label).Font(Font(20)).ColorAndOpacity(ColSaffron)
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)
		[
			SNew(SBox).HeightOverride(2.f)
			[
				SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.15f))
			]
		]
	];
}

TSharedRef<SWidget> SGIMenu::MakePanel(const FText& Heading, TSharedRef<SWidget> Body, float Width)
{
	return SNew(SBox).HAlign(HAlign_Center).VAlign(VAlign_Center)
	[
		SNew(SBox).WidthOverride(Width)
		[
			SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(ColPanel).Padding(FMargin(36.f, 28.f))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Text(Heading).Font(Font(40)).ColorAndOpacity(FLinearColor::White)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 14.f)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(60.f).HeightOverride(5.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(ColSaffron)]]
					+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(60.f).HeightOverride(5.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(FLinearColor::White)]]
					+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(60.f).HeightOverride(5.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(ColGreen)]]
				]
				+ SVerticalBox::Slot().FillHeight(1.f)
				[
					Body
				]
			]
		]
	];
}

// ---------------------------------------------------------------------------------------------
// Pages

TSharedRef<SWidget> SGIMenu::BuildTitle()
{
	TWeakObjectPtr<AGIPlayerController> O = Owner;
	TSharedRef<SVerticalBox> Buttons = SNew(SVerticalBox);
	auto Add = [&](const FText& L, TFunction<void()> F)
	{
		Buttons->AddSlot().AutoHeight().Padding(0.f, 5.f).HAlign(HAlign_Left)
		[
			SNew(SBox).MinDesiredWidth(320.f)[MakeButton(L, F, 26)]
		];
	};
	Add(LOCTEXT("PlayVaranasi", "VARANASI  -  Ganga Paar Delivery"), [O]() { if (O.IsValid()) O->StartCity(TEXT("Varanasi")); });
	Add(LOCTEXT("PlayMumbai", "MUMBAI  -  Dharavi ki Galiyan"), [O]() { if (O.IsValid()) O->StartCity(TEXT("Dharavi")); });
	Add(LOCTEXT("Settings", "SETTINGS"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::Settings); });
	Add(LOCTEXT("Controls", "CONTROLS"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::Controls); });
	Add(LOCTEXT("Credits", "CREDITS"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::Credits); });
	Add(LOCTEXT("Quit", "QUIT"), [O]() { if (O.IsValid()) O->QuitGame(); });

	return SNew(SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Left)
		[
			SNew(SBox).WidthOverride(640.f)
			[
				SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(0.f, 0.f, 0.f, 0.55f)).Padding(FMargin(70.f, 80.f, 40.f, 60.f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(STextBlock).Text(LOCTEXT("LogoGTA", "GTA")).Font(Font(120)).ColorAndOpacity(FLinearColor::White)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, -30.f, 0.f, 0.f)
					[
						SNew(STextBlock).Text(LOCTEXT("LogoIndia", "INDIA")).Font(Font(120)).ColorAndOpacity(ColSaffron)
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(110.f).HeightOverride(7.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(ColSaffron)]]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(110.f).HeightOverride(7.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(FLinearColor::White)]]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(110.f).HeightOverride(7.f)[SNew(SImage).Image(WhiteBrush()).ColorAndOpacity(ColGreen)]]
					]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 50.f)
					[
						SNew(STextBlock).Text(LOCTEXT("LogoCity", "V A R A N A S I")).Font(Font(28, TEXT("Regular"))).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.85f))
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						Buttons
					]
					+ SVerticalBox::Slot().FillHeight(1.f)
					[
						SNew(SSpacer)
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(STextBlock).Text(LOCTEXT("Hint", "Keyboard + mouse ya controller  •  v0.1")).Font(Font(14, TEXT("Regular"))).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.55f))
					]
				]
			]
		];
}

TSharedRef<SWidget> SGIMenu::BuildPause()
{
	TWeakObjectPtr<AGIPlayerController> O = Owner;
	TSharedRef<SVerticalBox> Body = SNew(SVerticalBox);
	auto Add = [&](const FText& L, TFunction<void()> F)
	{
		Body->AddSlot().AutoHeight().Padding(0.f, 5.f)[MakeButton(L, F, 24)];
	};
	Add(LOCTEXT("Resume", "Wapas Khelo (Resume)"), [O]() { if (O.IsValid()) O->ResumeGame(); });
	Add(LOCTEXT("PSettings", "Settings"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::Settings); });
	Add(LOCTEXT("PControls", "Controls"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::Controls); });
	if (O.IsValid() && O->IsMumbai())
	{
		Add(LOCTEXT("PWeather", "Mausam badlo  (Dhoop / Baarish)"), [O]() { if (O.IsValid()) O->ToggleWeather(); });
		Add(LOCTEXT("PToVaranasi", "Shehar badlo: Varanasi"), [O]() { if (O.IsValid()) O->StartCity(TEXT("Varanasi")); });
	}
	else
	{
		Add(LOCTEXT("PToMumbai", "Shehar badlo: Mumbai (Dharavi)"), [O]() { if (O.IsValid()) O->StartCity(TEXT("Dharavi")); });
	}
	Add(LOCTEXT("PTitle", "Main Menu"), [O]() { if (O.IsValid()) O->QuitToTitle(); });
	Add(LOCTEXT("PQuit", "Quit Game"), [O]() { if (O.IsValid()) O->QuitGame(); });
	return MakePanel(LOCTEXT("Paused", "RUKO! (Paused)"), Body, 520.f);
}

TSharedRef<SWidget> SGIMenu::BuildSettings()
{
	TWeakObjectPtr<AGIPlayerController> O = Owner;
	TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
	auto Row = [&](TSharedRef<SWidget> W) { List->AddSlot().AutoHeight()[W]; };
	auto GS = []() { return UGIGameUserSettings::Get(); };

	// Tips
	Row(SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(1.f, 0.6f, 0.1f, 0.12f)).Padding(FMargin(12.f, 8.f))
	[
		SNew(STextBlock).AutoWrapText(true).Font(Font(14, TEXT("Regular"))).ColorAndOpacity(FLinearColor(1.f, 0.93f, 0.8f))
		.Text(LOCTEXT("PerfTips", "FPS kam hai? Sabse bada fark yeh dete hain:\n"
			"1) Resolution Scale 70-80% + TSR (almost same sharpness, +30-50% FPS)\n"
			"2) Global Illumination (Lumen) Medium/Low   3) Shadows Medium + Shadow Distance 75%\n"
			"4) Crowd Density / Crowd Shadows kam karo (busy ghats pe bahut asar)\n"
			"5) Draw Distance 80% aur Volumetric Fog Off.  Frame Limit 60 se GPU thanda rehta hai."))
	]);

	// Presets
	Row(MakeSectionHeader(LOCTEXT("SecPreset", "Graphics Preset")));
	{
		TSharedRef<SHorizontalBox> Presets = SNew(SHorizontalBox);
		for (int32 Q = 0; Q < 4; ++Q)
		{
			Presets->AddSlot().AutoWidth().Padding(0.f, 0.f, 8.f, 0.f)
			[
				MakeButton(QualityText(Q), [this, Q, GS]()
				{
					if (UGIGameUserSettings* S = GS())
					{
						S->ApplyGamePreset(Q);
						Changed(true);
					}
				}, 18)
			];
		}
		Presets->AddSlot().AutoWidth()
		[
			MakeButton(LOCTEXT("AutoDetect", "Auto-detect"), [this, GS]()
			{
				if (UGIGameUserSettings* S = GS())
				{
					S->RunHardwareBenchmark();
					S->ApplyHardwareBenchmarkResults();
					S->ApplyGamePreset(FMath::Clamp(S->GetOverallScalabilityLevel(), 0, 3));
					Changed(true);
				}
			}, 18, false)
		];
		Row(Presets);
	}

	// Display
	Row(MakeSectionHeader(LOCTEXT("SecDisplay", "Display")));
	Row(MakeCycler(LOCTEXT("WindowMode", "Window Mode"),
		[GS]()
		{
			const UGIGameUserSettings* S = GS();
			switch (S ? S->GetFullscreenMode() : EWindowMode::Windowed)
			{
			case EWindowMode::Fullscreen: return LOCTEXT("WMFull", "Fullscreen");
			case EWindowMode::WindowedFullscreen: return LOCTEXT("WMBorderless", "Borderless");
			default: return LOCTEXT("WMWindowed", "Windowed");
			}
		},
		[this, GS](int32 Dir)
		{
			if (UGIGameUserSettings* S = GS())
			{
				const int32 M = ((int32)S->GetFullscreenMode() + Dir + 3) % 3;
				S->SetFullscreenMode((EWindowMode::Type)M);
				Changed();
			}
		}));
	Row(MakeCycler(LOCTEXT("Resolution", "Resolution"),
		[GS]()
		{
			const UGIGameUserSettings* S = GS();
			const FIntPoint R = S ? S->GetScreenResolution() : FIntPoint(1920, 1080);
			return FText::FromString(FString::Printf(TEXT("%d x %d"), R.X, R.Y));
		},
		[this, GS](int32 Dir)
		{
			if (UGIGameUserSettings* S = GS())
			{
				const FIntPoint Cur = S->GetScreenResolution();
				int32 Idx = Resolutions.IndexOfByKey(Cur);
				Idx = Idx == INDEX_NONE ? Resolutions.Num() - 1 : (Idx + Dir + Resolutions.Num()) % Resolutions.Num();
				S->SetScreenResolution(Resolutions[Idx]);
				Changed();
			}
		}, 3));
	Row(MakeCycler(LOCTEXT("VSync", "VSync"),
		[GS]() { const UGIGameUserSettings* S = GS(); return (S && S->IsVSyncEnabled()) ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->SetVSyncEnabled(!S->IsVSyncEnabled()); Changed(); } }));
	Row(MakeCycler(LOCTEXT("FrameLimit", "Frame Limit"),
		[GS]()
		{
			const float L = GS() ? GS()->GetFrameRateLimit() : 0.f;
			return L <= 0.f ? LOCTEXT("Unlimited", "Unlimited") : FText::AsNumber(FMath::RoundToInt(L));
		},
		[this, GS](int32 Dir)
		{
			static const float Limits[] = { 30.f, 60.f, 90.f, 120.f, 144.f, 0.f };
			if (UGIGameUserSettings* S = GS())
			{
				int32 Idx = 5;
				for (int32 i = 0; i < 6; ++i)
				{
					if (FMath::IsNearlyEqual(Limits[i], S->GetFrameRateLimit())) { Idx = i; }
				}
				S->SetFrameRateLimit(Limits[(Idx + Dir + 6) % 6]);
				Changed();
			}
		}));
	Row(MakeCycler(LOCTEXT("ResScale", "Resolution Scale"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt(GS() ? GS()->ScreenPercentage : 100.f))); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->ScreenPercentage = FMath::Clamp(S->ScreenPercentage + Dir * 5.f, 50.f, 100.f); Changed(); } }, 3));
	Row(MakeCycler(LOCTEXT("AA", "Anti-Aliasing / Upscaler"),
		[GS]()
		{
			switch ((EGIAntiAliasing)(GS() ? GS()->AntiAliasing : 4))
			{
			case EGIAntiAliasing::Off: return LOCTEXT("AAOff", "Off");
			case EGIAntiAliasing::FXAA: return LOCTEXT("AAFXAA", "FXAA");
			case EGIAntiAliasing::TAA: return LOCTEXT("AATAA", "TAA");
			default: return LOCTEXT("AATSR", "TSR");
			}
		},
		[this, GS](int32 Dir)
		{
			static const uint8 Modes[] = { 0, 1, 2, 4 };
			if (UGIGameUserSettings* S = GS())
			{
				int32 Idx = 3;
				for (int32 i = 0; i < 4; ++i) { if (Modes[i] == S->AntiAliasing) { Idx = i; } }
				S->AntiAliasing = Modes[(Idx + Dir + 4) % 4];
				Changed();
			}
		}, 2));

	// Quality groups
	Row(MakeSectionHeader(LOCTEXT("SecQuality", "Quality")));
	struct FGroup { FText Name; TFunction<int32(UGIGameUserSettings*)> Get; TFunction<void(UGIGameUserSettings*, int32)> Set; int32 Impact = 2; };
	const TArray<FGroup> Groups = {
		{ LOCTEXT("ViewDist", "View Distance"), [](UGIGameUserSettings* S) { return S->GetViewDistanceQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetViewDistanceQuality(V); }, 2 },
		{ LOCTEXT("Shadows", "Shadows"), [](UGIGameUserSettings* S) { return S->GetShadowQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetShadowQuality(V); }, 3 },
		{ LOCTEXT("GI", "Global Illumination (Lumen)"), [](UGIGameUserSettings* S) { return S->GetGlobalIlluminationQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetGlobalIlluminationQuality(V); }, 3 },
		{ LOCTEXT("Reflections", "Reflections"), [](UGIGameUserSettings* S) { return S->GetReflectionQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetReflectionQuality(V); }, 2 },
		{ LOCTEXT("Textures", "Textures"), [](UGIGameUserSettings* S) { return S->GetTextureQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetTextureQuality(V); }, 1 },
		{ LOCTEXT("Effects", "Effects"), [](UGIGameUserSettings* S) { return S->GetVisualEffectQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetVisualEffectQuality(V); }, 1 },
		{ LOCTEXT("Foliage", "Foliage"), [](UGIGameUserSettings* S) { return S->GetFoliageQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetFoliageQuality(V); }, 1 },
		{ LOCTEXT("PostFX", "Post Processing"), [](UGIGameUserSettings* S) { return S->GetPostProcessingQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetPostProcessingQuality(V); }, 1 },
		{ LOCTEXT("Shading", "Shading"), [](UGIGameUserSettings* S) { return S->GetShadingQuality(); }, [](UGIGameUserSettings* S, int32 V) { S->SetShadingQuality(V); }, 1 },
	};
	for (const FGroup& G : Groups)
	{
		Row(MakeCycler(G.Name,
			[G, GS]() { return QualityText(GS() ? G.Get(GS()) : 2); },
			[this, G, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { G.Set(S, (G.Get(S) + Dir + 4) % 4); Changed(); } }, G.Impact));
	}
	Row(MakeCycler(LOCTEXT("Crowd", "Crowd Density"),
		[GS]() { return QualityText(GS() ? GS()->CrowdDensity : 2); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->CrowdDensity = (S->CrowdDensity + Dir + 4) % 4; Changed(true); } }, 3));
	Row(MakeCycler(LOCTEXT("DrawDist", "Draw Distance"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt((GS() ? GS()->DrawDistance : 1.f) * 100.f))); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->DrawDistance = FMath::Clamp(S->DrawDistance + Dir * 0.1f, 0.4f, 2.f); Changed(); } }, 2));
	Row(MakeCycler(LOCTEXT("ShadowDist", "Shadow Distance"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt((GS() ? GS()->ShadowDistance : 1.f) * 100.f))); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->ShadowDistance = FMath::Clamp(S->ShadowDistance + Dir * 0.1f, 0.3f, 2.f); Changed(); } }, 2));
	Row(MakeCycler(LOCTEXT("CrowdDist", "Crowd Draw Distance"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%d m"), FMath::RoundToInt(GS() ? GS()->CrowdDrawDistance : 160.f))); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->CrowdDrawDistance = FMath::Clamp(S->CrowdDrawDistance + Dir * 20.f, 40.f, 300.f); Changed(); } }, 2));
	Row(MakeCycler(LOCTEXT("CrowdShadows", "Crowd Shadows"),
		[GS]() { const int32 V = GS() ? GS()->CrowdShadows : 2; return V == 0 ? LOCTEXT("Off", "Off") : (V == 1 ? LOCTEXT("Near", "Near (25 m)") : LOCTEXT("Far", "Far (60 m)")); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->CrowdShadows = (S->CrowdShadows + Dir + 3) % 3; Changed(); } }, 3));
	Row(MakeCycler(LOCTEXT("Sharpen", "Sharpening"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%d%%"), FMath::RoundToInt((GS() ? GS()->Sharpen : 0.4f) * 100.f))); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->Sharpen = FMath::Clamp(S->Sharpen + Dir * 0.1f, 0.f, 1.5f); Changed(); } }, 1));
	Row(MakeCycler(LOCTEXT("VolFog", "Volumetric Fog"),
		[GS]() { return GS() && GS()->bVolumetricFog ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->bVolumetricFog = !S->bVolumetricFog; Changed(); } }, 2));
	Row(MakeCycler(LOCTEXT("MotionBlur", "Motion Blur"),
		[GS]() { return GS() && GS()->bMotionBlur ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->bMotionBlur = !S->bMotionBlur; Changed(); } }, 1));
	Row(MakeCycler(LOCTEXT("FilmGrain", "Film Grain"),
		[GS]() { return GS() && GS()->bFilmGrain ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->bFilmGrain = !S->bFilmGrain; Changed(); } }, 1));

	// Gameplay
	Row(MakeSectionHeader(LOCTEXT("SecGame", "Camera & Controls")));
	Row(MakeCycler(LOCTEXT("FOV", "Field of View"),
		[GS]() { return FText::AsNumber(FMath::RoundToInt(GS() ? GS()->FieldOfView : 75.f)); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->FieldOfView = FMath::Clamp(S->FieldOfView + Dir * 5.f, 60.f, 115.f); Changed(); } }));
	Row(MakeCycler(LOCTEXT("Sens", "Look Sensitivity"),
		[GS]() { return FText::FromString(FString::Printf(TEXT("%.2f"), GS() ? GS()->MouseSensitivity : 1.f)); },
		[this, GS](int32 Dir) { if (UGIGameUserSettings* S = GS()) { S->MouseSensitivity = FMath::Clamp(S->MouseSensitivity + Dir * (S->MouseSensitivity < 0.5f || (Dir < 0 && S->MouseSensitivity <= 0.5f) ? 0.05f : 0.1f), 0.05f, 3.f); Changed(); } }));
	Row(MakeCycler(LOCTEXT("InvertY", "Invert Look Y"),
		[GS]() { return GS() && GS()->bInvertY ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->bInvertY = !S->bInvertY; Changed(); } }));
	Row(MakeCycler(LOCTEXT("FPS", "Show FPS"),
		[GS]() { return GS() && GS()->bShowFPS ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); },
		[this, GS](int32) { if (UGIGameUserSettings* S = GS()) { S->bShowFPS = !S->bShowFPS; Changed(); } }));

	TSharedRef<SHorizontalBox> Footer = SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth().Padding(0.f, 0.f, 10.f, 0.f)
		[
			MakeButton(LOCTEXT("Back", "Save & Back"), [O]() { if (O.IsValid()) O->CloseSettings(); }, 20, false)
		]
		+ SHorizontalBox::Slot().AutoWidth()
		[
			MakeButton(LOCTEXT("Defaults", "Reset Defaults"), [this, GS]() { if (UGIGameUserSettings* S = GS()) { S->SetToDefaults(); Changed(true); } }, 20, false)
		];

	return MakePanel(LOCTEXT("SettingsTitle", "SETTINGS"),
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().FillHeight(1.f)
		[
			SNew(SBox).MaxDesiredHeight(640.f)
			[
				SNew(SScrollBox).ScrollWhenFocusChanges(EScrollWhenFocusChanges::AnimatedScroll)
				+ SScrollBox::Slot()[List]
			]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 16.f, 0.f, 0.f)
		[
			Footer
		], 860.f);
}

TSharedRef<SWidget> SGIMenu::BuildControls()
{
	TWeakObjectPtr<AGIPlayerController> O = Owner;
	struct FLine { const TCHAR* Action; const TCHAR* Keys; const TCHAR* Pad; };
	const FLine Lines[] = {
		{ TEXT("Chalo (Move)"), TEXT("W A S D"), TEXT("Left stick") },
		{ TEXT("Dekho (Look)"), TEXT("Mouse"), TEXT("Right stick") },
		{ TEXT("Daudo (Sprint / swim fast)"), TEXT("Shift"), TEXT("L3 / RT") },
		{ TEXT("Aaram se chalo (Walk)"), TEXT("Hold Alt"), TEXT("Tilt stick lightly") },
		{ TEXT("Kudo (Jump)"), TEXT("Space"), TEXT("A") },
		{ TEXT("Dubki (Dive while swimming)"), TEXT("C / Ctrl"), TEXT("B") },
		{ TEXT("Interact (train pe chadho)"), TEXT("E"), TEXT("X") },
		{ TEXT("Bike pe baitho / utro"), TEXT("F"), TEXT("Y") },
		{ TEXT("Bike: race / brake"), TEXT("W / S"), TEXT("RT / LT") },
		{ TEXT("Bike: steer"), TEXT("A / D"), TEXT("Left stick") },
		{ TEXT("Bike: handbrake"), TEXT("Space"), TEXT("A") },
		{ TEXT("Horn"), TEXT("H"), TEXT("LB") },
		{ TEXT("Pause"), TEXT("Esc / P"), TEXT("Start") },
	};
	TSharedRef<SVerticalBox> Body = SNew(SVerticalBox);
	Body->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
	[
		SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().FillWidth(1.f)[SNew(STextBlock).Text(LOCTEXT("CAction", "Action")).Font(Font(16)).ColorAndOpacity(ColSaffron)]
		+ SHorizontalBox::Slot().FillWidth(0.5f)[SNew(STextBlock).Text(LOCTEXT("CKeys", "Keyboard")).Font(Font(16)).ColorAndOpacity(ColSaffron)]
		+ SHorizontalBox::Slot().FillWidth(0.5f)[SNew(STextBlock).Text(LOCTEXT("CPad", "Controller")).Font(Font(16)).ColorAndOpacity(ColSaffron)]
	];
	for (const FLine& L : Lines)
	{
		Body->AddSlot().AutoHeight().Padding(0.f, 4.f)
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(1.f)[SNew(STextBlock).Text(FText::FromString(L.Action)).Font(Font(18, TEXT("Regular"))).ColorAndOpacity(FLinearColor::White)]
			+ SHorizontalBox::Slot().FillWidth(0.5f)[SNew(STextBlock).Text(FText::FromString(L.Keys)).Font(Font(18)).ColorAndOpacity(ColGold)]
			+ SHorizontalBox::Slot().FillWidth(0.5f)[SNew(STextBlock).Text(FText::FromString(L.Pad)).Font(Font(18)).ColorAndOpacity(ColGold)]
		];
	}
	Body->AddSlot().AutoHeight().Padding(0.f, 18.f, 0.f, 0.f)
	[
		SNew(STextBlock).AutoWrapText(true).Font(Font(15, TEXT("Regular"))).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.7f))
		.Text(LOCTEXT("Tip", "Tip: Ganga mein tairte waqt HP ghatta hai. Jaldi paar karo! Bike se ghat tak jao, ya chalti train pe chadh jao."))
	];
	Body->AddSlot().AutoHeight().Padding(0.f, 16.f, 0.f, 0.f).HAlign(HAlign_Left)
	[
		MakeButton(LOCTEXT("CBack", "Back"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::None); }, 20)
	];
	return MakePanel(LOCTEXT("ControlsTitle", "CONTROLS"), Body, 820.f);
}

TSharedRef<SWidget> SGIMenu::BuildCredits()
{
	TWeakObjectPtr<AGIPlayerController> O = Owner;
	TSharedRef<SVerticalBox> List = SNew(SVerticalBox);
	List->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
	[
		SNew(STextBlock).AutoWrapText(true).Font(Font(16, TEXT("Regular"))).ColorAndOpacity(FLinearColor::White)
		.Text(LOCTEXT("CreditsIntro", "GTA India - a fan-made Varanasi prototype built with Unreal Engine 5. Textures and HDRIs from Poly Haven (CC0). 3D models from Sketchfab creators:"))
	];
	for (const FString& Line : UGIAssetSettings::Get().Credits)
	{
		List->AddSlot().AutoHeight().Padding(0.f, 2.f)
		[
			SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(Line)).Font(Font(13, TEXT("Regular"))).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.8f))
		];
	}
	return MakePanel(LOCTEXT("CreditsTitle", "CREDITS"),
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().FillHeight(1.f)
		[
			SNew(SBox).MaxDesiredHeight(560.f)[SNew(SScrollBox) + SScrollBox::Slot()[List]]
		]
		+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 14.f, 0.f, 0.f).HAlign(HAlign_Left)
		[
			MakeButton(LOCTEXT("CrBack", "Back"), [O]() { if (O.IsValid()) O->OpenPage(EGIMenuPage::None); }, 20)
		], 900.f);
}

#undef LOCTEXT_NAMESPACE
