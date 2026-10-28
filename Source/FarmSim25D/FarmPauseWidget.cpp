#include "FarmPauseWidget.h"
#include "FarmClock.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/SizeBox.h"

void UFarmPauseWidget::SetClock(AFarmClock* InClock)
{
	Clock = InClock;
}

TSharedRef<SWidget> UFarmPauseWidget::RebuildWidget()
{
	if (ContinueButton && WidgetTree && WidgetTree->RootWidget) return Super::RebuildWidget();
	if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("PauseWidgetTree"));

	UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
	WidgetTree->RootWidget = Canvas;

	UBorder* Dim = WidgetTree->ConstructWidget<UBorder>();
	Dim->SetBrushColor(FLinearColor(0.02f, 0.03f, 0.04f, 0.72f));
	auto* DimSlot = Canvas->AddChildToCanvas(Dim);
	DimSlot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
	DimSlot->SetOffsets(FMargin(0.f));

	USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>();
	Box->SetWidthOverride(360.f);
	Box->SetHeightOverride(160.f);
	auto* BoxSlot = Canvas->AddChildToCanvas(Box);
	BoxSlot->SetAnchors(FAnchors(0.5f, 0.5f));
	BoxSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	BoxSlot->SetSize(FVector2D(360.f, 160.f));

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
	Panel->SetBrushColor(FLinearColor(0.05f, 0.07f, 0.05f, 0.96f));
	Panel->SetPadding(FMargin(28.f, 24.f));
	Box->SetContent(Panel);

	UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
	Panel->SetContent(Stack);

	UTextBlock* Title = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = Title->GetFont();
		Font.Size = 20;
		Title->SetFont(Font);
		Title->SetJustification(ETextJustify::Center);
		Title->SetColorAndOpacity(FSlateColor(FLinearColor(0.92f, 0.88f, 0.7f)));
		Title->SetText(FText::FromString(TEXT("PAUSED")));
	}
	Stack->AddChildToVerticalBox(Title)->SetPadding(FMargin(0.f, 0.f, 0.f, 18.f));

	ContinueButton = WidgetTree->ConstructWidget<UButton>();
	{
		FButtonStyle Style = ContinueButton->GetStyle();
		Style.Normal.TintColor = FSlateColor(FLinearColor(0.18f, 0.42f, 0.28f, 1.f));
		Style.Hovered.TintColor = FSlateColor(FLinearColor(0.24f, 0.55f, 0.34f, 1.f));
		Style.Pressed.TintColor = FSlateColor(FLinearColor(0.12f, 0.32f, 0.2f, 1.f));
		ContinueButton->SetStyle(Style);
	}

	UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = Label->GetFont();
		Font.Size = 28;
		Label->SetFont(Font);
		Label->SetJustification(ETextJustify::Center);
		Label->SetColorAndOpacity(FSlateColor(FLinearColor(1.f, 0.96f, 0.84f)));
		Label->SetText(FText::FromString(FString::Chr(0x7EE7) + FString::Chr(0x7EED)));
	}
	ContinueButton->SetContent(Label);
	if (UButtonSlot* BS = Cast<UButtonSlot>(Label->Slot))
	{
		BS->SetPadding(FMargin(40.f, 16.f));
		BS->SetHorizontalAlignment(HAlign_Center);
		BS->SetVerticalAlignment(VAlign_Center);
	}
	Stack->AddChildToVerticalBox(ContinueButton)->SetHorizontalAlignment(HAlign_Center);

	SetVisibility(ESlateVisibility::Visible);
	return Super::RebuildWidget();
}

void UFarmPauseWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (ContinueButton)
	{
		ContinueButton->OnClicked.RemoveDynamic(this, &UFarmPauseWidget::OnContinueClicked);
		ContinueButton->OnClicked.AddDynamic(this, &UFarmPauseWidget::OnContinueClicked);
	}
}

void UFarmPauseWidget::OnContinueClicked()
{
	if (IsValid(Clock))
	{
		Clock->ResumeFromPauseMenu();
	}
}