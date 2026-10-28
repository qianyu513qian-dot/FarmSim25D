#include "FarmSaveGame.h"
#include <initializer_list>
#include "FarmPauseWidget.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "Engine/Engine.h"

namespace FarmSaveGamePrivate
{
	static FString Zh(std::initializer_list<int32> Codes)
	{
		FString Out;
		for (int32 C : Codes) Out.AppendChar(static_cast<TCHAR>(C));
		return Out;
	}
}

bool UFarmSaveGame::DoesSaveExist()
{
	return UGameplayStatics::DoesSaveGameExist(SlotName(), UserIndex);
}

bool UFarmSaveGame::DeleteSave()
{
	if (!DoesSaveExist()) return true;
	return UGameplayStatics::DeleteGameInSlot(SlotName(), UserIndex);
}

bool UFarmSaveGame::SaveFromWorld(UObject* WorldContext, const FFarmClockState& ClockState)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World) return false;

	UFarmSaveGame* Save = Cast<UFarmSaveGame>(UGameplayStatics::CreateSaveGameObject(UFarmSaveGame::StaticClass()));
	if (!Save) return false;

	Save->Clock = ClockState;
	if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
	{
		Save->Money = AFarmSeedShop::GetPawnInt(Pawn, TEXT("Money"));
		Save->SeedCount = AFarmSeedShop::GetPawnInt(Pawn, TEXT("SeedCount"));
		Save->CropCount = AFarmSeedShop::GetPawnInt(Pawn, TEXT("CropCount"));
	}

	const bool bOk = UGameplayStatics::SaveGameToSlot(Save, SlotName(), UserIndex);
	if (bOk && GEngine)
	{
		GEngine->AddOnScreenDebugMessage(99110, 2.5f, FColor::Green,
			FarmSaveGamePrivate::Zh({0x5DF2, 0x4FDD, 0x5B58}));
	}
	return bOk;
}

bool UFarmSaveGame::TryLoadToWorld(UObject* WorldContext, FFarmClockState& OutClock, bool bApplyEconomy, bool bShowToast)
{
	if (!DoesSaveExist()) return false;

	UFarmSaveGame* Save = Cast<UFarmSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName(), UserIndex));
	if (!Save) return false;

	OutClock = Save->Clock;
	OutClock.AbsoluteDay = FMath::Max(1, OutClock.AbsoluteDay);
	if (!FMath::IsFinite(OutClock.Minutes)) OutClock.Minutes = 360.0;
	OutClock.Minutes = FMath::Clamp(OutClock.Minutes, 360.0, 1559.999);

	if (bApplyEconomy)
	{
		UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
		if (World)
		{
			if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
			{
				AFarmSeedShop::SetPawnInt(Pawn, TEXT("Money"), Save->Money);
				AFarmSeedShop::SetPawnInt(Pawn, TEXT("SeedCount"), Save->SeedCount);
				AFarmSeedShop::SetPawnInt(Pawn, TEXT("CropCount"), Save->CropCount);
				AFarmSeedShop::CallPawnUpdateHud(Pawn);
			}
		}
	}

	if (bShowToast && GEngine)
	{
		GEngine->AddOnScreenDebugMessage(99111, 3.5f, FColor::Cyan,
			FarmSaveGamePrivate::Zh({0x7EE7, 0x7EED, 0x4E0A, 0x6B21, 0x8FDB, 0x5EA6}));
	}
	return true;
}
