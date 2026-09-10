#!/usr/bin/env node

const path = require("node:path");
const {
  CALC_HEADERS,
  RULE_DEFAULTS,
  buildExcelFormulaMap,
} = require("./clearance_math.cjs");
const { prepareRawData } = require("./prepare_clearance_input.cjs");
const {
  Workbook,
  applyTableStyle,
  columnLetter,
  exportWorkbook,
  findHeader,
  parseArgs,
  parseDate,
  readTable,
} = require("./spreadsheet_helpers.cjs");

const ALIASES = {
  sku: ["seller_sku", "SKU", "卖家SKU", "sellerSku"],
  asin: ["asin", "ASIN", "子ASIN"],
  title: ["product_title", "标题", "商品名称", "productTitle"],
  group: ["product_group", "产品组", "产品类型"],
  women: ["is_womens_bag", "是否女包", "女包"],
  u7: ["units_7d", "近7天销量"],
  u15: ["units_15d", "近15天销量"],
  u30: ["units_30d", "近30天销量"],
  u60: ["units_60d", "近60天销量"],
  u90: ["units_90d", "近90天销量"],
  prev15: ["units_prev_15d", "前15天销量"],
  revenue: ["revenue_30d", "近30天销售额"],
  adCost: ["ad_cost_30d", "近30天广告花费"],
  instock: ["supply_instock", "FBA可售", "可售库存"],
  reserved: ["supply_reserved", "预留库存"],
  inbound: ["supply_inbound", "在途库存"],
  supplyTotal: ["supply_total", "FBA库存总量"],
  oldest: ["oldest_age_days", "最老库龄"],
  aged110: ["aged_110_plus_units", "110天以上数量"],
  nextAged: ["next_snapshot_aged_units", "下一快照计费数量"],
  age181: ["aged_181_210"],
  age211: ["aged_211_240"],
  age241: ["aged_241_270"],
  age271: ["aged_271_300"],
  age301: ["aged_301_330"],
  age331: ["aged_331_365"],
  age365: ["aged_365_plus"],
  surcharge: ["estimated_aged_surcharge", "预计库龄附加费"],
  stranded: ["stranded_units", "stranded库存"],
  unfulfillable: ["unfulfillable_units", "不可售库存"],
  feeDate: ["next_fee_snapshot_date", "下一费用快照日"],
  landedCost: ["unit_landed_cost", "单件落地成本"],
  amazonFees: ["amazon_fees_per_unit", "Amazon单件费用"],
  contribution: ["unit_contribution", "单件贡献利润"],
  externalValue: ["external_resale_value", "外部回收单价"],
  removalFee: ["removal_fee_per_unit", "单件移除成本"],
  c: ["procurement_days", "采购周期"],
  d: ["prep_days", "预处理周期"],
  e: ["sea_days", "海运可售天数"],
  f: ["review_cycle_days", "复查周期"],
  n: ["safety_factor", "安全系数"],
  longTail: ["long_tail_approved", "高利润长尾确认"],
  inventoryPresent: ["inventory_report_present", "FBA库存报告有行"],
  agePresent: ["age_report_present", "库龄报告有行"],
  costPresent: ["cost_data_present", "成本数据有行"],
  apiInstock: ["api_supply_instock"],
  apiInbound: ["api_supply_inbound"],
  apiTotal: ["api_supply_total"],
  apiSuspect: ["api_inventory_suspect"],
  apiMismatch: ["api_inventory_mismatch"],
  reconciliation: ["inventory_reconciliation_issue"],
  inventorySnapshot: ["inventory_snapshot_date"],
  ageSnapshot: ["age_snapshot_date"],
  salesWindowEnd: ["sales_window_end_date"],
  sellerId: ["seller_id"],
  marketplace: ["marketplace"],
  notes: ["input_data_notes"],
};

const NUMERIC_KEYS = Object.freeze([
  "u7",
  "u15",
  "u30",
  "u60",
  "u90",
  "prev15",
  "revenue",
  "adCost",
  "instock",
  "reserved",
  "inbound",
  "supplyTotal",
  "oldest",
  "aged110",
  "nextAged",
  "age181",
  "age211",
  "age241",
  "age271",
  "age301",
  "age331",
  "age365",
  "surcharge",
  "stranded",
  "unfulfillable",
  "landedCost",
  "amazonFees",
  "contribution",
  "externalValue",
  "removalFee",
  "c",
  "d",
  "e",
  "f",
  "n",
  "apiInstock",
  "apiInbound",
  "apiTotal",
]);

function isoToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

function normalizeRows(rows, indexes) {
  return rows.map((sourceRow) => {
    const row = [...sourceRow];
    for (const key of NUMERIC_KEYS) {
      const index = indexes[key];
      const value = index >= 0 ? row[index] : null;
      if (value === null || value === undefined || String(value).trim() === "") continue;
      const parsed = Number(String(value).replace(/,/g, "").trim());
      if (Number.isFinite(parsed)) row[index] = parsed;
    }
    for (const key of ["feeDate", "inventorySnapshot", "ageSnapshot", "salesWindowEnd"]) {
      const index = indexes[key];
      if (index < 0 || row[index] instanceof Date) continue;
      const parsedDate = parseDate(row[index]);
      if (parsedDate) row[index] = parsedDate;
    }
    return row;
  });
}

function indexAliases(headers) {
  return Object.fromEntries(
    Object.entries(ALIASES).map(([key, aliases]) => [key, findHeader(headers, aliases)]),
  );
}

function yes(value) {
  return ["是", "yes", "true", "1"].includes(String(value ?? "").trim().toLowerCase());
}

function isLegacyPencilCase(row, indexes) {
  const values = [indexes.sku, indexes.title, indexes.group]
    .filter((index) => index >= 0)
    .map((index) => String(row[index] ?? "").toLowerCase())
    .join(" ");
  return ["pencil case", "pencil pouch", "pen case", "pen pouch", "pen bag"]
    .some((term) => values.includes(term));
}

function formulaParameters() {
  return {
    asOfDate: "'规则参数'!$B$2",
    procurementDays: "'规则参数'!$B$3",
    prepDays: "'规则参数'!$B$4",
    seaDays: "'规则参数'!$B$5",
    reviewCycleDays: "'规则参数'!$B$6",
    safetyFactor: "'规则参数'!$B$7",
    maxFbaTargetDays: "'规则参数'!$B$8",
    courseAgeWarningDays: "'规则参数'!$B$9",
    feeReferenceAgeDays: "'规则参数'!$B$10",
    liquidationRecoveryLow: "'规则参数'!$B$11",
    liquidationRecoveryHigh: "'规则参数'!$B$12",
  };
}

function addStatusFormatting(sheet, range) {
  range.conditionalFormats.add("containsText", {
    text: "紧急清退",
    format: { fill: "#FECACA", font: { color: "#991B1B", bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "主动清货",
    format: { fill: "#FED7AA", font: { color: "#9A3412", bold: true } },
  });
  range.conditionalFormats.add("containsText", {
    text: "停补观察",
    format: { fill: "#FEF3C7", font: { color: "#92400E" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "健康维持",
    format: { fill: "#D1FAE5", font: { color: "#065F46" } },
  });
  range.conditionalFormats.add("containsText", {
    text: "待补货",
    format: { fill: "#DBEAFE", font: { color: "#1E40AF" } },
  });
}

async function loadSource(args) {
  if (args.input) {
    return {
      ...(await readTable(path.resolve(args.input))),
      metadata: {
        mode: "标准表",
        inputPath: path.resolve(args.input),
        sellerId: args["seller-id"] || null,
        marketplace: args.marketplace || null,
        asOfDate: parseDate(args["as-of-date"]),
        feeSnapshotDate: parseDate(args["fee-snapshot-date"]),
      },
    };
  }
  if (args["api-json"]) {
    const raw = await prepareRawData({
      apiJson: args["api-json"],
      inventoryReport: args["inventory-report"],
      ageReport: args["age-report"],
      cost: args.cost,
      sellerId: args["seller-id"],
      marketplace: args.marketplace,
      asOfDate: args["as-of-date"],
      feeSnapshotDate: args["fee-snapshot-date"],
    });
    raw.metadata.mode = "原始数据自动合并";
    return raw;
  }
  throw new Error("Provide either --input or --api-json.");
}

async function buildWorkbook(args) {
  if (!args.output) {
    throw new Error(
      "Usage: generate_clearance_plan.cjs (--input standard.xlsx | --api-json api.json [--inventory-report inventory.csv] [--age-report age.csv] [--cost cost.xlsx]) --seller-id ID --marketplace US --as-of-date YYYY-MM-DD --fee-snapshot-date YYYY-MM-DD --output clearance.xlsx",
    );
  }
  const source = await loadSource(args);
  const asOfDate =
    parseDate(args["as-of-date"]) || source.metadata?.asOfDate || parseDate(isoToday());
  if (!asOfDate) throw new Error("--as-of-date must use YYYY-MM-DD.");
  const baseHeaders = source.headers.filter((header) => !CALC_HEADERS.includes(header));
  const baseSourceIndexes = baseHeaders.map((header) => source.headers.indexOf(header));
  const baseRows = source.rows.map((row) =>
    baseSourceIndexes.map((sourceIndex) => row[sourceIndex] ?? null),
  );
  const indexes = indexAliases(baseHeaders);
  if (indexes.sku < 0) throw new Error("Missing required column: seller_sku/SKU.");
  const allNormalizedRows = normalizeRows(baseRows, indexes);
  const legacyRows = allNormalizedRows.filter((row) => isLegacyPencilCase(row, indexes));
  const normalizedRows = allNormalizedRows.filter((row) => !isLegacyPencilCase(row, indexes));
  const outputHeaders = [...baseHeaders, ...CALC_HEADERS];
  const calcStart = baseHeaders.length;
  const calcIndexes = Object.fromEntries(
    CALC_HEADERS.map((header, offset) => [header, calcStart + offset]),
  );
  const lastRow = normalizedRows.length + 1;
  const lastColumn = columnLetter(outputHeaders.length - 1);
  const workbook = Workbook.create();
  const plan = workbook.worksheets.add("清货建议");
  const summary = workbook.worksheets.add("总览");
  const women = workbook.worksheets.add("女包摘要");
  const legacy = workbook.worksheets.add("历史遗留清退");
  const issues = workbook.worksheets.add("数据问题");
  const rules = workbook.worksheets.add("规则参数");
  const sources = workbook.worksheets.add("来源");

  plan.getRangeByIndexes(0, 0, normalizedRows.length + 1, outputHeaders.length).values = [
    outputHeaders,
    ...normalizedRows.map((row) => [...row, ...Array(CALC_HEADERS.length).fill(null)]),
  ];
  const legacyHeaders = [...baseHeaders, "隔离原因", "经营指标", "补货量"];
  legacy.getRangeByIndexes(0, 0, legacyRows.length + 1, legacyHeaders.length).values = [
    legacyHeaders,
    ...legacyRows.map((row) => [...row, "PENCIL_CASE_LEGACY_CLEARANCE_ONLY", "排除", 0]),
  ];
  applyTableStyle(legacy, Math.max(legacyRows.length + 1, 2), legacyHeaders.length - 1);
  legacy.getRangeByIndexes(0, 0, Math.max(legacyRows.length + 1, 2), legacyHeaders.length).format.wrapText = true;
  rules.getRange("A1:B15").values = [
    ["规则参数", "当前值"],
    ["计算日期", asOfDate],
    ["默认采购周期C", RULE_DEFAULTS.procurementDays],
    ["默认预处理D", RULE_DEFAULTS.prepDays],
    ["默认海运可售E", RULE_DEFAULTS.seaDays],
    ["默认复查周期F", RULE_DEFAULTS.reviewCycleDays],
    ["默认安全系数N", RULE_DEFAULTS.safetyFactor],
    ["FBA最大目标天数", RULE_DEFAULTS.maxFbaTargetDays],
    ["课程库龄预警天数", RULE_DEFAULTS.courseAgeWarningDays],
    ["当前计费参考天数", RULE_DEFAULTS.feeReferenceAgeDays],
    ["清算回收低估比例", RULE_DEFAULTS.liquidationRecoveryLow],
    ["清算回收高估比例", RULE_DEFAULTS.liquidationRecoveryHigh],
    ["规则版本", "v1.1"],
    ["默认值来源", "老陈课程案例默认：C=7、D=2、E=35、F=7、N=1.2"],
    ["执行限制", "只读建议；费用日、Outlet资格和渠道报价每次运行重新核实。"],
  ];

  if (normalizedRows.length) {
    const formulaRows = normalizedRows.map((_, index) => {
      const row = index + 2;
      const ref = (key) =>
        indexes[key] >= 0 ? `${columnLetter(indexes[key])}${row}` : '""';
      const calc = (name) => `${columnLetter(calcIndexes[name])}${row}`;
      const formulas = buildExcelFormulaMap({
        ref,
        calc,
        parameters: formulaParameters(),
      });
      return CALC_HEADERS.map((header) => formulas[header]);
    });
    plan
      .getRangeByIndexes(1, calcStart, normalizedRows.length, CALC_HEADERS.length)
      .formulas = formulaRows;
  }

  applyTableStyle(plan, lastRow, outputHeaders.length - 1);
  plan.getRange(`A1:${lastColumn}${Math.max(lastRow, 2)}`).format.wrapText = true;
  plan.getRange(`A1:${lastColumn}1`).format.rowHeight = 64;
  if (lastRow >= 2) plan.getRange(`A2:${lastColumn}${lastRow}`).format.rowHeight = 64;
  plan.getRange(`A1:B${Math.max(lastRow, 2)}`).format.columnWidth = 18;
  if (indexes.title >= 0) {
    plan
      .getRange(`${columnLetter(indexes.title)}1:${columnLetter(indexes.title)}${Math.max(lastRow, 2)}`)
      .format.columnWidth = 52;
  }
  for (const key of ["notes", "reconciliation"]) {
    if (indexes[key] >= 0) {
      plan
        .getRange(`${columnLetter(indexes[key])}1:${columnLetter(indexes[key])}${Math.max(lastRow, 2)}`)
        .format.columnWidth = 52;
    }
  }
  for (const key of ["feeDate", "inventorySnapshot", "ageSnapshot", "salesWindowEnd"]) {
    if (indexes[key] >= 0 && lastRow >= 2) {
      plan
        .getRange(`${columnLetter(indexes[key])}2:${columnLetter(indexes[key])}${lastRow}`)
        .format.numberFormat = "yyyy-mm-dd";
    }
  }
  plan
    .getRange(
      `${columnLetter(calcIndexes["建议动作"])}1:${columnLetter(calcIndexes["建议动作"])}${Math.max(lastRow, 2)}`,
    )
    .format.columnWidth = 48;
  plan
    .getRange(
      `${columnLetter(calcIndexes["数据问题"])}1:${columnLetter(calcIndexes["数据问题"])}${Math.max(lastRow, 2)}`,
    )
    .format.columnWidth = 42;
  for (const name of [
    "最近7天日销",
    "第8-15天日销",
    "第16-30天日销",
    "加权日销A",
    "趋势T",
    "成长系数B1",
    "成长系数B2",
    "FBA供给天数",
  ]) {
    if (lastRow >= 2) {
      plan
        .getRange(
          `${columnLetter(calcIndexes[name])}2:${columnLetter(calcIndexes[name])}${lastRow}`,
        )
        .format.numberFormat = "0.00";
    }
  }
  for (const name of [
    "健康库存H",
    "下一周期目标库存",
    "FBA目标库存",
    "潜在超量数量",
    "费用风险数量",
    "清货目标数量",
  ]) {
    if (lastRow >= 2) {
      plan
        .getRange(
          `${columnLetter(calcIndexes[name])}2:${columnLetter(calcIndexes[name])}${lastRow}`,
        )
        .format.numberFormat = "#,##0";
    }
  }
  for (const name of ["清算回收低估", "清算回收高估"]) {
    if (lastRow >= 2) {
      plan
        .getRange(
          `${columnLetter(calcIndexes[name])}2:${columnLetter(calcIndexes[name])}${lastRow}`,
        )
        .format.numberFormat = "$#,##0.00";
    }
  }
  if (lastRow >= 2) {
    addStatusFormatting(
      plan,
      plan.getRange(
        `${columnLetter(calcIndexes["主状态"])}2:${columnLetter(calcIndexes["主状态"])}${lastRow}`,
      ),
    );
    plan.tables.add(`A1:${lastColumn}${lastRow}`, true, "ClearancePlanTable");
  }

  summary.getRange("A1:C15").values = [
    ["库存清货总览", "数量/值", "说明"],
    ["计算日期", asOfDate, "只读建议，不执行任何外部写操作"],
    ["店铺/站点", `${source.metadata?.sellerId ?? args["seller-id"] ?? "未提供"} / ${source.metadata?.marketplace ?? args.marketplace ?? "未提供"}`, source.metadata?.mode ?? "标准表"],
    ["SKU总数", null, "基础商品、90天销量、库存与库龄并集"],
    ["紧急清退", null, "优先处理费用和不可售风险"],
    ["主动清货", null, "分阶段促销或退出"],
    ["停补观察", null, "停止采购并复查"],
    ["待补货", null, "转交补货Skill"],
    ["健康维持", null, "维持当前策略"],
    ["潜在超量数量", null, "超过动态FBA目标，不等于都要清货"],
    ["费用风险数量", null, "费用快照日前预计无法消化"],
    ["清货目标数量", null, "仅紧急清退、主动清货填写"],
    ["缺库存待确认", null, "FBA报告缺行时不采用API库存"],
    ["缺经济数据暂定", null, "风险可判断，经济性需补成本/报价"],
    ["输出版本", null, "库存、库龄或费用日缺失时自动降为受限预警版"],
  ];
  const skuRange = `'清货建议'!${columnLetter(indexes.sku)}2:${columnLetter(indexes.sku)}${lastRow}`;
  const statusRange = `'清货建议'!${columnLetter(calcIndexes["主状态"])}2:${columnLetter(calcIndexes["主状态"])}${lastRow}`;
  const potentialRange = `'清货建议'!${columnLetter(calcIndexes["潜在超量数量"])}2:${columnLetter(calcIndexes["潜在超量数量"])}${lastRow}`;
  const feeRiskRange = `'清货建议'!${columnLetter(calcIndexes["费用风险数量"])}2:${columnLetter(calcIndexes["费用风险数量"])}${lastRow}`;
  const targetRange = `'清货建议'!${columnLetter(calcIndexes["清货目标数量"])}2:${columnLetter(calcIndexes["清货目标数量"])}${lastRow}`;
  const quantityStatusRange = `'清货建议'!${columnLetter(calcIndexes["数量状态"])}2:${columnLetter(calcIndexes["数量状态"])}${lastRow}`;
  summary.getRange("B4").formulas = [[`=COUNTA(${skuRange})`]];
  for (let row = 5; row <= 9; row += 1) {
    summary.getRange(`B${row}`).formulas = [[`=COUNTIF(${statusRange},A${row})`]];
  }
  summary.getRange("B10").formulas = [[`=SUM(${potentialRange})`]];
  summary.getRange("B11").formulas = [[`=SUM(${feeRiskRange})`]];
  summary.getRange("B12").formulas = [[`=SUM(${targetRange})`]];
  summary.getRange("B13").formulas = [[
    `=COUNTIF(${quantityStatusRange},"需要人工确认-缺库存")`,
  ]];
  summary.getRange("B14").formulas = [[
    `=COUNTIF(${quantityStatusRange},"暂定-缺经济数据")`,
  ]];
  summary.getRange("B15").formulas = [[
    `=IF(OR(B13>0,'数据问题'!B4>0,'数据问题'!B5>0,'数据问题'!B6>0),"受限预警版","标准分析版")`,
  ]];
  applyTableStyle(summary, 15, 2);
  summary.getRange("A1:A15").format.columnWidth = 26;
  summary.getRange("B1:B15").format.columnWidth = 30;
  summary.getRange("C1:C15").format.columnWidth = 54;
  summary.getRange("A1:C15").format.wrapText = true;
  summary.getRange("B2").format.numberFormat = "yyyy-mm-dd";
  summary.getRange("B10:B12").format.numberFormat = "#,##0";

  const selectedHeaders = [
    "seller_sku",
    "asin",
    "product_title",
    "product_group",
    "is_womens_bag",
    "主状态",
    "潜在超量数量",
    "费用风险数量",
    "清货目标数量",
    "数量状态",
    "建议动作",
    "数据问题",
  ];
  const selectedIndexes = [
    indexes.sku,
    indexes.asin,
    indexes.title,
    indexes.group,
    indexes.women,
    calcIndexes["主状态"],
    calcIndexes["潜在超量数量"],
    calcIndexes["费用风险数量"],
    calcIndexes["清货目标数量"],
    calcIndexes["数量状态"],
    calcIndexes["建议动作"],
    calcIndexes["数据问题"],
  ];
  const womenRows = normalizedRows
    .map((row, index) => ({ row, sourceRow: index + 2 }))
    .filter(({ row }) => indexes.women >= 0 && yes(row[indexes.women]));
  women
    .getRangeByIndexes(0, 0, womenRows.length + 1, selectedHeaders.length)
    .values = [
    selectedHeaders,
    ...womenRows.map(() => Array(selectedHeaders.length).fill(null)),
  ];
  womenRows.forEach(({ sourceRow }, rowIndex) => {
    selectedIndexes.forEach((sourceIndex, columnIndex) => {
      if (sourceIndex < 0) return;
      const reference = `'清货建议'!${columnLetter(sourceIndex)}${sourceRow}`;
      women.getCell(rowIndex + 1, columnIndex).formulas = [
        [`=IF(LEN(${reference}&"")=0,"",${reference})`],
      ];
    });
  });
  const womenLastRow = Math.max(2, womenRows.length + 1);
  applyTableStyle(women, womenLastRow, selectedHeaders.length - 1);
  women.getRange(`A1:L${womenLastRow}`).format.wrapText = true;
  women.getRange(`A1:B${womenLastRow}`).format.columnWidth = 18;
  women.getRange(`C1:C${womenLastRow}`).format.columnWidth = 52;
  women.getRange(`D1:I${womenLastRow}`).format.columnWidth = 16;
  women.getRange(`J1:J${womenLastRow}`).format.columnWidth = 22;
  women.getRange(`K1:K${womenLastRow}`).format.columnWidth = 48;
  women.getRange(`L1:L${womenLastRow}`).format.columnWidth = 42;
  if (womenRows.length) women.getRange(`G2:I${womenLastRow}`).format.numberFormat = "#,##0";
  if (womenRows.length) {
    women.getRange(`A2:L${womenLastRow}`).format.rowHeight = 64;
    addStatusFormatting(women, women.getRange(`F2:F${womenLastRow}`));
  }

  const issueRows = [
    ["缺FBA库存报告行", "补齐FBA库存报告；禁止采用API库存代替"],
    ["缺少FBA可售", "保持清货目标空白，人工确认"],
    ["缺库龄报告行", "补齐Inventory Age/Health报告后重跑"],
    ["缺少最老库龄", "维持受限预警，不下主动清货结论"],
    ["缺少费用快照日", "按当前站点重新核实费用日期"],
    ["缺少贡献利润/完整成本", "数量标为暂定，不承诺净回收"],
    ["API库存疑似占位", "已隔离，仅保留诊断"],
    ["库存对账不一致", "仅采用FBA库存报告"],
    ["女包分类待确认", "人工确认产品范围"],
  ];
  issues.getRangeByIndexes(0, 0, issueRows.length + 1, 3).values = [
    ["数据问题", "SKU数", "处理"],
    ...issueRows.map(([label, action]) => [label, null, action]),
  ];
  const countRange = (index) =>
    index >= 0
      ? `'清货建议'!${columnLetter(index)}2:${columnLetter(index)}${lastRow}`
      : null;
  const exactCount = (index, value) =>
    normalizedRows.length && index >= 0 ? `=COUNTIF(${countRange(index)},"${value}")` : "=0";
  const blankCount = (index) =>
    normalizedRows.length && index >= 0 ? `=COUNTBLANK(${countRange(index)})` : "=0";
  const issueFormulas = [
    indexes.inventoryPresent >= 0
      ? exactCount(indexes.inventoryPresent, "否")
      : blankCount(indexes.instock),
    blankCount(indexes.instock),
    indexes.agePresent >= 0
      ? exactCount(indexes.agePresent, "否")
      : blankCount(indexes.oldest),
    blankCount(indexes.oldest),
    blankCount(indexes.feeDate),
    blankCount(indexes.contribution),
    exactCount(indexes.apiSuspect, "是"),
    exactCount(indexes.apiMismatch, "是"),
    exactCount(indexes.women, "待确认"),
  ];
  issues.getRange(`B2:B${issueRows.length + 1}`).formulas =
    issueFormulas.map((formula) => [formula]);
  applyTableStyle(issues, issueRows.length + 1, 2);
  issues.getRange(`A1:A${issueRows.length + 1}`).format.columnWidth = 32;
  issues.getRange(`B1:B${issueRows.length + 1}`).format.columnWidth = 14;
  issues.getRange(`C1:C${issueRows.length + 1}`).format.columnWidth = 58;
  issues.getRange(`A1:C${issueRows.length + 1}`).format.wrapText = true;

  applyTableStyle(rules, 15, 1);
  rules.getRange("A1:A15").format.columnWidth = 30;
  rules.getRange("B1:B15").format.columnWidth = 68;
  rules.getRange("A1:B15").format.wrapText = true;
  rules.getRange("A14:B15").format.rowHeight = 42;
  rules.getRange("B2").format.numberFormat = "yyyy-mm-dd";
  rules.getRange("B7").format.numberFormat = "0.0";
  rules.getRange("B11:B12").format.numberFormat = "0%";

  const metadata = source.metadata || {};
  const sourceRows = [
    ["运行模式", metadata.mode || "标准表", metadata.inputPath || metadata.apiPath || ""],
    ["店铺", "sellerId", metadata.sellerId || args["seller-id"] || "未提供"],
    ["站点", "marketplace", metadata.marketplace || args.marketplace || "未提供"],
    ["销量查询窗口", "7/15/30/60/90天及前15天", metadata.salesWindows || `截至 ${args["as-of-date"] || isoToday()}`],
    ["计算日期", "as-of-date", asOfDate],
    ["FBA库存快照", "inventory snapshot", metadata.inventorySnapshotDate || "未提供"],
    ["库龄快照", "age snapshot", metadata.ageSnapshotDate || "未提供"],
    ["费用日依据", "运行时输入；不可写死", metadata.feeSnapshotDate || parseDate(args["fee-snapshot-date"]) || "未提供"],
    ["SellerSpace API JSON", "销量；API库存仅对账", metadata.apiPath || "未使用"],
    ["Amazon FBA库存报告", "可售、预留、在途、总库存唯一来源", metadata.inventoryReportPath || "未提供"],
    ["Amazon库龄报告", "库龄、预计附加费、不可售", metadata.ageReportPath || "未提供"],
    ["成本表", "经济性判断；可选", metadata.costPath || "未提供"],
    ["库存课程底稿", "动态目标、110–115天预警思想", process.env.COURSE_KB_ROOT ? `${process.env.COURSE_KB_ROOT}/03-库存管理与补货规划.md` : "external dependency: COURSE_KB_ROOT"],
    ["Amazon FBA Inventory", "90天供给与库存健康参考", "https://sell.amazon.com/blog/fba-inventory"],
    ["Amazon FBA New Selection", "清算毛回收区间参考", "https://sell.amazon.com/blog/fba-new-selection-program"],
  ];
  sources.getRangeByIndexes(0, 0, sourceRows.length + 1, 3).values = [
    ["来源/范围", "用途", "值/URL/路径"],
    ...sourceRows,
  ];
  applyTableStyle(sources, sourceRows.length + 1, 2);
  sources.getRange(`A1:A${sourceRows.length + 1}`).format.columnWidth = 30;
  sources.getRange(`B1:B${sourceRows.length + 1}`).format.columnWidth = 38;
  sources.getRange(`C1:C${sourceRows.length + 1}`).format.columnWidth = 82;
  sources.getRange(`A1:C${sourceRows.length + 1}`).format.wrapText = true;
  sources.getRange(`A2:C${sourceRows.length + 1}`).format.rowHeight = 46;
  for (const row of [6, 7, 8, 9]) {
    sources.getRange(`C${row}`).format.numberFormat = "yyyy-mm-dd";
  }

  return {
    workbook,
    rowCount: normalizedRows.length,
    metadata,
    outputHeaders,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const result = await buildWorkbook(args);
  await exportWorkbook(result.workbook, path.resolve(args.output));
  console.log(
    JSON.stringify({
      output: path.resolve(args.output),
      skuCount: result.rowCount,
      mode: result.metadata?.mode,
    }),
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.stack || error.message || error);
    process.exitCode = 1;
  });
}

module.exports = {
  ALIASES,
  buildWorkbook,
  indexAliases,
  isLegacyPencilCase,
  normalizeRows,
};
