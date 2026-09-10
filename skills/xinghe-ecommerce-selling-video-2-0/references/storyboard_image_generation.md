# 带货分镜图生图 Helper

正常付费生成前必须有本地 `storyboard_sheet.png`。本文件规定生图工具优先级，只服务于带货视频的视觉分镜图，不用于生成最终视频帧。

## 优先级

1. 优先使用 `scripts/generate_storyboard_image.py` 生成分镜图。
2. 脚本先调用本机部署 helper：
   `%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`
3. helper 不可用或失败时，脚本再走 OpenAI-compatible HTTP API：
   - 有产品图/参考图：`https://xinghe.xin/v1/images/edits`
   - 纯文本分镜：`https://xinghe.xin/v1/images/generations`
   - 默认模型：`gpt-image-2`
4. 只有脚本、helper、HTTP API 都不可用或无法保存本地 `storyboard_sheet.png` 时，才使用 Codex 内置 `image_gen` 作为最终兜底。
5. 内置 `image_gen` 不得作为默认首选路径。

## 默认值

- 模型：`gpt-image-2`
- 尺寸：`auto`，根据 panel 数自动选择 `2048x1536` 或 `1536x2048`
- 输出文件名：`storyboard_sheet.png`
- 输出类型：单张导演分镜表，不是多张独立图片
- 参考图片：优先传用户产品图。产品图只用于锁定商品外观；分镜图只规划镜头、动作、构图、空间和结果画面。

## 命令

```bash
PYTHON_BIN="${CODEX_BUNDLED_PYTHON:-python3}"
SKILL_ROOT="${CODEX_HOME:-$HOME/.codex}/skills/xinghe-ecommerce-selling-video-2-0"
"$PYTHON_BIN" "$SKILL_ROOT/scripts/generate_storyboard_image.py" \
  --storyboard-json "/path/storyboard.json" \
  --reference-image "/path/product.png" \
  --size "auto" \
  --output-dir "/path/storyboard-image"
```

已有 `storyboard_sheet_prompt.txt` 时也可以直接使用 prompt 文件：

```bash
"$PYTHON_BIN" "$SKILL_ROOT/scripts/generate_storyboard_image.py" \
  --prompt-file "/path/storyboard_sheet_prompt.txt" \
  --reference-image "/path/product.png" \
  --size "2048x1536" \
  --output-dir "/path/storyboard-image"
```

prompt-file 模式下，`auto` 会默认到 `2048x1536`，因为脚本无法从 prompt 文件可靠读取 panel 数。需要竖版分镜表时手动指定 `1536x2048`。

## 环境变量兜底

HTTP API 兜底读取这些变量：

- API key：`IMG_API_KEY`、`OPENAI_API_KEY` 或 `API_KEY`
- Base URL：`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`IMG_BASE_URL` 或 `BASE_URL`
- Model：`OPENAI_IMAGE_MODEL`、`IMG_MODEL`、`OPENAI_MODEL` 或 `IMAGE_MODEL`
- Generations URL：`OPENAI_IMAGE_GENERATIONS_URL` 或 `IMG_GENERATIONS_URL`
- Edits URL：`OPENAI_IMAGE_EDITS_URL` 或 `IMG_EDITS_URL`

没有配置 base URL 时，默认使用：

- `https://xinghe.xin/v1/images/generations`
- `https://xinghe.xin/v1/images/edits`

## 保存规则

生成成功后，本地必须存在输出图片。脚本写出：

- `storyboard_sheet.png`
- `storyboard-image-manifest.json`
- `storyboard-image-result.json`
- `storyboard_sheet_prompt.txt`

如果生成失败，保留 prompt 文件和 result JSON，方便检查或重试。

## 商品身份规则

- 产品图是最高优先级商品身份来源。
- `storyboard_sheet.png` 是导演参考，不是商品身份参考。
- 分镜图不得重新设计商品，不得改变颜色、形状、包装、Logo/标签、材质、配件和尺寸比例。
- 分镜图不能替代产品图提交给 Seedance；正式生成时必须同时提交产品图和分镜图。
