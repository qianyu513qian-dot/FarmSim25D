#include "FarmClock.h"
#include "FarmClockWidget.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/PointLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Materials/MaterialParameterCollection.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/InputComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PawnMovementComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "UObject/UnrealType.h"

AFarmClock::AFarmClock()
{
    PrimaryActorTick.bCanEverTick = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    auto Key = [&](float H, float S, float Sky, float M, float L, FLinearColor SunC, FLinearColor SkyC)
    {
        FFarmLightKey K; K.Hour=H; K.Sun=S; K.Sky=Sky; K.Moon=M; K.Lamps=L; K.SunColor=SunC; K.SkyColor=SkyC;
        LightKeys.Add(K);
    };
    const FLinearColor Day(0.83f,0.91f,1), Night(0.34f,0.48f,0.8f);
    Key(0,0,0.38f,2.2f,1,FLinearColor(1,0.55f,0.3f),Night);
    Key(5,0,0.38f,0.8f,1,FLinearColor(1,0.55f,0.3f),Night);
    Key(6,1.8f,0.65f,0.12f,0.4f,FLinearColor(1,0.64f,0.4f),FLinearColor(0.72f,0.76f,0.9f));
    Key(8,6.5f,1.15f,0,0,FLinearColor(1,0.88f,0.7f),Day);
    Key(12,8,1.25f,0,0,FLinearColor(1,0.95f,0.84f),Day);
    Key(16,7,1.15f,0,0,FLinearColor(1,0.87f,0.65f),Day);
    Key(18,3.2f,0.8f,0.05f,0.25f,FLinearColor(1,0.48f,0.2f),FLinearColor(0.85f,0.61f,0.67f));
    Key(19.5f,0.25f,0.42f,0.8f,1,FLinearColor(1,0.3f,0.12f),FLinearColor(0.47f,0.48f,0.75f));
    Key(21,0,0.38f,2.2f,1,FLinearColor(1,0.3f,0.12f),Night);
    Key(24,0,0.38f,2.2f,1,FLinearColor(1,0.3f,0.12f),Night);
}

void AFarmClock::BeginPlay()
{
    Super::BeginPlay();
    State.AbsoluteDay = FMath::Max(1,State.AbsoluteDay);
    State.Minutes = FMath::Clamp(State.Minutes,360.0,1559.999);
    if (IsValid(GridManager)) GridManager->SetActorTickEnabled(false);
    EnsurePlotVisualCapacity();
    if (auto* PC = UGameplayStatics::GetPlayerController(this,0))
    {
        EnableInput(PC);
        InputComponent->BindKey(EKeys::B,IE_Pressed,this,&AFarmClock::SleepInput);
        auto& Pause = InputComponent->BindKey(EKeys::P,IE_Pressed,this,&AFarmClock::TogglePause);
        Pause.bExecuteWhenPaused = true;
        if (bShowClock && PC->IsLocalController())
        {
            ClockWidget = CreateWidget<UFarmClockWidget>(PC,UFarmClockWidget::StaticClass());
            ClockWidget->SetClock(this);
            ClockWidget->AddToViewport(20);
        }
    }
    SyncLegacyState();
    ApplyLighting(float(State.Minutes/60));
    PublishTime();
}

void AFarmClock::EndPlay(const EEndPlayReason::Type Reason)
{
    if (ClockWidget) ClockWidget->RemoveFromParent();
    if (bPausedByClock) UGameplayStatics::SetGamePaused(this,false);
    Super::EndPlay(Reason);
}

void AFarmClock::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (GetWorld() && !GetWorld()->IsGameWorld()) PreviewLighting();
}

void AFarmClock::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    HintSeconds = FMath::Max(0.f,HintSeconds-DeltaSeconds);
    if (bEndingDay)
    {
        TransitionSeconds += DeltaSeconds;
        if (TransitionSeconds >= 1.0f) FinishDay();
    }
    else AdvanceClock(DeltaSeconds);
    LightingAccumulator += DeltaSeconds;
    if (LightingAccumulator >= 0.1f)
    {
        LightingAccumulator = 0;
        ApplyLighting(float(State.Minutes/60));
        SyncLegacyState();
        if (ClockWidget) ClockWidget->Refresh();
    }
}

void AFarmClock::AdvanceClock(double RealSeconds)
{
    if (bClockPaused || bEndingDay || !FMath::IsFinite(RealSeconds) || RealSeconds <= 0) return;
    const double SafeSeconds = FMath::IsFinite(SecondsPerTenMinutes) ? FMath::Max(0.1f,SecondsPerTenMinutes) : 7.0;
    const double Speed = FMath::IsFinite(TimeSpeed) ? FMath::Clamp(TimeSpeed,0.f,100.f) : 1.0;
    const double Next = FMath::Min(1560.0,State.Minutes + RealSeconds * Speed * 10.0 / SafeSeconds);
    // Dispatch every crossed ten-minute boundary, including on a long frame.
    int32 Boundary = (GetDisplayMinutes()/10+1)*10;
    while (Boundary <= FMath::FloorToInt(Next + 1.e-7))
    {
        State.Minutes = Boundary;
        SyncLegacyState();
        PublishTime();
        Boundary += 10;
    }
    State.Minutes = Next;
    if (State.Minutes >= 1560) RequestEndDay();
}

void AFarmClock::SetClockPaused(bool bPaused)
{
    bClockPaused = bPaused;
    if (ClockWidget) ClockWidget->Refresh();
}

void AFarmClock::TogglePause()
{
    if (bEndingDay) return;
    bPausedByClock = !bPausedByClock;
    SetClockPaused(bPausedByClock);
    UGameplayStatics::SetGamePaused(this,bPausedByClock);
}

bool AFarmClock::CanSleep() const
{
    const auto* Pawn = UGameplayStatics::GetPlayerPawn(this,0);
    return !bEndingDay && !bClockPaused && Pawn && FVector::Dist2D(Pawn->GetActorLocation(),HomeLocation) <= SleepRadius;
}

bool AFarmClock::TrySleep()
{
    if (!CanSleep()) { HintSeconds=3; return false; }
    RequestEndDay();
    return true;
}

void AFarmClock::SleepInput() { TrySleep(); }

void AFarmClock::RequestEndDay()
{
    if (bEndingDay || bClockPaused) return;
    bEndingDay=true; TransitionSeconds=0;
    OnDayEnding.Broadcast(State.AbsoluteDay);
    if (auto* PC=UGameplayStatics::GetPlayerController(this,0))
    {
        PC->SetIgnoreMoveInput(true);
        if (PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(0,1,0.8f,FLinearColor::Black,false,true);
    }
    if (ClockWidget) ClockWidget->Refresh();
}

void AFarmClock::FinishDay()
{
    // The guard guarantees one growth call even if sleep and 02:00 coincide.
    if (!bEndingDay) return;
    State.AbsoluteDay++;
    State.Minutes=360;
    SyncLegacyState();
    if (IsValid(GridManager))
    {
        EnsurePlotVisualCapacity();
        if (UFunction* Growth=GridManager->FindFunction(TEXT("AdvanceDayGrowth")))
            GridManager->ProcessEvent(Growth,nullptr);
    }
    if (auto* PC=UGameplayStatics::GetPlayerController(this,0))
    {
        if (APawn* Pawn=PC->GetPawn())
        {
            Pawn->SetActorLocation(WakeLocation,false,nullptr,ETeleportType::TeleportPhysics);
            if (auto* Movement = Pawn->GetMovementComponent()) Movement->StopMovementImmediately();
        }
        PC->SetIgnoreMoveInput(false);
        if (PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(1,0,0.8f,FLinearColor::Black,false,false);
    }
    bEndingDay=false; TransitionSeconds=0;
    LastDisplayMinute=INDEX_NONE;
    ApplyLighting(6);
    PublishTime();
    OnDayStarted.Broadcast(State.AbsoluteDay);
}

void AFarmClock::RestoreClock(FFarmClockState SavedState)
{
    if (bEndingDay) return;
    State.AbsoluteDay=FMath::Max(1,SavedState.AbsoluteDay);
    State.Minutes=FMath::IsFinite(SavedState.Minutes) ? FMath::Clamp(SavedState.Minutes,360.0,1559.999) : 360;
    LastDisplayMinute=INDEX_NONE;
    SyncLegacyState(); ApplyLighting(float(State.Minutes/60)); PublishTime();
}

int32 AFarmClock::GetDisplayMinutes() const { return FMath::FloorToInt((State.Minutes+1.e-7)/10)*10; }
int32 AFarmClock::GetDayOfSeason() const { return (FMath::Max(State.AbsoluteDay,1)-1)%28+1; }
int32 AFarmClock::GetSeasonIndex() const { return ((FMath::Max(State.AbsoluteDay,1)-1)/28)%4; }
int32 AFarmClock::GetYear() const { return (FMath::Max(State.AbsoluteDay,1)-1)/112+1; }

FText AFarmClock::GetDateText() const
{
    static const TCHAR* Seasons[]={TEXT("Spring"),TEXT("Summer"),TEXT("Autumn"),TEXT("Winter")};
    static const TCHAR* Days[]={TEXT("Mon"),TEXT("Tue"),TEXT("Wed"),TEXT("Thu"),TEXT("Fri"),TEXT("Sat"),TEXT("Sun")};
    return FText::FromString(FString::Printf(TEXT("%s %02d  |  %s  |  Y%d"),Seasons[GetSeasonIndex()],GetDayOfSeason(),Days[(State.AbsoluteDay-1)%7],GetYear()));
}

FText AFarmClock::GetClockText() const
{
    const int32 Display=GetDisplayMinutes()%1440;
    return FText::FromString(FString::Printf(TEXT("%02d:%02d"),Display/60,Display%60));
}

FText AFarmClock::GetStatusText() const
{
    if (bEndingDay) return FText::FromString(TEXT("Resting... a new day awaits"));
    if (bClockPaused) return FText::FromString(TEXT("Paused"));
    if (HintSeconds>0) return FText::FromString(TEXT("Walk to the farmhouse to sleep"));
    if (State.Minutes>=1440) return FText::FromString(TEXT("Late! Rest before 02:00"));
    if (CanSleep()) return FText::FromString(TEXT("At home  |  B to sleep"));
    if (State.Minutes>=1200) return FText::FromString(TEXT("Moonlit farm"));
    if (State.Minutes>=1050) return FText::FromString(TEXT("Golden evening"));
    if (State.Minutes<480) return FText::FromString(TEXT("A fresh morning"));
    return FText::FromString(TEXT("A day on the farm"));
}

void AFarmClock::PublishTime()
{
    const int32 Display=GetDisplayMinutes();
    if (Display!=LastDisplayMinute)
    {
        LastDisplayMinute=Display;
        OnTimeChanged.Broadcast(State.AbsoluteDay,Display);
        if (ClockWidget) ClockWidget->Refresh();
    }
}

void AFarmClock::SyncLegacyState()
{
    if (!IsValid(GridManager)) return;
    if (auto* P=FindFProperty<FIntProperty>(GridManager->GetClass(),TEXT("CurrentDay"))) P->SetPropertyValue_InContainer(GridManager,State.AbsoluteDay);
    if (auto* P=FindFProperty<FDoubleProperty>(GridManager->GetClass(),TEXT("TimeOfDay"))) P->SetPropertyValue_InContainer(GridManager,FMath::Fmod(State.Minutes,1440.0)/1440.0);
    if (auto* P=FindFProperty<FDoubleProperty>(GridManager->GetClass(),TEXT("DayLengthSeconds"))) P->SetPropertyValue_InContainer(GridManager,SecondsPerTenMinutes*120.0);
}

void AFarmClock::EnsurePlotVisualCapacity()
{
    if (!IsValid(GridManager)) return;
    const auto* Width=FindFProperty<FIntProperty>(GridManager->GetClass(),TEXT("GridWidth"));
    const auto* Height=FindFProperty<FIntProperty>(GridManager->GetClass(),TEXT("GridHeight"));
    auto* Visuals=FindFProperty<FArrayProperty>(GridManager->GetClass(),TEXT("PlotVisuals"));
    if (!Width || !Height || !Visuals || !CastField<FObjectPropertyBase>(Visuals->Inner)) return;
    const int64 Count=int64(Width->GetPropertyValue_InContainer(GridManager))*Height->GetPropertyValue_InContainer(GridManager);
    if (Count<=0 || Count>1000000) return;
    FScriptArrayHelper Array(Visuals,Visuals->ContainerPtrToValuePtr<void>(GridManager));
    if (Array.Num()<Count) Array.AddValues(int32(Count)-Array.Num());
}

void AFarmClock::ApplyLighting(float Hour)
{
    if (LightKeys.Num()<2 || !FMath::IsFinite(Hour)) return;
    const float H=FMath::Fmod(FMath::Max(0.f,Hour),24.f);
    FFarmLightKey A=LightKeys[0], B=LightKeys.Last();
    for (int32 I=1;I<LightKeys.Num();++I)
        if (H<=LightKeys[I].Hour) { A=LightKeys[I-1]; B=LightKeys[I]; break; }
    float Alpha=FMath::Clamp((H-A.Hour)/FMath::Max(0.001f,B.Hour-A.Hour),0.f,1.f);
    Alpha=Alpha*Alpha*(3-2*Alpha);
    auto Lerp=[&](float X,float Y){ return FMath::Lerp(X,Y,Alpha); };
    const bool bMoonDominant=Lerp(A.Moon,B.Moon)>Lerp(A.Sun,B.Sun);
    // Same solar elevation controls orientation and the day/night handoff.
    const float Elevation=FMath::Cos((H-12)*PI/14);
    if (IsValid(SunLight))
    {
        SunLight->SetActorRotation(FRotator(-65*Elevation,SunYaw+(H-12)*7,0));
        auto* C=SunLight->GetLightComponent();
        C->SetIntensity(Lerp(A.Sun,B.Sun));
        C->SetLightColor(FMath::Lerp(A.SunColor,B.SunColor,Alpha));
        CastChecked<UDirectionalLightComponent>(C)->SetForwardShadingPriority(bMoonDominant ? 0 : 1);
    }
    if (IsValid(MoonLight))
    {
        // The farm's upright voxel facades need a readable three-quarter moon key.
        MoonLight->SetActorRotation(FRotator(-FMath::Max(30.f,-Elevation*65),SunYaw+20,0));
        MoonLight->GetLightComponent()->SetIntensity(Lerp(A.Moon,B.Moon));
        MoonLight->GetLightComponent()->SetLightColor(FLinearColor(0.48f,0.63f,1));
        CastChecked<UDirectionalLightComponent>(MoonLight->GetLightComponent())->SetForwardShadingPriority(bMoonDominant ? 1 : 0);
    }
    if (IsValid(SkyLight))
    {
        SkyLight->GetLightComponent()->SetIntensity(Lerp(A.Sky,B.Sky));
        SkyLight->GetLightComponent()->SetLightColor(FMath::Lerp(A.SkyColor,B.SkyColor,Alpha));
    }
    const float LampBlend=Lerp(A.Lamps,B.Lamps);
    if (IsValid(AmbientGrade))
    {
        auto& S=AmbientGrade->Settings;
        S.bOverride_AmbientCubemapIntensity=true;
        S.bOverride_AmbientCubemapTint=true;
        S.AmbientCubemapIntensity=FMath::Lerp(0.65f,0.25f,LampBlend);
        S.AmbientCubemapTint=FMath::Lerp(FLinearColor(0.84f,0.9f,1),FLinearColor(0.28f,0.42f,0.8f),LampBlend);
    }
    if (IsValid(LightingParameters))
    {
        UKismetMaterialLibrary::SetVectorParameterValue(this,LightingParameters,TEXT("WaterTint"),FMath::Lerp(FLinearColor::White,FLinearColor(0.10f,0.16f,0.32f),LampBlend));
        UKismetMaterialLibrary::SetScalarParameterValue(this,LightingParameters,TEXT("NightBlend"),LampBlend);
    }
    for (APointLight* Lamp:NightLights)
        if (IsValid(Lamp)) Lamp->GetLightComponent()->SetIntensity(LampIntensity*LampBlend);
    if (IsValid(Fog))
    {
        auto* C=Fog->GetComponent();
        C->SetFogDensity(FMath::Lerp(0.009f,0.018f,LampBlend));
        C->SetFogInscatteringColor(FMath::Lerp(FLinearColor(0.58f,0.65f,0.72f),FLinearColor(0.055f,0.09f,0.18f),LampBlend));
    }
}

void AFarmClock::PreviewLighting() { ApplyLighting(PreviewHour); }
void AFarmClock::PreviewMorning() { PreviewHour=6; PreviewLighting(); }
void AFarmClock::PreviewNoon() { PreviewHour=12; PreviewLighting(); }
void AFarmClock::PreviewSunset() { PreviewHour=18; PreviewLighting(); }
void AFarmClock::PreviewNight() { PreviewHour=23; PreviewLighting(); }
