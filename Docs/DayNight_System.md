# 农场时间与昼夜系统

当前关卡 `/Game/TopDown/Lvl_TopDown` 已放置 `FarmClock`。时间、界面与灯光由项目运行时模块 `FarmSim25D` 实现，游戏运行不依赖 Python 或 MCP。蓝图、材质和关卡接入通过 UE 5.8 自带的 **ModelContextProtocol + EditorToolset** 完成；`farm_mcp_tools.FarmDayNightTools` 是按 Epic Toolset Registry 扩展方式注册的项目工具。

## 游玩

- 每日 **06:00** 开始，现实 **7 秒 = 游戏 10 分钟**；完整活动日到次日 **02:00**，约 14 分钟。
- 时间内部连续推进，右上角时钟以 10 分钟为单位显示，灯光平滑过渡。
- **午夜只把显示改成 00:00，不增加农场日期**。
- 靠近农舍（550 uu 内）按 **B** 睡觉；在别处按 B 会显示提示。
- **P** 暂停/恢复游戏和时钟；暂停时 P 仍可响应。
- 凌晨 02:00 自动进入休息过渡，淡出、结算、回到安全出生点，次日 06:00 淡入。
- 每季 28 天，春夏秋冬四季，每年 112 天；显示星期和年份。
- 00:00 后时钟变红并提示回家。尚无体力/昏倒罚款系统，因此没有添加金钱惩罚。

## 与当前农场的连接

`FarmClock` 引用现有 `BP_GridManager`，同步它的 `CurrentDay`、`TimeOfDay` 和 `DayLengthSeconds`。旧的 75 秒循环 Tick 和 BeginPlay 灯光初始化执行链已断开。现有锄地、播种、浇水、收获函数保留。

每次休息完成只调用一次 `AdvanceDayGrowth`，保留原有 **已浇水 3 → 成熟 4**、未浇水种子不生长的规则。系统初始化时补齐 `PlotVisuals` 的空引用槽位，避免首日结算时越界读取。

太阳、月光、天空补光、雾、环境色共同过渡。主方向光优先级随昼夜切换，避免双方向光竞争提示。固定 EV100=0，避免自动曝光把夜晚补亮成白天。

2026-10-26 第二轮视觉修正：第一轮的太阳强度 3.8 仍被用户反馈发白，现正午降为 2.1；天空光 1.05、环境立方体补光 0.25、Bloom 0。8:00、16:00、18:00 关键值一并衔接。相机恢复原 Yaw 90°，采用俯角 48°、FOV 32°、臂长 4200 的轻微透视；详见 [本轮验收说明](Visual_Acceptance.md)。

农舍及两座桥的六盏灯笼在黄昏渐亮，清晨渐灭。灯柱使用无碰撞装饰网格，不改变原有道路通行。`MPC_FarmLighting` 的 `NightBlend` 驱动灯芯发光；`WaterTint` 调整现有 `M_Water` 的自发光，防止水面夜间仍维持白天亮度。

## 调整与扩展

在关卡中选择 **FarmClock**：

| 属性/接口 | 用途 |
|---|---|
| `SecondsPerTenMinutes` | 标准为 7 秒，可调整一天的长度 |
| `TimeSpeed` | 0 冻结推进，1 标准速度，支持加速 |
| `LightKeys` | 按小时递增排列的日照、环境光、月光、灯笼和颜色关键值 |
| `LampIntensity` | 当前关卡为 230 流明 |
| `HomeLocation / SleepRadius` | 农舍休息范围 |
| `WakeLocation` | 次日安全返回点，使用现有关卡 PlayerStart |
| `PreviewMorning / Noon / Sunset / Night` | 编辑器 Details 中的预览按钮，不推进游戏日期 |
| `SetClockPaused` | 背包/对话等界面可控制时钟暂停 |
| `OnTimeChanged` | 每跨越 10 分钟触发，包括长帧跨过多个刻度 |
| `OnDayEnding / OnDayStarted` | 日结、任务、商店等蓝图扩展事件 |
| `CaptureClock / RestoreClock` | 读写日期/时间快照，供后续统一 SaveGame 系统使用 |

`CaptureClock` 是存档接口；目前不会单独写磁盘存档，以免时钟与现有未存档的农田状态脱节。新开游戏从春 1 日 06:00 开始。

## 后台工作流程

`Tools/Start-FarmMcp.ps1` 自动定位 UE 5.8，使用 `UnrealEditor-Cmd.exe -RenderOffscreen -unattended`，隐藏窗口、低进程优先级、10 FPS 上限。默认 `-nullrhi` 不占用渲染资源；需要离屏图片时加 `-Render`。脚本会拒绝同时启动同项目的第二个编辑实例。

```powershell
# 首次编译/代码更新后，由已安装 UE 的 Build.bat 构建 FarmSim25DEditor。
./Tools/Start-FarmMcp.ps1 -Render

# 以下 python.exe 使用 UE 自带的 Engine/Binaries/ThirdParty/Python3/Win64/python.exe。
python Content/Python/ue_mcp_client.py
python Content/Python/ue_mcp_client.py script farm_dn_install.py
python Content/Python/ue_mcp_client.py script farm_dn_finalize.py
python Content/Python/ue_mcp_client.py script farm_dn_shutdown.py
```

默认端点 `http://127.0.0.1:8000/mcp`。端口变更时设置 `UE_MCP_URL`。所有 MCP 调用串行执行，不使用鼠标、键盘模拟、窗口激活或桌面截图。

重新创建灯光素材时先运行 `farm_dn_materials.py`（需要已经放置的六个灯笼点光源），再运行 `farm_dn_install.py`；正常使用已保存的关卡无需重跑安装脚本。关卡为 World Partition，保存流程同时保存关卡及外部 Actor 包。

## 验证

- `FarmSim25DEditor Win64 Development` 编译。
- `FarmSim25D Win64 Development` 游戏目标编译通过，运行时代码不依赖编辑器模块。
- 冷启动后的 `farm_dn_verify_saved.py` 通过 8 项保存与引用检查；地图检查为 0 错误、0 警告。
- 通过官方 MCP `StartPIE` 在后台实际运行游戏，串行执行 `farm_dn_runtime_test.py`、等待至少 1 秒、`farm_dn_runtime_after.py`、等待至少 1 秒、`farm_dn_runtime_sleep_after.py`。
- 27 项断言覆盖七秒步进、暂停、跨午夜、长帧、速度倍率、季节/年份、无效快照修正、UMG 实例、旧时钟停用、农田初始化、02:00 换天、重复请求保护、作物成熟、未浇水不生长、返回出生点、农舍睡觉及春夏转换。
- 测试会修改 PIE 临时世界里的时间和两格作物；结束 PIE 后不保存测试状态。
- 离屏图像与 JSON 结果位于 `Saved/DayNight`，可复查正午、黄昏、夜间及真实游戏界面。

参考： [Epic Unreal MCP 文档](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor)、[Stardew Valley Day Cycle](https://wiki.stardewvalley.net/Day_Cycle)。
