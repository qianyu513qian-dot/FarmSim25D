# 保留场景布置的美术优化

2026-10-26。当前植被造型已应用到原资源，整场景使用新版本，不再只是两件预览样例。模型内部的造型发生变化；原 Actor 位置、旋转、缩放、数量、资源引用、调色板材质和碰撞定义保留。木板路、栅栏连接、房屋与道具布局不受本轮影响。

## 全场植被覆盖

| 资源 | 场景实例 | 每个资源三角形数 |
| --- | ---: | ---: |
| Tree_Broadleaf | 73 | 5,994 |
| Tree_Tall | 40 | 5,265 |
| Flower_White | 1 | 756 |
| Flower_Yellow | 2 | 860 |
| FlowerPatch_White | 1 | 4,244 |
| FlowerPatch_Yellow | 1 | 3,956 |
| Shrub_Low | 2 | 2,556 |
| Shrub_Tall | 1 | 2,556 |
| Bush | 2 | 2,556 |

共 9 个资源、123 个实例。阔叶树与高树依据各自原 FBX 的枝冠位置重建叶团、疏密和伸出的尖叶，树干与分枝逐渐收细。高树保留更高、更窄的分层轮廓。白花与黄花分别保留原花头数量、位置、高度和颜色，重建薄花瓣、花心、弯茎与交错叶片。花丛保留原底座并补足贴地叶簇；三种灌木保持各自原外包尺寸与材质调色板。

原 FBX 和源贴图不变。游戏直接加载已保存的静态网格，不需要运行几何脚本。当前树资源比最初原始网格增加了几何量，但比此前圆角版本减少；没有进行目标设备帧率基准测试。

## 材质、光照与镜头

- 草地压缩原调色板绿色亮度差，加入约 3.5% 的连续大尺度变化，降低棋盘色差与碎噪点。
- 木材保留原色区，调整粗糙度与暖色中间调，并叠加约 ±4% 的局部顺向纹理；坐标通过 VertexInterpolator 传给像素阶段。
- 水面使用原 T_Water 和昼夜 WaterTint，降低纹样反差，UV 6×30 匹配原 1:5 水面尺寸，并缓慢平移。
- 太阳光源角 3.5°，月光保持 4°，暗部 Gamma 1.10。正午太阳强度 2.1、固定曝光 EV0、Bloom 关闭。
- 沿用已提交的镜头修复：透视 FOV32、臂长4200、俯角−48°、原水平朝向90°。放大的验收镜头仅作用于 PIE。

## 生成、验证与备份

使用项目 Unreal MCP 客户端在非 PIE 编辑器内依次运行：

1. `farm_dn_prepare_vegetation.py`：从原 FBX 导入临时语义部件。
2. `farm_dn_complete_vegetation.py`：写回 9 个原 StaticMesh；两件已完成样例作为阔叶树和白花丛的造型源。
3. `farm_dn_vegetation_verify.py`：检查保存版本、面数、有限坐标、UV、材质路径、碰撞摘要，并逐 Actor 核对全场覆盖。
4. `farm_dn_content_baseline.py`：检查 1718 个静态 Actor 的引用与变换等基线。
5. `farm_dn_cleanup_vegetation.py`：清理独立 VegetationBuild 文件夹内的临时导入资源。

`farm_vegetation_geometry.py` 提供造型构建；两个 vegetation_*palette.json 从现有两张调色板提取，生成过程不依赖图像库。GeometryScripting 仅为编辑器插件。`farm_dn_surface_finish.py` 和 `farm_dn_shadow_finish.py` 分别维护材质与阴影。

完整生成清单在 `Saved/ArtReview/full_anatomy_manifest.json`。本轮写回前的 9 个资源备份在 `Saved/ArtReview/before_full_anatomy/`；更早的原始六个植被资源在 `Saved/ArtReview/rounded_originals/`。旧圆角脚本遇到已替代标记会拒绝覆盖新造型。直接重新导入原 FBX 会覆盖新造型，应按上述流程再生成。

## 验收证据与范围

- 覆盖核对：113 棵树、5 处单株/花丛、5 处灌木，遗漏列表为空。两件样例之外的资源均已实际写回。
- 布局核对：1718 个静态 Actor 的原网格引用、变换、材质引用及碰撞开关一致；资源内部几何已变更。逐资产原碰撞几何摘要一致。
- 保存后重启编辑器，9 个资源的几何、材质、碰撞与 123 个实例覆盖再次通过；材质编译及这些网格的加载没有失败。`git diff --check` 通过。
- 验收图在 `Saved/VisualReview/`：`full_anatomy_overview00000.png` 为常规镜头全景；`full_anatomy_yellow00000.png` 为黄花近景；`full_anatomy_shrub00000.png` 检查高树与灌木。
- 预览日志仍有角色蓝图 GridManagerRef 空引用，本轮美术验证不代表种植交互功能通过，未编辑该交互链。

此前被拒绝的场景内容改造备份在 `Saved/ArtReview/rejected_content_pass_20261026/`，不参与运行。旧样例与圆角截图仅作历史对照，不能作为当前全场覆盖证据。最终视觉效果由用户验收。
