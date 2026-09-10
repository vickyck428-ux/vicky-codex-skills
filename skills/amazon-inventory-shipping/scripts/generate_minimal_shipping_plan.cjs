#!/usr/bin/env node

const path = require("node:path");
const {
  Workbook,
  applyBaseTableStyle,
  columnLetter,
  exportWorkbook,
  findHeader,
  parseArgs,
  parseBoolean,
  parseDate,
  parseNumber,
  readTable,
} = require("./spreadsheet_helpers.cjs");

const FIELD_ALIASES = {
  sku: ["SKU", "sku", "商品SKU", "卖家SKU", "seller sku"],
  asin: ["ASIN", "asin", "子ASIN", "child_asin", "child asin"],
  launchDate: ["上架日期", "首次上架日期", "launch_date", "sale_start_date"],
  cumulativeUnits: [
    "累计有效出单件数",
    "累计出单量",
    "累计销量",
    "cumulative_valid_units",
    "cumulative_orders",
  ],
  currentStock: ["当前库存", "可售库存", "FBA库存", "current_stock"],
  inbound: ["在途数量", "在途库存", "inbound_on_way", "inbound"],
  selected: ["是否选中", "入选", "selected"],
};

const APPENDED_HEADERS = [
  "上架天数",
  "日均出单",
  "发货分档",
  "目标库存",
  "建议发货数量",
  "计算说明",
  "数据检查",
  "产品名称",
  "Amazon图片状态",
  "Amazon主图链接",
  "Amazon图片本地路径",
  "1688匹配状态",
  "1688供应商",
  "1688链接",
  "供应商价格",
  "起订量",
  "筛选说明",
];

function usage() {
  console.error(
    "Usage: generate_minimal_shipping_plan.cjs --input file.csv|xlsx --output file.xlsx [--as-of-date YYYY-MM-DD]",
  );
}

function isoToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

function cleanInputRows(rows, indexes) {
  return rows.filter((row) => indexes.selected < 0 || parseBoolean(row[indexes.selected], true));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input || !args.output) {
    usage();
    process.exitCode = 2;
    return;
  }

  const inputPath = path.resolve(args.input);
  const outputPath = path.resolve(args.output);
  const asOfDate = parseDate(args["as-of-date"] || isoToday());
  if (!asOfDate) throw new Error("--as-of-date must use YYYY-MM-DD.");

  const { headers, rows } = await readTable(inputPath);
  const indexes = {};
  for (const [field, aliases] of Object.entries(FIELD_ALIASES)) {
    indexes[field] = findHeader(headers, aliases);
  }

  const missing = ["sku", "asin", "launchDate", "cumulativeUnits"].filter(
    (field) => indexes[field] < 0,
  );
  if (missing.length) {
    throw new Error(`Missing required columns: ${missing.join(", ")}`);
  }

  const selectedRows = cleanInputRows(rows, indexes);
  const duplicateSkus = new Set();
  const seenSkus = new Set();
  for (const row of selectedRows) {
    const sku = String(row[indexes.sku] ?? "").trim().toLowerCase();
    if (sku && seenSkus.has(sku)) duplicateSkus.add(sku);
    seenSkus.add(sku);
  }

  const outputHeaders = [...headers, ...APPENDED_HEADERS.filter((header) => !headers.includes(header))];
  const outputRows = selectedRows.map((row) => {
    const padded = [...row, ...Array(Math.max(0, outputHeaders.length - row.length)).fill("")];
    const sku = String(row[indexes.sku] ?? "").trim().toLowerCase();
    const launchDate = parseDate(row[indexes.launchDate]);
    const issues = [];
    if (!String(row[indexes.sku] ?? "").trim()) issues.push("缺少SKU");
    const asin = String(row[indexes.asin] ?? "").trim();
    const validAsin = /^[A-Z0-9]{10}$/i.test(asin);
    if (!asin) issues.push("缺少ASIN");
    else if (!validAsin) issues.push("ASIN格式异常");
    if (!launchDate) issues.push("上架日期无效");
    else if (launchDate > asOfDate) issues.push("上架日期晚于计算日期");
    if (duplicateSkus.has(sku)) issues.push("SKU重复");
    for (const key of ["currentStock", "inbound", "cumulativeUnits"]) {
      if (indexes[key] >= 0 && parseNumber(row[indexes[key]]) < 0) issues.push("负数已按0处理");
    }
    if (launchDate) padded[indexes.launchDate] = launchDate;
    padded[outputHeaders.indexOf("数据检查")] = issues.length ? issues.join("；") : "通过";
    const amazonStatusIndex = outputHeaders.indexOf("Amazon图片状态");
    const supplierStatusIndex = outputHeaders.indexOf("1688匹配状态");
    if (!String(padded[amazonStatusIndex] ?? "").trim()) {
      padded[amazonStatusIndex] = validAsin ? "待抓取" : "抓取失败";
    }
    if (!String(padded[supplierStatusIndex] ?? "").trim()) {
      padded[supplierStatusIndex] = validAsin ? "待搜索" : "需要人工确认";
    }
    return padded;
  });

  const workbook = Workbook.create();
  const plan = workbook.worksheets.add("发货表");
  const rules = workbook.worksheets.add("规则说明");
  const matrix = [outputHeaders, ...outputRows];
  plan.getRangeByIndexes(0, 0, matrix.length, outputHeaders.length).values = matrix;

  const headerIndex = Object.fromEntries(outputHeaders.map((header, index) => [header, index]));
  const inputCol = (field) => columnLetter(indexes[field]);
  const calcCol = (header) => columnLetter(headerIndex[header]);
  const lastRow = outputRows.length + 1;

  for (let rowNumber = 2; rowNumber <= lastRow; rowNumber += 1) {
    const launch = `${inputCol("launchDate")}${rowNumber}`;
    const sales = `${inputCol("cumulativeUnits")}${rowNumber}`;
    const stock =
      indexes.currentStock >= 0 ? `${inputCol("currentStock")}${rowNumber}` : "0";
    const inbound = indexes.inbound >= 0 ? `${inputCol("inbound")}${rowNumber}` : "0";
    const days = `${calcCol("上架天数")}${rowNumber}`;
    const daily = `${calcCol("日均出单")}${rowNumber}`;
    const target = `${calcCol("目标库存")}${rowNumber}`;

    plan.getRange(`${calcCol("上架天数")}${rowNumber}`).formulas = [
      [`=IF(OR(${launch}="",${launch}>'规则说明'!$B$2),"",'规则说明'!$B$2-${launch}+1)`],
    ];
    plan.getRange(`${calcCol("日均出单")}${rowNumber}`).formulas = [
      [`=IF(${days}="","",IFERROR(MAX(0,${sales})/${days},0))`],
    ];
    plan.getRange(`${calcCol("发货分档")}${rowNumber}`).formulas = [
      [
        `=IF(${days}="","需要人工确认",IF(${days}<'规则说明'!$B$3,"测款1个",IF(${daily}>='规则说明'!$B$4,"好卖5个","低销量1个")))`,
      ],
    ];
    plan.getRange(`${calcCol("目标库存")}${rowNumber}`).formulas = [
      [
        `=IF(${days}="","",IF(${days}<'规则说明'!$B$3,'规则说明'!$B$5,IF(${daily}>='规则说明'!$B$4,'规则说明'!$B$6,'规则说明'!$B$5)))`,
      ],
    ];
    plan.getRange(`${calcCol("建议发货数量")}${rowNumber}`).formulas = [
      [`=IF(${target}="","",MAX(0,${target}-MAX(0,${stock})-MAX(0,${inbound})))`],
    ];
    plan.getRange(`${calcCol("计算说明")}${rowNumber}`).formulas = [
      [
        `=IF(${days}="","上架日期无效或晚于计算日期",IF(${days}<'规则说明'!$B$3,"上架不足7天，按1个测款",IF(${daily}>='规则说明'!$B$4,"日均出单达到0.2，目标库存5个","日均出单低于0.2，目标库存1个")))`,
      ],
    ];
  }

  rules.getRange("A1:B7").values = [
    ["规则参数", "当前值"],
    ["计算日期", asOfDate],
    ["测款观察天数", 7],
    ["好卖日均阈值", 0.2],
    ["低销量目标库存", 1],
    ["好卖目标库存", 5],
    ["异常低价阈值", 0.6],
  ];
  rules.getRange("D1:D6").values = [
    ["使用说明"],
    ["只需填写 SKU、ASIN、上架日期、累计有效出单件数。"],
    ["当前库存和在途数量可留空，按0处理。"],
    ["累计出单按件数统计，排除取消订单。"],
    ["Amazon与1688失败的行会保留并标记人工确认。"],
    ["本表仅提供采购参考，不自动下单。"],
  ];

  applyBaseTableStyle(plan, outputRows.length + 1, outputHeaders.length - 1);
  applyBaseTableStyle(rules, 7, 3);
  if (lastRow >= 2) {
    plan.getRange(`${calcCol("日均出单")}2:${calcCol("日均出单")}${lastRow}`).format.numberFormat =
      "0.000";
    plan.getRange(`${inputCol("launchDate")}2:${inputCol("launchDate")}${lastRow}`).format.numberFormat =
      "yyyy-mm-dd";
    plan.getRange(`${calcCol("供应商价格")}2:${calcCol("供应商价格")}${lastRow}`).format.numberFormat =
      "0.00";
    plan.getRange(`${calcCol("起订量")}2:${calcCol("起订量")}${lastRow}`).format.numberFormat =
      "#,##0";
  }
  rules.getRange("B2").format.numberFormat = "yyyy-mm-dd";
  rules.getRange("B4").format.numberFormat = "0.0";
  rules.getRange("B7").format.numberFormat = "0%";
  plan.getRange("A1:B" + lastRow).format.columnWidth = 16;
  plan.getRange("C1:C" + lastRow).format.columnWidth = 13;
  plan.getRange("D1:D" + lastRow).format.columnWidth = 18;
  plan.getRange("E1:F" + lastRow).format.columnWidth = 12;
  plan.getRange("G1:H" + lastRow).format.columnWidth = 22;
  plan.getRange("I1:M" + lastRow).format.columnWidth = 13;
  plan.getRange("N1:N" + lastRow).format.columnWidth = 30;
  plan.getRange("O1:O" + lastRow).format.columnWidth = 20;
  plan.getRange("P1:P" + lastRow).format.columnWidth = 24;
  plan.getRange("Q1:Q" + lastRow).format.columnWidth = 16;
  plan.getRange("R1:S" + lastRow).format.columnWidth = 28;
  plan.getRange("T1:U" + lastRow).format.columnWidth = 18;
  plan.getRange("V1:V" + lastRow).format.columnWidth = 36;
  plan.getRange("W1:X" + lastRow).format.columnWidth = 13;
  plan.getRange("Y1:Y" + lastRow).format.columnWidth = 38;
  plan.getRange(`N1:N${lastRow}`).format.wrapText = true;
  plan.getRange(`R1:S${lastRow}`).format.wrapText = true;
  plan.getRange(`V1:V${lastRow}`).format.wrapText = true;
  plan.getRange(`Y1:Y${lastRow}`).format.wrapText = true;
  if (lastRow >= 2) plan.getRange(`A2:Y${lastRow}`).format.rowHeight = 44;
  rules.getRange("A1:D7").format.autofitColumns();
  rules.getRange("D1:D6").format.columnWidth = 48;
  rules.getRange("D1:D6").format.wrapText = true;

  if (outputRows.length > 0) {
    plan.tables.add(
      `A1:${columnLetter(outputHeaders.length - 1)}${outputRows.length + 1}`,
      true,
      "ShippingPlanTable",
    );
  }

  await exportWorkbook(workbook, outputPath);
  console.log(`Wrote ${outputRows.length} selected rows to ${outputPath}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
