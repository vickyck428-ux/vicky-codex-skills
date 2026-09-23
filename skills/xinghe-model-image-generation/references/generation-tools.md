# Generation Tools

Read this file for direct model-image generation. Unless the user explicitly asks for prompts only, do not stop at a prompt pack.

## Priority

1. First attempt the deployment helper written by the installer for actual image generation.
2. Resolve the helper from `XINGHE_IMAGE_GENERATOR` first, then `%LOCALAPPDATA%\ApiCodexOneClick\tools\generate-image.ps1`.
3. The helper owns endpoint routing, model, API key handling, output saving, and Markdown preview output. Do not ask the user for a key.
4. Use built-in Codex `image_gen` only as the final fallback after the helper is missing, unavailable, fails, or cannot save/display the result.
5. Do not call built-in `image_gen` before resolving and attempting the helper.
6. Do not use local scripts, Pillow, SVG, canvas, local compositing, background replacement, text overlay, or stitching to create final delivered images.

## Helper Resolution

Resolve the helper at runtime:

```powershell
$helper = $env:XINGHE_IMAGE_GENERATOR
if (-not $helper) { $helper = Join-Path $env:LOCALAPPDATA 'ApiCodexOneClick\tools\generate-image.ps1' }
```

For reference-image generation, join all uploaded product/reference image paths with semicolons and pass the joined string to `-ReferenceImage`. Do not pass a PowerShell array or comma-separated multiple paths directly.

```powershell
$promptFile = "<absolute prompt file path>"
$referenceImages = @("C:\path\to\product-front.png", "C:\path\to\product-side.png")
$referenceImageArg = ($referenceImages -join ';')
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $helper `
  -PromptFile $promptFile `
  -ReferenceImage $referenceImageArg `
  -OutputDir "<absolute output directory>" `
  -Size "1024x1024" `
  -FileName "model-01.png"
```

For text-only generation, omit `-ReferenceImage`.

## Staggered Concurrent Helper Calls

For the default unified-model workflow, generate image 1 synchronously first as the saved `Model Identity Reference`. Do not submit images 2-8 until image 1 exists on disk and can be passed as a reference.

When generating the remaining images through the helper:

- Submit the first helper call as a background job.
- Wait 3 seconds.
- Submit the next helper call without waiting for the previous image to finish.
- Repeat until all planned images are submitted.
- After all jobs are submitted, wait for all jobs, collect output, and verify saved files.

Use one independent prompt file and one independent output filename per image. For images 2-8, pass both the original product image and the saved `Model Identity Reference` image when reference inputs are supported. If staggered concurrency fails, times out, or causes rate limits, retry failed images one by one with the same helper arguments.

## Save Output Rule

- After every successful generation, save the image to a local file path.
- The final response must list the absolute local path for each image.
- In chat surfaces that support image display, show each generated image with Markdown image syntax.
- If local files cannot be confirmed, do not claim image generation is complete. Explain the failure and keep the prompts available.

## Response Handling

The helper or endpoint may return an absolute path, Markdown image tag, URL, `b64_json`, or task ID. Convert the result into saved local files before delivery. If the result is a URL or base64 payload, save it into the output directory and verify the file exists.

Allowed post-processing is limited to downloading, copying, renaming, and checking dimensions/file existence. Do not locally assemble, retouch, crop-composite, stitch, overlay text, or repair generated files into final deliverables.

## Failure Handling

Deliver a prompt pack without images only when both generation paths have been attempted or resolved and neither can produce saved image files:

- The deployment helper is missing, unavailable, fails, cannot read credentials, cannot reach the network, or cannot save/display the result; and
- built-in `image_gen` is unavailable, fails, cannot reach the network, or cannot save/display the result.

Explain the failure briefly. Do not describe prompt-only output as completed image generation.
