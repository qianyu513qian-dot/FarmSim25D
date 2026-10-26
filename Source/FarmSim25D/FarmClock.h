#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FarmClock.generated.h"

class ADirectionalLight;
class ASkyLight;
class APointLight;
class AExponentialHeightFog;
class UFarmClockWidget;
class APostProcessVolume;
class UMaterialParameterCollection;

/** A farming day spans 06:00 to 26:00. Midnight does not change the farming date. */
USTRUCT(BlueprintType)
struct FARMSIM25D_API FFarmClockState
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 AbsoluteDay = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) double Minutes = 360.0;
};

USTRUCT(BlueprintType)
struct FARMSIM25D_API FFarmLightKey
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Hour = 6;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Sun = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Sky = 0.7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Moon = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Lamps = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor SunColor = FLinearColor::White;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor SkyColor = FLinearColor::White;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FFarmTimeChanged, int32, Day, int32, DisplayMinutes);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FFarmDayChanged, int32, Day);

/** Runtime clock and lighting owner. Python/MCP is only needed for editor authoring. */
UCLASS(Blueprintable)
class FARMSIM25D_API AFarmClock : public AActor
{
    GENERATED_BODY()
public:
    AFarmClock();
    virtual void Tick(float DeltaSeconds) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnConstruction(const FTransform& Transform) override;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Farm|Time") FFarmClockState State;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Time", meta=(ClampMin="0.1", ClampMax="600")) float SecondsPerTenMinutes = 7.0f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Time", meta=(ClampMin="0", ClampMax="100")) float TimeSpeed = 1.0f;
    UPROPERTY(BlueprintReadOnly, Category="Farm|Time") bool bClockPaused = false;
    UPROPERTY(BlueprintReadOnly, Category="Farm|Time") bool bEndingDay = false;
    UPROPERTY(EditAnywhere, Category="Farm|Time") bool bShowClock = true;
    UPROPERTY(EditAnywhere, Category="Farm|Time", meta=(ClampMin="100")) float SleepRadius = 550;
    UPROPERTY(EditAnywhere, Category="Farm|Time") FVector HomeLocation = FVector(1950,3400,0);
    UPROPERTY(EditAnywhere, Category="Farm|Time") FVector WakeLocation = FVector(1650,1850,100);

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<AActor> GridManager;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<ADirectionalLight> SunLight;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<ADirectionalLight> MoonLight;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<ASkyLight> SkyLight;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<AExponentialHeightFog> Fog;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TObjectPtr<APostProcessVolume> AmbientGrade;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Lighting") TObjectPtr<UMaterialParameterCollection> LightingParameters;
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category="Farm|Scene") TArray<TObjectPtr<APointLight>> NightLights;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Lighting") TArray<FFarmLightKey> LightKeys;
    UPROPERTY(EditAnywhere, Category="Farm|Lighting", meta=(ClampMin="0", ClampMax="26")) float PreviewHour = 10;
    UPROPERTY(EditAnywhere, Category="Farm|Lighting") float SunYaw = -35;
    UPROPERTY(EditAnywhere, Category="Farm|Lighting") float LampIntensity = 650;

    UPROPERTY(BlueprintAssignable, Category="Farm|Events") FFarmTimeChanged OnTimeChanged;
    UPROPERTY(BlueprintAssignable, Category="Farm|Events") FFarmDayChanged OnDayEnding;
    UPROPERTY(BlueprintAssignable, Category="Farm|Events") FFarmDayChanged OnDayStarted;

    UFUNCTION(BlueprintCallable, Category="Farm|Time") void SetClockPaused(bool bPaused);
    UFUNCTION(BlueprintCallable, Category="Farm|Time") bool TrySleep();
    UFUNCTION(BlueprintCallable, Category="Farm|Time") void RequestEndDay();
    UFUNCTION(BlueprintCallable, Category="Farm|Time") void AdvanceClock(double RealSeconds);
    UFUNCTION(BlueprintCallable, Category="Farm|Time") void RestoreClock(FFarmClockState SavedState);
    UFUNCTION(BlueprintPure, Category="Farm|Time") FFarmClockState CaptureClock() const { return State; }
    UFUNCTION(BlueprintPure, Category="Farm|Time") int32 GetDisplayMinutes() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") int32 GetDayOfSeason() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") int32 GetSeasonIndex() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") int32 GetYear() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") FText GetDateText() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") FText GetClockText() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") FText GetStatusText() const;
    UFUNCTION(BlueprintPure, Category="Farm|Time") bool CanSleep() const;
    UFUNCTION(BlueprintCallable, Category="Farm|Lighting") void ApplyLighting(float Hour);
    UFUNCTION(CallInEditor, Category="Farm|Lighting") void PreviewLighting();
    UFUNCTION(CallInEditor, Category="Farm|Lighting") void PreviewMorning();
    UFUNCTION(CallInEditor, Category="Farm|Lighting") void PreviewNoon();
    UFUNCTION(CallInEditor, Category="Farm|Lighting") void PreviewSunset();
    UFUNCTION(CallInEditor, Category="Farm|Lighting") void PreviewNight();

private:
    UPROPERTY(Transient) TObjectPtr<UFarmClockWidget> ClockWidget;
    float TransitionSeconds = 0;
    int32 LastDisplayMinute = INDEX_NONE;
    float LightingAccumulator = 0;
    float HintSeconds = 0;
    bool bPausedByClock = false;
    void FinishDay();
    void SyncLegacyState();
    void EnsurePlotVisualCapacity();
    void PublishTime();
    void TogglePause();
    void SleepInput();
};
