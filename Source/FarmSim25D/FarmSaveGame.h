#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "FarmClock.h"
#include "FarmSaveGame.generated.h"

/** Local SaveGame slot for day-end continue (clock + pawn Money/SeedCount/CropCount). Plots not persisted (MVP). */
UCLASS()
class FARMSIM25D_API UFarmSaveGame : public USaveGame
{
	GENERATED_BODY()
public:
	static const TCHAR* SlotName() { return TEXT("FarmSim25D_Slot0"); }
	static constexpr int32 UserIndex = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Farm|Save")
	FFarmClockState Clock;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Farm|Save")
	int32 Money = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Farm|Save")
	int32 SeedCount = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Farm|Save")
	int32 CropCount = 0;

	/** Capture pawn economy + clock and write slot. Returns false on failure. */
	UFUNCTION(BlueprintCallable, Category="Farm|Save")
	static bool SaveFromWorld(UObject* WorldContext, const FFarmClockState& ClockState);

	/** If slot exists, fill Out and optionally apply Money/Seeds/Crops to player pawn. */
	UFUNCTION(BlueprintCallable, Category="Farm|Save")
	static bool TryLoadToWorld(UObject* WorldContext, FFarmClockState& OutClock, bool bApplyEconomy = true, bool bShowToast = true);

	UFUNCTION(BlueprintCallable, Category="Farm|Save")
	static bool DoesSaveExist();

	UFUNCTION(BlueprintCallable, Category="Farm|Save")
	static bool DeleteSave();
};
