#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameFramework/Actor.h"
#include "FarmPauseWidget.generated.h"

class AFarmClock;
class UButton;
class UTextBlock;
class UStaticMeshComponent;
class UTextRenderComponent;
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

/** Seed shop UI (code-built, Chinese). Buy seeds / sell crops / close. */
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
	UPROPERTY(Transient) TObjectPtr<UButton> SellButton;
	UPROPERTY(Transient) TObjectPtr<UButton> CloseButton;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusLabel;
	UFUNCTION() void OnBuyClicked();
	UFUNCTION() void OnSellClicked();
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

	/** Fallback crop sell price if pawn has no TomatoSellPrice (or it is <=0). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Farm|Shop")
	int32 CropSellPrice = 10;

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

	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	bool TrySellCrop();

	/** Resolve sell price: pawn TomatoSellPrice if >0, else CropSellPrice. */
	UFUNCTION(BlueprintCallable, Category="Farm|Shop")
	int32 GetEffectiveCropSellPrice() const;

	/** Restaurant cook start: need CropCount>=1, deduct 1, refresh HUD. No refund on void. */
	UFUNCTION(BlueprintCallable, Category="Farm|Restaurant")
	static bool TryConsumeCropForCook(APawn* Pawn);

	static bool CloseAnyOpenShop(UWorld* World);

	static int32 GetPawnInt(APawn* Pawn, const TCHAR* Name);
	static void SetPawnInt(APawn* Pawn, const TCHAR* Name, int32 Value);
	static void CallPawnUpdateHud(APawn* Pawn);

protected:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UTextRenderComponent> NameLabel;

private:
	UPROPERTY(Transient) TObjectPtr<UFarmShopWidget> ShopWidget;
	void InteractInput();
	void ApplyShopPresentation(bool bOpen);
};