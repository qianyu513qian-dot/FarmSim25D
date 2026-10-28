#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameFramework/Actor.h"
#include "FarmPauseWidget.generated.h"

class AFarmClock;
class UButton;
class UTextBlock;
class UStaticMeshComponent;
class AFarmSeedShop;
class APawn;

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

/** Minimal seed shop UI (code-built, Chinese). Buy tomato seeds / close. */
UCLASS()
class FARMSIM25D_API UFarmShopWidget : public UUserWidget
{
	GENERATED_BODY()
public:
	void SetShop(AFarmSeedShop* InShop);
	void RefreshStatus();
protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeConstruct() override;
	virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
private:
	UPROPERTY(Transient) TObjectPtr<AFarmSeedShop> Shop;
	UPROPERTY(Transient) TObjectPtr<UButton> BuyButton;
	UPROPERTY(Transient) TObjectPtr<UButton> CloseButton;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLabel;
	UFUNCTION() void OnBuyClicked();
	UFUNCTION() void OnCloseClicked();
};

/** Near-farmhouse seed counter. E opens shop UI when player is close. */
UCLASS()
class FARMSIM25D_API AFarmSeedShop : public AActor
{
	GENERATED_BODY()
public:
	AFarmSeedShop();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Shop")
	float InteractRadius = 220.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Shop")
	int32 SeedPrice = 5;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Shop")
	int32 SeedsPerPurchase = 1;

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	bool IsPlayerInRange() const;

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	bool IsShopOpen() const;

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	void OpenShop();

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	void CloseShop();

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	bool TryBuySeeds();

	static bool CloseAnyOpenShop(UWorld* World);

protected:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;

private:
	UPROPERTY(Transient) TObjectPtr<UFarmShopWidget> ShopWidget;
	void InteractInput();
	void ApplyShopPresentation(bool bOpen);
	static int32 GetPawnInt(APawn* Pawn, const TCHAR* Name);
	static void SetPawnInt(APawn* Pawn, const TCHAR* Name, int32 Value);
	static void CallPawnUpdateHud(APawn* Pawn);
};
