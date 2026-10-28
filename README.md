# FarmSim25D

UE5.8 等距 / 2.5D **种田 + 模拟经营** 项目（进行中 / WIP）。  
节奏参考《星露谷物语》的一天日程，餐厅段参考「速速上菜」式跑堂手感。当前主关卡：`Lvl_TopDown`。

> 诚实说明：这是可玩的 **垂直切片**，不是完整商业游戏。农场核心循环已实现（当前迭代优先餐厅）；餐厅为南桥划区 2 桌 2 菜 MVP。

---

## 游戏内容介绍

### 定位

| 项 | 内容 |
|---|---|
| 引擎 | Unreal Engine **5.8** |
| 视角 | 等距正交（Voxel Micro Farm 体素场景） |
| 类型 | 种田模拟 + 餐厅经营 |
| 状态 | **WIP** — 农场可玩；餐厅垂直切片：开业/换色客人/UMG 订单条/持菜高亮正确桌/结账进 COINS；调试色块默认关闭 |

### 一日日程（FarmClock）

| 时段 | 模式 | 玩法重心 |
|---|---|---|
| 约 06:00 – 17:00 | 农场 | 锄地、播种、浇水、生长、收获 |
| 约 17:00 – 23:00 | 餐厅营业 | 开业牌开业、客人点单、灶台做菜、上菜收钱 |
| 23:00 之后 | 自由 | 打烊后自由活动（完整睡觉/过日流程仍在迭代） |

种地部分：**核心循环已实现**；当前开发迭代暂停优先餐厅垂直切片。

### 农场玩法（已实现核心）

- **移动**：WASD 四向，沿世界轴移动  
- **交互**：情境 **E**（锄地等）  
- **种植循环**：锄地 → 播种 → 浇水 → 生长 → 收获  
- **网格地块**：道路 / 水 / 道具区域禁耕  
- **资源**：库存与货币（COINS）  
- **日夜**：`FarmClock` + 日月双灯驱动光照与时间 UI  

### 餐厅垂直切片（南桥划区）

南桥东侧码头陆地：家具已拉开摆放；调试色块默认关闭，开业牌绿/红表示营业状态，订单看右上角 UMG。

| 物件 | 作用 |
|---|---|
| **开业牌** | 17:00 后按 E 开业 / 可提前打烊；23:00 自动打烊；牌面绿=营业 / 红=打烊 |
| **餐桌 ×2** | 入座自动点单；正确桌上菜 → 用餐片刻 → `PAY +$` 清桌（并入左上角 COINS） |
| **灶台** | E 开始做菜 → READY 后再 E 端上手；头顶有做菜中 / 菜好了进度提示 |
| **垃圾桶** | 丢弃手上菜品 |

菜品（MVP）：

| 菜 | 约价 | 约烹饪时间 |
|---|---|---|
| TomatoSalad（番茄沙拉） | ~$15 | ~3s |
| Stew（炖菜） | ~$28 | ~6s |

规则摘要：

1. 开业后空桌刷客，客人（换色 Manny）坐到椅边并自动点单  
2. 灶台做对应菜 → 端手上（一次一盘；身前可见持菜小模型）  
3. **正确桌**上菜 → 桌上放菜、状态「用餐中」→ 结账清桌，钱进 **COINS**  
4. **错桌** → $0 离席；**耐心约 20–25s** 超时离席  
5. 可扔垃圾桶清空手上菜  

本轮已接上的体验（仍 WIP）：

- 右上角 UMG 订单条；桌面耐心/用餐中提示；持菜时高亮正确桌  
- 结账并入 COINS；开业牌绿/红；**T** 跳到 17:00  
- 灶台进度与持菜提示/模型；上菜后桌上菜  
- 打烊黄字营收小结（`RestDayEnd`）；17:00 开业提醒  

调试色块默认关闭（Manager.bShowRestDebugLabels=false）；开业牌绿/红仍保留；订单看右上角 UMG。

设计文档：[`Docs/Restaurant_Framework.md`](Docs/Restaurant_Framework.md)  
场景内说明：[`Content/Farm/Restaurant/README.md`](Content/Farm/Restaurant/README.md)

### 操作摘要

| 按键 | 作用 |
|---|---|
| **WASD** | 移动 |
| **E** | 情境交互（锄地 / 开业牌 / 灶台 / 餐桌 / 垃圾桶） |
| **T** | 跳到约 17:00（方便测餐厅） |
| **Esc** | 暂停（若已接好 UI） |

### 美术与关卡

- 场景资源：Voxel Micro Farm（VMF）体素农场包  
- 镜头：等距正交俯视  
- 主关卡：`Content/TopDown/Lvl_TopDown`  
- 餐厅蓝图：`Content/Farm/Restaurant/`  

### 工程速览

```
FarmSim25D/
├── Content/
│   ├── TopDown/          # 角色、输入、主关卡
│   ├── Farm/             # 网格、UI、光照、Restaurant/
│   └── Python/           # 编辑器脚本（日夜 / 餐厅脚手架）
├── Source/FarmSim25D/    # FarmClock 等 C++
├── Docs/                 # 框架与验收文档
└── FarmSim25D.uproject
```

打开方式：用 UE 5.8 打开 `FarmSim25D.uproject` → PIE `Lvl_TopDown`。  
测餐厅：按 **T** 跳到 ≥17:00（或把时间调到约 1020 分钟）→ 开业牌 E → 灶台做菜 → 正确桌上菜 → 打烊看日结。

---

## English blurb

**FarmSim25D** is a WIP Unreal Engine 5.8 isometric farming + restaurant sim. Daytime farming loop (till / plant / water / harvest) is in; evenings open a south-bridge restaurant vertical slice (2 tables, 2 dishes, tinted guests, cook → hold → serve → COINS pay, stove progress, close-day summary). UMG order list + held-dish table highlight in; identity debug cubes default off. Not a finished game.

---

## License / 资产说明

第三方 VMF 等美术资产请遵守其各自许可；本仓库代码与自制蓝图文档按作者后续声明为准。