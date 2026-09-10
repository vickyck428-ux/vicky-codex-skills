#!/usr/bin/env node

const path = require("node:path");
const {
  Workbook,
  applyBaseTableStyle,
  columnLetter,
  exportWorkbook,
  parseArgs,
} = require("./spreadsheet_helpers.cjs");

const HEADERS = [
  "seller_sku", "asin", "product_title", "product_group", "is_womens_bag", "clearance_status",
  "units_7d", "units_15d", "units_30d", "units_90d", "units_prev_15d",
  "seasonal_product", "yoy_growth_ratio", "b1_override", "b2_override", "promotion_overlap", "supply_instock",
  "supply_reserved", "supply_inbound", "inbound_ready_date", "supply_total",
  "unit_contribution", "long_tail_approved",
  "last_fba_receipt_date", "last_fba_receipt_units", "post_restock_units",
  "receipt_evidence_status", "receipt_evidence_source", "receipt_confirmed_at",
  "fba_competitor_check_status", "confirmed_fba_competitor_count",
  "lowest_fba_competitor_landed_price", "fastest_fba_competitor_delivery_days",
  "fba_competitor_evidence",
  "procurement_days", "prep_days", "review_cycle_days", "safety_factor", "express_days",
  "air_days", "sea_days", "express_cost_per_unit", "air_cost_per_unit",
  "sea_cost_per_unit", "moq", "carton_qty",
];

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.output) throw new Error("Usage: build_replenishment_template.cjs --output template.xlsx");
  const workbook = Workbook.create();
  const input = workbook.worksheets.add("SKU补货输入");
  const guide = workbook.worksheets.add("填写说明");
  const rules = workbook.worksheets.add("课程公式");
  const blankRows = Array.from({ length: 15 }, () => Array(HEADERS.length).fill(""));
  input.getRangeByIndexes(0, 0, 16, HEADERS.length).values = [HEADERS, ...blankRows];
  const lastColumn = columnLetter(HEADERS.length - 1);
  input.tables.add(`A1:${lastColumn}16`, true, "ReplenishmentInputTable");
  applyBaseTableStyle(input, 16, HEADERS.length - 1);
  input.getRange(`A1:${lastColumn}1`).format.rowHeight = 64;
  input.freezePanes.freezeColumns(2);
  input.getRange("A1:F16").format.columnWidth = 18;
  input.getRange("C1:C16").format.columnWidth = 38;
  input.getRange(`G1:${lastColumn}16`).format.columnWidth = 14;
  input.getRange(`A1:${lastColumn}16`).format.wrapText = true;
  input.getRange("E2:E16").dataValidation = { rule: { type: "list", values: ["是", "否", "待确认"] } };
  input.getRange("F2:F16").dataValidation = {
    rule: { type: "list", values: ["紧急清退", "主动清货", "停补观察", "健康维持", "待补货"] },
  };
  input.getRange("L2:L16").dataValidation = { rule: { type: "list", values: ["是", "否"] } };
  input.getRange("P2:P16").dataValidation = { rule: { type: "list", values: ["是", "否"] } };
  input.getRange("W2:W16").dataValidation = { rule: { type: "list", values: ["是", "否"] } };
  input.getRange("T2:T16").format.numberFormat = "yyyy-mm-dd";
  input.getRange("X2:X16").format.numberFormat = "yyyy-mm-dd";
  input.getRange("AC2:AC16").format.numberFormat = "yyyy-mm-dd";
  input.getRange("AA2:AA16").dataValidation = { rule: { type: "list", values: ["SYSTEM_CONFIRMED", "USER_CONFIRMED", "UNVERIFIED"] } };
  input.getRange("AD2:AD16").dataValidation = { rule: { type: "list", values: ["COMPLETE_NO_FBA_EXACT_COMPETITOR", "FBA_EXACT_COMPETITOR_FOUND", "INCOMPLETE"] } };

  guide.getRange("A1:D14").values = [
    ["模块", "字段", "填写原则", "缺失后果"],
    ["清货冲突", "clearance_status", "先运行清货Skill；前三种状态禁止补货", "空白时只能给初步建议"],
    ["销量", "7/15/30天与前15天", "累计窗口；无销量填0，读取失败留空", "日销置信度下降"],
    ["季节", "seasonal / yoy / B1-B2覆盖", "季节款优先同比；明确预测可分别覆盖B1、B2", "改用15天环比"],
    ["促销", "promotion_overlap", "统计窗口重叠促销时填是", "补货量标低置信度"],
    ["FBA库存", "instock/reserved/inbound/total", "货件接口有可靠ETA时记录日期；无ETA时做保守/及时到达敏感性", "库存缺失不得猜0"],
    ["利润", "unit_contribution", "已扣Amazon费用、广告和成本的单件贡献", "数量只能暂定"],
    ["补货后销量", "last_fba_receipt_* / post_restock_units", "只填实际入仓日、入仓件数及入仓次日至计算日的已发货件数", "缺失、冲突或不足7天禁止加购；满7天0销量归零"],
    ["FBA竞品", "fba_competitor_*", "复用竞品监控：4天内A级精确同款、精确变体、在售且FBA", "检查不完整禁止加购；发现同款须人工复核数量"],
    ["周期", "C/D/F/N", "使用真实采购、处理、复查和安全系数", "空白使用课程案例"],
    ["运输", "express/air/sea days", "均填到仓可售时间，不是纯运输时间", "运输拆分失真"],
    ["取整", "moq / carton_qty", "先算净需求，再向上取整", "不做取整"],
    ["FBA上限", "90天需求", "长期缓冲优先留国内", "避免形成新积压"],
    ["执行", "全部输出", "本Skill只读，不采购、不创建货件", "必须人工确认"],
  ];
  applyBaseTableStyle(guide, 14, 3);
  guide.getRange("A1:B14").format.columnWidth = 24;
  guide.getRange("C1:D14").format.columnWidth = 54;
  guide.getRange("A1:D14").format.wrapText = true;

  rules.getRange("A1:B9").values = [
    ["公式/规则", "表达"],
    ["加权日销A", "最近7天50% + 第8–15天30% + 第16–30天20%"],
    ["健康库存H", "A × B1 × (C + D + E) × N"],
    ["补货Q", "max(0, A × B2 × F + H − I)"],
    ["成长系数", "B1限制0.8–1.2；B2限制0.7–1.3"],
    ["安全系数", "稳定1.1；普通多变体1.2；波动/长周期1.3；上限1.4"],
    ["状态优先", "清货状态优先于补货；利润缺失仅输出暂定量"],
    ["补货后销量门禁", "入仓次日起观察；不足7天暂定，满7天0发货转停补观察并归零"],
    ["FBA竞品门禁", "证据≤4天；A级精确同款FBA保留原量但必须人工复核；证据不完整禁止加购"],
  ];
  applyBaseTableStyle(rules, 9, 1);
  rules.getRange("A1:A9").format.columnWidth = 26;
  rules.getRange("B1:B9").format.columnWidth = 74;
  rules.getRange("A1:B9").format.wrapText = true;

  await exportWorkbook(workbook, path.resolve(args.output));
  console.log(`Wrote replenishment template to ${path.resolve(args.output)}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
