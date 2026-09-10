#!/usr/bin/env node

const path = require("node:path");
const {
  Workbook,
  applyBaseTableStyle,
  exportWorkbook,
  parseArgs,
} = require("./spreadsheet_helpers.cjs");

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.output) {
    throw new Error("Usage: build_minimal_template.cjs --output template.xlsx");
  }

  const workbook = Workbook.create();
  const input = workbook.worksheets.add("选品输入");
  const rules = workbook.worksheets.add("填写说明");
  const headers = [
    "SKU",
    "ASIN",
    "上架日期",
    "累计有效出单件数",
    "当前库存",
    "在途数量",
    "规格备注",
    "产品图片",
  ];
  input.getRange("A1:H4").values = [
    headers,
    ["", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
  ];
  input.tables.add("A1:H4", true, "MinimalSelectionTable");
  applyBaseTableStyle(input, 4, 7);
  input.getRange("C2:C4").format.numberFormat = "yyyy-mm-dd";
  input.getRange("D2:F4").format.numberFormat = "#,##0";
  input.getRange("A1:B4").format.columnWidth = 18;
  input.getRange("C1:C4").format.columnWidth = 14;
  input.getRange("D1:F4").format.columnWidth = 17;
  input.getRange("G1:H4").format.columnWidth = 24;
  input.getRange("G1:H4").format.wrapText = true;

  rules.getRange("A1:C10").values = [
    ["字段", "是否必填", "怎么填"],
    ["SKU", "必填", "一个具体颜色/尺寸/套装一行"],
    ["ASIN", "必填", "Amazon美国站子ASIN，不填父ASIN"],
    ["上架日期", "必填", "该SKU第一次可销售的日期"],
    ["累计有效出单件数", "必填", "按件数统计，排除取消订单"],
    ["当前库存", "选填", "留空按0处理"],
    ["在途数量", "选填", "留空按0处理"],
    ["规格备注", "选填", "颜色、尺寸、材质、套装数量"],
    ["产品图片", "选填", "Amazon抓图失败时作为备用"],
    ["发货规则", "自动", "不足7天目标1个；满7天且日均≥0.2目标5个；再扣库存和在途"],
  ];
  applyBaseTableStyle(rules, 10, 2);
  rules.getRange("A1:C10").format.autofitColumns();
  rules.getRange("C1:C10").format.columnWidth = 54;
  rules.getRange("C1:C10").format.wrapText = true;
  rules.getRange("A10:C10").format.rowHeight = 42;

  await exportWorkbook(workbook, path.resolve(args.output));
  console.log(`Wrote template to ${path.resolve(args.output)}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
