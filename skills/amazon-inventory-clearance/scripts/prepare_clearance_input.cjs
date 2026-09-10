const fs = require("node:fs/promises");
const path = require("node:path");
const { parseDate, readTable } = require("./spreadsheet_helpers.cjs");

const NORMALIZED_HEADERS = Object.freeze([
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
  "supply_reserved",
  "supply_inbound",
  "supply_total",
  "oldest_age_days",
  "aged_110_plus_units",
  "next_snapshot_aged_units",
  "aged_181_210",
  "aged_211_240",
  "aged_241_270",
  "aged_271_300",
  "aged_301_330",
  "aged_331_365",
  "aged_365_plus",
  "estimated_aged_surcharge",
  "stranded_units",
  "unfulfillable_units",
  "next_fee_snapshot_date",
  "unit_landed_cost",
  "amazon_fees_per_unit",
  "unit_contribution",
  "external_resale_value",
  "removal_fee_per_unit",
  "purchase_cost_cny",
  "fba_first_leg_cost_cny",
  "procurement_days",
  "prep_days",
  "sea_days",
  "review_cycle_days",
  "safety_factor",
  "long_tail_approved",
  "inventory_report_present",
  "age_report_present",
  "cost_data_present",
  "api_supply_instock",
  "api_supply_inbound",
  "api_supply_total",
  "api_inventory_suspect",
  "api_inventory_mismatch",
  "inventory_reconciliation_issue",
  "inventory_snapshot_date",
  "age_snapshot_date",
  "sales_window_end_date",
  "seller_id",
  "marketplace",
  "oldest_age_basis",
  "input_data_notes",
]);

const FEE_QUANTITY_FIELDS = Object.freeze([
  "quantity-to-be-charged-ais-181-210-days",
  "quantity-to-be-charged-ais-211-240-days",
  "quantity-to-be-charged-ais-241-270-days",
  "quantity-to-be-charged-ais-271-300-days",
  "quantity-to-be-charged-ais-301-330-days",
  "quantity-to-be-charged-ais-331-365-days",
  "quantity-to-be-charged-ais-366-455-days",
  "quantity-to-be-charged-ais-456-plus-days",
]);

const FEE_AMOUNT_FIELDS = Object.freeze([
  "estimated-ais-181-210-days",
  "estimated-ais-211-240-days",
  "estimated-ais-241-270-days",
  "estimated-ais-271-300-days",
  "estimated-ais-301-330-days",
  "estimated-ais-331-365-days",
  "estimated-ais-366-455-days",
  "estimated-ais-456-plus-days",
]);

function textOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  return String(value).trim();
}

function numberOrNull(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const parsed = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function dateOrNull(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  return parseDate(value);
}

function normalizeObjectKey(value) {
  return String(value ?? "")
    .replace(/^\uFEFF/, "")
    .trim()
    .toLowerCase();
}

function rowsToObjects(table) {
  const headers = table.headers.map(normalizeObjectKey);
  return table.rows.map((row) =>
    Object.fromEntries(headers.map((header, index) => [header, row[index] ?? null])),
  );
}

function getByAliases(row, aliases) {
  if (!row) return null;
  for (const alias of aliases) {
    const value = row[normalizeObjectKey(alias)];
    if (value !== null && value !== undefined && String(value).trim() !== "") return value;
  }
  return null;
}

function indexBySku(rows) {
  const result = new Map();
  for (const row of rows) {
    const sku = textOrNull(getByAliases(row, ["sku", "seller_sku", "sellerSku", "卖家SKU"]));
    if (sku) result.set(sku, row);
  }
  return result;
}

function indexApiRows(rows) {
  const result = new Map();
  for (const row of rows || []) {
    const sku = textOrNull(row.sellerSku ?? row.seller_sku ?? row.sku);
    if (sku) result.set(sku, row);
  }
  return result;
}

function oldestAgeLowerBound(row) {
  if (!row) return null;
  const buckets = [
    [["inv-age-456-plus-days"], 456],
    [["inv-age-366-to-455-days"], 366],
    [["inv-age-331-to-365-days"], 331],
    [["inv-age-271-to-365-days"], 271],
    [["inv-age-181-to-330-days"], 181],
    [["inv-age-181-to-270-days"], 181],
    [["inv-age-91-to-180-days"], 91],
    [["inv-age-61-to-90-days"], 61],
    [["inv-age-31-to-60-days"], 31],
    [["inv-age-0-to-30-days", "inv-age-0-to-90-days"], 0],
  ];
  for (const [aliases, lowerBound] of buckets) {
    const value = numberOrNull(getByAliases(row, aliases));
    if (value !== null && value > 0) return lowerBound;
  }
  return null;
}

function sumPresent(row, fields) {
  if (!row) return null;
  const values = fields.map((field) => numberOrNull(getByAliases(row, [field])));
  if (!values.some((value) => value !== null)) return null;
  return values.reduce((sum, value) => sum + (value ?? 0), 0);
}

function classifyWomensBag(title, group) {
  const source = `${title ?? ""} ${group ?? ""}`.toLowerCase();
  const exclusions = [
    "pencil case",
    "pencil pouch",
    "pen case",
    "pen pouch",
    "pen bag",
    "makeup bag",
    "cosmetic bag",
    "lunch bag",
    "packing cube",
  ];
  if (exclusions.some((term) => source.includes(term))) return "否";
  const strongTerms = [
    "handbag",
    "purse",
    "shoulder bag",
    "crossbody",
    "tote bag",
    "hobo bag",
    "ita bag",
    "itabag",
    "satchel",
    "clutch",
    "wallet",
    "bucket bag",
    "bag for women",
    "women's bag",
    "womens bag",
  ];
  if (strongTerms.some((term) => source.includes(term))) return "是";
  if (/\bbag\b/.test(source)) return "待确认";
  return "否";
}

function firstApiRow(apiMaps, sku) {
  for (const window of ["u90", "u60", "u30", "u15", "u7", "base"]) {
    const row = apiMaps[window]?.get(sku);
    if (row) return row;
  }
  return null;
}

function apiInventory(apiRow) {
  return {
    instock: numberOrNull(apiRow?.supplyInstock ?? apiRow?.supply_instock),
    inbound: numberOrNull(apiRow?.supplyInbound ?? apiRow?.supply_inbound),
    total: numberOrNull(apiRow?.supplyTotal ?? apiRow?.supply_total),
  };
}

function isSuspiciousApiInventory(values) {
  return Object.values(values).some((value) => value === 999 || value === 1000);
}

function costValue(cost, aliases) {
  return numberOrNull(getByAliases(cost, aliases));
}

async function optionalRows(filePath) {
  if (!filePath) return [];
  const table = await readTable(path.resolve(filePath));
  const hasSkuHeader = table.headers.some((header) =>
    ["sku", "sellersku", "卖家sku"].includes(
      normalizeObjectKey(header).replace(/[\s_-]+/g, ""),
    ),
  );
  if (hasSkuHeader) return rowsToObjects(table);
  const embeddedHeaderIndex = table.rows.findIndex((row) =>
    row.some((value) =>
      ["sku", "sellersku", "卖家sku"].includes(
        normalizeObjectKey(value).replace(/[\s_-]+/g, ""),
      ),
    ),
  );
  if (embeddedHeaderIndex >= 0) {
    return rowsToObjects({
      headers: table.rows[embeddedHeaderIndex],
      rows: table.rows.slice(embeddedHeaderIndex + 1),
    });
  }
  return rowsToObjects(table);
}

async function prepareRawData(options) {
  if (!options.apiJson) throw new Error("Raw mode requires --api-json.");
  const apiPath = path.resolve(options.apiJson);
  const apiPayload = JSON.parse(await fs.readFile(apiPath, "utf8"));
  const inventoryRows = await optionalRows(options.inventoryReport);
  const ageRows = await optionalRows(options.ageReport);
  const costRows = await optionalRows(options.cost);
  const inventoryBySku = indexBySku(inventoryRows);
  const ageBySku = indexBySku(ageRows);
  const costBySku = indexBySku(costRows);
  const costByAsin = new Map();
  for (const row of costRows) {
    const asin = textOrNull(getByAliases(row, ["asin", "ASIN", "子ASIN"]));
    if (asin && !costByAsin.has(asin)) costByAsin.set(asin, row);
  }
  const apiSource = apiPayload.api || apiPayload.windows || {};
  const apiMaps = Object.fromEntries(
    ["base", "u7", "u15", "u30", "u60", "u90", "prev15"].map((window) => [
      window,
      indexApiRows(apiSource[window]),
    ]),
  );
  const skuSet = new Set([
    ...apiMaps.base.keys(),
    ...apiMaps.u90.keys(),
    ...inventoryBySku.keys(),
    ...ageBySku.keys(),
  ]);
  const skus = [...skuSet].sort((left, right) => left.localeCompare(right));
  const asOfDate =
    parseDate(options.asOfDate) || parseDate(apiPayload.asOfDate) || parseDate(apiPayload.scope?.asOfDate);
  const feeSnapshotDate = parseDate(options.feeSnapshotDate);
  const sellerId =
    textOrNull(options.sellerId) ??
    textOrNull(apiPayload.scope?.sellerId) ??
    textOrNull(firstApiRow(apiMaps, skus[0])?.sellerId);
  const marketplace =
    textOrNull(options.marketplace) ??
    textOrNull(apiPayload.scope?.marketplace) ??
    textOrNull(firstApiRow(apiMaps, skus[0])?.marketplace);

  const rows = skus.map((sku) => {
    const inventory = inventoryBySku.get(sku);
    const age = ageBySku.get(sku);
    const apiRow = firstApiRow(apiMaps, sku);
    const asin =
      textOrNull(apiRow?.asin) ??
      textOrNull(getByAliases(inventory, ["asin"])) ??
      textOrNull(getByAliases(age, ["asin"]));
    const cost = costBySku.get(sku) ?? costByAsin.get(asin);
    const apiTitle = textOrNull(apiRow?.productTitle ?? apiRow?.product_title);
    const reportTitle =
      textOrNull(getByAliases(inventory, ["product-name", "product_title", "标题"])) ??
      textOrNull(getByAliases(age, ["product-name", "product_title", "标题"]));
    const title = apiTitle && apiTitle !== asin ? apiTitle : reportTitle ?? apiTitle;
    const group =
      textOrNull(getByAliases(inventory, ["product-group", "product_group", "产品组"])) ??
      textOrNull(getByAliases(age, ["product-group", "product_group", "产品组"]));
    const oldest = oldestAgeLowerBound(age);
    const apiValues = apiInventory(apiRow);
    const suspicious = isSuspiciousApiInventory(apiValues);
    const reportInstock = numberOrNull(getByAliases(inventory, ["available", "supply_instock"]));
    const reportInbound = numberOrNull(
      getByAliases(inventory, ["inbound-quantity", "supply_inbound"]),
    );
    const reportTotal = numberOrNull(
      getByAliases(inventory, ["Inventory Supply at FBA", "supply_total"]),
    );
    const reconciliation = [];
    let inventoryMismatch = false;
    if (!inventory && Object.values(apiValues).some((value) => value !== null)) {
      reconciliation.push("API有库存但FBA库存报告缺行，未采用");
    } else if (
      inventory &&
      ((apiValues.instock !== null && reportInstock !== null && apiValues.instock !== reportInstock) ||
        (apiValues.inbound !== null && reportInbound !== null && apiValues.inbound !== reportInbound) ||
        (apiValues.total !== null && reportTotal !== null && apiValues.total !== reportTotal))
    ) {
      inventoryMismatch = true;
      reconciliation.push("API库存与FBA库存报告不一致，仅采用FBA报告");
    }
    if (suspicious) reconciliation.push("API库存含999/1000疑似占位值，已隔离");
    const unitLandedCost = costValue(cost, ["unit_landed_cost", "单件落地成本"]);
    const amazonFees = costValue(cost, ["amazon_fees_per_unit", "Amazon单件费用"]);
    const contribution = costValue(cost, ["unit_contribution", "单件贡献利润"]);
    const externalValue = costValue(cost, ["external_resale_value", "外部回收单价"]);
    const removalFee = costValue(cost, ["removal_fee_per_unit", "单件移除成本"]);
    const purchaseCostCny = costValue(cost, ["purchase_cost_cny", "采购成本", "采购成本CNY"]);
    const firstLegCny = costValue(cost, [
      "fba_first_leg_cost_cny",
      "头程成本",
      "FBA头程成本CNY",
    ]);
    const hasEconomicData = [
      unitLandedCost,
      amazonFees,
      contribution,
      externalValue,
      removalFee,
      purchaseCostCny,
      firstLegCny,
    ].some((value) => value !== null);
    const notes = [];
    if (!inventory) notes.push("缺FBA库存报告行，FBA库存保持空白");
    if (!age) notes.push("缺库龄报告行");
    if (!feeSnapshotDate) notes.push("缺费用快照日");
    if (!hasEconomicData) notes.push("缺经济数据，清货目标为暂定");
    if (oldest !== null) notes.push(`最老库龄为分段下限${oldest}天`);
    if (reconciliation.length) notes.push(...reconciliation);

    const record = {
      seller_sku: sku,
      asin,
      product_title: title,
      product_group: group,
      is_womens_bag: classifyWomensBag(title, group),
      units_7d: numberOrNull(apiMaps.u7.get(sku)?.units) ?? 0,
      units_15d: numberOrNull(apiMaps.u15.get(sku)?.units) ?? 0,
      units_30d: numberOrNull(apiMaps.u30.get(sku)?.units) ?? 0,
      units_60d: numberOrNull(apiMaps.u60.get(sku)?.units) ?? 0,
      units_90d: numberOrNull(apiMaps.u90.get(sku)?.units) ?? 0,
      units_prev_15d: numberOrNull(apiMaps.prev15.get(sku)?.units) ?? 0,
      revenue_30d: numberOrNull(apiMaps.u30.get(sku)?.revenue) ?? 0,
      ad_cost_30d: numberOrNull(apiMaps.u30.get(sku)?.adCost) ?? 0,
      // FBA quantities below are report-only by design. API quantities are diagnostic columns.
      supply_instock: reportInstock,
      supply_reserved: numberOrNull(
        getByAliases(inventory, ["Total Reserved Quantity", "supply_reserved"]),
      ),
      supply_inbound: reportInbound,
      supply_total: reportTotal,
      oldest_age_days: oldest,
      aged_110_plus_units: null,
      next_snapshot_aged_units: sumPresent(age, FEE_QUANTITY_FIELDS),
      aged_181_210: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-181-210-days", "aged_181_210"]),
      ),
      aged_211_240: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-211-240-days", "aged_211_240"]),
      ),
      aged_241_270: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-241-270-days", "aged_241_270"]),
      ),
      aged_271_300: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-271-300-days", "aged_271_300"]),
      ),
      aged_301_330: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-301-330-days", "aged_301_330"]),
      ),
      aged_331_365: numberOrNull(
        getByAliases(age, ["quantity-to-be-charged-ais-331-365-days", "aged_331_365"]),
      ),
      aged_365_plus: sumPresent(age, [
        "quantity-to-be-charged-ais-366-455-days",
        "quantity-to-be-charged-ais-456-plus-days",
      ]),
      estimated_aged_surcharge: sumPresent(age, FEE_AMOUNT_FIELDS),
      stranded_units: numberOrNull(getByAliases(age, ["stranded_units", "stranded库存"])),
      unfulfillable_units:
        numberOrNull(getByAliases(age, ["unfulfillable-quantity", "unfulfillable_units"])) ??
        numberOrNull(
          getByAliases(inventory, ["unfulfillable-quantity", "unfulfillable_units"]),
        ),
      next_fee_snapshot_date: feeSnapshotDate,
      unit_landed_cost: unitLandedCost,
      amazon_fees_per_unit: amazonFees,
      unit_contribution: contribution,
      external_resale_value: externalValue,
      removal_fee_per_unit: removalFee,
      purchase_cost_cny: purchaseCostCny,
      fba_first_leg_cost_cny: firstLegCny,
      procurement_days: costValue(cost, ["procurement_days", "采购周期"]),
      prep_days: costValue(cost, ["prep_days", "预处理周期"]),
      sea_days: costValue(cost, ["sea_days", "海运可售天数"]),
      review_cycle_days: costValue(cost, ["review_cycle_days", "复查周期"]),
      safety_factor: costValue(cost, ["safety_factor", "安全系数"]),
      long_tail_approved: textOrNull(
        getByAliases(cost, ["long_tail_approved", "高利润长尾确认"]),
      ),
      inventory_report_present: inventory ? "是" : "否",
      age_report_present: age ? "是" : "否",
      cost_data_present: hasEconomicData ? "是" : "否",
      api_supply_instock: apiValues.instock,
      api_supply_inbound: apiValues.inbound,
      api_supply_total: apiValues.total,
      api_inventory_suspect: suspicious ? "是" : "否",
      api_inventory_mismatch: inventoryMismatch ? "是" : "否",
      inventory_reconciliation_issue: reconciliation.join("；"),
      inventory_snapshot_date:
        dateOrNull(getByAliases(inventory, ["snapshot-date", "inventory_snapshot_date"])) ??
        dateOrNull(apiPayload.inventorySnapshotDate),
      age_snapshot_date:
        dateOrNull(getByAliases(age, ["Inventory age snapshot date", "age_snapshot_date"])) ??
        dateOrNull(getByAliases(age, ["snapshot-date"])),
      sales_window_end_date: asOfDate,
      seller_id: sellerId,
      marketplace,
      oldest_age_basis: oldest === null ? "缺失" : "Amazon库龄分段下限",
      input_data_notes: notes.join("；"),
    };
    return NORMALIZED_HEADERS.map((header) => record[header] ?? null);
  });

  return {
    headers: [...NORMALIZED_HEADERS],
    rows,
    metadata: {
      sellerId,
      marketplace,
      asOfDate,
      feeSnapshotDate,
      apiPath,
      inventoryReportPath: options.inventoryReport
        ? path.resolve(options.inventoryReport)
        : null,
      ageReportPath: options.ageReport ? path.resolve(options.ageReport) : null,
      costPath: options.cost ? path.resolve(options.cost) : null,
      inventorySnapshotDate:
        dateOrNull(
          getByAliases(inventoryRows[0], ["snapshot-date", "inventory_snapshot_date"]),
        ) ?? dateOrNull(apiPayload.inventorySnapshotDate),
      ageSnapshotDate:
        dateOrNull(
          getByAliases(ageRows[0], ["Inventory age snapshot date", "age_snapshot_date"]),
        ) ?? dateOrNull(getByAliases(ageRows[0], ["snapshot-date"])),
      salesWindows: apiPayload.windows
        ? JSON.stringify(apiPayload.windows)
        : "7/15/30/60/90天及前15天",
      apiSkuCount: new Set([
        ...apiMaps.base.keys(),
        ...apiMaps.u90.keys(),
      ]).size,
      inventorySkuCount: inventoryBySku.size,
      ageSkuCount: ageBySku.size,
      costSkuCount: costBySku.size,
    },
  };
}

module.exports = {
  FEE_AMOUNT_FIELDS,
  FEE_QUANTITY_FIELDS,
  NORMALIZED_HEADERS,
  classifyWomensBag,
  indexBySku,
  isSuspiciousApiInventory,
  numberOrNull,
  oldestAgeLowerBound,
  prepareRawData,
  rowsToObjects,
  sumPresent,
  textOrNull,
};
