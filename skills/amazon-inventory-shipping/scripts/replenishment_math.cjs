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

function ceilMultiple(value, multiple) {
  const safe = Math.max(0, Math.ceil(value));
  if (!(multiple > 0)) return safe;
  return Math.ceil(safe / multiple) * multiple;
}

function parseDate(value) {
  const text = String(value ?? "").trim();
  const match = text.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (Number.isNaN(date.getTime())) return null;
  return date.getUTCFullYear() === Number(match[1])
    && date.getUTCMonth() === Number(match[2]) - 1
    && date.getUTCDate() === Number(match[3])
    ? date
    : null;
}

function addDays(date, days) {
  return date ? new Date(date.getTime() + Math.max(0, days) * 86400000) : null;
}

function isoDate(date) {
  return date ? date.toISOString().slice(0, 10) : null;
}

function assessPostRestockSales(input = {}) {
  const asOfDate = parseDate(input.asOfDate);
  const receiptDate = parseDate(input.lastFbaReceiptDate);
  const receiptUnits = finiteNumber(input.lastFbaReceiptUnits);
  const shippedUnits = finiteNumber(input.postRestockUnits);
  const evidenceStatus = String(input.receiptEvidenceStatus ?? "").trim().toUpperCase();
  const evidenceValid = Boolean(
    asOfDate
    && receiptDate
    && receiptDate <= asOfDate
    && receiptUnits !== null
    && receiptUnits > 0
    && shippedUnits !== null
    && shippedUnits >= 0
    && ["SYSTEM_CONFIRMED", "USER_CONFIRMED"].includes(evidenceStatus)
    && input.receiptAsinConflict !== true
  );
  const common = {
    last_receipt_date: isoDate(receiptDate),
    last_receipt_quantity: receiptUnits,
    evidence_status: evidenceStatus || "UNVERIFIED",
    evidence_source: input.receiptEvidenceSource ?? null,
    source_record_id: input.receiptEvidenceRecordId ?? null,
    confirmed_at: input.receiptConfirmedAt ?? null,
    observation_start_date: receiptDate ? isoDate(addDays(receiptDate, 1)) : null,
    observation_end_date: isoDate(asOfDate),
    actual_shipped_units: shippedUnits,
  };
  if (!evidenceValid) {
    return {
      ...common,
      observation_days: null,
      daily_sales: null,
      status: "UNVERIFIED",
      passed: false,
      blocking_codes: ["LAST_FBA_RECEIPT_UNVERIFIED"],
    };
  }
  const observationDays = Math.floor((asOfDate - receiptDate) / 86400000);
  const observed = {
    ...common,
    observation_days: observationDays,
    daily_sales: observationDays > 0 ? shippedUnits / observationDays : null,
  };
  if (observationDays < 7) {
    return {
      ...observed,
      status: "OBSERVATION_PENDING",
      passed: false,
      blocking_codes: ["POST_RESTOCK_OBSERVATION_PENDING"],
    };
  }
  if (shippedUnits === 0) {
    return {
      ...observed,
      status: "ZERO_SALES_7D",
      passed: false,
      blocking_codes: ["ZERO_SALES_AFTER_RESTOCK_7D"],
    };
  }
  return { ...observed, status: "PASSED", passed: true, blocking_codes: [] };
}

function eligibleByDate(quantity, readyDate, cutoffDate) {
  const qty = Math.max(0, numberOr(quantity, 0));
  if (qty <= 0) return 0;
  const ready = parseDate(readyDate);
  if (!ready || !cutoffDate) return 0;
  return ready <= cutoffDate ? qty : 0;
}

function weightedDailySales(input) {
  const u7 = finiteNumber(input.units7);
  const u15 = finiteNumber(input.units15);
  const u30 = finiteNumber(input.units30);
  const segments = [
    { value: u7 === null ? null : Math.max(0, u7) / 7, weight: 0.5 },
    { value: u7 === null || u15 === null ? null : Math.max(0, u15 - u7) / 8, weight: 0.3 },
    { value: u15 === null || u30 === null ? null : Math.max(0, u30 - u15) / 15, weight: 0.2 },
  ];
  const valid = segments.filter((segment) => segment.value !== null);
  if (!valid.length) return { dailySales: null, segments, confidence: "低" };
  const weight = valid.reduce((sum, segment) => sum + segment.weight, 0);
  return {
    dailySales: valid.reduce((sum, segment) => sum + segment.value * segment.weight, 0) / weight,
    segments,
    confidence: valid.length === 3 ? "高" : valid.length === 2 ? "中" : "低",
  };
}

function growthCoefficients(input) {
  const seasonal = ["是", "yes", "true"].includes(String(input.seasonalProduct ?? "").trim().toLowerCase());
  const yoy = finiteNumber(input.yoyGrowthRatio);
  const recent = finiteNumber(input.units15);
  const previous = finiteNumber(input.previous15);
  let trend;
  let confidence = "高";
  if (seasonal && yoy !== null && yoy > 0) trend = yoy;
  else if (recent !== null && previous !== null && previous > 0) trend = Math.max(0, recent) / previous;
  else {
    trend = 1;
    confidence = "低";
  }
  return { trend, b1: clamp(trend, 0.8, 1.2), b2: clamp(trend, 0.7, 1.3), confidence };
}

function splitTransport({ totalQty, dailySales, b1, coverageDays, expressDays, airDays, seaDays }) {
  const total = Math.max(0, Math.ceil(totalQty));
  const demand = Math.max(0, numberOr(dailySales, 0) * numberOr(b1, 1));
  const cover = Math.max(0, numberOr(coverageDays, 0));
  const expressLead = Math.max(0, numberOr(expressDays, 0));
  const airLead = Math.max(expressLead, numberOr(airDays, expressLead));
  const seaLead = Math.max(airLead, numberOr(seaDays, airLead));
  if (cover >= seaLead) {
    return { expressQty: 0, airQty: 0, seaQty: total, stockoutDays: 0 };
  }
  const expressQty = Math.min(total, Math.ceil(Math.max(0, airLead - cover) * demand));
  const airQty = Math.min(total - expressQty, Math.ceil(Math.max(0, seaLead - Math.max(airLead, cover)) * demand));
  return {
    expressQty,
    airQty,
    seaQty: Math.max(0, total - expressQty - airQty),
    stockoutDays: Math.max(0, expressLead - cover),
  };
}

function calculateReplenishment(input) {
  const velocity = weightedDailySales(input);
  const growth = growthCoefficients(input);
  const b1Override = finiteNumber(input.b1Override);
  const b2Override = finiteNumber(input.b2Override);
  const b1 = b1Override === null ? growth.b1 : clamp(b1Override, 0.8, 1.2);
  const b2 = b2Override === null ? growth.b2 : clamp(b2Override, 0.7, 1.3);
  const a = velocity.dailySales;
  const c = numberOr(input.procurementDays, 14);
  const g = Math.max(0, numberOr(input.productionDays, 0));
  const d = numberOr(input.prepDays, 2);
  const e = numberOr(input.seaDays, 35);
  const f = numberOr(input.reviewCycleDays, 7);
  const n = clamp(numberOr(input.safetyFactor, 1.2), 1, 1.4);
  const asOfDate = parseDate(input.asOfDate);
  const planningCutoff = addDays(asOfDate, c + g + d + e + f);
  const supplyTotal = finiteNumber(input.supplyTotal);
  const inbound = Math.max(0, numberOr(input.supplyInbound));
  const eligibleInbound = eligibleByDate(inbound, input.inboundReadyDate, planningCutoff);
  const fbaPosition =
    supplyTotal !== null
      ? Math.max(0, supplyTotal - inbound + eligibleInbound)
      : Math.max(0, numberOr(input.supplyInstock)) +
        Math.max(0, numberOr(input.supplyReserved)) +
        eligibleInbound;
  const position = fbaPosition;
  const health = a === null ? null : a * b1 * (c + g + d + e) * n;
  const raw = a === null ? null : a * b2 * f + health - position;
  const net = raw === null ? null : Math.max(0, raw);
  const moq = Math.max(0, numberOr(input.moq));
  const carton = Math.max(0, numberOr(input.cartonQty));
  let rounded = net === null ? null : Math.ceil(net);
  if (rounded > 0 && moq > 0) rounded = Math.max(rounded, Math.ceil(moq));
  if (rounded > 0 && carton > 0) rounded = ceilMultiple(rounded, carton);
  const instock = Math.max(0, numberOr(input.supplyInstock));
  const cover = a === null ? null : a <= 0 ? (instock > 0 ? Infinity : 0) : instock / (a * b1);
  const clearanceStatus = String(input.clearanceStatus ?? "").trim();
  const blocked = new Set(["紧急清退", "主动清货", "停补观察"]).has(clearanceStatus);
  const continuous = velocity.segments.every((segment) => segment.value !== null && segment.value > 0);
  const longTail = ["是", "yes", "true"].includes(String(input.longTailApproved ?? "").trim().toLowerCase());
  const missingSales = a === null;
  const missingInventory = finiteNumber(input.supplyInstock) === null;
  const missingProfit = finiteNumber(input.unitContribution) === null;
  const missingClearance = clearanceStatus === "";
  const missingLead =
    finiteNumber(input.procurementDays) === null ||
    finiteNumber(input.seaDays) === null;
  const promotionOverlap = ["是", "yes", "true"].includes(
    String(input.promotionOverlap ?? "").trim().toLowerCase(),
  );
  const missingInboundDate = inbound > 0 && !parseDate(input.inboundReadyDate);
  const postRestockSales = assessPostRestockSales(input);
  let status = "健康维持";
  if (blocked) {
    rounded = 0;
    status = clearanceStatus;
  } else if (missingSales || missingInventory) {
    rounded = 0;
    status = "停补观察";
  } else if (rounded > 0 && (continuous || longTail)) status = "待补货";
  else if (rounded > 0) {
    rounded = 0;
    status = "停补观察";
  }
  if (postRestockSales.status === "ZERO_SALES_7D") {
    rounded = 0;
    status = "停补观察";
  }
  const urgency =
    status !== "待补货"
      ? "不补货"
      : cover < numberOr(input.expressDays, 5)
        ? "预计断货"
        : cover < e
          ? "加急补货"
          : "常规补货";
  const transport = splitTransport({
    totalQty: rounded || 0,
    dailySales: a || 0,
    b1,
    coverageDays: Number.isFinite(cover) ? cover : 99999,
    expressDays: input.expressDays,
    airDays: input.airDays,
    seaDays: input.seaDays,
  });
  return {
    dailySales: a,
    trend: growth.trend,
    b1,
    b2,
    healthInventory: health,
    inventoryPosition: position,
    rawQty: raw,
    recommendedQty: rounded,
    coverageDays: cover,
    status,
    urgency,
    confidence:
      missingSales ||
      missingInventory ||
      missingProfit ||
      missingClearance ||
      missingInboundDate
        ? "低"
        : missingLead || promotionOverlap || growth.confidence === "低" || velocity.confidence !== "高"
          ? "中"
          : "高",
    provisional: missingProfit || ["UNVERIFIED", "OBSERVATION_PENDING"].includes(postRestockSales.status),
    postRestockSales,
    postRestockActionable: postRestockSales.passed,
    blockingCodes: postRestockSales.blocking_codes,
    procurementDaysUsed: c,
    productionDays: g,
    ...transport,
  };
}

function calculateReplenishmentScenarios(input) {
  const configured = Array.isArray(input.procurementScenariosDays)
    ? input.procurementScenariosDays
    : [];
  const fastDays = numberOr(input.fastProcurementDays ?? configured[0], 7);
  const formalDays = numberOr(input.formalProcurementDays ?? configured[1], 14);
  return {
    fast7: calculateReplenishment({ ...input, procurementDays: fastDays }),
    formal14: calculateReplenishment({ ...input, procurementDays: formalDays }),
  };
}

module.exports = {
  assessPostRestockSales,
  calculateReplenishment,
  calculateReplenishmentScenarios,
  ceilMultiple,
  clamp,
  finiteNumber,
  growthCoefficients,
  splitTransport,
  weightedDailySales,
};
