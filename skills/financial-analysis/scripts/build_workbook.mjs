import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

function money(value) {
  return typeof value === "number" ? value : 0;
}

function pct(value) {
  return typeof value === "number" ? value : null;
}

function fitColumns(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 4000, 1).format.columnWidth = width;
  });
}

function styleTitle(range) {
  range.format.fill = "#A84C42";
  range.format.font = { color: "#FFFFFF", bold: true, size: 18 };
  range.format.horizontalAlignment = "Left";
  range.format.verticalAlignment = "Center";
}

function styleSection(range) {
  range.format.fill = "#F4E6D7";
  range.format.font = { color: "#4A2E24", bold: true, size: 11 };
  range.format.borders = { preset: "outside", style: "thin", color: "#D7C2B2" };
}

function styleHeader(range) {
  range.format.fill = "#E8F0EE";
  range.format.font = { color: "#1F2933", bold: true, size: 10 };
  range.format.borders = { preset: "all", style: "thin", color: "#DCE3E8" };
}

function styleBody(range) {
  range.format.borders = { preset: "inside", style: "thin", color: "#EDF1F4" };
  range.format.font = { color: "#1F2933", size: 10 };
}

function setNumberFormat(range, format) {
  range.setNumberFormat(format);
}

async function main() {
  const [, , analysisPath, outputPath] = process.argv;
  if (!analysisPath || !outputPath) {
    throw new Error("Usage: node build_workbook.mjs <analysis.json> <output.xlsx>");
  }

  const analysis = JSON.parse(await fs.readFile(analysisPath, "utf8"));
  const workbook = Workbook.create();

  const summary = workbook.worksheets.add("Summary");
  const skuSheet = workbook.worksheets.add("SKU Analysis");
  const detailSheet = workbook.worksheets.add("Detail");
  const typeSheet = workbook.worksheets.add("Type Analysis");
  const riskSheet = workbook.worksheets.add("Risk Review");

  summary.showGridLines = false;
  summary.getRange("A1:F2").merge();
  summary.getRange("A1").values = [["Amazon Finance Profit Dashboard"]];
  styleTitle(summary.getRange("A1:F2"));

  summary.getRange("A4:B4").values = [["核心指标", "结果"]];
  styleSection(summary.getRange("A4:B4"));

  const summaryRows = [
    ["Amazon结算净额", money(analysis.summary.amazon_total)],
    ["产品成本影响", money(analysis.summary.product_cost_impact)],
    ["头程成本影响", money(analysis.summary.first_leg_cost_impact)],
    ["流水毛利", money(analysis.summary.gross_profit)],
    ["毛利率", pct(analysis.summary.gross_margin)],
    ["未匹配成本行数", analysis.summary.missing_cost_rows],
    ["亏损SKU数", analysis.summary.loss_skus],
    ["低毛利SKU数", analysis.summary.low_margin_skus],
    ["高退货SKU数", analysis.summary.high_return_skus],
    ["缺成本SKU数", analysis.summary.missing_cost_skus],
  ];
  summary.getRange(`A5:B${4 + summaryRows.length}`).values = summaryRows;
  styleBody(summary.getRange(`A5:B${4 + summaryRows.length}`));
  setNumberFormat(summary.getRange("B5:B8"), '"$"#,##0.00');
  setNumberFormat(summary.getRange("B9"), "0.0%");
  setNumberFormat(summary.getRange("B10:B14"), "0");

  summary.getRange("D4:F4").values = [["自动洞察", "", ""]];
  summary.getRange("D4:F4").merge();
  styleSection(summary.getRange("D4:F4"));
  const insightRows = analysis.insights.length ? analysis.insights : ["暂无自动洞察。"];
  summary.getRange(`D5:F${4 + insightRows.length}`).merge(true);
  summary.getRange(`D5:F${4 + insightRows.length}`).values = insightRows.map((item) => [item, null, null]);
  summary.getRange(`D5:F${4 + insightRows.length}`).format.wrapText = true;
  styleBody(summary.getRange(`D5:F${4 + insightRows.length}`));

  summary.getRange("A18:F18").values = [["类型", "行数", "Amazon净额", "流水毛利", "", ""]];
  summary.getRange("A18:D18").format.fill = "#E8F0EE";
  summary.getRange("A18:D18").format.font = { bold: true, color: "#1F2933" };
  styleHeader(summary.getRange("A18:D18"));
  const typeRows = analysis.type_summary.slice(0, 8).map((row) => [
    row.type,
    row.rows,
    money(row.amazon_total),
    money(row.gross_profit),
  ]);
  if (typeRows.length) {
    summary.getRange(`A19:D${18 + typeRows.length}`).values = typeRows;
    styleBody(summary.getRange(`A19:D${18 + typeRows.length}`));
    setNumberFormat(summary.getRange(`C19:D${18 + typeRows.length}`), '"$"#,##0.00');
  }

  summary.getRange("A32:F32").values = [["Top SKU", "订单数", "净件数", "流水毛利", "毛利率", "退货率"]];
  styleHeader(summary.getRange("A32:F32"));
  const skuTopRows = analysis.sku_summary.slice(0, 10).map((row) => [
    row.sku,
    row.orders,
    row.net_units,
    money(row.gross_profit),
    pct(row.gross_margin),
    pct(row.return_rate),
  ]);
  if (skuTopRows.length) {
    summary.getRange(`A33:F${32 + skuTopRows.length}`).values = skuTopRows;
    styleBody(summary.getRange(`A33:F${32 + skuTopRows.length}`));
    setNumberFormat(summary.getRange(`D33:D${32 + skuTopRows.length}`), '"$"#,##0.00');
    setNumberFormat(summary.getRange(`E33:F${32 + skuTopRows.length}`), "0.0%");
  }

  fitColumns(summary, [24, 18, 18, 22, 22, 18]);
  summary.freezePanes.freezeRows(4);

  skuSheet.getRange("A1:O1").values = [[
    "SKU",
    "风险等级",
    "风险标签",
    "订单数",
    "退款数",
    "出库件数",
    "退回件数",
    "净件数",
    "销售额",
    "Amazon净额",
    "流水毛利",
    "毛利率",
    "退货率",
    "单件利润",
    "缺成本行数",
  ]];
  styleHeader(skuSheet.getRange("A1:O1"));
  const skuRows = analysis.sku_summary.map((row) => [
    row.sku,
    row.risk_level,
    row.risk_tags.join(" / "),
    row.orders,
    row.refunds,
    row.order_units,
    row.refund_units,
    row.net_units,
    money(row.product_sales),
    money(row.amazon_total),
    money(row.gross_profit),
    pct(row.gross_margin),
    pct(row.return_rate),
    money(row.profit_per_unit),
    row.missing_cost_rows,
  ]);
  if (skuRows.length) {
    skuSheet.getRange(`A2:O${1 + skuRows.length}`).values = skuRows;
    styleBody(skuSheet.getRange(`A2:O${1 + skuRows.length}`));
    setNumberFormat(skuSheet.getRange(`I2:K${1 + skuRows.length}`), '"$"#,##0.00');
    setNumberFormat(skuSheet.getRange(`L2:M${1 + skuRows.length}`), "0.0%");
    setNumberFormat(skuSheet.getRange(`N2:N${1 + skuRows.length}`), '"$"#,##0.00');
    setNumberFormat(skuSheet.getRange(`O2:O${1 + skuRows.length}`), "0");
    skuSheet.getRange(`B2:B${1 + skuRows.length}`).conditionalFormats.add("containsText", {
      text: "高风险",
      format: { fill: "#FDE8E6", font: { color: "#A7372F", bold: true } },
    });
    skuSheet.getRange(`B2:B${1 + skuRows.length}`).conditionalFormats.add("containsText", {
      text: "关注",
      format: { fill: "#FFF0D8", font: { color: "#9A5A18", bold: true } },
    });
  }
  fitColumns(skuSheet, [24, 11, 20, 10, 10, 10, 10, 10, 14, 16, 16, 10, 10, 14, 12]);
  skuSheet.freezePanes.freezeRows(1);

  detailSheet.getRange("A1:N1").values = [[
    "Date/Time",
    "Type",
    "Order ID",
    "SKU",
    "Quantity",
    "Product Sales",
    "Amazon Total",
    "Action",
    "Unit Product Cost",
    "Unit First-Leg Cost",
    "Product Cost Impact",
    "First-Leg Cost Impact",
    "Gross Profit",
    "Cost Found",
  ]];
  styleHeader(detailSheet.getRange("A1:N1"));
  const detailRows = analysis.detail_rows.map((row) => [
    row.date_time,
    row.type,
    row.order_id,
    row.sku,
    row.quantity,
    money(row.product_sales),
    money(row.amazon_total),
    row.action,
    money(row.unit_product_cost),
    money(row.unit_first_leg_cost),
    money(row.product_cost_impact),
    money(row.first_leg_cost_impact),
    money(row.gross_profit),
    row.cost_found ? "Yes" : "No",
  ]);
  if (detailRows.length) {
    detailSheet.getRange(`A2:N${1 + detailRows.length}`).values = detailRows;
    styleBody(detailSheet.getRange(`A2:N${1 + detailRows.length}`));
    setNumberFormat(detailSheet.getRange(`F2:M${1 + detailRows.length}`), '"$"#,##0.00');
  }
  fitColumns(detailSheet, [22, 18, 20, 24, 10, 14, 14, 20, 18, 20, 18, 20, 16, 10]);
  detailSheet.freezePanes.freezeRows(1);

  typeSheet.getRange("A1:D1").values = [["Type", "Rows", "Amazon Total", "Gross Profit"]];
  styleHeader(typeSheet.getRange("A1:D1"));
  const typeSheetRows = analysis.type_summary.map((row) => [
    row.type,
    row.rows,
    money(row.amazon_total),
    money(row.gross_profit),
  ]);
  if (typeSheetRows.length) {
    typeSheet.getRange(`A2:D${1 + typeSheetRows.length}`).values = typeSheetRows;
    styleBody(typeSheet.getRange(`A2:D${1 + typeSheetRows.length}`));
    setNumberFormat(typeSheet.getRange(`C2:D${1 + typeSheetRows.length}`), '"$"#,##0.00');
  }
  fitColumns(typeSheet, [22, 10, 16, 16]);
  typeSheet.freezePanes.freezeRows(1);

  riskSheet.showGridLines = false;
  riskSheet.getRange("A1:H2").merge();
  riskSheet.getRange("A1").values = [["SKU Risk Review"]];
  styleTitle(riskSheet.getRange("A1:H2"));

  riskSheet.getRange("A4:D4").values = [["风险类型", "SKU数", "判断标准", "处理优先级"]];
  styleHeader(riskSheet.getRange("A4:D4"));
  riskSheet.getRange("A5:D8").values = [
    ["亏损SKU", analysis.summary.loss_skus, "流水毛利 < 0", "P0"],
    ["缺成本SKU", analysis.summary.missing_cost_skus, "订单或退款未匹配成本", "P0"],
    ["高退货SKU", analysis.summary.high_return_skus, "退货率 >= 20%，出库件数 >= 5", "P1"],
    ["低毛利SKU", analysis.summary.low_margin_skus, "毛利率 < 15%，订单数 >= 10", "P1"],
  ];
  styleBody(riskSheet.getRange("A5:D8"));
  setNumberFormat(riskSheet.getRange("B5:B8"), "0");

  function writeRiskBlock(startRow, title, rows) {
    riskSheet.getRange(`A${startRow}:H${startRow}`).merge();
    riskSheet.getRange(`A${startRow}`).values = [[title]];
    styleSection(riskSheet.getRange(`A${startRow}:H${startRow}`));
    const headerRow = startRow + 1;
    riskSheet.getRange(`A${headerRow}:H${headerRow}`).values = [[
      "SKU",
      "风险标签",
      "订单数",
      "销售额",
      "流水毛利",
      "毛利率",
      "退货率",
      "缺成本行数",
    ]];
    styleHeader(riskSheet.getRange(`A${headerRow}:H${headerRow}`));
    const data = rows.slice(0, 10).map((row) => [
      row.sku,
      row.risk_tags.join(" / "),
      row.orders,
      money(row.product_sales),
      money(row.gross_profit),
      pct(row.gross_margin),
      pct(row.return_rate),
      row.missing_cost_rows,
    ]);
    if (!data.length) return;
    const endRow = headerRow + data.length;
    riskSheet.getRange(`A${headerRow + 1}:H${endRow}`).values = data;
    styleBody(riskSheet.getRange(`A${headerRow + 1}:H${endRow}`));
    setNumberFormat(riskSheet.getRange(`D${headerRow + 1}:E${endRow}`), '"$"#,##0.00');
    setNumberFormat(riskSheet.getRange(`F${headerRow + 1}:G${endRow}`), "0.0%");
    setNumberFormat(riskSheet.getRange(`H${headerRow + 1}:H${endRow}`), "0");
  }

  writeRiskBlock(10, "亏损 SKU - 优先暂停扩量并核对费用", analysis.risk_summary.loss_making);
  writeRiskBlock(24, "低毛利 SKU - 优先复核售价、佣金与头程", analysis.risk_summary.low_margin);
  writeRiskBlock(38, "高退货 SKU - 优先结合评价与售后原因复盘", analysis.risk_summary.high_return);
  writeRiskBlock(52, "缺成本 SKU - 补齐成本后重新核算", analysis.risk_summary.missing_cost);
  fitColumns(riskSheet, [25, 20, 28, 15, 15, 10, 10, 13]);
  riskSheet.freezePanes.freezeRows(4);

  const outDir = path.dirname(outputPath);
  await fs.mkdir(outDir, { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
}

await main();
