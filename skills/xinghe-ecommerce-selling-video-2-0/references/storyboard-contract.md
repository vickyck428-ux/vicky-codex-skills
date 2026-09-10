# 带货分镜图契约

正常付费生成前必须先完成文字分镜和视觉分镜图。

## 文字分镜

从带货 brief 生成：

- `storyboard.json`
- `storyboard.md`

每个 panel 对应一个 shot，必须包含：时间、目的、构图、机位、动作、商品位置、口播、贴纸/文字意图、音效意图、商品一致性、风险提示。

每个 panel 还必须包含：

- 人物/手模/模特角色
- 商品身份锁
- 物理接触关系
- 空间锚点
- 必拍结果画面
- 单动作规则

## 视觉分镜图

生成单张 `storyboard_sheet.png`。每格对应一个 shot，按阅读顺序排列，展示：

- 构图和景别
- 商品位置和动作
- 场景/背景/灯光
- 模特或手部角色
- 贴纸/文字位置
- 口播摘要和 CTA

视觉分镜图是导演参考，不是商品身份参考。提交 Seedance 时，产品图锁定商品外观，分镜图指导镜头顺序、叙事、构图、动作和文字/音效意图。

分镜图不得重新设计商品。它只规划镜头、人物动作、空间、物理接触和结果画面；最终视频中的颜色、形状、包装、Logo/标签、图案、材质和配件必须以产品照片为准。

## 生图工具优先级

生成 `storyboard_sheet.png` 时，按以下顺序执行：

1. 先用 `scripts/generate_storyboard_image.py`。
2. 脚本优先调用本机 helper：`%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`。
3. helper 不可用或失败时，再走 `https://xinghe.xin/v1/images/edits` 或 `https://xinghe.xin/v1/images/generations`，默认模型 `gpt-image-2`。
4. 只有脚本、helper、HTTP API 都不可用或无法保存本地分镜图时，才使用内置 `image_gen` 兜底。

内置 `image_gen` 不是默认首选路径。

## 门禁

- 没有 `storyboard_sheet.png` 时，不进入正常付费生成。
- 正常生成前必须先尝试 helper/API 生图路径；失败时保留 `storyboard-image-result.json` 方便排查。
- 只允许用户明确要求诊断或 dry-run 时跳过分镜图。
- 分镜 panel 数必须等于 shot 数，shot 总时长必须等于 brief 时长。
- 每条视频至少 3 个 panel 必须有人物动作、真实使用过程或完成结果画面，不能全是产品静物。
- 检查没有漂浮、穿模、比例错乱、空间锚点跳变。

## 人物规则

如分镜图出现人物，使用真实匿名成人模特/手模/生活方式人物，不要求同一张脸，不使用名人脸，不上传脸部身份参考。
