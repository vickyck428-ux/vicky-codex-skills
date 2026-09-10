#!/usr/bin/env node

const path = require("node:path");
const {
  exportWorkbook,
  findHeader,
  parseArgs,
  parseBoolean,
  parseNumber,
  readTable,
} = require("./spreadsheet_helpers.cjs");

const ALIASES = {
  sku: ["SKU", "sku", "商品SKU"],
  asin: ["ASIN", "asin", "子ASIN"],
  supplierName: ["供应商名称", "supplier_name", "1688供应商"],
  supplierUrl: ["1688链接", "supplier_1688_url", "supplier_url"],
  price: ["价格", "supplier_price", "供应商价格"],
  minOrderQty: ["起订量", "min_order_qty", "moq"],
  sameProduct: ["同款确认", "same_product"],
  storeStatus: ["店铺状态", "store_status"],
  factoryStatus: ["厂家状态", "factory_status"],
  notes: ["候选备注", "candidate_notes", "备注"],
};

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function keyFor(row, indexes) {
  const sku = indexes.sku >= 0 ? String(row[indexes.sku] ?? "").trim().toLowerCase() : "";
  const asin = indexes.asin >= 0 ? String(row[indexes.asin] ?? "").trim().toLowerCase() : "";
  return sku ? `sku:${sku}` : asin ? `asin:${asin}` : "";
}

function selectGroup(candidates, indexes) {
  const evaluated = candidates.map((row) => {
    const price = parseNumber(row[indexes.price]);
    const reasons = [];
    const name = String(row[indexes.supplierName] ?? "").trim();
    const url = String(row[indexes.supplierUrl] ?? "").trim();
    const sameProduct = indexes.sameProduct >= 0 && parseBoolean(row[indexes.sameProduct], false);
    const storeStatus =
      indexes.storeStatus >= 0 ? String(row[indexes.storeStatus] ?? "").trim() : "未知";
    if (!name) reasons.push("缺少供应商名称");
    if (!/^https?:\/\//i.test(url)) reasons.push("链接无效");
    if (!(price > 0)) reasons.push("价格无效");
    if (!sameProduct) reasons.push("未确认同款");
    if (storeStatus !== "正常") reasons.push(storeStatus === "异常" ? "店铺异常" : "店铺状态未确认");
    return { row, price, reasons, storeStatus };
  });

  const comparable = evaluated.filter((item) => item.reasons.length === 0);
  const midpoint = median(comparable.map((item) => item.price));
  for (const item of comparable) {
    if (midpoint > 0 && item.price < midpoint * 0.6) {
      item.reasons.push(`价格低于中位价60%（中位价${midpoint.toFixed(2)}）`);
    }
  }
  const valid = comparable.filter((item) => item.reasons.length === 0).sort((a, b) => a.price - b.price);
  if (!valid.length) {
    const notes = evaluated
      .flatMap((item) => item.reasons)
      .filter(Boolean)
      .slice(0, 4)
      .join("；");
    return { status: "需要人工确认", note: notes || "没有可靠候选" };
  }

  const selected = valid[0];
  const factoryStatus =
    indexes.factoryStatus >= 0
      ? String(selected.row[indexes.factoryStatus] ?? "").trim()
      : "未知";
  const status = factoryStatus === "已确认" ? "已匹配" : "需要人工确认";
  const sourceNote = indexes.notes >= 0 ? String(selected.row[indexes.notes] ?? "").trim() : "";
  const note = [
    `通过${valid.length}个有效候选筛选`,
    `中位价${midpoint.toFixed(2)}`,
    factoryStatus === "已确认" ? "厂家已确认" : "厂家身份未确认",
    sourceNote,
  ]
    .filter(Boolean)
    .join("；");
  return {
    status,
    name: selected.row[indexes.supplierName],
    url: selected.row[indexes.supplierUrl],
    price: selected.price,
    minOrderQty: indexes.minOrderQty >= 0 ? selected.row[indexes.minOrderQty] : "",
    note,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.plan || !args.candidates || !args.output) {
    throw new Error(
      "Usage: select_supplier_candidates.cjs --plan shipping-plan.xlsx --candidates candidates.xlsx --output result.xlsx",
    );
  }

  const planPath = path.resolve(args.plan);
  const candidatePath = path.resolve(args.candidates);
  const outputPath = path.resolve(args.output);
  const planData = await readTable(planPath);
  const candidateData = await readTable(candidatePath);

  const planIndexes = {
    sku: findHeader(planData.headers, ALIASES.sku),
    asin: findHeader(planData.headers, ALIASES.asin),
    status: findHeader(planData.headers, ["1688匹配状态"]),
    name: findHeader(planData.headers, ["1688供应商"]),
    url: findHeader(planData.headers, ["1688链接"]),
    price: findHeader(planData.headers, ["供应商价格"]),
    minOrderQty: findHeader(planData.headers, ["起订量"]),
    note: findHeader(planData.headers, ["筛选说明"]),
  };
  if (planIndexes.sku < 0 && planIndexes.asin < 0) {
    throw new Error("Plan must contain SKU or ASIN.");
  }
  for (const field of ["status", "name", "url", "price", "minOrderQty", "note"]) {
    if (planIndexes[field] < 0) throw new Error(`Plan is missing supplier output column: ${field}`);
  }

  const candidateIndexes = {};
  for (const [field, aliases] of Object.entries(ALIASES)) {
    candidateIndexes[field] = findHeader(candidateData.headers, aliases);
  }
  for (const field of ["supplierName", "supplierUrl", "price"]) {
    if (candidateIndexes[field] < 0) throw new Error(`Candidate sheet is missing: ${field}`);
  }
  if (candidateIndexes.sku < 0 && candidateIndexes.asin < 0) {
    throw new Error("Candidate sheet must contain SKU or ASIN.");
  }

  const groups = new Map();
  for (const row of candidateData.rows) {
    const key = keyFor(row, candidateIndexes);
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  }

  for (let index = 0; index < planData.rows.length; index += 1) {
    const row = planData.rows[index];
    const key = keyFor(row, planIndexes);
    const result = key && groups.has(key) ? selectGroup(groups.get(key), candidateIndexes) : {
      status: "需要人工确认",
      note: "没有采集到1688候选",
    };
    const excelRow = index + 2;
    planData.sheet.getCell(excelRow - 1, planIndexes.status).values = [[result.status]];
    planData.sheet.getCell(excelRow - 1, planIndexes.name).values = [[result.name || ""]];
    planData.sheet.getCell(excelRow - 1, planIndexes.url).values = [[result.url || ""]];
    planData.sheet.getCell(excelRow - 1, planIndexes.price).values = [[result.price || ""]];
    planData.sheet.getCell(excelRow - 1, planIndexes.minOrderQty).values = [[result.minOrderQty || ""]];
    planData.sheet.getCell(excelRow - 1, planIndexes.note).values = [[result.note || ""]];
  }

  await exportWorkbook(planData.workbook, outputPath);
  console.log(`Merged supplier decisions into ${outputPath}`);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
