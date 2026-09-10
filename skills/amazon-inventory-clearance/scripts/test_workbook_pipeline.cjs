const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { SpreadsheetFile } = require("@oai/artifact-tool");
const { calculateClearance } = require("./clearance_math.cjs");
const { buildWorkbook } = require("./generate_clearance_plan.cjs");

const headers = [
  "seller_sku",
  "asin",
  "product_title",
  "product_group",
  "is_womens_bag",
  "units_7d",
  "units_15d",
  "units_30d",
  "units_60d",
  "units_90d",
  "units_prev_15d",
  "revenue_30d",
  "ad_cost_30d",
  "supply_instock",
  "oldest_age_days",
  "next_snapshot_aged_units",
  "stranded_units",
  "unfulfillable_units",
  "estimated_aged_surcharge",
  "next_fee_snapshot_date",
  "unit_landed_cost",
  "amazon_fees_per_unit",
  "unit_contribution",
  "external_resale_value",
  "removal_fee_per_unit",
  "long_tail_approved",
];

const fixtures = [
  {
    seller_sku: "URGENT",
    asin: "U",
    product_title: "Urgent Bag",
    product_group: "bag",
    is_womens_bag: "是",
    units_7d: 0,
    units_15d: 0,
    units_30d: 0,
    units_60d: 0,
    units_90d: 0,
    units_prev_15d: 0,
    revenue_30d: 0,
    ad_cost_30d: 0,
    supply_instock: 40,
    oldest_age_days: 190,
    next_snapshot_aged_units: 40,
    stranded_units: 0,
    unfulfillable_units: 0,
    estimated_aged_surcharge: 0,
    next_fee_snapshot_date: "2026-08-15",
  },
  {
    seller_sku: "ACTIVE",
    supply_instock: 100,
  },
  {
    seller_sku: "OBSERVE",
    supply_instock: 80,
    unit_contribution: 2,
    external_resale_value: 4,
    removal_fee_per_unit: 1,
  },
  {
    seller_sku: "REPLENISH",
    units_7d: 18,
    units_15d: 35,
    units_30d: 62,
    units_60d: 120,
    units_90d: 170,
    units_prev_15d: 27,
    supply_instock: 12,
    oldest_age_days: 45,
    unit_contribution: 4,
  },
  {
    seller_sku: "HEALTHY",
    supply_instock: 59.8,
    unit_contribution: 2,
  },
  {
    seller_sku: "MISSING-STOCK",
    supply_instock: null,
    unit_contribution: 2,
  },
].map((row) => ({
  asin: row.seller_sku,
  product_title: `${row.seller_sku} Product`,
  product_group: "bag",
  is_womens_bag: "否",
  units_7d: 7,
  units_15d: 15,
  units_30d: 30,
  units_60d: 60,
  units_90d: 90,
  units_prev_15d: 15,
  revenue_30d: 300,
  ad_cost_30d: 20,
  oldest_age_days: 30,
  next_snapshot_aged_units: 0,
  stranded_units: 0,
  unfulfillable_units: 0,
  estimated_aged_surcharge: 0,
  next_fee_snapshot_date: "2026-08-15",
  unit_landed_cost: null,
  amazon_fees_per_unit: null,
  unit_contribution: null,
  external_resale_value: null,
  removal_fee_per_unit: null,
  long_tail_approved: "否",
  ...row,
}));

function csvCell(value) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function formulaInput(row) {
  return {
    units7: row.units_7d,
    units15: row.units_15d,
    units30: row.units_30d,
    units60: row.units_60d,
    previous15: row.units_prev_15d,
    supplyInstock: row.supply_instock,
    oldestAgeDays: row.oldest_age_days,
    nextSnapshotAgedUnits: row.next_snapshot_aged_units,
    daysToSnapshot: 20,
    strandedUnits: row.stranded_units,
    unfulfillableUnits: row.unfulfillable_units,
    estimatedAgedSurcharge: row.estimated_aged_surcharge,
    unitLandedCost: row.unit_landed_cost,
    amazonFeesPerUnit: row.amazon_fees_per_unit,
    unitContribution: row.unit_contribution,
    externalResaleValue: row.external_resale_value,
    removalFeePerUnit: row.removal_fee_per_unit,
    longTailApproved: row.long_tail_approved,
  };
}

function nearlyEqual(actual, expected, tolerance = 1e-7) {
  if (actual === expected) return true;
  if ((actual === "" || actual === null) && expected === null) return true;
  return (
    typeof actual === "number" &&
    typeof expected === "number" &&
    Math.abs(actual - expected) <= tolerance
  );
}

async function main() {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "clearance-workbook-"));
  const inputPath = path.join(tempDir, "input.csv");
  const outputPath = path.join(tempDir, "output.xlsx");
  await fs.writeFile(
    inputPath,
    [
      headers.join(","),
      ...fixtures.map((row) => headers.map((header) => csvCell(row[header])).join(",")),
    ].join("\n"),
  );
  const result = await buildWorkbook({
    input: inputPath,
    output: outputPath,
    "as-of-date": "2026-07-26",
    "seller-id": "56321",
    marketplace: "US",
  });
  assert.deepEqual(
    result.workbook.worksheets.items.map((sheet) => sheet.name),
    ["清货建议", "总览", "女包摘要", "数据问题", "规则参数", "来源"],
  );
  const plan = result.workbook.worksheets.getItem("清货建议");
  const values = plan.getUsedRange(true).values;
  const outputHeaders = values[0].map((value) => String(value ?? ""));
  const index = Object.fromEntries(
    outputHeaders.map((header, position) => [header, position]),
  );
  const seenStatuses = new Set();
  for (let position = 0; position < fixtures.length; position += 1) {
    const expected = calculateClearance(formulaInput(fixtures[position]));
    const actual = values[position + 1];
    assert.equal(actual[index["主状态"]], expected.status);
    assert.equal(actual[index["数量状态"]], expected.quantityStatus);
    assert.equal(actual[index["风险判断置信度"]], expected.riskConfidence);
    assert.equal(actual[index["经济性置信度"]], expected.economicConfidence);
    assert.ok(
      nearlyEqual(actual[index["潜在超量数量"]], expected.potentialExcessQty),
      `${fixtures[position].seller_sku} potential excess mismatch`,
    );
    assert.ok(
      nearlyEqual(actual[index["费用风险数量"]], expected.feeRiskQty),
      `${fixtures[position].seller_sku} fee risk mismatch`,
    );
    assert.ok(
      nearlyEqual(actual[index["清货目标数量"]], expected.clearanceTargetQty),
      `${fixtures[position].seller_sku} clearance target mismatch`,
    );
    if (fixtures[position].supply_instock !== null) {
      assert.ok(
        actual[index["清货目标数量"]] <= fixtures[position].supply_instock,
      );
    }
    if (
      fixtures[position].supply_instock !== null &&
      ["停补观察", "待补货", "健康维持"].includes(expected.status)
    ) {
      assert.equal(actual[index["清货目标数量"]], 0);
    }
    seenStatuses.add(expected.status);
  }
  assert.deepEqual(
    [...seenStatuses].sort(),
    ["主动清货", "停补观察", "健康维持", "待补货", "紧急清退"].sort(),
  );
  const firstFormulaRow = plan
    .getRangeByIndexes(1, index["最近7天日销"], 1, 23)
    .formulas[0];
  assert.ok(firstFormulaRow.every((formula) => String(formula).startsWith("=")));

  await (await SpreadsheetFile.exportXlsx(result.workbook)).save(outputPath);
  const errors = await result.workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: "test formula error scan",
  });
  assert.match(errors.ndjson, /matched 0 entries/);
  const summary = result.workbook.worksheets.getItem("总览").getRange("A1:C15").values;
  assert.equal(summary[3][1], fixtures.length);
  assert.equal(summary[12][1], 1);
  const issueValues = result.workbook.worksheets
    .getItem("数据问题")
    .getRange("A1:C10").values;
  assert.equal(issueValues[2][1], 1);
  assert.equal(issueValues[6][1], 2);
  console.log("clearance workbook pipeline tests passed");
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
