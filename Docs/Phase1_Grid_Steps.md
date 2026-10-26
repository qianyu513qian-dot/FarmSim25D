# FarmSim25D 阶段1 - 网格地块

## 目标
- BP_GridManager：CellSize / 宽高 / Origin
- 世界坐标 <-> 格子 (GX,GY)
- E_PlotState 枚举
- 玩家脚下格子可读；选中格可视化

## 步骤 A
Content/Farm/Grid/
- E_PlotState: Empty, Tilled, Seeded, Growing, Mature

## 步骤 B
BP_GridManager (Actor)
- CellSize Float 100
- GridWidth Int 20
- GridHeight Int 20
- GridOrigin Vector 0,0,0
Instance Editable 全开

## 步骤 C（下一步）
函数 WorldToGrid / GridToWorld / IsValidCell
