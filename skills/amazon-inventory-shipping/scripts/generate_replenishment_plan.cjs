#!/usr/bin/env node

const path = require("node:path");
const {
  Workbook,
  applyBaseTableStyle,
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
  group: ["product_group", "产品组"],
  women: ["is_womens_bag", "是否女包"],
  clearance: ["clearance_status", "清货状态", "主状态"],
  u7: ["units_7d", "近7天销量"],
  u15: ["units_15d", "近15天销量"],
  u30: ["units_30d", "近30天销量"],
  u90: ["units_90d", "近90天销量"],
  prev15: ["units_prev_15d", "前15天销量"],
  seasonal: ["seasonal_product", "季节商品"],
  yoy: ["yoy_growth_ratio", "同比成长系数"],
  b1Override: ["b1_override", "B1覆盖"],
  b2Override: ["b2_override", "B2覆盖"],
  promo: ["promotion_overlap", "促销重叠"],
  instock: ["supply_instock", "FBA可售", "可售库存"],
  reserved: ["supply_reserved", "预留库存"],
  inbound: ["supply_inbound", "在途库存"],
  inboundDate: ["inbound_ready_date", "在途到仓可售日期", "在途预计可售日"],
  supplyTotal: ["supply_total", "FBA库存总量"],
  contribution: ["unit_contribution", "单件贡献利润"],
  longTail: ["long_tail_approved", "高利润长尾确认"],
  receiptDate: ["last_fba_receipt_date", "最后FBA入仓日期"],
  receiptUnits: ["last_fba_receipt_units", "最后FBA入仓数量"],
  postRestockUnits: ["post_restock_units", "入仓后实际发货件数"],
  receiptStatus: ["receipt_evidence_status", "入仓证据状态"],
  competitorCheck: ["fba_competitor_check_status", "FBA竞品检查状态"],
  fbaCompetitorCount: ["confirmed_fba_competitor_count", "FBA精确同款数量"],
  fbaCompetitorPrice: ["lowest_fba_competitor_landed_price", "FBA竞品最低到手价"],
  fbaCompetitorDelivery: ["fastest_fba_competitor_delivery_days", "FBA竞品最快配送天数"],
  c: ["procurement_days", "采购周期"],
  d: ["prep_days", "预处理周期"],
  f: ["review_cycle_days", "复查周期"],
  n: ["safety_factor", "安全系数"],
  expressDays: ["express_days", "快递可售天数"],
  airDays: ["air_days", "空运可售天数"],
  seaDays: ["sea_days", "海运可售天数"],
  expressCost: ["express_cost_per_unit", "快递单件成本"],
  airCost: ["air_cost_per_unit", "空运单件成本"],
  seaCost: ["sea_cost_per_unit", "海运单件成本"],
  moq: ["moq", "起订量"],
  carton: ["carton_qty", "整箱数量"],
};

const CALC_HEADERS = [
  "最近7天日销", "第8-15天日销", "第16-30天日销", "加权日销A", "趋势T",
  "成长系数B1", "成长系数B2", "健康库存H", "库存位置I", "原始补货Q",
  "净补货量", "建议采购数量", "FBA供给天数", "主状态", "补货级别",
  "快递建议量", "空运建议量", "海运建议量", "预计断货天数",
  "建议立即发FBA数量", "取整增加覆盖天数", "置信度", "数据问题",
  "入仓后观察天数", "入仓后日均销量", "补货后销量门禁", "FBA竞品复核状态",
  "可进入1688加购预览", "补货阻断码",
];

function isoToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

function normalizeInputRows(sourceRows, indexes) {
  const numericKeys = [
    "u7", "u15", "u30", "u90", "prev15", "yoy", "b1Override", "b2Override",
    "instock", "reserved", "inbound", "supplyTotal",
    "contribution", "c", "d", "f", "n", "expressDays", "airDays", "seaDays",
    "expressCost", "airCost", "seaCost", "moq", "carton", "receiptUnits",
    "postRestockUnits", "fbaCompetitorCount", "fbaCompetitorPrice", "fbaCompetitorDelivery",
  ];
  return sourceRows.map((sourceRow) => {
    const row = [...sourceRow];
    for (const key of numericKeys) {
      const index = indexes[key];
      const value = index >= 0 ? row[index] : null;
      if (value === null || value === undefined || String(value).trim() === "") continue;
      const parsed = Number(String(value).replace(/,/g, "").trim());
      if (Number.isFinite(parsed)) row[index] = parsed;
    }
    for (const key of ["inboundDate", "receiptDate"]) {
      const index = indexes[key];
      if (index < 0) continue;
      const parsedDate = parseDate(row[index]);
      if (parsedDate) row[index] = parsedDate;
    }
    return row;
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input || !args.output) {
    throw new Error(
      "Usage: generate_replenishment_plan.cjs --input inventory.csv|xlsx --output replenishment.xlsx [--as-of-date YYYY-MM-DD]",
    );
  }
  const asOfDate = parseDate(args["as-of-date"] || isoToday());
  if (!asOfDate) throw new Error("--as-of-date must use YYYY-MM-DD.");
  const source = await readTable(path.resolve(args.input));
  const indexes = Object.fromEntries(
    Object.entries(ALIASES).map(([key, aliases]) => [key, findHeader(source.headers, aliases)]),
  );
  if (indexes.sku < 0) throw new Error("Missing required column: seller_sku/SKU.");

  const outputHeaders = [
    ...source.headers,
    ...CALC_HEADERS.filter((header) => !source.headers.includes(header)),
  ];
  const normalizedRows = normalizeInputRows(source.rows, indexes);
  const rows = normalizedRows.map((row) => [
    ...row,
    ...Array(Math.max(0, outputHeaders.length - row.length)).fill(""),
  ]);
  const workbook = Workbook.create();
  const plan = workbook.worksheets.add("补货建议");
  const summary = workbook.worksheets.add("总览");
  const women = workbook.worksheets.add("女包摘要");
  const issues = workbook.worksheets.add("数据问题");
  const rules = workbook.worksheets.add("规则参数");
  const sources = workbook.worksheets.add("来源");
  plan.getRangeByIndexes(0, 0, rows.length + 1, outputHeaders.length).values = [
    outputHeaders,
    ...rows,
  ];

  rules.getRange("A1:B17").values = [
    ["规则参数", "当前值"],
    ["计算日期", asOfDate],
    ["默认采购周期C", 14],
    ["默认预处理D", 2],
    ["默认复查周期F", 7],
    ["默认安全系数N", 1.2],
    ["默认快递可售天数", 5],
    ["默认空运可售天数", 14],
    ["默认海运可售天数E", 35],
    ["FBA最大目标天数", 90],
    ["B1下限", 0.8],
    ["B1上限", 1.2],
    ["B2下限", 0.7],
    ["B2上限", 1.3],
    ["说明", "同时比较7天和14天场景；正式建议暂用14天，生产周期固定0。"],
    ["补货后最少观察天数", 7],
    ["FBA竞品证据最大年龄", 4],
  ];

  const calc = Object.fromEntries(CALC_HEADERS.map((header) => [header, outputHeaders.indexOf(header)]));
  const col = (index, row) => (index >= 0 ? `${columnLetter(index)}${row}` : '""');
  const empty = (reference) => `LEN(${reference}&"")=0`;
  const calcCell = (name, row) => `${columnLetter(calc[name])}${row}`;
  const lastRow = rows.length + 1;
  for (let r = 2; r <= lastRow; r += 1) {
    const u7 = col(indexes.u7, r);
    const u15 = col(indexes.u15, r);
    const u30 = col(indexes.u30, r);
    const prev15 = col(indexes.prev15, r);
    const instock = col(indexes.instock, r);
    const reserved = col(indexes.reserved, r);
    const inbound = col(indexes.inbound, r);
    const inboundDate = col(indexes.inboundDate, r);
    const supplyTotal = col(indexes.supplyTotal, r);
    const clearance = col(indexes.clearance, r);
    const contribution = col(indexes.contribution, r);
    const longTail = col(indexes.longTail, r);
    const promo = col(indexes.promo, r);
    const seasonal = col(indexes.seasonal, r);
    const yoy = col(indexes.yoy, r);
    const receiptDate = col(indexes.receiptDate, r);
    const receiptUnits = col(indexes.receiptUnits, r);
    const postRestockUnits = col(indexes.postRestockUnits, r);
    const receiptStatus = col(indexes.receiptStatus, r);
    const competitorCheck = col(indexes.competitorCheck, r);
    const c = indexes.c >= 0 ? `IF(${empty(col(indexes.c, r))},'规则参数'!$B$3,${col(indexes.c, r)})` : "'规则参数'!$B$3";
    const d = indexes.d >= 0 ? `IF(${empty(col(indexes.d, r))},'规则参数'!$B$4,${col(indexes.d, r)})` : "'规则参数'!$B$4";
    const f = indexes.f >= 0 ? `IF(${empty(col(indexes.f, r))},'规则参数'!$B$5,${col(indexes.f, r)})` : "'规则参数'!$B$5";
    const n = indexes.n >= 0 ? `MIN(1.4,MAX(1,IF(${empty(col(indexes.n, r))},'规则参数'!$B$6,${col(indexes.n, r)})))` : "'规则参数'!$B$6";
    const expressDays = indexes.expressDays >= 0 ? `IF(${empty(col(indexes.expressDays, r))},'规则参数'!$B$7,${col(indexes.expressDays, r)})` : "'规则参数'!$B$7";
    const airDays = indexes.airDays >= 0 ? `IF(${empty(col(indexes.airDays, r))},'规则参数'!$B$8,${col(indexes.airDays, r)})` : "'规则参数'!$B$8";
    const seaDays = indexes.seaDays >= 0 ? `IF(${empty(col(indexes.seaDays, r))},'规则参数'!$B$9,${col(indexes.seaDays, r)})` : "'规则参数'!$B$9";
    const d7 = calcCell("最近7天日销", r);
    const d815 = calcCell("第8-15天日销", r);
    const d1630 = calcCell("第16-30天日销", r);
    const a = calcCell("加权日销A", r);
    const t = calcCell("趋势T", r);
    const b1 = calcCell("成长系数B1", r);
    const b2 = calcCell("成长系数B2", r);
    const h = calcCell("健康库存H", r);
    const inventory = calcCell("库存位置I", r);
    const rawQ = calcCell("原始补货Q", r);
    const netQ = calcCell("净补货量", r);
    const finalQ = calcCell("建议采购数量", r);
    const cover = calcCell("FBA供给天数", r);
    const status = calcCell("主状态", r);
    const urgency = calcCell("补货级别", r);
    const expressQty = calcCell("快递建议量", r);
    const airQty = calcCell("空运建议量", r);
    const postDays = calcCell("入仓后观察天数", r);
    const postDaily = calcCell("入仓后日均销量", r);
    const postGate = calcCell("补货后销量门禁", r);
    const competitionGate = calcCell("FBA竞品复核状态", r);
    const planningCutoff = `'规则参数'!$B$2+${c}+${d}+${seaDays}+${f}`;
    const eligibleInbound = `IF(${inbound}<=0,0,IF(AND(NOT(${empty(inboundDate)}),${inboundDate}<=${planningCutoff}),MAX(0,${inbound}),0))`;

    plan.getRange(d7).formulas = [[`=IF(${empty(u7)},"",MAX(0,${u7})/7)`]];
    plan.getRange(d815).formulas = [[`=IF(OR(${empty(u7)},${empty(u15)}),"",MAX(0,${u15}-${u7})/8)`]];
    plan.getRange(d1630).formulas = [[`=IF(OR(${empty(u15)},${empty(u30)}),"",MAX(0,${u30}-${u15})/15)`]];
    plan.getRange(a).formulas = [[
      `=IF(AND(${empty(d7)},${empty(d815)},${empty(d1630)}),"",(IF(${empty(d7)},0,${d7}*0.5)+IF(${empty(d815)},0,${d815}*0.3)+IF(${empty(d1630)},0,${d1630}*0.2))/(IF(${empty(d7)},0,0.5)+IF(${empty(d815)},0,0.3)+IF(${empty(d1630)},0,0.2)))`,
    ]];
    const seasonalYes = `OR(LOWER(${seasonal})="是",LOWER(${seasonal})="yes",LOWER(${seasonal})="true")`;
    plan.getRange(t).formulas = [[
      `=IF(AND(${seasonalYes},NOT(${empty(yoy)}),${yoy}>0),${yoy},IF(OR(${empty(u15)},${empty(prev15)},${prev15}<=0),1,MAX(0,${u15})/${prev15}))`,
    ]];
    plan.getRange(b1).formulas = [[`=IF(${empty(a)},"",IF(NOT(${empty(col(indexes.b1Override, r))}),MIN('规则参数'!$B$12,MAX('规则参数'!$B$11,${col(indexes.b1Override, r)})),MIN('规则参数'!$B$12,MAX('规则参数'!$B$11,${t}))))`]];
    plan.getRange(b2).formulas = [[`=IF(${empty(a)},"",IF(NOT(${empty(col(indexes.b2Override, r))}),MIN('规则参数'!$B$14,MAX('规则参数'!$B$13,${col(indexes.b2Override, r)})),MIN('规则参数'!$B$14,MAX('规则参数'!$B$13,${t}))))`]];
    plan.getRange(h).formulas = [[`=IF(${empty(a)},"",${a}*${b1}*(${c}+${d}+${seaDays})*${n})`]];
    plan.getRange(inventory).formulas = [[
      `=IF(NOT(${empty(supplyTotal)}),MAX(0,${supplyTotal})-MAX(0,${inbound})+${eligibleInbound},MAX(0,${instock})+MAX(0,${reserved})+${eligibleInbound})`,
    ]];
    plan.getRange(rawQ).formulas = [[`=IF(${empty(a)},"",${a}*${b2}*${f}+${h}-${inventory})`]];
    plan.getRange(netQ).formulas = [[`=IF(${empty(rawQ)},"",MAX(0,${rawQ}))`]];
    const moq = col(indexes.moq, r);
    const carton = col(indexes.carton, r);
    const blocked = `OR(${clearance}="紧急清退",${clearance}="主动清货",${clearance}="停补观察",${postGate}="ZERO_SALES_AFTER_RESTOCK_7D")`;
    const continuous = `AND(${d7}>0,${d815}>0,${d1630}>0)`;
    const longTailOk = `OR(LOWER(${longTail})="是",LOWER(${longTail})="yes",LOWER(${longTail})="true")`;
    plan.getRange(finalQ).formulas = [[
      `=IF(OR(${empty(netQ)},${blocked},NOT(OR(${continuous},${longTailOk}))),0,IF(${netQ}<=0,0,IF(${carton}>0,ROUNDUP(MAX(${netQ},MAX(0,${moq}))/${carton},0)*${carton},ROUNDUP(MAX(${netQ},MAX(0,${moq})),0))))`,
    ]];
    plan.getRange(cover).formulas = [[`=IF(OR(${empty(a)},${empty(instock)}),"",IF(${a}<=0,IF(${instock}>0,99999,0),MAX(0,${instock})/(${a}*${b1})))`]];
    plan.getRange(status).formulas = [[
      `=IF(${postGate}="ZERO_SALES_AFTER_RESTOCK_7D","停补观察",IF(${blocked},${clearance},IF(AND(${finalQ}>0,OR(${continuous},${longTailOk})),"待补货",IF(AND(${netQ}>0,NOT(OR(${continuous},${longTailOk}))),"停补观察","健康维持"))))`,
    ]];
    plan.getRange(urgency).formulas = [[
      `=IF(${status}<>"待补货","不补货",IF(${cover}<${expressDays},"预计断货",IF(${cover}<${seaDays},"加急补货","常规补货")))`,
    ]];
    plan.getRange(expressQty).formulas = [[
      `=IF(OR(${status}<>"待补货",${cover}>=${seaDays}),0,MIN(${finalQ},ROUNDUP(ROUND(MAX(0,${airDays}-${cover})*${a}*${b1},6),0)))`,
    ]];
    plan.getRange(airQty).formulas = [[
      `=IF(${status}<>"待补货",0,MIN(MAX(0,${finalQ}-${expressQty}),ROUNDUP(ROUND(MAX(0,${seaDays}-MAX(${airDays},${cover}))*${a}*${b1},6),0)))`,
    ]];
    plan.getRange(calcCell("海运建议量", r)).formulas = [[`=MAX(0,${finalQ}-${expressQty}-${airQty})`]];
    plan.getRange(calcCell("预计断货天数", r)).formulas = [[`=IF(${status}<>"待补货",0,MAX(0,${expressDays}-${cover}))`]];
    const fbaPosition = `IF(NOT(${empty(supplyTotal)}),MAX(0,${supplyTotal})-MAX(0,${inbound})+${eligibleInbound},MAX(0,${instock})+MAX(0,${reserved})+${eligibleInbound})`;
    plan.getRange(calcCell("建议立即发FBA数量", r)).formulas = [[
      `=0`,
    ]];
    plan.getRange(calcCell("取整增加覆盖天数", r)).formulas = [[
      `=IF(OR(${empty(a)},${a}<=0,${finalQ}=0),0,MAX(0,${finalQ}-${netQ})/(${a}*${b1}))`,
    ]];
    plan.getRange(calcCell("置信度", r)).formulas = [[
      `=IF(OR(${empty(a)},${empty(instock)},${empty(contribution)},${empty(clearance)},AND(${inbound}>0,${empty(inboundDate)})),"低",IF(OR(${promo}="是",${empty(prev15)},${empty(col(indexes.c, r))},${empty(col(indexes.seaDays, r))}),"中","高"))`,
    ]];
    const sku = col(indexes.sku, r);
    plan.getRange(postDays).formulas = [[
      `=IF(OR(${empty(receiptDate)},${receiptDate}>'规则参数'!$B$2),"",'规则参数'!$B$2-${receiptDate})`,
    ]];
    plan.getRange(postDaily).formulas = [[
      `=IF(OR(${empty(postDays)},${postDays}<=0,${empty(postRestockUnits)}),"",MAX(0,${postRestockUnits})/${postDays})`,
    ]];
    plan.getRange(postGate).formulas = [[
      `=IF(OR(${empty(receiptDate)},${empty(receiptUnits)},${receiptUnits}<=0,${empty(postRestockUnits)},${postRestockUnits}<0,NOT(OR(${receiptStatus}="SYSTEM_CONFIRMED",${receiptStatus}="USER_CONFIRMED")),${receiptDate}>'规则参数'!$B$2),"LAST_FBA_RECEIPT_UNVERIFIED",IF(${postDays}<'规则参数'!$B$16,"POST_RESTOCK_OBSERVATION_PENDING",IF(${postRestockUnits}=0,"ZERO_SALES_AFTER_RESTOCK_7D","PASSED")))`,
    ]];
    plan.getRange(competitionGate).formulas = [[
      `=IF(OR(${competitorCheck}="COMPLETE_NO_FBA_EXACT_COMPETITOR",${competitorCheck}="FBA_EXACT_COMPETITOR_FOUND",${competitorCheck}="COMPLETE"),${competitorCheck},"FBA_COMPETITOR_CHECK_INCOMPLETE")`,
    ]];
    plan.getRange(calcCell("可进入1688加购预览", r)).formulas = [[
      `=IF(AND(${status}="待补货",${finalQ}>0,${postGate}="PASSED",${competitionGate}<>"FBA_COMPETITOR_CHECK_INCOMPLETE"),"是","否")`,
    ]];
    plan.getRange(calcCell("补货阻断码", r)).formulas = [[
      `=IF(${postGate}="PASSED","",${postGate})&IF(${competitionGate}="FBA_COMPETITOR_CHECK_INCOMPLETE",IF(${postGate}="PASSED","",";")&"FBA_COMPETITOR_CHECK_INCOMPLETE","")`,
    ]];
    plan.getRange(calcCell("数据问题", r)).formulas = [[
      `=IF(${empty(sku)},"缺少SKU；","")&IF(${empty(instock)},"缺少FBA可售；","")&IF(${empty(a)},"缺少销量窗口；","")&IF(${empty(clearance)},"未导入清货状态；","")&IF(${empty(contribution)},"利润待确认，数量仅暂定；","")&IF(${promo}="是","促销与销量窗口重叠；","")&IF(AND(${inbound}>0,${empty(inboundDate)}),"在途到仓日待确认，暂不计入I；","")&IF(${postGate}<>"PASSED",${postGate}&"；","")&IF(${competitionGate}="FBA_COMPETITOR_CHECK_INCOMPLETE","FBA_COMPETITOR_CHECK_INCOMPLETE；","")`,
    ]];
  }

  applyBaseTableStyle(plan, lastRow, outputHeaders.length - 1);
  plan.freezePanes.freezeColumns(2);
  plan.getRange(`A1:${columnLetter(outputHeaders.length - 1)}${lastRow}`).format.wrapText = true;
  plan.getRange(`A1:${columnLetter(outputHeaders.length - 1)}1`).format.rowHeight = 64;
  plan.getRange(`A1:F${lastRow}`).format.columnWidth = 18;
  if (indexes.title >= 0) plan.getRange(`${columnLetter(indexes.title)}1:${columnLetter(indexes.title)}${lastRow}`).format.columnWidth = 38;
  if (indexes.inboundDate >= 0) plan.getRange(`${columnLetter(indexes.inboundDate)}2:${columnLetter(indexes.inboundDate)}${lastRow}`).format.numberFormat = "yyyy-mm-dd";
  plan.getRange(`${columnLetter(calc["数据问题"])}1:${columnLetter(calc["数据问题"])}${lastRow}`).format.columnWidth = 42;
  for (const name of ["最近7天日销", "第8-15天日销", "第16-30天日销", "加权日销A", "趋势T", "成长系数B1", "成长系数B2", "FBA供给天数", "预计断货天数", "取整增加覆盖天数"]) {
    plan.getRange(`${columnLetter(calc[name])}2:${columnLetter(calc[name])}${lastRow}`).format.numberFormat = "0.00";
  }
  for (const name of ["健康库存H", "库存位置I", "原始补货Q", "净补货量", "建议采购数量", "快递建议量", "空运建议量", "海运建议量", "建议立即发FBA数量"]) {
    plan.getRange(`${columnLetter(calc[name])}2:${columnLetter(calc[name])}${lastRow}`).format.numberFormat = "#,##0";
  }
  const statusRange = plan.getRange(`${columnLetter(calc["主状态"])}2:${columnLetter(calc["主状态"])}${lastRow}`);
  statusRange.conditionalFormats.add("containsText", { text: "待补货", format: { fill: "#DBEAFE", font: { color: "#1E40AF", bold: true } } });
  statusRange.conditionalFormats.add("containsText", { text: "健康维持", format: { fill: "#D1FAE5", font: { color: "#065F46" } } });
  statusRange.conditionalFormats.add("containsText", { text: "停补观察", format: { fill: "#FEF3C7", font: { color: "#92400E" } } });
  statusRange.conditionalFormats.add("containsText", { text: "主动清货", format: { fill: "#FED7AA", font: { color: "#9A3412" } } });
  statusRange.conditionalFormats.add("containsText", { text: "紧急清退", format: { fill: "#FECACA", font: { color: "#991B1B", bold: true } } });
  if (rows.length) plan.tables.add(`A1:${columnLetter(outputHeaders.length - 1)}${lastRow}`, true, "ReplenishmentPlanTable");

  summary.getRange("A1:C8").values = [
    ["补货规划总览", "数量", "说明"],
    ["计算日期", asOfDate, "只读建议，不采购、不创建货件"],
    ["SKU总数", "", "当前单站点范围"],
    ["待补货", "", "含常规和加急"],
    ["预计断货", "", "最快方式仍可能断货"],
    ["加急补货", "", "海运赶不上"],
    ["常规补货", "", "海运可衔接"],
    ["被清货状态阻断", "", "前三种状态补货强制为0"],
  ];
  summary.getRange("B3").formulas = [[`=COUNTA('补货建议'!${columnLetter(indexes.sku)}2:${columnLetter(indexes.sku)}${lastRow})`]];
  summary.getRange("B4").formulas = [[`=COUNTIF('补货建议'!${columnLetter(calc["主状态"])}2:${columnLetter(calc["主状态"])}${lastRow},"待补货")`]];
  summary.getRange("B5").formulas = [[`=COUNTIF('补货建议'!${columnLetter(calc["补货级别"])}2:${columnLetter(calc["补货级别"])}${lastRow},"预计断货")`]];
  summary.getRange("B6").formulas = [[`=COUNTIF('补货建议'!${columnLetter(calc["补货级别"])}2:${columnLetter(calc["补货级别"])}${lastRow},"加急补货")`]];
  summary.getRange("B7").formulas = [[`=COUNTIF('补货建议'!${columnLetter(calc["补货级别"])}2:${columnLetter(calc["补货级别"])}${lastRow},"常规补货")`]];
  summary.getRange("B8").formulas = [[`=COUNTIF('补货建议'!${columnLetter(calc["主状态"])}2:${columnLetter(calc["主状态"])}${lastRow},"紧急清退")+COUNTIF('补货建议'!${columnLetter(calc["主状态"])}2:${columnLetter(calc["主状态"])}${lastRow},"主动清货")+COUNTIF('补货建议'!${columnLetter(calc["主状态"])}2:${columnLetter(calc["主状态"])}${lastRow},"停补观察")`]];
  applyBaseTableStyle(summary, 8, 2);
  summary.getRange("A1:B8").format.columnWidth = 26;
  summary.getRange("C1:C8").format.columnWidth = 52;
  summary.getRange("A1:C8").format.wrapText = true;
  summary.getRange("B2").format.numberFormat = "yyyy-mm-dd";

  const selectedCols = ["seller_sku", "asin", "product_title", "product_group", "is_womens_bag", "主状态", "补货级别", "建议采购数量", "快递建议量", "空运建议量", "海运建议量", "数据问题"];
  const selectedIndexes = [
    indexes.sku,
    indexes.asin,
    indexes.title,
    indexes.group,
    indexes.women,
    calc["主状态"],
    calc["补货级别"],
    calc["建议采购数量"],
    calc["快递建议量"],
    calc["空运建议量"],
    calc["海运建议量"],
    calc["数据问题"],
  ];
  const womenRows = source.rows
    .map((row, index) => ({ row, sourceRow: index + 2 }))
    .filter(({ row }) => indexes.women >= 0 && ["是", "yes", "true"].includes(String(row[indexes.women] ?? "").trim().toLowerCase()));
  women.getRangeByIndexes(0, 0, womenRows.length + 1, selectedCols.length).values = [selectedCols, ...womenRows.map(() => Array(selectedCols.length).fill(""))];
  womenRows.forEach(({ sourceRow }, idx) => {
    selectedIndexes.forEach((sourceIndex, colIndex) => {
      if (sourceIndex >= 0) {
        const reference = `'补货建议'!${columnLetter(sourceIndex)}${sourceRow}`;
        women.getCell(idx + 1, colIndex).formulas = [[`=IF(LEN(${reference}&"")=0,"",${reference})`]];
      }
    });
  });
  applyBaseTableStyle(women, womenRows.length + 1, selectedCols.length - 1);
  women.getRange(`A1:L${Math.max(2, womenRows.length + 1)}`).format.wrapText = true;
  women.getRange("A1:B" + Math.max(2, womenRows.length + 1)).format.columnWidth = 20;
  women.getRange("C1:C" + Math.max(2, womenRows.length + 1)).format.columnWidth = 38;
  women.getRange("D1:K" + Math.max(2, womenRows.length + 1)).format.columnWidth = 16;
  women.getRange("L1:L" + Math.max(2, womenRows.length + 1)).format.columnWidth = 46;

  issues.getRange("A1:C2").values = [["说明", "定位", "处理"], ["所有问题保留在补货建议的数据问题列", "按SKU筛选", "补齐利润、库存、周期后重新生成"]];
  applyBaseTableStyle(issues, 2, 2);
  issues.getRange("A1:C2").format.columnWidth = 46;
  issues.getRange("A1:C2").format.wrapText = true;

  applyBaseTableStyle(rules, 17, 1);
  rules.getRange("A1:A17").format.columnWidth = 30;
  rules.getRange("B1:B17").format.columnWidth = 64;
  rules.getRange("A1:B17").format.wrapText = true;
  rules.getRange("B2").format.numberFormat = "yyyy-mm-dd";
  rules.getRange("B6").format.numberFormat = "0.0";

  sources.getRange("A1:C3").values = [
    ["来源", "用途", "URL/路径"],
    ["库存课程底稿", "健康库存、补货和运输桥接公式", process.env.COURSE_KB_ROOT ? `${process.env.COURSE_KB_ROOT}/03-库存管理与补货规划.md` : "external dependency: COURSE_KB_ROOT"],
    ["Amazon FBA Inventory", "90天供给与库存健康参考", "https://sell.amazon.com/blog/fba-inventory"],
  ];
  applyBaseTableStyle(sources, 3, 2);
  sources.getRange("A1:B3").format.columnWidth = 32;
  sources.getRange("C1:C3").format.columnWidth = 82;
  sources.getRange("A1:C3").format.wrapText = true;

  await exportWorkbook(workbook, path.resolve(args.output));
  console.log(`Wrote ${rows.length} SKU rows to ${path.resolve(args.output)}`);
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exitCode = 1;
});
