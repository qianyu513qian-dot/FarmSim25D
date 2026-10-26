# FarmSim25D 进度总览（可复刻）
更新：2026-10-24（香港时间）

工程：`E:\UE\FarmSim25D`（UE5.8，纯蓝图，自 TP_TopDownBP）  
地图：`Lvl_TopDown`  
禁止改：CropoutSampleProject / AoELiteFramework  
主跟：Zenva《Build a 2.5D Farming RPG》  
美术预定：VectoRaith Farming Sim Asset Pack（稍后导入）

---

## 一、新建工程（已完成）

1. 启动 `E:\UE_5.8` 的 Unreal Editor。
2. Games → Top Down → Blueprint（不要 C++）。
3. 项目名 `FarmSim25D`，路径 `E:\UE\`，创建。
4. 打开后确认能进 `Lvl_TopDown` 并 Play。

**验收**：Play 后能看见俯视角色；Esc 退出正常。

---

## 二、阶段0：世界轴 WASD + 正交相机（已通过）

### 2.1 关掉“朝向跟随移动”

1. 内容浏览器打开：`Content/TopDown/Blueprints/BP_TopDownCharacter`。
2. 选中组件 **Character Movement (CharMoveComp)**。
3. Details 搜 `Orient`，取消勾选 **Orient Rotation to Movement**。
4. Compile → Save。

**预期**：转身不再自动对准移动方向（后面用世界轴推角色）。

### 2.2 Enhanced Input：确认 IA_Move

1. 打开 `Content/TopDown/Input/Actions/IA_Move`（路径以你工程里实际名为准）。
2. Value Type 应为 **Axis2D (Vector2D)**。

### 2.3 IMC：WASD 映射（世界轴约定）

打开 Input Mapping Context（TopDown 用的那个 IMC）：

| 键 | 目标 | Modifiers（顺序很重要） |
|----|------|-------------------------|
| W | IA_Move | Swizzle Input Axis Values = **YXZ**（把 W 的 1 打到 Y） |
| S | IA_Move | **Negate**，再 **Swizzle YXZ** |
| A | IA_Move | **Negate**（X 负方向） |
| D | IA_Move | 无 Modifier（X 正方向） |

保存 IMC。

**约定**：W 永远朝场景世界 +Y（屏幕/场景“上方”），不是角色面朝方向。

### 2.4 BP_TopDownCharacter：移动图

Event Graph 里找到（或新建）**EnhancedInputAction IA_Move**，事件用 **Triggered**：

1. `Action Value` → **Break Vector2D** → 得到 X、Y。
2. 第一条 **Add Movement Input**：
   - World Direction = **Make Vector**（X = Break.X，Y = 0，Z = 0）——左右
   - Scale Value = `1.0`（或你需要的速度系数）
3. 第二条 **Add Movement Input**：
   - World Direction = **Make Vector**（X = 0，Y = Break.Y，Z = 0）——前后/上下
   - Scale Value = `1.0`

**不要**用 `Get Actor Forward Vector` / `Get Actor Right Vector`（那是角色朝向，不符合本项目约定）。

Compile → Save。

**验收**：Play 后  
- W = 往场景上方走  
- S = 下方  
- A = 左，D = 右  
- 旋转角色朝向，WASD 方向不变。

### 2.5 相机：2.5D 正交俯视（类 Stardew，约 -60°）

在 `BP_TopDownCharacter`：

1. 选中 **CameraBoom**（SpringArm）：
   - **Use Pawn Control Rotation** = 关（若有）
   - Camera Settings：**Do Collision Test** = **关**
   - **Inherit Pitch / Yaw / Roll** = **全部关**
   - Transform → Rotation：改用 **Absolute Rotation**（细节面板小锁/绝对），Pitch ≈ **-60**，Yaw/Roll = 0  
     （不要用 -90，会太平、不像经营视角）
2. 选中 **FollowCamera**（Camera）：
   - Projection Mode = **Orthographic**
   - **Ortho Width** = **1000**（调远近主要靠这个，不是 Arm Length）
3. Compile → Save → Play 看距离。

**验收**：角色完整在画面中；略带一点透视倾斜感；移动流畅。

---

## 三、阶段1：网格地块（进行中）

### 3.1 文件夹（已完成）

内容浏览器新建：`Content/Farm/Grid/`

### 3.2 枚举 E_PlotState（已完成）

1. 右键 `Content/Farm/Grid` → Blueprints → Enumeration → 命名 `E_PlotState`。
2. 打开，添加枚举项（顺序建议）：
   - Empty
   - Tilled
   - Seeded
   - Growing
   - Mature
3. Save。

### 3.3 BP_GridManager（已完成资源 + 变量）

1. 右键 `Content/Farm/Grid` → Blueprint Class → **Actor** → 命名 `BP_GridManager`。
2. 若打开是 Data Only：点 **Open Full Blueprint Editor**。
3. 在 My Blueprint → Variables 添加（全部勾选 **Instance Editable**，方便关卡里调）：

| 变量名 | 类型 | 默认值 |
|--------|------|--------|
| CellSize | Float | 100 |
| GridWidth | Integer | 20 |
| GridHeight | Integer | 20 |
| GridOrigin | Vector | (0, 0, 0) |

4. Compile → Save。

**注意**：路径是 `Content/Farm/Grid/BP_GridManager`，不是 `Content/TopDown/Blueprints`。

### 3.4 函数 WorldToGrid（已完成）

My Blueprint → Functions → + → 命名 `WorldToGrid`。

**输入**
- World Location：Vector

**输出**
- Grid X：Integer  
- Grid Y：Integer

**公式**  
`Grid = Floor( (World - GridOrigin) / CellSize )`（只用 X/Y，忽略 Z）

**节点接法（与你当前图一致）**

1. World Location → Break Vector  
2. Grid Origin → Break Vector  
3. X：`(World.X - Origin.X) / CellSize` → **Floor** → 接到 Return 的 **Grid X**  
4. Y：`(World.Y - Origin.Y) / CellSize` → **Floor** → 接到 Return 的 **Grid Y**  
5. 若 Floor 出来是 float、Grid X 是 int：中间加 **To Integer (Truncate)**，或改用返回 Integer 的 Floor。  
6. 入口白色执行线连到 Return。

Compile，无红叉。

**自测思路（下一小步会用）**：把角色脚底世界坐标丢进 WorldToGrid，应得到稳定整数格。

### 3.5 函数 GridToWorld（下一步，未完成）

Functions → + → `GridToWorld`

**输入**：Grid X (Int)、Grid Y (Int)  
**输出**：World Location (Vector)

**公式（格子中心）**
- `X = Origin.X + (GridX + 0.5) * CellSize`
- `Y = Origin.Y + (GridY + 0.5) * CellSize`
- `Z = Origin.Z`

节点提示：GridX → To Float → + 0.5 → × CellSize → + Origin.X；Y 同理；Make Vector → Return。

### 3.6 函数 IsValidCell（再下一步）

输入 Grid X / Grid Y，输出 Boolean：  
`GridX >= 0 && GridX < GridWidth && GridY >= 0 && GridY < GridHeight`

### 3.7 关卡放置与脚下高亮（尚未做）

1. 把 `BP_GridManager` 拖进 `Lvl_TopDown`，摆在合适 Origin。  
2. 角色每帧/定时：脚底位置 → WorldToGrid →（可选）Debug 画框或贴花高亮当前格。

---

## 四、当前状态一句话

| 模块 | 状态 |
|------|------|
| 工程 FarmSim25D | 完成 |
| 世界轴 WASD | 完成并通过 |
| 正交相机 Ortho 1000 / Pitch -60 | 完成并通过 |
| E_PlotState | 完成 |
| BP_GridManager 变量 | 完成 |
| WorldToGrid | 完成 |
| GridToWorld / IsValidCell / 关卡实例 / 脚下高亮 | 未做 |
| 锄地播种浇水 / 天数货币 UI | 未开始 |
| VectoRaith 导入 | 未开始 |

---

## 五、立刻接着做

打开 `BP_GridManager` → 按 **§3.5** 做完 `GridToWorld` → Compile → 截图确认。