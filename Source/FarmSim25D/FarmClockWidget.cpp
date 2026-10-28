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
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "UObject/UnrealType.h"

TSharedRef<SWidget> UFarmClockWidget::RebuildWidget()
{
    if (DateLabel && WidgetTree && WidgetTree->RootWidget) return Super::RebuildWidget();
    if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this,TEXT("ClockWidgetTree"));
    UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    WidgetTree->RootWidget = Canvas;
    UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
    Panel->SetBrushColor(FLinearColor(0.028f,0.038f,0.024f,0.94f));
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
    Help->SetText(FText::FromString(TEXT("B  Sleep near home     Esc  Pause")));

    // One stable HUD replaces the prototype's screen prints and world-space text.
    auto* Supplies = WidgetTree->ConstructWidget<UBorder>();
    Supplies->SetBrushColor(FLinearColor(0.028f,0.038f,0.024f,0.94f));
    Supplies->SetPadding(FMargin(18,12));
    auto* SuppliesSlot = Canvas->AddChildToCanvas(Supplies);
    SuppliesSlot->SetPosition(FVector2D(24,24));
    SuppliesSlot->SetSize(FVector2D(340,86));
    auto* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    Supplies->SetContent(Row);
    auto Resource = [&](const TCHAR* Title)
    {
        auto* Column = WidgetTree->ConstructWidget<UVerticalBox>();
        Row->AddChildToHorizontalBox(Column)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
        auto* Heading = WidgetTree->ConstructWidget<UTextBlock>();
        auto Font = Heading->GetFont(); Font.Size = 11; Heading->SetFont(Font);
        Heading->SetText(FText::FromString(Title));
        Heading->SetColorAndOpacity(FSlateColor(FLinearColor(0.72f,0.66f,0.43f)));
        Column->AddChildToVerticalBox(Heading)->SetPadding(FMargin(0,0,0,4));
        auto* Value = WidgetTree->ConstructWidget<UTextBlock>();
        Font.Size = 23; Value->SetFont(Font);
        Value->SetColorAndOpacity(FSlateColor(FLinearColor(1,0.94f,0.75f)));
        Column->AddChildToVerticalBox(Value);
        return Value;
    };
    MoneyLabel = Resource(TEXT("COINS"));
    SeedsLabel = Resource(TEXT("SEEDS"));
    CropsLabel = Resource(TEXT("CROPS"));
    auto* Tools = WidgetTree->ConstructWidget<UBorder>();
    Tools->SetBrushColor(FLinearColor(0.028f,0.038f,0.024f,0.9f));
    Tools->SetPadding(FMargin(16,10));
    auto* ToolsSlot = Canvas->AddChildToCanvas(Tools);
    ToolsSlot->SetAnchors(FAnchors(0,1));
    ToolsSlot->SetAlignment(FVector2D(0,1));
    ToolsSlot->SetPosition(FVector2D(24,-24));
    ToolsSlot->SetSize(FVector2D(460,42));
    auto* Legend = WidgetTree->ConstructWidget<UTextBlock>();
    auto LegendFont = Legend->GetFont(); LegendFont.Size = 13; Legend->SetFont(LegendFont);
    Legend->SetColorAndOpacity(FSlateColor(FLinearColor(0.9f,0.86f,0.68f)));
    Legend->SetText(FText::FromString(TEXT("E  Hoe     F  Plant     R  Water     H  Harvest")));
    Tools->SetContent(Legend);
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
    if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this,0))
    {
        auto UpdateResource = [&](UTextBlock* Label, const TCHAR* Property)
        {
            if (!Label) return;
            const auto* Value = FindFProperty<FIntProperty>(Pawn->GetClass(),Property);
            Label->SetText(Value ? FText::AsNumber(Value->GetPropertyValue_InContainer(Pawn)) : FText::FromString(TEXT("--")));
        };
        UpdateResource(MoneyLabel,TEXT("Money"));
        UpdateResource(SeedsLabel,TEXT("SeedCount"));
        UpdateResource(CropsLabel,TEXT("CropCount"));
    }
}
