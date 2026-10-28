#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "FarmPauseWidget.generated.h"

class AFarmClock;
class UButton;
class UTextBlock;

/** Centered Esc-pause overlay with a Continue button. Built in code (no WBP asset). */
UCLASS()
class FARMSIM25D_API UFarmPauseWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	void SetClock(AFarmClock* InClock);
protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeConstruct() override;
private:
	UPROPERTY(Transient) TObjectPtr<AFarmClock> Clock;
	UPROPERTY(Transient) TObjectPtr<UButton> ContinueButton;
	UFUNCTION() void OnContinueClicked();
};
