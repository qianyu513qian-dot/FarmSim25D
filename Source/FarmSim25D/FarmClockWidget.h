#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "FarmClockWidget.generated.h"
class AFarmClock;
class UTextBlock;
class UProgressBar;

UCLASS()
class FARMSIM25D_API UFarmClockWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetClock(AFarmClock* InClock) { Clock = InClock; }
    void Refresh();
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeConstruct() override;
private:
    UPROPERTY(Transient) TObjectPtr<AFarmClock> Clock;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DateLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLabel;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> DayProgress;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> MoneyLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SeedsLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CropsLabel;
};
