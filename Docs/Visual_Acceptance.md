# 第二轮光照与视角验收

2026-10-26。第一轮被用户明确否定：正午仍然发白，而且绕 Z 轴转 45° 没有解决俯视感的问题。本说明取代第一轮结论；本轮仍待用户体验确认。

## 分析与修改

草地源贴图是较深的绿色，材质检查确认它使用正常 sRGB 贴图接入 Base Color，没有自发光。第一轮太阳强度 3.8 下，实际受光后的草地与树冠仍然偏浅。因此继续降低白天直射光，保留原贴图与配色，没有使用全局饱和度补偿。

| 光照设置 | 第一轮（未通过） | 第二轮 |
|---|---:|---:|
| 08:00 太阳 | 3.3 | 1.8 |
| 12:00 太阳 | 3.8 | 2.1 |
| 16:00 太阳 | 3.5 | 1.9 |
| 18:00 太阳 | 2.4 | 1.5 |
| Bloom | 0.08 | 0 |

正午天空光保持 1.05，环境立方体补光保持 0.25，曝光保持 EV100=0、Bias=0。初次暗曝光试验过于暗沉，没有采用。夜间月光和灯笼强度保留。

视角问题包含正交投影缺少近大远小、俯角与画面覆盖范围之间的关系，不是地图朝向问题。对比更高的正交俯视与窄视野透视后，本轮采用后者：

- **Yaw 恢复原来的 90°**，撤回第一轮 135°。
- 投影改为 Perspective，FOV 32°，臂长 4200，俯角 48°。
- 固定镜头朝向，不随角色转身或桥栏碰撞改变。
- 保持较弱透视，让远处物体自然缩小，同时保留俯视农场的操作方式。
- 原有 WASD 通过 CameraComponent 的 Forward / Right 计算方向，继续适配当前镜头。

保留现有模型、地图布局及材质。地块重复感、桥栏与角色的美术比例、水面等其他问题不应混入本轮验收。

## 验证与复现

编辑器和游戏 Development 目标重新编译。`farm_dn_visual_apply.py` 将新代码默认日照曲线、后处理、角色蓝图相机保存进关卡与资源；游戏运行不依赖 Python。

`farm_dn_visual_verify.py` 检查运行中的投影、FOV、臂长、朝向、日照曲线、曝光及移动图依赖。间隔实际引擎 Tick 后，`farm_dn_visual_verify_after.py` 检查角色转身不带动镜头，时钟不会把正午恢复到旧值。`farm_dn_verify_saved.py` 检查原始关卡接入与 06:00 新游戏状态。

`Tools/visual_review.py start` 启动 PIE；`preview 12 v2_noon` 临时固定正午并截图；`stop` 退出 PIE。预览只固定时钟，人物仍可走动。退出并重新 Play 后，恢复正常 06:00 开始的一天。

实际截图保存于 `Saved/VisualReview/v2_*.png`。`v2_initial` 为未采用的过暗试验，`v2_balanced` 为正交对比，`v2_perspective_wide` 为轻微透视对比；`v2_final_*` 为保存后重启 PIE 的最终检查图。截图来自引擎游戏渲染。

后台入口是 `Tools/Start-FarmMcp.ps1 -Render`；同项目已有编辑器时必须复用，避免两个实例同时写资产。Python 使用 UE 自带解释器，MCP 地址沿用 `UE_MCP_URL` 或本地 8000 端口。

参考：[Epic 正交相机说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/orthographic-camera-in-unreal-engine)、[Epic 材质输入与反射说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine)。具体视觉选择仍以本项目的实际画面和用户验收为准。
