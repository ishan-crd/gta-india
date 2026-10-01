#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "GIPlayerController.h"

class SBox;
class SButton;

/** All front-end pages in one Slate widget: title, pause, settings, controls, credits. */
class SGIMenu : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SGIMenu) {}
		SLATE_ARGUMENT(TWeakObjectPtr<AGIPlayerController>, Owner)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	void ShowPage(EGIMenuPage Page);
	void FocusFirst();

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent) override;

private:
	TSharedRef<SWidget> BuildTitle();
	TSharedRef<SWidget> BuildPause();
	TSharedRef<SWidget> BuildSettings();
	TSharedRef<SWidget> BuildControls();
	TSharedRef<SWidget> BuildCredits();

	TSharedRef<SButton> MakeButton(const FText& Label, TFunction<void()> OnClick, int32 FontSize = 24, bool bRegisterFirst = true);
	/** Impact: 0 = none shown, 1 = low, 2 = medium, 3 = high FPS cost. */
	TSharedRef<SWidget> MakeCycler(const FText& Label, TFunction<FText()> GetValue, TFunction<void(int32)> OnStep, int32 Impact = 0);
	TSharedRef<SWidget> MakeSectionHeader(const FText& Label);
	TSharedRef<SWidget> MakePanel(const FText& Heading, TSharedRef<SWidget> Body, float Width = 760.f);

	void Changed(bool bCrowd = false);

	TWeakObjectPtr<AGIPlayerController> Owner;
	TSharedPtr<SBox> Content;
	TSharedPtr<SWidget> FirstFocus;
	EGIMenuPage Page = EGIMenuPage::None;
	TArray<FIntPoint> Resolutions;
};
