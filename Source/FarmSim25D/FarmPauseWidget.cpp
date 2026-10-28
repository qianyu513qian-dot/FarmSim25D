#include "FarmPauseWidget.h"
#include "FarmClock.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/SizeBox.h"

void UFarmPauseWidget::SetClock(AFarmClock* InClock)
{
	Clock = InClock;
}

TSharedRef<SWidget> UFarmPauseWidget::RebuildWidget()
{
	if (ContinueButton && WidgetTree && WidgetTree->RootWidget) return Super::RebuildWidget();
	if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("PauseWidgetTree"));

	UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
	WidgetTree->RootWidget = Canvas;

	UBorder* Dim = WidgetTree->ConstructWidget<UBorder>();
	Dim->SetBrushColor(FLinearColor(0.02f, 0.03f, 0.04f, 0.72f));
	auto* DimSlot = Canvas->AddChildToCanvas(Dim);
	DimSlot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
	DimSlot->SetOffsets(FMargin(0.f));

	USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>();
	Box->SetWidthOverride(360.f);
	Box->SetHeightOverride(160.f);
	auto* BoxSlot = Canvas->AddChildToCanvas(Box);
	BoxSlot->SetAnchors(FAnchors(0.5f, 0.5f));
	BoxSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	BoxSlot->SetSize(FVector2D(360.f, 160.f));

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
	Panel->SetBrushColor(FLinearColor(0.05f, 0.07f, 0.05f, 0.96f));
	Panel->SetPadding(FMargin(28.f, 24.f));
	Box->SetContent(Panel);

	UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
	Panel->SetContent(Stack);

	UTextBlock* Title = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = Title->GetFont();
		Font.Size = 20;
		Title->SetFont(Font);
		Title->SetJustification(ETextJustify::Center);
		Title->SetColorAndOpacity(FSlateColor(FLinearColor(0.92f, 0.88f, 0.7f)));
		Title->SetText(FText::FromString(TEXT("PAUSED")));
	}
	Stack->AddChildToVerticalBox(Title)->SetPadding(FMargin(0.f, 0.f, 0.f, 18.f));

	ContinueButton = WidgetTree->ConstructWidget<UButton>();
	{
		FButtonStyle Style = ContinueButton->GetStyle();
		Style.Normal.TintColor = FSlateColor(FLinearColor(0.18f, 0.42f, 0.28f, 1.f));
		Style.Hovered.TintColor = FSlateColor(FLinearColor(0.24f, 0.55f, 0.34f, 1.f));
		Style.Pressed.TintColor = FSlateColor(FLinearColor(0.12f, 0.32f, 0.2f, 1.f));
		ContinueButton->SetStyle(Style);
	}

	UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = Label->GetFont();
		Font.Size = 28;
		Label->SetFont(Font);
		Label->SetJustification(ETextJustify::Center);
		Label->SetColorAndOpacity(FSlateColor(FLinearColor(1.f, 0.96f, 0.84f)));
		Label->SetText(FText::FromString(FString::Chr(0x7EE7) + FString::Chr(0x7EED)));
	}
	ContinueButton->SetContent(Label);
	if (UButtonSlot* BS = Cast<UButtonSlot>(Label->Slot))
	{
		BS->SetPadding(FMargin(40.f, 16.f));
		BS->SetHorizontalAlignment(HAlign_Center);
		BS->SetVerticalAlignment(VAlign_Center);
	}
	Stack->AddChildToVerticalBox(ContinueButton)->SetHorizontalAlignment(HAlign_Center);

	SetVisibility(ESlateVisibility::Visible);
	return Super::RebuildWidget();
}

void UFarmPauseWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (ContinueButton)
	{
		ContinueButton->OnClicked.RemoveDynamic(this, &UFarmPauseWidget::OnContinueClicked);
		ContinueButton->OnClicked.AddDynamic(this, &UFarmPauseWidget::OnContinueClicked);
	}
}

void UFarmPauseWidget::OnContinueClicked()
{
	if (IsValid(Clock))
	{
		Clock->ResumeFromPauseMenu();
	}
}

// ---- Seed shop (merged into this TU so Live Coding can pick it up without new cpp files) ----
#include <initializer_list>
#include "InputCoreTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

static FString ZH(std::initializer_list<int32> Codes)
{
	FString Out;
	for (int32 C : Codes) Out.AppendChar(static_cast<TCHAR>(C));
	return Out;
}

void UFarmShopWidget::SetShop(AFarmSeedShop* InShop)
{
	Shop = InShop;
	RefreshStatus();
}

TSharedRef<SWidget> UFarmShopWidget::RebuildWidget()
{
	if (BuyButton && WidgetTree && WidgetTree->RootWidget) return Super::RebuildWidget();
	if (!WidgetTree) WidgetTree = NewObject<UWidgetTree>(this, TEXT("ShopWidgetTree"));

	UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
	WidgetTree->RootWidget = Canvas;

	UBorder* Dim = WidgetTree->ConstructWidget<UBorder>();
	Dim->SetBrushColor(FLinearColor(0.02f, 0.03f, 0.04f, 0.55f));
	auto* DimSlot = Canvas->AddChildToCanvas(Dim);
	DimSlot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
	DimSlot->SetOffsets(FMargin(0.f));

	USizeBox* Box = WidgetTree->ConstructWidget<USizeBox>();
	Box->SetWidthOverride(420.f);
	Box->SetHeightOverride(320.f);
	auto* BoxSlot = Canvas->AddChildToCanvas(Box);
	BoxSlot->SetAnchors(FAnchors(0.5f, 0.5f));
	BoxSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	BoxSlot->SetSize(FVector2D(420.f, 320.f));

	UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
	Panel->SetBrushColor(FLinearColor(0.06f, 0.09f, 0.05f, 0.97f));
	Panel->SetPadding(FMargin(28.f, 22.f));
	Box->SetContent(Panel);

	UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
	Panel->SetContent(Stack);

	UTextBlock* Title = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = Title->GetFont();
		Font.Size = 22;
		Title->SetFont(Font);
		Title->SetJustification(ETextJustify::Center);
		Title->SetColorAndOpacity(FSlateColor(FLinearColor(0.92f, 0.88f, 0.7f)));
		Title->SetText(FText::FromString(ZH({0x79CD, 0x5B50, 0x5E97})));
	}
	Stack->AddChildToVerticalBox(Title)->SetPadding(FMargin(0.f, 0.f, 0.f, 10.f));

	StatusLabel = WidgetTree->ConstructWidget<UTextBlock>();
	{
		FSlateFontInfo Font = StatusLabel->GetFont();
		Font.Size = 14;
		StatusLabel->SetFont(Font);
		StatusLabel->SetJustification(ETextJustify::Center);
		StatusLabel->SetColorAndOpacity(FSlateColor(FLinearColor(0.75f, 0.82f, 0.7f)));
		StatusLabel->SetText(FText::FromString(TEXT("")));
	}
	Stack->AddChildToVerticalBox(StatusLabel)->SetPadding(FMargin(0.f, 0.f, 0.f, 14.f));

	auto StyleBtn = [](UButton* Btn, const FLinearColor& Normal)
	{
		FButtonStyle Style = Btn->GetStyle();
		Style.Normal.TintColor = FSlateColor(Normal);
		Style.Hovered.TintColor = FSlateColor(Normal * 1.25f);
		Style.Pressed.TintColor = FSlateColor(Normal * 0.75f);
		Btn->SetStyle(Style);
	};

	auto MakeBtnLabel = [this](UButton* Btn, const FString& Text, int32 FontSize)
	{
		UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
		FSlateFontInfo Font = Label->GetFont();
		Font.Size = FontSize;
		Label->SetFont(Font);
		Label->SetJustification(ETextJustify::Center);
		Label->SetColorAndOpacity(FSlateColor(FLinearColor(1.f, 0.96f, 0.84f)));
		Label->SetText(FText::FromString(Text));
		Btn->SetContent(Label);
		if (UButtonSlot* BS = Cast<UButtonSlot>(Label->Slot))
		{
			BS->SetPadding(FMargin(24.f, 11.f));
			BS->SetHorizontalAlignment(HAlign_Center);
			BS->SetVerticalAlignment(VAlign_Center);
		}
	};

	BuyButton = WidgetTree->ConstructWidget<UButton>();
	StyleBtn(BuyButton, FLinearColor(0.22f, 0.48f, 0.28f, 1.f));
	MakeBtnLabel(BuyButton, ZH({0x4E70, 0x756A, 0x8304, 0x79CD, 0x5B50}) + TEXT(" -$5"), 16);
	{
		UVerticalBoxSlot* BuySlot = Stack->AddChildToVerticalBox(BuyButton);
		BuySlot->SetPadding(FMargin(0.f, 0.f, 0.f, 8.f));
		BuySlot->SetHorizontalAlignment(HAlign_Center);
	}

	SellButton = WidgetTree->ConstructWidget<UButton>();
	StyleBtn(SellButton, FLinearColor(0.48f, 0.36f, 0.16f, 1.f));
	MakeBtnLabel(SellButton, ZH({0x5356, 0x4F5C, 0x7269}) + TEXT(" +$10"), 16);
	{
		UVerticalBoxSlot* SellSlot = Stack->AddChildToVerticalBox(SellButton);
		SellSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 8.f));
		SellSlot->SetHorizontalAlignment(HAlign_Center);
	}

	CloseButton = WidgetTree->ConstructWidget<UButton>();
	StyleBtn(CloseButton, FLinearColor(0.28f, 0.28f, 0.3f, 1.f));
	{
		UTextBlock* Label = WidgetTree->ConstructWidget<UTextBlock>();
		FSlateFontInfo Font = Label->GetFont();
		Font.Size = 15;
		Label->SetFont(Font);
		Label->SetJustification(ETextJustify::Center);
		Label->SetColorAndOpacity(FSlateColor(FLinearColor(0.9f, 0.9f, 0.88f)));
		Label->SetText(FText::FromString(ZH({0x5173, 0x95ED})));
		CloseButton->SetContent(Label);
		if (UButtonSlot* BS = Cast<UButtonSlot>(Label->Slot))
		{
			BS->SetPadding(FMargin(28.f, 10.f));
			BS->SetHorizontalAlignment(HAlign_Center);
			BS->SetVerticalAlignment(VAlign_Center);
		}
	}
	Stack->AddChildToVerticalBox(CloseButton)->SetHorizontalAlignment(HAlign_Center);

	SetIsFocusable(true);
	SetVisibility(ESlateVisibility::Visible);
	return Super::RebuildWidget();
}

void UFarmShopWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (BuyButton)
	{
		BuyButton->OnClicked.RemoveDynamic(this, &UFarmShopWidget::OnBuyClicked);
		BuyButton->OnClicked.AddDynamic(this, &UFarmShopWidget::OnBuyClicked);
	}
	if (SellButton)
	{
		SellButton->OnClicked.RemoveDynamic(this, &UFarmShopWidget::OnSellClicked);
		SellButton->OnClicked.AddDynamic(this, &UFarmShopWidget::OnSellClicked);
	}
	if (CloseButton)
	{
		CloseButton->OnClicked.RemoveDynamic(this, &UFarmShopWidget::OnCloseClicked);
		CloseButton->OnClicked.AddDynamic(this, &UFarmShopWidget::OnCloseClicked);
	}
	RefreshStatus();
}

void UFarmShopWidget::RefreshStatus()
{
	if (!StatusLabel) return;
	if (!IsValid(Shop))
	{
		StatusLabel->SetText(FText::FromString(TEXT("")));
		return;
	}

	APawn* Pawn = UGameplayStatics::GetPlayerPawn(Shop, 0);
	const int32 Money = AFarmSeedShop::GetPawnInt(Pawn, TEXT("Money"));
	const int32 Crops = AFarmSeedShop::GetPawnInt(Pawn, TEXT("CropCount"));
	const int32 Seeds = AFarmSeedShop::GetPawnInt(Pawn, TEXT("SeedCount"));
	const int32 SeedP = Shop->SeedPrice;
	const int32 SellP = Shop->GetEffectiveCropSellPrice();

	StatusLabel->SetText(FText::FromString(
		TEXT("COINS $") + FString::FromInt(Money) +
		TEXT("  |  ") + ZH({0x4F5C, 0x7269}) + TEXT(" ") + FString::FromInt(Crops) +
		TEXT("  |  ") + ZH({0x79CD, 0x5B50}) + TEXT(" ") + FString::FromInt(Seeds) +
		TEXT("\n") +
		ZH({0x4E70}) + TEXT(" -$") + FString::FromInt(SeedP) +
		TEXT("   ") +
		ZH({0x5356}) + TEXT(" +$") + FString::FromInt(SellP)));

	// Keep button labels in sync with prices
	if (BuyButton)
	{
		if (UTextBlock* L = Cast<UTextBlock>(BuyButton->GetContent()))
		{
			L->SetText(FText::FromString(ZH({0x4E70, 0x756A, 0x8304, 0x79CD, 0x5B50}) + TEXT(" -$") + FString::FromInt(SeedP)));
		}
	}
	if (SellButton)
	{
		if (UTextBlock* L = Cast<UTextBlock>(SellButton->GetContent()))
		{
			L->SetText(FText::FromString(ZH({0x5356, 0x4F5C, 0x7269}) + TEXT(" +$") + FString::FromInt(SellP)));
		}
	}
}

void UFarmShopWidget::OnBuyClicked()
{
	if (IsValid(Shop))
	{
		Shop->TryBuySeeds();
		RefreshStatus();
	}
}

void UFarmShopWidget::OnSellClicked()
{
	if (IsValid(Shop))
	{
		Shop->TrySellCrop();
		RefreshStatus();
	}
}

void UFarmShopWidget::OnCloseClicked()
{
	if (IsValid(Shop))
	{
		Shop->CloseShop();
	}
}

FReply UFarmShopWidget::NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent)
{
	if (InKeyEvent.GetKey() == EKeys::Escape)
	{
		OnCloseClicked();
		return FReply::Handled();
	}
	return Super::NativeOnKeyDown(InGeometry, InKeyEvent);
}

AFarmSeedShop::AFarmSeedShop()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ShopMesh"));
	SetRootComponent(Mesh);
	Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Mesh->SetCollisionResponseToAllChannels(ECR_Block);
	Mesh->SetGenerateOverlapEvents(false);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(
		TEXT("/Game/Farm/VoxelMicroFarm/Models/Props/SM_VMF_Prop_ShippingChest"));
	if (MeshFinder.Succeeded())
	{
		Mesh->SetStaticMesh(MeshFinder.Object);
	}

	NameLabel = CreateDefaultSubobject<UTextRenderComponent>(TEXT("ShopNameLabel"));
	NameLabel->SetupAttachment(Mesh);
	NameLabel->SetRelativeLocation(FVector(0.f, 0.f, 120.f));
	NameLabel->SetHorizontalAlignment(EHTA_Center);
	NameLabel->SetVerticalAlignment(EVRTA_TextCenter);
	NameLabel->SetWorldSize(28.f);
	NameLabel->SetTextRenderColor(FColor(120, 220, 140));
	NameLabel->SetText(FText::FromString(TEXT("SHOP")));
	NameLabel->SetHiddenInGame(false);

	Tags.Add(FName(TEXT("FarmShop")));
	Tags.Add(FName(TEXT("Farm_Shop")));
}

void AFarmSeedShop::BeginPlay()
{
	Super::BeginPlay();
	SetActorLabel(TEXT("Farm_Shop"));
	if (NameLabel)
	{
		// Prefer ASCII billboard so PIE does not show "Tt" for missing CJK glyphs
		NameLabel->SetText(FText::FromString(TEXT("SHOP")));
		NameLabel->SetWorldSize(32.f);
	}
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		EnableInput(PC);
		if (InputComponent)
		{
			InputComponent->BindKey(EKeys::E, IE_Pressed, this, &AFarmSeedShop::InteractInput);
		}
	}
}

void AFarmSeedShop::EndPlay(const EEndPlayReason::Type Reason)
{
	CloseShop();
	Super::EndPlay(Reason);
}

bool AFarmSeedShop::IsPlayerInRange() const
{
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!IsValid(Pawn)) return false;
	return FVector::Dist(Pawn->GetActorLocation(), GetActorLocation()) <= InteractRadius;
}

bool AFarmSeedShop::IsShopOpen() const
{
	return ShopWidget && ShopWidget->IsInViewport();
}

void AFarmSeedShop::InteractInput()
{
	if (IsShopOpen()) return;
	if (!IsPlayerInRange()) return;
	OpenShop();
}

void AFarmSeedShop::OpenShop()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	if (!ShopWidget)
	{
		ShopWidget = CreateWidget<UFarmShopWidget>(PC, UFarmShopWidget::StaticClass());
		if (ShopWidget) ShopWidget->SetShop(this);
	}
	if (ShopWidget && !ShopWidget->IsInViewport())
	{
		ShopWidget->AddToViewport(90);
		ShopWidget->RefreshStatus();
		ShopWidget->SetKeyboardFocus();
	}
	ApplyShopPresentation(true);
	if (GEngine)
	{
		FString Msg;
		Msg.AppendChar(0x79CD); Msg.AppendChar(0x5B50); Msg.AppendChar(0x5E97);
		Msg.AppendChar(0x5F00);
		GEngine->AddOnScreenDebugMessage(-1, 2.f, FColor::Cyan, Msg);
	}
}

void AFarmSeedShop::CloseShop()
{
	if (ShopWidget)
	{
		ShopWidget->RemoveFromParent();
		ShopWidget = nullptr;
	}
	ApplyShopPresentation(false);
}

void AFarmSeedShop::ApplyShopPresentation(bool bOpen)
{
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		if (bOpen)
		{
			FInputModeUIOnly Mode;
			if (ShopWidget) Mode.SetWidgetToFocus(ShopWidget->TakeWidget());
			Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
			PC->SetInputMode(Mode);
			PC->bShowMouseCursor = true;
			PC->SetIgnoreMoveInput(true);
			PC->SetIgnoreLookInput(true);
		}
		else
		{
			FInputModeGameOnly Mode;
			PC->SetInputMode(Mode);
			PC->bShowMouseCursor = false;
			PC->ResetIgnoreMoveInput();
			PC->ResetIgnoreLookInput();
		}
	}
}

int32 AFarmSeedShop::GetPawnInt(APawn* Pawn, const TCHAR* Name)
{
	if (!IsValid(Pawn)) return 0;
	if (const FIntProperty* Prop = FindFProperty<FIntProperty>(Pawn->GetClass(), Name))
	{
		return Prop->GetPropertyValue_InContainer(Pawn);
	}
	return 0;
}

void AFarmSeedShop::SetPawnInt(APawn* Pawn, const TCHAR* Name, int32 Value)
{
	if (!IsValid(Pawn)) return;
	if (FIntProperty* Prop = FindFProperty<FIntProperty>(Pawn->GetClass(), Name))
	{
		Prop->SetPropertyValue_InContainer(Pawn, Value);
	}
}

void AFarmSeedShop::CallPawnUpdateHud(APawn* Pawn)
{
	if (!IsValid(Pawn)) return;
	static const FName FnName(TEXT("UpdateFarmHUD"));
	if (UFunction* Fn = Pawn->FindFunction(FnName))
	{
		Pawn->ProcessEvent(Fn, nullptr);
	}
}

int32 AFarmSeedShop::GetEffectiveCropSellPrice() const
{
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	const int32 FromPawn = GetPawnInt(Pawn, TEXT("TomatoSellPrice"));
	if (FromPawn > 0) return FromPawn;
	return CropSellPrice > 0 ? CropSellPrice : 10;
}

bool AFarmSeedShop::TryBuySeeds()
{
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!IsValid(Pawn)) return false;

	const int32 Money = GetPawnInt(Pawn, TEXT("Money"));
	if (Money < SeedPrice)
	{
		if (GEngine)
		{
			FString Msg;
			Msg.AppendChar(0x94B1); Msg.AppendChar(0x4E0D); Msg.AppendChar(0x591F);
			GEngine->AddOnScreenDebugMessage(-1, 2.f, FColor::Orange, Msg + TEXT(" ($") + FString::FromInt(Money) + TEXT(")"));
		}
		return false;
	}

	const int32 Seeds = GetPawnInt(Pawn, TEXT("SeedCount"));
	SetPawnInt(Pawn, TEXT("Money"), Money - SeedPrice);
	SetPawnInt(Pawn, TEXT("SeedCount"), Seeds + SeedsPerPurchase);
	CallPawnUpdateHud(Pawn);

	if (GEngine)
	{
		FString Msg;
		Msg.AppendChar(0x4E70); Msg.AppendChar(0x5230);
		Msg.AppendChar(0x756A); Msg.AppendChar(0x8304);
		Msg.AppendChar(0x79CD); Msg.AppendChar(0x5B50);
		Msg += TEXT(" +");
		Msg += FString::FromInt(SeedsPerPurchase);
		Msg += TEXT("  -$");
		Msg += FString::FromInt(SeedPrice);
		GEngine->AddOnScreenDebugMessage(-1, 2.5f, FColor::Green, Msg);
	}
	if (ShopWidget) ShopWidget->RefreshStatus();
	return true;
}

bool AFarmSeedShop::TrySellCrop()
{
	APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!IsValid(Pawn)) return false;

	const int32 Crops = GetPawnInt(Pawn, TEXT("CropCount"));
	if (Crops <= 0)
	{
		if (GEngine)
		{
			GEngine->AddOnScreenDebugMessage(-1, 2.f, FColor::Orange, ZH({0x6CA1, 0x6709, 0x4F5C, 0x7269}));
		}
		return false;
	}

	const int32 SellP = GetEffectiveCropSellPrice();
	const int32 Money = GetPawnInt(Pawn, TEXT("Money"));
	SetPawnInt(Pawn, TEXT("CropCount"), Crops - 1);
	SetPawnInt(Pawn, TEXT("Money"), Money + SellP);
	CallPawnUpdateHud(Pawn);

	if (GEngine)
	{
		FString Msg = ZH({0x5356, 0x51FA, 0x4F5C, 0x7269});
		Msg += TEXT("  +$");
		Msg += FString::FromInt(SellP);
		GEngine->AddOnScreenDebugMessage(-1, 2.5f, FColor::Yellow, Msg);
	}
	if (ShopWidget) ShopWidget->RefreshStatus();
	return true;
}

bool AFarmSeedShop::CloseAnyOpenShop(UWorld* World)
{
	if (!World) return false;
	bool bClosed = false;
	for (TActorIterator<AFarmSeedShop> It(World); It; ++It)
	{
		if (It->IsShopOpen())
		{
			It->CloseShop();
			bClosed = true;
		}
	}
	return bClosed;
}
