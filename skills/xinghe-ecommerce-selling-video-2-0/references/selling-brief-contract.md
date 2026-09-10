# 带货 Brief 契约

生成视频前先产出结构化 brief。brief 是后续文字分镜、视觉分镜图和 Seedance prompt 的唯一来源。

## 必需字段

```json
{
  "mode": "product_selling_video",
  "product_name": "",
  "platform": "douyin",
  "category": "general",
  "target_audience": "",
  "selling_points": [],
  "duration": 15,
  "ratio": "9:16",
  "resolution": "480p",
  "voiceover_language": "zh-CN",
  "voiceover_policy": {"enabled": true, "style": ""},
  "caption_layer_policy": {"mode": "sparse_stickers"},
  "presenter_mode": "",
  "result_showcase_type": "",
  "product_identity_locks": [],
  "physical_scene_constraints": "",
  "must_show_result_frame": "",
  "shot_plan": [],
  "adapted_voiceover": [],
  "adapted_on_screen_text": [],
  "product_identity_constraints": "",
  "negative_constraints": []
}
```

## Shot Plan 字段

每个 shot 必须包含：

- `start`、`end`
- `purpose`
- `visual`
- `framing`
- `camera`
- `action`
- `model_or_host_role`
- `sticker_overlay`
- `sound_effect`
- `product_fidelity`
- `physical_scene`
- `space_anchor`
- `result_frame_requirement`
- `single_action_rule`

## 默认 15 秒结构

- `0-2s`：首秒钩子，立刻出现商品或痛点。
- `2-5s`：核心卖点 1，用动作解决痛点。
- `5-8s`：核心卖点 2，展示场景或使用前后。
- `8-11.5s`：材质、结构、成分、规格或细节证明。
- `11.5-15s`：适用人群、完整使用场景、CTA。

## 商品一致性

每个 shot 都要重复商品一致性约束：颜色、形状、包装、Logo/标签位置、材质、配件、数量和可见结构不得改变。产品图是商品身份参考，分镜图只指导镜头与动作。

## 真人带货与物理空间

- 默认按类目选择真人主播、模特、手模或画外音配真实使用场景。
- 不允许纯商品静物旋转；至少 3 个 shot 要有人物动作、真实使用过程或完成结果画面。
- 每个 shot 只允许一个主要动作，避免复杂动作导致穿帮。
- 每个 shot 必须写明商品身份锁、物理接触锁和空间锚点锁。
- 服装必须上身展示；四件套/床品必须铺完整张床；收纳/清洁必须展示前后变化；食品必须展示感官结果；美妆必须展示质地或使用后状态。

## 非复刻边界

本技能不做参考视频复刻。即使用户给参考视频，也只可把它当作风格/灵感描述；不要下载、抽帧、ASR、OCR、blueprint、逐镜头还原或复刻节奏迁移。
