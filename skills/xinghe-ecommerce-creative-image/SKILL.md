---
name: xinghe-ecommerce-creative-image
description: CTR-first ecommerce creative image generation skill for product photos. Use when the user asks for 车图制作, 电商创意图, 商品主图, 高点击主图, 信息流广告图, 带货图, 小红书商品图, 抖音商品图, 拼多多主图, 淘宝主图, Amazon product ad image, or gives product images with optional selling points, marketing copy, platform requirements, or competitor references. Default to directly generating one image with the deployment image helper via XINGHE_IMAGE_GENERATOR or %LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1 unless the user asks only for prompts or strategy. Use built-in image_gen only as the final fallback if the helper is unavailable or fails. Prioritize click-through rate, product fidelity, concise high-readability copy, competitor click-logic analysis, platform adaptation, and compliance.
---

# 星河创意图4.0

把产品图、卖点文案和竞品参考图转成点击率优先的电商创意图。这里的“车图”指广告创意图，不是汽车图。

## Non-Negotiables

- 点击率优先：所有标题、构图、场景、光影、标签和对比都服务于停留与点击。
- 默认直接出图：只要用户提供产品图并要求做图，立即使用部署工具 helper 生成，不要先输出 prompt 询问是否出图。
- 生图工具优先级：优先使用 `$env:XINGHE_IMAGE_GENERATOR`，其次使用 `%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`，最后才使用内置 `image_gen` 兜底。
- 默认数量：用户未指定数量时生成 `1` 张；指定数量时严格按数量生成，每张图单独调用一次生图接口；多张图按错峰并发规则提交，间隔 3 秒，不等上一张落盘再提交下一张。
- 默认比例：`1:1` 方图，除非用户指定平台比例或尺寸。
- 产品保真：保持产品外观、颜色、包装、logo、结构、材质、SKU 和关键细节，不为了创意改坏产品。
- 合规优先：不虚构销量、评价、认证、检测、授权、功效、医疗/保健效果或绝对化承诺。

## Required Workflow

1. 判断输入类型：
   - 产品图 only：读 `references/input-routing.md` 和 `references/title-formulas.md`。
   - 产品图 + 卖点/营销文案：读 `references/input-routing.md` 和 `references/generation-output.md`。
   - 产品图 + 竞品参考图：读 `references/competitor-analysis.md`。
   - 指定平台：读 `references/platform-strategies.md`。
   - 食品、保健、美妆功效、母婴、儿童、医疗等高风险品类：读 `references/compliance-qc.md`。
2. 先在内部完成点击率判断：卖什么、解决什么痛点、用户为什么点。
3. 生成前只给用户一句简短方向说明，不要长篇策略汇报。
4. 直接调用部署工具 helper 出图。除非用户明确说“只要提示词/先给方案/不要出图”。优先使用 `$env:XINGHE_IMAGE_GENERATOR`；如果该变量不存在，再使用 `%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`；有参考图通过 `-ReferenceImage`，纯文案起图不传 `-ReferenceImage`。只有 helper 不存在或执行失败时，才使用内置 `image_gen` 作为最后兜底。
5. 出图后按 `references/compliance-qc.md` 做快速复核；如明显失败，说明问题并给出重生成方向。

## Default Creative Structure

- 主标题：1 个，6-14 个中文字优先，问题感/利益感/冲突感强。
- 辅助文案：最多 1 行，不抢主标题。
- 卖点标签：最多 3 个，每个 2-6 个字。
- 产品占比：通常 45%-70%，缩略图下仍清楚。
- 画面层级：第一眼产品 + 标题，第二眼痛点/结果，第三眼标签/细节。

## Direct Generation Rules

- 用户说“做图、生成、出图、车图、主图、创意图、广告图”时，默认是要图片，不要只输出提示词。
- 如果只有产品图，基于可见事实和品类常见购买阻力生成问题吸引点击型创意图。
- 如果用户给了文案/卖点，优先使用用户内容，再压缩成更适合点击的短标题与标签。
- 如果用户给了竞品参考，保留点击逻辑与层级，不能照搬竞品文案、商标、版式细节或图形资产。
- 如果产品图缺失，先简短提醒用户上传产品图；不要凭空生成具体产品广告。

## Output Shape

生成前简短说明：

```text
按【<输入类型>】处理：主打 <点击钩子>，默认生成 <数量> 张 <比例> 创意图。
```

然后直接调用部署工具 helper。只有用户明确要求“给我 prompt”时，才输出 `references/generation-output.md` 里的 prompt 模板。

## Reference Map

- `references/input-routing.md`：输入分类、产品 only、文案优先规则。
- `references/platform-strategies.md`：淘宝/拼多多/抖音/小红书/亚马逊等平台适配。
- `references/title-formulas.md`：高点击标题公式和标签写法。
- `references/competitor-analysis.md`：竞品参考图拆解与保留/避开规则。
- `references/compliance-qc.md`：合规边界、失败重生成规则、验收测试。
- `references/generation-output.md`：生图 prompt 结构与多图变化方式。

## Generation Tool Priority

默认优先使用部署工具写入的 helper。只有在 helper 不存在、不可用、执行失败，或无法把结果稳定保存为本地文件并在对话中预览时，才使用内置 `image_gen` 作为最后兜底。不要使用 SDK 默认 key 或本地绘图脚本作为替代。

helper 解析顺序：

```text
$env:XINGHE_IMAGE_GENERATOR
%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1
```

接口规则：

- 有产品图、参考图、竞品图等参考图片时，调用 helper，并通过一个分号分隔字符串传给 `-ReferenceImage`；helper 会路由到 `https://xinghe.xin/v1/images/edits`。
- 没有参考图片、纯文本起图时，不传 `-ReferenceImage`；helper 会路由到 `https://xinghe.xin/v1/images/generations`。
- 模型固定使用部署工具配置的 `gpt-image-2`。
- API Key 使用部署工具安装时校验并写入的 key，不向用户询问，不在回复中输出、保存或复述真实 key。
- 完整生图提示词必须先写入 UTF-8 prompt 文件，再用 `-PromptFile` 调用；不要把长提示词直接拼到命令行。
- 多张参考图必须先合并成一个分号分隔字符串传给 `-ReferenceImage`；不要把 PowerShell 数组或多个逗号分隔路径直接传给 `-ReferenceImage`，避免后续参数被错绑成 `TimeoutSec` 等参数。
- 每张图单独调用一次 helper，保存到本地输出目录。
- 当需要生成多张图时，使用错峰并发提交：第 1 张 helper 调用提交后等待 3 秒，不等图片落盘，立即提交第 2 张；依次类推。所有任务提交后再统一等待完成并检查输出。单张图保持普通同步调用。
- helper 会输出本地绝对路径和 Markdown 图片预览；最终回复必须使用本地绝对路径展示图片。

PowerShell 示例：

```powershell
$helper = $env:XINGHE_IMAGE_GENERATOR
if (-not $helper) { $helper = Join-Path $env:LOCALAPPDATA 'ApiCodexOneClick\tools\generate-image.ps1' }
$promptFile = "<absolute prompt file path>"
$referenceImages = @("C:\path\to\product.png", "C:\path\to\reference.png")
$referenceImageArg = ($referenceImages -join ';')
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper `
  -PromptFile $promptFile `
  -ReferenceImage $referenceImageArg `
  -OutputDir "<absolute output directory>" `
  -Size "1024x1024" `
  -FileName "image-01.png"
```

无参考图时删除 `-ReferenceImage ...` 参数。

多张图并发提交示例：

```powershell
$serialFallback = $false
$jobs = @()
try {
  foreach ($task in $imageTasks) {
    $jobs += Start-Job -ScriptBlock {
      param($helper, $promptFile, $referenceImageArg, $outputDir, $size, $fileName)
      if ($referenceImageArg) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper -PromptFile $promptFile -ReferenceImage $referenceImageArg -OutputDir $outputDir -Size $size -FileName $fileName
      } else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper -PromptFile $promptFile -OutputDir $outputDir -Size $size -FileName $fileName
      }
    } -ArgumentList $helper, $task.PromptFile, $task.ReferenceImageArg, $task.OutputDir, $task.Size, $task.FileName
    Start-Sleep -Seconds 3
  }
  $jobs | Wait-Job | Out-Null
  $results = $jobs | Receive-Job -ErrorAction Stop
} catch {
  $serialFallback = $true
} finally {
  if ($jobs.Count -gt 0) {
    if ($serialFallback) { $jobs | Stop-Job -ErrorAction SilentlyContinue }
    $jobs | Remove-Job -Force -ErrorAction SilentlyContinue
  }
}
if ($serialFallback) {
  $results = @()
  foreach ($task in $imageTasks) {
    $outPath = Join-Path $task.OutputDir $task.FileName
    if (Test-Path -LiteralPath $outPath) { continue }
    if ($task.ReferenceImageArg) {
      $results += & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper -PromptFile $task.PromptFile -ReferenceImage $task.ReferenceImageArg -OutputDir $task.OutputDir -Size $task.Size -FileName $task.FileName
    } else {
      $results += & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper -PromptFile $task.PromptFile -OutputDir $task.OutputDir -Size $task.Size -FileName $task.FileName
    }
  }
}
```

并发提交时，每张图必须使用独立的 prompt 文件、输出文件名和输出路径记录；不要在提交下一张前等待上一张落盘。若并发调用失败或接口限流，再降级为逐张串行重试。

如果 helper 不存在或执行失败，不要改用 Pillow、matplotlib、SVG、canvas 或占位图。只有当前会话明确暴露可用的内置 `image_gen` 时才使用它作为最后兜底；否则报告 helper 缺失或执行失败。
