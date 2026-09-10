const RULE_DEFAULTS = Object.freeze({
  procurementDays: 7,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 7,
  safetyFactor: 1.2,
  maxFbaTargetDays: 90,
  courseAgeWarningDays: 110,
  feeReferenceAgeDays: 181,
  liquidationRecoveryLow: 0.05,
  liquidationRecoveryHigh: 0.1,
});

const CALC_HEADERS = Object.freeze([
  "最近7天日销",
  "第8-15天日销",
  "第16-30天日销",
  "加权日销A",
  "趋势T",
  "成长系数B1",
  "成长系数B2",
  "健康库存H",
  "下一周期目标库存",
  "FBA目标库存",
  "FBA供给天数",
  "距费用日天数",
  "潜在超量数量",
  "费用风险数量",
  "清货目标数量",
  "数量状态",
  "主状态",
  "建议动作",
  "风险判断置信度",
  "经济性置信度",
  "数据问题",
  "清算回收低估",
  "清算回收高估",
]);

function finiteNumber(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const parsed = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

function numberOr(value, fallback = 0) {
  const parsed = finiteNumber(value);
  return parsed === null ? fallback : parsed;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function isAffirmative(value) {
  return ["是", "yes", "true", "1"].includes(String(value ?? "").trim().toLowerCase());
}

function reportFlagMissing(input, key) {
  if (!Object.prototype.hasOwnProperty.call(input, key)) return false;
  return !isAffirmative(input[key]);
}

function weightedDailySales(input) {
  const u7 = finiteNumber(input.units7);
  const u15 = finiteNumber(input.units15);
  const u30 = finiteNumber(input.units30);
  const segments = [
    { value: u7 === null ? null : Math.max(0, u7) / 7, weight: 0.5 },
    {
      value: u7 === null || u15 === null ? null : Math.max(0, u15 - u7) / 8,
      weight: 0.3,
    },
    {
      value: u15 === null || u30 === null ? null : Math.max(0, u30 - u15) / 15,
      weight: 0.2,
    },
  ];
  const available = segments.filter((segment) => segment.value !== null);
  if (!available.length) {
    return { segments: segments.map((segment) => segment.value), dailySales: null, confidence: "低" };
  }
  const weight = available.reduce((sum, segment) => sum + segment.weight, 0);
  const dailySales =
    available.reduce((sum, segment) => sum + segment.value * segment.weight, 0) / weight;
  return {
    segments: segments.map((segment) => segment.value),
    dailySales,
    confidence: available.length === 3 ? "高" : available.length === 2 ? "中" : "低",
  };
}

function growthCoefficients(units15, previous15) {
  const recent = finiteNumber(units15);
  const previous = finiteNumber(previous15);
  if (recent === null || previous === null || previous <= 0) {
    return { trend: 1, b1: 1, b2: 1, confidence: "低" };
  }
  const trend = Math.max(0, recent) / previous;
  return {
    trend,
    b1: clamp(trend, 0.8, 1.2),
    b2: clamp(trend, 0.7, 1.3),
    confidence: "高",
  };
}

function economicConfidence(input) {
  const contribution = finiteNumber(input.unitContribution);
  const landed = finiteNumber(input.unitLandedCost);
  const fees = finiteNumber(input.amazonFeesPerUnit);
  const resale = finiteNumber(input.externalResaleValue);
  const removal = finiteNumber(input.removalFeePerUnit);
  if (contribution !== null && resale !== null && removal !== null) return "高";
  if (contribution !== null || (landed !== null && fees !== null)) return "中";
  return "低";
}

function calculateClearance(input) {
  const velocity = weightedDailySales({
    units7: input.units7,
    units15: input.units15,
    units30: input.units30,
  });
  const growth = growthCoefficients(input.units15, input.previous15);
  const [daily7, daily8To15, daily16To30] = velocity.segments;
  const a = velocity.dailySales;
  const b1 = growth.b1;
  const b2 = growth.b2;
  const c = numberOr(input.procurementDays, RULE_DEFAULTS.procurementDays);
  const d = numberOr(input.prepDays, RULE_DEFAULTS.prepDays);
  const e = numberOr(input.seaDays, RULE_DEFAULTS.seaDays);
  const f = numberOr(input.reviewCycleDays, RULE_DEFAULTS.reviewCycleDays);
  const n = clamp(numberOr(input.safetyFactor, RULE_DEFAULTS.safetyFactor), 1, 1.4);
  const instockValue = finiteNumber(input.supplyInstock);
  const instock = instockValue === null ? null : Math.max(0, instockValue);
  const health = a === null ? null : a * b1 * (c + d + e) * n;
  const cycleTarget = a === null ? null : health + a * b2 * f;
  const fbaTarget =
    a === null ? null : Math.min(cycleTarget, a * RULE_DEFAULTS.maxFbaTargetDays);
  const coverageDays =
    a === null || instock === null
      ? null
      : a <= 0
        ? instock > 0
          ? Infinity
          : 0
        : instock / (a * b1);
  const potentialExcessQty =
    instock === null || fbaTarget === null ? null : Math.max(0, instock - fbaTarget);

  const nextSnapshotAged = finiteNumber(input.nextSnapshotAgedUnits);
  const daysToSnapshot = finiteNumber(input.daysToSnapshot);
  const feeRiskQty =
    a === null || nextSnapshotAged === null || daysToSnapshot === null
      ? null
      : Math.max(0, nextSnapshotAged - a * Math.max(0, daysToSnapshot));

  const stranded = numberOr(input.strandedUnits, 0);
  const unfulfillable = numberOr(input.unfulfillableUnits, 0);
  const surcharge = numberOr(input.estimatedAgedSurcharge, 0);
  const oldestValue = finiteNumber(input.oldestAgeDays);
  const oldest = numberOr(input.oldestAgeDays, 0);
  const units60 = finiteNumber(input.units60);
  const missingCritical =
    a === null ||
    instock === null ||
    oldestValue === null ||
    daysToSnapshot === null ||
    reportFlagMissing(input, "inventoryReportPresent") ||
    reportFlagMissing(input, "ageReportPresent");
  const declining = growth.trend < 0.8;
  const overTarget =
    fbaTarget !== null && instock !== null && instock > fbaTarget;
  const noSales60 = units60 !== null && units60 <= 0 && instock !== null && instock > 0;
  const projectedDaysTo181 =
    coverageDays === null ? null : coverageDays;
  const aged110Risk =
    projectedDaysTo181 !== null &&
    oldest >= RULE_DEFAULTS.courseAgeWarningDays &&
    oldest + projectedDaysTo181 >= RULE_DEFAULTS.feeReferenceAgeDays;
  const urgent =
    stranded > 0 ||
    unfulfillable > 0 ||
    (feeRiskQty !== null && feeRiskQty > 0) ||
    (surcharge > 0 && potentialExcessQty !== null && potentialExcessQty > 0);
  const active =
    !missingCritical &&
    ((coverageDays !== null &&
      coverageDays > RULE_DEFAULTS.maxFbaTargetDays &&
      growth.trend <= 1) ||
      aged110Risk ||
      (noSales60 && oldest >= RULE_DEFAULTS.courseAgeWarningDays));
  const continuousDemand =
    daily7 !== null &&
    daily8To15 !== null &&
    daily16To30 !== null &&
    daily7 > 0 &&
    daily8To15 > 0 &&
    daily16To30 > 0;
  const replenishCandidate =
    cycleTarget !== null && instock !== null && instock < cycleTarget;
  const replenishEligible = continuousDemand || isAffirmative(input.longTailApproved);

  let status;
  if (urgent) {
    status = "紧急清退";
  } else if (active) {
    status = "主动清货";
  } else if (
    missingCritical ||
    declining ||
    overTarget ||
    (replenishCandidate && !replenishEligible)
  ) {
    status = "停补观察";
  } else if (replenishCandidate && replenishEligible) {
    status = "待补货";
  } else {
    status = "健康维持";
  }

  const targetBase =
    potentialExcessQty === null
      ? null
      : Math.max(potentialExcessQty, feeRiskQty === null ? 0 : feeRiskQty);
  const clearanceTargetQty =
    instock === null
      ? null
      : status === "紧急清退" || status === "主动清货"
        ? Math.min(instock, Math.ceil(targetBase ?? 0))
        : 0;
  const quantityStatus =
    instock === null
      ? "需要人工确认-缺库存"
      : finiteNumber(input.unitContribution) === null
        ? "暂定-缺经济数据"
        : "已计算";
  const riskConfidence =
    missingCritical
      ? "低"
      : velocity.confidence !== "高" ||
          growth.confidence !== "高" ||
          nextSnapshotAged === null
        ? "中"
        : "高";
  const issues = [];
  if (instock === null) issues.push("缺少FBA可售");
  if (a === null) issues.push("缺少销量窗口");
  if (oldestValue === null) issues.push("缺少最老库龄");
  if (daysToSnapshot === null) issues.push("缺少费用快照日");
  if (finiteNumber(input.unitContribution) === null) issues.push("利润待确认");

  return {
    daily7,
    daily8To15,
    daily16To30,
    dailySales: a,
    trend: growth.trend,
    b1,
    b2,
    healthInventory: health,
    cycleTarget,
    fbaTarget,
    coverageDays,
    potentialExcessQty,
    feeRiskQty,
    clearanceTargetQty,
    quantityStatus,
    status,
    riskConfidence,
    economicConfidence: economicConfidence(input),
    dataIssues: issues,
    // v1.0 compatibility aliases.
    atRiskUnits: feeRiskQty,
    clearanceQty: clearanceTargetQty,
    confidence: riskConfidence,
  };
}

function buildExcelFormulaMap(context) {
  const { ref, calc, parameters } = context;
  const empty = (reference) => `LEN(${reference}&"")=0`;
  const u7 = ref("u7");
  const u15 = ref("u15");
  const u30 = ref("u30");
  const u60 = ref("u60");
  const prev15 = ref("prev15");
  const instock = ref("instock");
  const oldest = ref("oldest");
  const nextAged = ref("nextAged");
  const stranded = ref("stranded");
  const unfulfillable = ref("unfulfillable");
  const surcharge = ref("surcharge");
  const feeDate = ref("feeDate");
  const longTail = ref("longTail");
  const contribution = ref("contribution");
  const landedCost = ref("landedCost");
  const amazonFees = ref("amazonFees");
  const externalValue = ref("externalValue");
  const removalFee = ref("removalFee");
  const inventoryPresent = ref("inventoryPresent");
  const agePresent = ref("agePresent");
  const apiSuspect = ref("apiSuspect");
  const reconciliation = ref("reconciliation");
  const women = ref("women");
  const d7 = calc("最近7天日销");
  const d815 = calc("第8-15天日销");
  const d1630 = calc("第16-30天日销");
  const a = calc("加权日销A");
  const t = calc("趋势T");
  const b1 = calc("成长系数B1");
  const b2 = calc("成长系数B2");
  const h = calc("健康库存H");
  const cycle = calc("下一周期目标库存");
  const fbaTarget = calc("FBA目标库存");
  const cover = calc("FBA供给天数");
  const daysFee = calc("距费用日天数");
  const potential = calc("潜在超量数量");
  const feeRisk = calc("费用风险数量");
  const target = calc("清货目标数量");
  const status = calc("主状态");
  const c = `IF(${empty(ref("c"))},${parameters.procurementDays},${ref("c")})`;
  const d = `IF(${empty(ref("d"))},${parameters.prepDays},${ref("d")})`;
  const e = `IF(${empty(ref("e"))},${parameters.seaDays},${ref("e")})`;
  const f = `IF(${empty(ref("f"))},${parameters.reviewCycleDays},${ref("f")})`;
  const n = `MIN(1.4,MAX(1,IF(${empty(ref("n"))},${parameters.safetyFactor},${ref("n")})))`;
  const ageFields = [
    "age181",
    "age211",
    "age241",
    "age271",
    "age301",
    "age331",
    "age365",
  ].map(ref);
  const allAgeEmpty = `AND(${ageFields.map(empty).join(",")})`;
  const ageSum = ageFields.map((reference) => `MAX(0,${reference})`).join("+");
  const rawCriticalMissing = [
    empty(a),
    empty(instock),
    empty(feeDate),
    empty(oldest),
    inventoryPresent === '""' ? null : `NOT(OR(LOWER(${inventoryPresent})="是",LOWER(${inventoryPresent})="yes",LOWER(${inventoryPresent})="true"))`,
    agePresent === '""' ? null : `NOT(OR(LOWER(${agePresent})="是",LOWER(${agePresent})="yes",LOWER(${agePresent})="true"))`,
  ].filter(Boolean);
  const criticalMissing = `OR(${rawCriticalMissing.join(",")})`;
  const continuous = `AND(${d7}>0,${d815}>0,${d1630}>0)`;
  const longTailOk = `OR(LOWER(${longTail})="是",LOWER(${longTail})="yes",LOWER(${longTail})="true")`;
  const urgent = `OR(${stranded}>0,${unfulfillable}>0,AND(NOT(${empty(feeRisk)}),${feeRisk}>0),AND(${surcharge}>0,${potential}>0))`;
  const active = `AND(NOT(${criticalMissing}),OR(AND(${cover}>${parameters.maxFbaTargetDays},${t}<=1),AND(${oldest}>=${parameters.courseAgeWarningDays},${oldest}+${cover}>=${parameters.feeReferenceAgeDays}),AND(NOT(${empty(u60)}),${u60}<=0,${instock}>0,${oldest}>=${parameters.courseAgeWarningDays})))`;
  const replenishCandidate = `AND(${instock}<${cycle},NOT(${empty(cycle)}))`;
  const riskMedium = `OR(${empty(prev15)},${prev15}<=0,${empty(u7)},${empty(u15)},${empty(u30)},${empty(nextAged)})`;
  const recoveryAveragePrice = `IF(OR(${empty(u30)},${u30}<=0,${empty(ref("revenue"))}),"",${ref("revenue")}/${u30})`;
  const maybeIssue = (reference, label) =>
    reference === '""' ? `""` : `IF(${empty(reference)},"${label}；","")`;
  const inventoryFlagIssue =
    inventoryPresent === '""'
      ? `""`
      : `IF(OR(LOWER(${inventoryPresent})="是",LOWER(${inventoryPresent})="yes",LOWER(${inventoryPresent})="true"),"","缺FBA库存报告行；")`;
  const ageFlagIssue =
    agePresent === '""'
      ? `""`
      : `IF(OR(LOWER(${agePresent})="是",LOWER(${agePresent})="yes",LOWER(${agePresent})="true"),"","缺库龄报告行；")`;
  const apiIssue =
    apiSuspect === '""'
      ? `""`
      : `IF(OR(LOWER(${apiSuspect})="是",LOWER(${apiSuspect})="yes",LOWER(${apiSuspect})="true"),"API库存疑似占位，已隔离；","")`;
  const reconciliationIssue =
    reconciliation === '""'
      ? `""`
      : `IF(${empty(reconciliation)},"",${reconciliation}&"；")`;
  const womenIssue =
    women === '""'
      ? `""`
      : `IF(OR(${empty(women)},LOWER(${women})="待确认"),"女包分类待确认；","")`;

  return {
    "最近7天日销": `=IF(${empty(u7)},"",MAX(0,${u7})/7)`,
    "第8-15天日销": `=IF(OR(${empty(u7)},${empty(u15)}),"",MAX(0,${u15}-${u7})/8)`,
    "第16-30天日销": `=IF(OR(${empty(u15)},${empty(u30)}),"",MAX(0,${u30}-${u15})/15)`,
    "加权日销A": `=IF(AND(${empty(d7)},${empty(d815)},${empty(d1630)}),"",(IF(${empty(d7)},0,${d7}*0.5)+IF(${empty(d815)},0,${d815}*0.3)+IF(${empty(d1630)},0,${d1630}*0.2))/(IF(${empty(d7)},0,0.5)+IF(${empty(d815)},0,0.3)+IF(${empty(d1630)},0,0.2)))`,
    "趋势T": `=IF(OR(${empty(u15)},${empty(prev15)},${prev15}<=0),1,MAX(0,${u15})/${prev15})`,
    "成长系数B1": `=IF(${empty(a)},"",MIN(1.2,MAX(0.8,${t})))`,
    "成长系数B2": `=IF(${empty(a)},"",MIN(1.3,MAX(0.7,${t})))`,
    "健康库存H": `=IF(${empty(a)},"",${a}*${b1}*(${c}+${d}+${e})*${n})`,
    "下一周期目标库存": `=IF(${empty(h)},"",${h}+${a}*${b2}*${f})`,
    "FBA目标库存": `=IF(${empty(cycle)},"",MIN(${cycle},${a}*${parameters.maxFbaTargetDays}))`,
    "FBA供给天数": `=IF(OR(${empty(a)},${empty(instock)}),"",IF(${a}<=0,IF(${instock}>0,99999,0),MAX(0,${instock})/(${a}*${b1})))`,
    "距费用日天数": `=IF(${empty(feeDate)},"",MAX(0,${feeDate}-${parameters.asOfDate}))`,
    "潜在超量数量": `=IF(OR(${empty(instock)},${empty(fbaTarget)}),"",MAX(0,${instock}-${fbaTarget}))`,
    "费用风险数量": `=IF(OR(${empty(daysFee)},${empty(a)},AND(${empty(nextAged)},${allAgeEmpty})),"",MAX(0,IF(${empty(nextAged)},${ageSum},${nextAged})-${a}*${daysFee}))`,
    "清货目标数量": `=IF(${empty(instock)},"",IF(OR(${status}="紧急清退",${status}="主动清货"),MIN(MAX(0,${instock}),ROUNDUP(MAX(IF(${empty(potential)},0,${potential}),IF(${empty(feeRisk)},0,${feeRisk})),0)),0))`,
    "数量状态": `=IF(${empty(instock)},"需要人工确认-缺库存",IF(${empty(contribution)},"暂定-缺经济数据","已计算"))`,
    "主状态": `=IF(${urgent},"紧急清退",IF(${active},"主动清货",IF(OR(${criticalMissing},${t}<0.8,${instock}>${fbaTarget},AND(${replenishCandidate},NOT(OR(${continuous},${longTailOk})))),"停补观察",IF(AND(${replenishCandidate},OR(${continuous},${longTailOk})),"待补货","健康维持"))))`,
    "建议动作": `=IF(${status}="紧急清退","立即比较Outlet、移除、外部销售、清算、弃置/捐赠；不完整等待轻促销",IF(${status}="主动清货","停止采购；轻促销7–14天；无改善再扩大折扣或退出",IF(${status}="停补观察","停止新采购并在7–14天复查；只保留有效流量",IF(${status}="待补货","转交补货Skill；本表不下采购结论","保持当前策略，按周期复查"))))`,
    "风险判断置信度": `=IF(${criticalMissing},"低",IF(${riskMedium},"中","高"))`,
    "经济性置信度": `=IF(AND(NOT(${empty(contribution)}),NOT(${empty(externalValue)}),NOT(${empty(removalFee)})),"高",IF(OR(NOT(${empty(contribution)}),AND(NOT(${empty(landedCost)}),NOT(${empty(amazonFees)}))),"中","低"))`,
    "数据问题": `=${maybeIssue(ref("sku"), "缺少SKU")}&${inventoryFlagIssue}&${ageFlagIssue}&${maybeIssue(instock, "缺少FBA可售")}&${maybeIssue(a, "缺少销量窗口")}&${maybeIssue(feeDate, "缺少费用快照日")}&${maybeIssue(oldest, "缺少最老库龄")}&${maybeIssue(contribution, "利润待确认")}&${apiIssue}&${reconciliationIssue}&${womenIssue}`,
    "清算回收低估": `=IF(OR(${empty(target)},${empty(recoveryAveragePrice)}),"",${target}*${recoveryAveragePrice}*${parameters.liquidationRecoveryLow})`,
    "清算回收高估": `=IF(OR(${empty(target)},${empty(recoveryAveragePrice)}),"",${target}*${recoveryAveragePrice}*${parameters.liquidationRecoveryHigh})`,
  };
}

module.exports = {
  CALC_HEADERS,
  RULE_DEFAULTS,
  buildExcelFormulaMap,
  calculateClearance,
  clamp,
  economicConfidence,
  finiteNumber,
  growthCoefficients,
  weightedDailySales,
};
