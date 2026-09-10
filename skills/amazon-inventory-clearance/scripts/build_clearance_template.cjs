#!/usr/bin/env node

const path = require("node:path");
const { NORMALIZED_HEADERS } = require("./prepare_clearance_input.cjs");
const {
  Workbook,
  applyTableStyle,
  columnLetter,
  exportWorkbook,
  parseArgs,
} = require("./spreadsheet_helpers.cjs");

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.output) throw new Error("Usage: build_clearance_template.cjs --output template.xlsx");
  const workbook = Workbook.create();
  const input = workbook.worksheets.add("SKU配置与快照");
  const guide = workbook.worksheets.add("填写说明");
  const age = workbook.worksheets.add("库龄导入说明");
  const lastColumn = columnLetter(NORMALIZED_HEADERS.length - 1);
  const blankRows = Array.from({ length: 15 }, () =>
    Array(NORMALIZED_HEADERS.length).fill(null),
  );

  input
    .getRangeByIndexes(0, 0, blankRows.length + 1, NORMALIZED_HEADERS.length)
    .values = [NORMALIZED_HEADERS, ...blankRows];
  input.tables.add(`A1:${lastColumn}16`, true, "InventoryClearanceInput");
  applyTableStyle(input, 16, NORMALIZED_HEADERS.length - 1);
  input.getRange(`A1:${lastColumn}1`).format.rowHeight = 68;
  input.getRange("A1:B16").format.columnWidth = 18;
  input.getRange("C1:C16").format.columnWidth = 42;
  input.getRange(`D1:${lastColumn}16`).format.columnWidth = 15;
  input.getRange(`A1:${lastColumn}16`).format.wrapText = true;
  for (const header of [
    "next_fee_snapshot_date",
    "inventory_snapshot_date",
    "age_snapshot_date",
    "sales_window_end_date",
  ]) {
    const index = NORMALIZED_HEADERS.indexOf(header);
    input
      .getRange(`${columnLetter(index)}2:${columnLetter(index)}16`)
      .format.numberFormat = "yyyy-mm-dd";
  }
  const womenColumn = columnLetter(NORMALIZED_HEADERS.indexOf("is_womens_bag"));
  input.getRange(`${womenColumn}2:${womenColumn}16`).dataValidation = {
    rule: { type: "list", values: ["是", "否", "待确认"] },
  };
  for (const header of [
    "long_tail_approved",
    "inventory_report_present",
    "age_report_present",
    "cost_data_present",
    "api_inventory_suspect",
    "api_inventory_mismatch",
  ]) {
    const column = columnLetter(NORMALIZED_HEADERS.indexOf(header));
    input.getRange(`${column}2:${column}16`).dataValidation = {
      rule: { type: "list", values: ["是", "否"] },
    };
  }

  guide.getRange("A1:D16").values = [
    ["模块", "必填程度", "字段/模式", "填写原则"],
    ["推荐模式", "首选", "--api-json + FBA库存报告 + 库龄报告", "脚本自动按SKU并集合并；成本表可选"],
    ["兼容模式", "可选", "--input 标准表", "继续支持手工准备CSV/XLSX"],
    ["身份", "必填", "seller_sku", "一个具体变体一行；后台合并主键"],
    ["范围", "女包分析需确认", "product_group / is_womens_bag", "自动分类不确定时保留待确认"],
    ["销量", "后台读取", "7/15/30/60/90天及前15天", "已知SKU无返回行记0；不使用异常salesVelocity"],
    ["FBA库存", "权威来源", "可售/预留/在途/总量", "只采用FBA库存报告；缺行保持空白"],
    ["API库存", "仅诊断", "api_supply_*", "只对账；999/1000等疑似占位值隔离"],
    ["库龄", "风险判断", "oldest_age_days / age buckets", "从Inventory Age/Health报告导入"],
    ["费用日", "运行时核实", "next_fee_snapshot_date", "缺失时生成受限预警版"],
    ["成本", "可选", "成本/费用/贡献利润", "缺失时数量标暂定，不承诺净回收"],
    ["周期", "默认可覆盖", "C/D/E/F/N", "空白时使用课程默认值7/2/35/7/1.2"],
    ["数量拆分", "自动", "潜在超量/费用风险/清货目标", "仅紧急清退、主动清货产生清货目标"],
    ["数量状态", "自动", "已计算/暂定/人工确认", "缺库存时清货目标留空"],
    ["旧库存", "课程口径", "110–115天", "预警线，不是Amazon强制线"],
    ["写操作", "禁止", "调价/促销/移除/清算/广告", "工作簿只读建议，执行必须另行人工审批"],
  ];
  applyTableStyle(guide, 16, 3);
  guide.getRange("A1:C16").format.columnWidth = 22;
  guide.getRange("D1:D16").format.columnWidth = 66;
  guide.getRange("A1:D16").format.wrapText = true;
  guide.getRange("A2:D16").format.rowHeight = 36;

  age.getRange("A1:C13").values = [
    ["字段", "说明", "缺失处理"],
    ["oldest_age_days", "最老库存天数；自动模式使用最高非零库龄分段下限", "留空并降低风险判断置信度"],
    ["aged_110_plus_units", "课程预警区数量", "无法可靠获取时留空"],
    ["next_snapshot_aged_units", "下一费用快照预计进入计费区数量", "自动模式汇总报告计费数量字段"],
    ["aged_181_210", "181–210天库存", "0只能代表报告明确为0"],
    ["aged_211_240", "211–240天库存", "同上"],
    ["aged_241_270", "241–270天库存", "同上"],
    ["aged_271_300", "271–300天库存", "同上"],
    ["aged_301_330 / aged_331_365", "分段老库存", "同上"],
    ["aged_365_plus", "365天以上库存", "同上"],
    ["estimated_aged_surcharge", "报告预计附加费", "不自行套费率"],
    ["age_report_present", "SKU是否在库龄报告中有行", "否时状态限制为停补观察"],
    ["next_fee_snapshot_date", "当前站点费用快照日", "每次运行重新核实，禁止写死"],
  ];
  applyTableStyle(age, 13, 2);
  age.getRange("A1:A13").format.columnWidth = 34;
  age.getRange("B1:C13").format.columnWidth = 54;
  age.getRange("A1:C13").format.wrapText = true;
  age.getRange("A2:C13").format.rowHeight = 34;

  await exportWorkbook(workbook, path.resolve(args.output));
  console.log(`Wrote clearance template to ${path.resolve(args.output)}`);
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exitCode = 1;
});
