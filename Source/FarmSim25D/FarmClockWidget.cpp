#include "FarmClockWidget.h"
#include "FarmClock.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/ProgressBar.h"

TSharedRef<SWidget> UFarmClockWidget::RebuildWidget()
{
    if (DateLabel && WidgetTree && WidgetTree->RootWidget) return Super::RebuildWidget();
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this,TEXT("ClockWidgetTree"));
    UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget = Canvas;
    UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetBrushColor(FLinearColor(0.035f,0.055f,0.075f,0.94f));
    Panel->SetPadding(FMargin(20,16));
    auto* PanelSlot = Canvas->AddChildToCanvas(Panel);
    PanelSlot->SetAnchors(FAnchors(1,0));
    PanelSlot->SetAlignment(FVector2D(1,0));
    PanelSlot->SetPosition(FVector2D(-24,24));
    PanelSlot->SetSize(FVector2D(300,212));
    UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
    Panel->SetContent(Stack);
    auto Text = [&](int32 Size, FLinearColor Color)
    {
        auto* Label = WidgetTree->ConstructWidget<UTextBlock>();
        auto Font = Label->GetFont(); Font.Size = Size;
        Label->SetFont(Font); Label->SetColorAndOpacity(FSlateColor(Color));
        Stack->AddChildToVerticalBox(Label)->SetPadding(FMargin(0,0,0,6));
        return Label;
    };
    DateLabel = Text(17, FLinearColor(0.92f,0.76f,0.45f));
    TimeLabel = Text(34, FLinearColor(1,0.96f,0.84f));
    DayProgress = WidgetTree->ConstructWidget<UProgressBar>();
    DayProgress->SetFillColorAndOpacity(FLinearColor(0.94f,0.56f,0.18f));
    Stack->AddChildToVerticalBox(DayProgress)->SetPadding(FMargin(0,2,0,8));
    StatusLabel = Text(15, FLinearColor(0.7f,0.82f,0.88f));
    auto* Help = Text(12, FLinearColor(0.56f,0.64f,0.68f));
    Help->SetText(FText::FromString(TEXT("B  Sleep near home     P  Pause")));
    SetVisibility(ESlateVisibility::HitTestInvisible);
    Refresh();
    return Super::RebuildWidget();
}

void UFarmClockWidget::NativeConstruct()
{
    Super::NativeConstruct();
    Refresh();
}

void UFarmClockWidget::Refresh()
{
    if (!IsValid(Clock) || !DateLabel) return;
    DateLabel->SetText(Clock->GetDateText());
    TimeLabel->SetText(Clock->GetClockText());
    StatusLabel->SetText(Clock->GetStatusText());
    const bool Late = Clock->State.Minutes >= 1440;
    TimeLabel->SetColorAndOpacity(FSlateColor(Late ? FLinearColor(1,0.36f,0.24f) : FLinearColor(1,0.96f,0.84f)));
    DayProgress->SetPercent(FMath::Clamp(float((Clock->State.Minutes - 360) / 1200),0.f,1.f));
}
