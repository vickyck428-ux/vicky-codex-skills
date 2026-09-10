---
name: lc-1688-purchase-shipping
description: Turn post-purchase 1688 order screenshots into a reviewed, image-complete purchase and shipping manifest, then idempotently upsert it to the dedicated Feishu Base only after explicit confirmation. Use when the user sends 1688 order, payment, or logistics screenshots or asks to 录入1688采购、整理1688订单截图、生成采购发货表、记录待付款商品. Do not use for 1688 product links, Excel/CSV store exports, product selection, listing generation, or market research; route those to lc-1688-product-import.
---

# 1688采购发货

## 守住职责边界

- 只处理订货后的 1688 截图：订单列表、订单详情、待付款、待发货、物流和收货页面。
- 将待付款订单默认纳入采购台账，并把 `采购状态` 设为 `待付款`。
- 将购物车、收藏、纯商品详情页默认排除；只有用户明确说已经购买或要求计入时才纳入。
- 遇到 1688 链接、Excel、CSV、整店导出或选品任务时停止本流程，改用 `$lc-1688-product-import`。
- 把飞书多维表格视为唯一主账。用户在表内选择 Amazon、Walmart 或拆分后，不再执行第二次“同步”。

## 执行工作流

### 1. 建立截图批次

1. 收集用户明确归为同一批的原始截图，不修改原文件。
2. 使用 `scripts/manifest_tool.py fingerprint` 计算截图批次指纹。
3. 识别订单状态、付款状态、供应商、订单号、商品名称、规格和数量。
4. 对滚动截图的重叠区域去重。购物车或详情页中出现、但订单区没有证据的商品记入 `excluded`，不要放进 `items`。
5. 每种颜色、款式、尺寸各占一行。相同外观仅尺寸不同可以复用主图，规格仍必须分行。

### 2. 裁取商品图并建立清单

1. 从订单截图或补充的商品详情截图中，为每行裁出无订单文字、按钮和其他商品的干净商品图。
2. 不同外观必须使用不同图片；禁止把整张订单截图当作 `商品主图`。
3. 保留每行对应的 `源订单截图`。到货后可补充 `到货实拍`。
4. 按 `references/manifest-schema.md` 建立 JSON 清单。
5. 运行：

   ```bash
   python3 scripts/manifest_tool.py prepare manifest.json --output manifest.prepared.json
   python3 scripts/manifest_tool.py validate manifest.prepared.json --require-images
   python3 scripts/manifest_tool.py summary manifest.prepared.json
   ```

6. 标题、规格、数量、商品图对应关系不可靠时，给该行增加阻塞性 `issues`。数量不确定或缺少对应商品图时，不得把该行视为录入完成。

### 3. 生成确认预览

1. 运行 `scripts/build_preview.sh --manifest manifest.prepared.json --output-dir preview`。
2. 向用户提供：
   - 每行一张商品卡；
   - 分页汇总预览；
   - 结构化清单；
   - 总行数、总件数、待付款行数/件数、排除项和所有识别疑点。
3. 在预览中显示商品名称、规格、数量、采购状态、供应商和疑点；商品主图附件仍使用无文字干净裁图。
4. 用户修改任何识别结果后，重新 `prepare`、`validate` 和生成预览。

### 4. 等待明确确认

未收到用户明确表达“确认写入”“确认填写”“可以写入飞书”或同等含义前，禁止创建、更新、删除飞书记录或附件。

只确认“识别正确”“看起来可以”等模糊表述时，继续展示预览并请求明确写入确认。

### 5. 幂等写入飞书

用户明确确认后：

1. 使用 `$lark-base`，并完整读取 `references/base-schema.md`。
2. 通过 Base URL 实时解析 Base、数据表、字段和视图；禁止硬编码可变化的字段 ID。
3. 运行 `manifest_tool.py payload` 生成写入载荷。以 `明细ID` 为唯一匹配键：
   - 已存在：更新原记录；
   - 不存在：新增记录；
   - 同一 `明细ID` 命中多行：停止并报告数据异常。
4. 先写文字、数字、单选和日期字段，再逐行上传 `商品主图` 与 `源订单截图`。
5. 附件上传超时或网络失败时，先读回该附件单元格；确认目标文件未出现后再重试，避免重复附件。
6. 不写入公式字段。若实时结构与参考结构不一致，先只读检查；需要改结构时必须另行预览变更并取得明确确认。

### 6. 写后核验

逐项核验并向用户报告：

- 写入行数、更新数、新增数和总件数；
- `明细ID` 唯一且无重复；
- 每行 `商品主图` 和 `源订单截图` 都有附件；
- 待付款记录进入 `00 待付款`；
- 缺图记录进入 `01 缺少商品图`，且不进入正常待发流程；
- 数量异常进入 `03 数量异常`；
- Amazon、Walmart 和拆分记录进入对应待发视图；
- 重复提交同一批截图只更新，不重复新增。

## 明细ID规则

- 若清单已持久化 `detail_id`，始终保留，便于兼容已写入的历史记录。
- 有订单号时，使用订单号、商品签名和同款重复序号生成稳定 ID。
- 无订单号时，使用截图批次指纹、商品签名和同款重复序号生成稳定 ID。
- 商品签名使用供应商、商品名称和规格，不包含数量，因此修正数量仍会更新原记录。
- 对同一商品签名的重复行，先人工排除滚动重叠；确认确属两笔明细后再设置不同 `occurrence_index`。

## 失败与恢复

- OCR 或视觉识别无法可靠判断时，要求补发订单详情或清晰商品图，不用模糊图凑数。
- 飞书字段缺失、类型不符或单选项不兼容时停止写入，报告准确字段名和需要的修复。
- 部分写入后中断时，按 `明细ID` 读回并继续缺失部分；不要整批盲目重写。
- 运行测试、演练或重复导入检查时默认使用 dry-run 和只读查询，除非用户再次明确授权正式写入。

## 资源

- `references/manifest-schema.md`：截图识别清单格式、疑点和排除项规则。
- `references/base-schema.md`：飞书主账、字段语义、状态与固定视图。
- `scripts/manifest_tool.py`：批次指纹、稳定 ID、清单校验、汇总和飞书载荷。
- `scripts/build_preview.sh`：独立商品卡和分页预览图。
- `scripts/test_manifest_tool.py`：无网络单元测试。
