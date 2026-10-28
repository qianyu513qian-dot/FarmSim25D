# Restaurant Vertical Slice — Actor Map (Knife 1)

> 2026-10-27 第一刀：南桥陆地侧场景摆放 + 可交互骨架。种地循环仍暂停；勿改 Cropout/AoELite。

## Level placement (Lvl_TopDown, south bridge / dock)

Layout sketch (2026-10-27 spaced + Chinese in-world labels):

`
  Y~700  [垃圾桶 1780] -------------------- [灶台 2080]
  Y~500  [开业牌 1680]   (Manager 1900 hidden)
  Y~300  [餐桌1 1820] -------------------- [餐桌2 2080]
           ^ west / bridge approach              east ^
`

| Actor Label | Blueprint / Class | World (approx) | In-world name | Mesh |
|---|---|---|---|---|
| Restaurant_OpenSign | BP_RestaurantOpenSign | (1680, 500, 81) | 开业牌 | FarmSign |
| Restaurant_Table1 | BP_RestaurantTable | (1820, 300, 28) | 餐桌1 | ShippingChest |
| Restaurant_Table2 | BP_RestaurantTable | (2080, 300, 28) | 餐桌2 | ShippingChest |
| RestChair_chair* | StaticMeshActor | near tables | (visual) | Crate |
| Restaurant_Stove | BP_RestaurantStove | (2080, 700, 53) | 灶台 | CrateStack |
| Restaurant_Trash | BP_RestaurantTrash | (1780, 700, 40) | 垃圾桶 | CompostBin |
| Restaurant_Manager | BP_RestaurantManager | (1900, 500, 80) hidden | — | logic only |
| RestLabel_* | TextRenderActor | above each prop | 开业牌/灶台/餐桌1/餐桌2/垃圾桶 | Font_SimHei_TR |

Interactables carry Actor Tag **RestInteract**. Floating RestLabel_* use TextRender + /Game/Farm/Restaurant/Font_SimHei_TR (SimHei). Scale of VMF props stays ~0.01.

## Content paths

- `/Game/Farm/Restaurant/BP_RestaurantInteractable` — parent; `InteractLabel`, `InteractRange`, `RestaurantInteract()` prints label
- `/Game/Farm/Restaurant/BP_RestaurantTable` — `TableId`, `bOccupied`, `CurrentDishId`
- `/Game/Farm/Restaurant/BP_RestaurantStove` — `bCooking`, `bCookReady`, `CookingDishId`
- `/Game/Farm/Restaurant/BP_RestaurantTrash`
- `/Game/Farm/Restaurant/BP_RestaurantOpenSign` — `bIsOpenBusiness`
- `/Game/Farm/Restaurant/BP_RestaurantManager` — `bIsOpenBusiness`, `InteractRange`, `HeldDishId`; `HandlePlayerE` stub

Design source of truth: `Docs/Restaurant_Framework.md`

## E interact (knife 1)

`BP_TopDownCharacter` / `IA_Interact` **Started**:

1. `GetAllActorsWithTag(RestInteract)`
2. `ForEach` + `Distance2D` to player pawn `< 200`
3. `PrintString` with actor display name (differentiates table/stove/trash/sign)
4. `Completed` → existing `TillSoil` (farming paused; keep as fallback)

## How to test

1. Open `FarmSim25D` / PIE `Lvl_TopDown`
2. Walk south toward bridge land (~1850–2250 X, ~400–700 Y) — furniture should be visible
3. Stand next to OpenSign / Table / Stove / Trash and press **E** — screen print `Restaurant E -> …` with that actor’s name
4. Optional: with FarmClock console/debug, jump minutes to ≥1020 (17:00) / ≥1380 (23:00) for next knife’s open/close gate

## Done this knife

- [x] 2 tables + chairs, stove, trash, open sign placed (VMF meshes)
- [x] Restaurant BP skeleton under `Content/Farm/Restaurant/`
- [x] E distance scan + differentiated Print feedback
- [ ] OpenSign **clock gate** (≥17 open / ≥23 auto-close) — vars exist, logic next
- [ ] Spawn guests / orders / cook / serve / money / UI bubbles

## Next knife (suggested)

1. OpenSign: read `FarmClock.State.Minutes`; gate open at ≥1020; toggle `bIsOpenBusiness`; auto-close ≥1380; swap sign color/scale
2. `BP_RestaurantManager` authoritative open state + empty-table guest spawn (3–5s)
3. Auto order on seat; patience 20–25s; stove cook 3s/6s; hold 1 dish; serve / wrong-table / trash rules per framework
4. Bubble + side order strip UI
5. Esc pause UI (optional)

## Authoring scripts (editor remote)

- `Content/Python/restaurant_slice1_build2.py`
- `Content/Python/restaurant_slice1_rebuild_interact.py`
- `Content/Python/restaurant_fix_ia_chain2.py`
