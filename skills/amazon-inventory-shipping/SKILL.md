---
name: amazon-inventory-shipping
description: Build Amazon replenishment, FBA shipment, and test-launch workbooks from connected store data or CSV/XLSX inputs. Supports weighted 7/15/30-day demand, actual shipped units after the last confirmed FBA receipt, fresh exact-match FBA competitor review, growth coefficients, healthy inventory, purchase quantity, express/air/sea bridging, and 1688 supplier enrichment. Use when the user asks for 补货数量、补货后销量、FBA同行竞品、备货计划、FBA发货数量、断货预测、运输拆分、测品发货表或按 SKU 生成补货 Excel。
---

# Amazon 补货与发货

只生成只读计划。不要自动采购、创建货件或修改 Amazon/广告状态。

在计算销量、库存或补货前排除标题、产品组或 SKU 命中 `pencil case/pouch`、`pen case/pouch/bag` 的记录。实物遗留库存只交给独立“历史遗留清退”，补货量固定为 0。

## 选择模型

1. **完整补货模型**：用户提供后台销量/库存或 7/15/30 天数据，并询问补货、断货或运输拆分时使用。
2. **极简测品模型**：表格包含 SKU、子 ASIN、上架日期和累计有效销量时使用；保留原 1 个/5 个规则。
3. **旧覆盖天数模型**：用户明确提供日销、提前期和安全库存天数时使用。
4. **1688 回填**：只在用户要求供应商、图片找同款或采购链接时执行。

读取 [references/input-schema.md](references/input-schema.md) 了解旧模型；完整补货读取 [references/replenishment-schema.md](references/replenishment-schema.md) 和 [references/replenishment-policy.md](references/replenishment-policy.md)。

## 完整补货工作流

1. 未指定店铺/站点时先列出并确认；每次只处理一个 `sellerId + marketplace`。
2. 店铺由 `${AMAZON_SELLER_ID}` 与 `marketplace` 显式指定；不要把示例账号写入 Skill，也不要自动遍历其他站点。
3. 分页读取 SKU 基础清单及近 7、15、30、90 天、前 15 天销量；有需要时补 60 天和去年同期。另读取最后一次实际 FBA 入仓记录，并统计入仓次日至运行日的已发货件数。SKU 主集合取基础清单、90 天窗口和库存数据的并集，不用单一窗口条数代替全店范围。
4. 已知 SKU 在某销售窗口无返回行时，该窗口销量记 0；库存字段缺失保持空值。
5. 不直接采用异常或缺失的后台 `salesVelocity`。
6. 先运行 `$amazon-inventory-clearance`，或导入其 `主状态`。前三类状态不得补货。
7. 使用统一模板 `assets/amazon-replenishment-template.xlsx` 补充成本、在途到仓日、周期、MOQ 和箱规。
8. 读取 `$amazon-competitor-monitor` 的最新精确同款证据。只有 4 天内、A级、精确变体确认、在售且 FBA 的竞品算有效 FBA 同行；不要在本 Skill 建第二套竞品匹配逻辑。
9. 运行确定性脚本：

```bash
NODE_PATH="<bundled-node-modules>" node scripts/generate_replenishment_plan.cjs \
  --input replenishment-input.xlsx \
  --output replenishment-plan-YYYYMMDD.xlsx \
  --as-of-date YYYY-MM-DD
```

库存运行器使用 JSON 证据时增加 `--receipts replenishment-receipts.json`；销量窗口同时提供 `windows.post_restock[seller_sku]`。

10. 检查公式、负数归零、MOQ/箱规取整、FBA 90 天上限、清货冲突、补货后销量门禁、FBA 竞品门禁和断货日期。
11. 读取 `$amazon-competitor-monitor` 已生成的 FBA 转仓风险结果，不在本 Skill
    内重新评分：
    - `HIGH`：保留 7 天/14 天原计算量，增加利润压力测试、缩量试单提示和人工数量复核；不得自动减量。
    - 已确认精确 A 级竞品 `FBM→FBA`：立即重算覆盖天数、竞争到手价和后续补货场景。
    - `PROVISIONAL/REVIEW`：只提示补 Seller ID、精确履约或冲突证据，不形成正式采购量变更。

## 极简测品与 1688 兼容流程

极简测品继续使用：

```bash
NODE_PATH="<bundled-node-modules>" node scripts/generate_minimal_shipping_plan.cjs \
  --input selected-products.xlsx \
  --output shipping-plan.xlsx \
  --as-of-date YYYY-MM-DD
```

供应商回填继续使用：

```bash
NODE_PATH="<bundled-node-modules>" node scripts/select_supplier_candidates.cjs \
  --plan shipping-plan.xlsx \
  --candidates supplier-candidates.xlsx \
  --output shipping-plan-with-suppliers.xlsx
```

读取 [references/1688-image-search.md](references/1688-image-search.md)。使用用户已登录的浏览器；遇到登录、滑块或验证码时标记人工确认。

## 决策纪律

- 清货状态优先，禁止同一 SKU 同时清货和采购。
- 利润缺失时只输出“暂定补货量”。
- 促销期无法剔除时降低置信度，不把促销峰值直接当长期日销。
- 补货结果为负时归零，并提示转清货检查。
- 当前项目不读取国内库存，也不把国内库存或生产中库存计入 `I`；生产周期固定为 0。
- 同时计算 7 天快速采购和 14 天保守采购两种场景，正式建议暂用 14 天。
- 每批记录下单日期和供应商可发日期；累计至少 5 批后，用实际采购周期第 80 百分位替换 14 天默认值。
- 发送 FBA 原则上不超过 90 天需求。
- 运输拆分只给建议数量与预计断货日，不创建货件。
- 竞品转 FBA 不等于本店应清货；只有正式清货主状态进入前三类时补货量才归零。
- 不得从货件名称或普通 `update_time` 猜入仓日期。系统实际入仓记录优先；缺失时可用 Vicky 明确确认并保存在唯一 `inventory-actions.json.replenishment_receipt_confirmations`。
- 入仓后不足 7 天保留暂定量但禁止 1688 加购；满 7 天实际发货为 0 时转“停补观察”并将 7/14 天量归零。
- 入仓证据缺失或冲突、FBA 履约未知、精确变体未确认、竞品证据超过 4 天时均禁止 1688 加购。
- 有效 FBA 精确同款不自动缩减模型量，但必须展示竞品证据并由 Vicky 通过当次 `preview_id` 确认数量。

## 输出要求

- 完整模型生成 `总览`、`补货建议`、`女包摘要`、`数据问题`、`规则参数`、`来源`；补货建议必须显示最后入仓、入仓后销量与 FBA 同款复核字段。
- 保留输入列、公式、参数、计算日期、置信度和取整影响。
- 旧模型继续生成原有发货表和 1688 字段，不改变列义。
