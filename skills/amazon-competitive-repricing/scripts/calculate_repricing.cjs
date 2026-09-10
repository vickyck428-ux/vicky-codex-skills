#!/usr/bin/env node
"use strict";

const fs = require("fs");

const DEFAULT_RULES = Object.freeze({
  inventoryMaxAgeDays: 7,
  competitorMaxAgeDays: 4,
  minimumSessions: 30,
  activeLossPct: 0.15,
  urgentLossPct: 0.30,
  fxSafetyBufferPct: 0.02,
  activeUndercutPct: 0.01,
  activeUndercutMaxUsd: 0.30,
  urgentUndercutPct: 0.02,
  urgentUndercutMaxUsd: 0.50,
  lowStockRaisePct: 0.02,
  lowStockCompetitorCapPct: 0.03,
});

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--self-test") {
      args.selfTest = true;
      continue;
    }
    if (!token.startsWith("--")) throw new Error(`Unknown argument: ${token}`);
    const key = token.slice(2);
    const value = argv[i + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for --${key}`);
    args[key] = value;
    i += 1;
  }
  return args;
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function n0(value) {
  return numberOrNull(value) ?? 0;
}

function roundMoney(value) {
  return value === null || value === undefined ? null : Math.round((value + Number.EPSILON) * 100) / 100;
}

function ceilMoney(value) {
  return value === null || value === undefined ? null : Math.ceil((value - Number.EPSILON) * 100) / 100;
}

function parseDate(value, label) {
  if (!value) return null;
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) throw new Error(`Invalid ${label}: ${value}`);
  return date;
}

function dateText(date) {
  return date.toISOString().slice(0, 10);
}

function dayDiff(later, earlier) {
  return Math.floor((later.getTime() - earlier.getTime()) / 86400000);
}

function addDays(date, days) {
  const copy = new Date(date);
  copy.setUTCDate(copy.getUTCDate() + days);
  return copy;
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function pickPsychPrice(low, high) {
  if (!(low > 0) || !(high >= low)) return null;
  const candidates = [];
  for (let whole = Math.floor(low) - 1; whole <= Math.ceil(high) + 1; whole += 1) {
    for (const ending of [0.49, 0.99]) {
      const candidate = roundMoney(whole + ending);
      if (candidate >= low - 1e-9 && candidate <= high + 1e-9) candidates.push(candidate);
    }
  }
  if (candidates.length) return Math.max(...candidates);
  return roundMoney((low + high) / 2);
}

function normalizeFulfillment(value) {
  const normalized = String(value || "UNKNOWN").trim().toUpperCase();
  if (normalized === "PRIME") return "FBA";
  return ["FBA", "FBM"].includes(normalized) ? normalized : "UNKNOWN";
}

function effectiveCompetitorPrice(row) {
  const price = numberOrNull(row.price);
  if (!(price > 0)) return null;
  return roundMoney(price + n0(row.shipping));
}

function deliveryPremium(row, ownDeliveryDays, ownFulfillment) {
  if (row.direct_from_china === true) {
    return { value: 3, basis: "DIRECT_FROM_CHINA" };
  }
  const competitorDays = numberOrNull(row.delivery_days);
  if (competitorDays === null) return { value: 0, basis: "DELIVERY_DAYS_UNKNOWN" };
  if (normalizeFulfillment(ownFulfillment) === "FBA") {
    if (competitorDays > 14) return { value: 3, basis: "FBA_VS_FBM_OVER_14_DAYS" };
    if (competitorDays >= 8) return { value: 2, basis: "FBA_VS_FBM_8_14_DAYS" };
    if (competitorDays >= 4) return { value: 1, basis: "FBA_VS_FBM_4_7_DAYS" };
    return { value: 0, basis: "FBA_VS_FBM_0_3_DAYS" };
  }
  if (ownDeliveryDays === null) return { value: 0, basis: "OWN_DELIVERY_DAYS_UNKNOWN" };
  const difference = competitorDays - ownDeliveryDays;
  if (difference > 14) return { value: 3, basis: "DELIVERY_GAP_OVER_14_DAYS" };
  if (difference >= 8) return { value: 2, basis: "DELIVERY_GAP_8_14_DAYS" };
  if (difference >= 4) return { value: 1, basis: "DELIVERY_GAP_4_7_DAYS" };
  return { value: 0, basis: "DELIVERY_GAP_0_3_DAYS" };
}

function competitorAgeDays(row, asOfDate) {
  if (!row.captured_at) return null;
  const captured = parseDate(row.captured_at, "competitor captured_at");
  return dayDiff(asOfDate, captured);
}

function buildCompetitorContext(input, asOfDate, rules, issues) {
  const ownDeliveryDays = numberOrNull(input.pricing?.own_delivery_days);
  const ownFulfillment = normalizeFulfillment(input.pricing?.own_fulfillment);
  const normalized = (input.competitors || []).map((row) => {
    const effectivePrice = effectiveCompetitorPrice(row);
    const ageDays = competitorAgeDays(row, asOfDate);
    const fresh = ageDays !== null && ageDays >= 0 && ageDays <= rules.competitorMaxAgeDays;
    const fulfillment = normalizeFulfillment(row.fulfillment);
    const premiumDecision = fulfillment === "FBM"
      ? deliveryPremium(row, ownDeliveryDays, ownFulfillment)
      : { value: 0, basis: "FBA_NO_PREMIUM" };
    const originalGrade = String(row.original_grade || row.grade || "").toUpperCase();
    const userPromoted = row.user_promoted_to_a === true && originalGrade === "B";
    const effectiveGrade = userPromoted
      ? "A"
      : String(row.effective_grade || originalGrade).toUpperCase();
    const confirmationStatus = userPromoted
      ? "USER_CONFIRMED"
      : String(row.confirmation_status || "AGENT_CONFIRMED").toUpperCase();
    const exactVariantConfirmed = userPromoted
      || confirmationStatus === "USER_CONFIRMED"
      || row.exact_variant_confirmed === true
      || row.variant_confirmed === true;
    const fulfillmentDetailsReady = fulfillment === "FBA"
      || (fulfillment === "FBM" && (
        row.direct_from_china === true || numberOrNull(row.delivery_days) !== null
      ));
    return {
      ...row,
      original_grade: originalGrade,
      effective_grade: effectiveGrade,
      user_promoted_to_a: userPromoted,
      grade: effectiveGrade,
      confirmation_status: confirmationStatus,
      exact_variant_confirmed: exactVariantConfirmed,
      fulfillment_details_ready: fulfillmentDetailsReady,
      price_role: String(row.price_role || "REFERENCE").toUpperCase(),
      fulfillment,
      effective_price: effectivePrice,
      delivery_premium: premiumDecision.value,
      delivery_premium_basis: premiumDecision.basis,
      adjusted_reference_price: effectivePrice === null ? null : roundMoney(effectivePrice + premiumDecision.value),
      competitor_age_days: ageDays,
      fresh,
    };
  });

  const usableA = normalized.filter(
    (row) =>
      row.grade === "A" &&
      ["USER_CONFIRMED", "AGENT_CONFIRMED", "TEMP_A"].includes(row.confirmation_status) &&
      row.exact_variant_confirmed === true &&
      row.fulfillment_details_ready === true &&
      row.price_role !== "EXCLUDED" &&
      row.in_stock !== false &&
      row.effective_price !== null
  );
  if (normalized.some((row) => row.grade === "A") && !normalized.some((row) =>
    row.grade === "A" && row.exact_variant_confirmed === true
  )) {
    issues.push({
      severity: "blocking",
      code: "COMPETITOR_VARIANT_UNVERIFIED",
      message: "A-grade appearance candidates require exact child-variant confirmation before formal pricing.",
    });
  }
  if (normalized.some((row) =>
    row.grade === "A" && row.exact_variant_confirmed === true
  ) && !normalized.some((row) =>
    row.grade === "A" && row.exact_variant_confirmed === true && row.fulfillment_details_ready === true
  )) {
    issues.push({
      severity: "blocking",
      code: "COMPETITOR_FULFILLMENT_UNVERIFIED",
      message: "A-grade competitors require confirmed FBA fulfillment or FBM delivery evidence.",
    });
  }
  const freshA = usableA.filter((row) => row.fresh);
  if (usableA.length && !freshA.length) {
    issues.push({
      severity: "blocking",
      code: "COMPETITOR_DATA_STALE",
      message: `All usable A-grade competitor prices are older than ${rules.competitorMaxAgeDays} days or lack captured_at.`,
    });
  }

  const confirmedA = freshA.filter(
    (row) => row.confirmation_status === "USER_CONFIRMED" || row.confirmation_status === "AGENT_CONFIRMED"
  );
  const benchmarkA = confirmedA.length ? confirmedA : freshA;
  if (!confirmedA.length && freshA.some((row) => row.confirmation_status === "TEMP_A")) {
    issues.push({
      severity: "blocking",
      code: "TEMP_A_COMPETITOR_ONLY",
      message: "Only temporary A-grade competitors are available; the market target is provisional.",
    });
  }

  const fbaAll = benchmarkA.filter((row) => row.fulfillment === "FBA");
  const fbaPrimary = fbaAll.filter((row) => row.price_role === "PRIMARY");
  const fbmAll = benchmarkA.filter((row) => row.fulfillment === "FBM");
  const fbmPrimary = fbmAll.filter((row) => row.price_role === "PRIMARY");

  const activeRows = fbaPrimary.length
    ? fbaPrimary
    : fbaAll.filter((row) => row.price_role !== "LOWER_BOUND");
  const activeFbmRows = fbmPrimary.length
    ? fbmPrimary
    : fbmAll.filter((row) => row.price_role !== "LOWER_BOUND");

  const activeBenchmark = activeRows.length
    ? {
        type: "A_FBA_PRIMARY",
        value: median(activeRows.map((row) => row.effective_price)),
        asins: activeRows.map((row) => row.asin),
      }
    : activeFbmRows.length
      ? {
          type: "A_FBM_DELIVERY_ADJUSTED",
          value: median(activeFbmRows.map((row) => row.adjusted_reference_price)),
          asins: activeFbmRows.map((row) => row.asin),
        }
      : null;

  const urgentRows = fbaAll.length ? fbaAll : fbmAll;
  const urgentBenchmark = urgentRows.length
    ? {
        type: fbaAll.length ? "A_FBA_LOWEST" : "A_FBM_LOWEST_DELIVERY_ADJUSTED",
        value: Math.min(
          ...urgentRows.map((row) =>
            fbaAll.length ? row.effective_price : row.adjusted_reference_price
          )
        ),
        asins: urgentRows.map((row) => row.asin),
      }
    : null;

  return {
    rows: normalized,
    activeBenchmark,
    urgentBenchmark,
    hasFreshAFba: fbaAll.length > 0,
    hasFreshA: benchmarkA.length > 0,
    hasB: normalized.some((row) => row.original_grade === "B"),
  };
}

function computeCosts(input, issues, rules) {
  const costs = input.costs || {};
  const fees = input.fees || {};
  const procurement = numberOrNull(costs.procurement_cost_cny);
  const firstLegProvided = numberOrNull(costs.first_leg_cost_cny);
  const firstLeg = firstLegProvided ?? 10;
  const fx = numberOrNull(costs.usd_cny_rate);
  const buffer = numberOrNull(costs.fx_safety_buffer_pct) ?? rules.fxSafetyBufferPct;
  const referralRate = numberOrNull(fees.referral_fee_rate);
  const fulfillmentFee = numberOrNull(fees.fulfillment_fee);
  const operatingFeeFields = [
    "storage_per_unit",
    "return_reserve_per_unit",
    "future_ad_cost_per_order",
    "other_variable_fee_per_unit",
  ];
  const operatingCostsComplete = operatingFeeFields.every((field) => (
    Object.prototype.hasOwnProperty.call(fees, field)
    && numberOrNull(fees[field]) !== null
    && numberOrNull(fees[field]) >= 0
  ));

  if (procurement === null) {
    issues.push({ severity: "blocking", code: "PROCUREMENT_COST_MISSING", message: "Procurement cost is required." });
  }
  if (!(fx > 0)) {
    issues.push({ severity: "blocking", code: "FX_RATE_MISSING", message: "Current USD/CNY rate is required." });
  }
  if (!(referralRate >= 0 && referralRate < 1) || fulfillmentFee === null || fees.exact !== true) {
    issues.push({
      severity: "blocking",
      code: "EXACT_FEES_MISSING",
      message: "Exact/current referral rate and fulfillment fee are required for an executable price.",
    });
  }
  if (!operatingCostsComplete) {
    issues.push({
      severity: "warning",
      code: "OPERATING_COSTS_INCOMPLETE",
      message: "Storage, return reserve, advertising, or other variable costs are incomplete; operating profit remains pending.",
    });
  }

  if (procurement === null || !(fx > 0) || !(buffer >= 0 && buffer < 1)) {
    return {
      first_leg_cost_cny: firstLeg,
      used_default_first_leg: firstLegProvided === null,
      landed_cost_usd: null,
      cash_normal_floor: null,
      cash_active_floor: null,
      cash_urgent_floor: null,
      operating_normal_floor: null,
      operating_active_floor: null,
      operating_urgent_floor: null,
      operating_costs_complete: operatingCostsComplete,
      operating_cost_completeness: operatingCostsComplete ? "COMPLETE" : "INCOMPLETE",
      normal_floor: null,
      active_floor: null,
      urgent_floor: null,
    };
  }

  const conservativeFx = fx * (1 - buffer);
  const landedCost = (procurement + firstLeg) / conservativeFx;
  const cashFixedVariableFees = n0(fulfillmentFee);
  const operatingFixedVariableFees = operatingCostsComplete
    ? cashFixedVariableFees + operatingFeeFields.reduce((sum, field) => sum + n0(fees[field]), 0)
    : null;

  if (!(referralRate >= 0 && referralRate < 1) || fulfillmentFee === null) {
    return {
      first_leg_cost_cny: firstLeg,
      used_default_first_leg: firstLegProvided === null,
      conservative_usd_cny_rate: roundMoney(conservativeFx),
      landed_cost_usd: roundMoney(landedCost),
      cash_fixed_variable_fees: null,
      operating_fixed_variable_fees: null,
      fixed_variable_fees: null,
      cash_normal_floor: null,
      cash_active_floor: null,
      cash_urgent_floor: null,
      operating_normal_floor: null,
      operating_active_floor: null,
      operating_urgent_floor: null,
      operating_costs_complete: operatingCostsComplete,
      operating_cost_completeness: operatingCostsComplete ? "COMPLETE" : "CASH_ONLY",
      normal_floor: null,
      active_floor: null,
      urgent_floor: null,
    };
  }

  const priceFloor = (lossPct, fixedFees) =>
    fixedFees === null
      ? null
      : ceilMoney((landedCost * (1 - lossPct) + fixedFees) / (1 - referralRate));
  const cashNormalFloor = priceFloor(0, cashFixedVariableFees);
  const cashActiveFloor = priceFloor(rules.activeLossPct, cashFixedVariableFees);
  const cashUrgentFloor = priceFloor(rules.urgentLossPct, cashFixedVariableFees);
  const operatingNormalFloor = priceFloor(0, operatingFixedVariableFees);
  const operatingActiveFloor = priceFloor(rules.activeLossPct, operatingFixedVariableFees);
  const operatingUrgentFloor = priceFloor(rules.urgentLossPct, operatingFixedVariableFees);

  return {
    first_leg_cost_cny: firstLeg,
    used_default_first_leg: firstLegProvided === null,
    conservative_usd_cny_rate: roundMoney(conservativeFx),
    landed_cost_usd: roundMoney(landedCost),
    cash_fixed_variable_fees: roundMoney(cashFixedVariableFees),
    operating_fixed_variable_fees: roundMoney(operatingFixedVariableFees),
    fixed_variable_fees: roundMoney(operatingCostsComplete ? operatingFixedVariableFees : cashFixedVariableFees),
    cash_normal_floor: cashNormalFloor,
    cash_active_floor: cashActiveFloor,
    cash_urgent_floor: cashUrgentFloor,
    operating_normal_floor: operatingNormalFloor,
    operating_active_floor: operatingActiveFloor,
    operating_urgent_floor: operatingUrgentFloor,
    operating_costs_complete: operatingCostsComplete,
    operating_cost_completeness: operatingCostsComplete ? "COMPLETE" : "CASH_ONLY",
    normal_floor: operatingNormalFloor ?? cashNormalFloor,
    active_floor: operatingActiveFloor ?? cashActiveFloor,
    urgent_floor: operatingUrgentFloor ?? cashUrgentFloor,
  };
}

function sumAged181(inventory) {
  return (
    n0(inventory.age_181_270) +
    n0(inventory.age_271_365) +
    n0(inventory.age_366_455) +
    n0(inventory.age_456_plus)
  );
}

const CLEARANCE_STATUSES = new Set(["紧急清退", "主动清货", "停补观察", "健康维持", "待补货"]);
const CLEARANCE_CONFIDENCE = new Set(["高", "中", "低"]);

function validateClearanceDecision(input, issues) {
  const decision = input.clearance_decision;
  if (!decision) return null;

  const inventory = input.inventory || {};
  const status = String(decision.status || "").trim();
  const confidence = String(decision.confidence || "").trim();
  const quantity = numberOrNull(decision.recommended_clearance_quantity);
  const sourceFile = String(decision.source_file || "").trim();
  const reasons = Array.isArray(decision.reasons)
    ? decision.reasons.map((reason) => String(reason).trim()).filter(Boolean)
    : [];

  if (!CLEARANCE_STATUSES.has(status)) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_STATUS_INVALID",
      message: "Clearance status must come from amazon-inventory-clearance.",
    });
  }
  if (!CLEARANCE_CONFIDENCE.has(confidence)) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_CONFIDENCE_INVALID",
      message: "Clearance confidence must be 高, 中, or 低.",
    });
  } else if (confidence === "低") {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_CONFIDENCE_LOW",
      message: "Low-confidence clearance output can only support a provisional price.",
    });
  }
  if (quantity === null || quantity < 0 || !Number.isInteger(quantity)) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_QUANTITY_INVALID",
      message: "A non-negative recommended clearance quantity is required.",
    });
  }
  if (!sourceFile) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_SOURCE_MISSING",
      message: "The source clearance plan file is required for auditability.",
    });
  }
  if (!reasons.length) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_REASONS_MISSING",
      message: "The clearance decision must include at least one reason.",
    });
  }
  if (!decision.seller_sku || decision.seller_sku !== input.sku) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_SKU_CONFLICT",
      message: "Clearance decision SKU does not match the requested SKU.",
    });
  }
  if (!decision.asin || !input.asin || decision.asin !== input.asin) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_ASIN_CONFLICT",
      message: "Clearance decision ASIN does not match the requested ASIN.",
    });
  }
  if (
    !decision.inventory_age_snapshot_date ||
    decision.inventory_age_snapshot_date !== inventory.inventory_age_snapshot_date
  ) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_SNAPSHOT_CONFLICT",
      message: "Clearance decision and repricing input must use the same inventory-age snapshot.",
    });
  }

  return {
    seller_sku: decision.seller_sku || null,
    asin: decision.asin || null,
    status: CLEARANCE_STATUSES.has(status) ? status : null,
    recommended_clearance_quantity:
      quantity !== null && quantity >= 0 && Number.isInteger(quantity) ? quantity : null,
    confidence: CLEARANCE_CONFIDENCE.has(confidence) ? confidence : null,
    reasons,
    inventory_age_snapshot_date: decision.inventory_age_snapshot_date || null,
    source_file: sourceFile || null,
  };
}

function hasPotentialClearanceRisk(input) {
  const inventory = input.inventory || {};
  const performance = input.performance || {};
  const available = numberOrNull(inventory.available);
  const units60 = numberOrNull(performance.units_60d);
  const daysSupply = numberOrNull(inventory.days_of_supply);
  return (
    n0(inventory.age_91_180) > 0 ||
    sumAged181(inventory) > 0 ||
    n0(inventory.quantity_to_be_charged_181_plus) > 0 ||
    n0(inventory.estimated_aged_surcharge) > 0 ||
    n0(inventory.estimated_excess_quantity) > 0 ||
    (daysSupply !== null && daysSupply > 90) ||
    (available !== null && available > 0 && units60 === 0)
  );
}

function determineStatus(input, clearanceDecision, issues, rules) {
  const inventory = input.inventory || {};
  const performance = input.performance || {};
  const available = numberOrNull(inventory.available);
  const units30 = numberOrNull(performance.units_30d);
  const sessions = numberOrNull(performance.sessions_30d);
  const alert = String(inventory.alert || "").toLowerCase();
  const health = String(inventory.inventory_health_status || "").toLowerCase();
  const inbound = n0(inventory.inbound);
  const minimumLevel = numberOrNull(inventory.fba_minimum_inventory_level);
  const totalSupply = numberOrNull(inventory.total_supply_including_open_shipments) ?? (
    available === null ? null : available + inbound
  );

  if (available === null) {
    issues.push({ severity: "blocking", code: "AVAILABLE_MISSING", message: "Sellable inventory is required." });
  }
  if (available !== null && available <= 0) {
    return { code: "NO_SELLABLE_INVENTORY", action: "NONE", reasons: ["Sellable inventory is zero."], reviewDays: 7 };
  }
  if (
    clearanceDecision &&
    (!clearanceDecision.status || clearanceDecision.recommended_clearance_quantity === null)
  ) {
    return {
      code: "CLEARANCE_REVIEW_REQUIRED",
      action: "NONE",
      reasons: ["The supplied clearance decision has an invalid status or quantity."],
      reviewDays: 7,
    };
  }

  if (clearanceDecision?.status === "主动清货") {
    if (!(clearanceDecision.recommended_clearance_quantity > 0)) {
      issues.push({
        severity: "blocking",
        code: "CLEARANCE_QUANTITY_REQUIRED",
        message: "Active-clearance pricing requires a positive quantity from amazon-inventory-clearance.",
      });
      return {
        code: "CLEARANCE_REVIEW_REQUIRED",
        action: "NONE",
        reasons: ["The active-clearance decision does not contain a positive clearance quantity."],
        reviewDays: 7,
      };
    }
    return {
      code: "ACTIVE_CLEARANCE",
      action: "LOWER",
      reasons: clearanceDecision.reasons,
      reviewDays: 7,
    };
  }
  if (clearanceDecision?.status === "紧急清退") {
    if (clearanceDecision.recommended_clearance_quantity > 0) {
      return {
        code: "URGENT_EXIT",
        action: "LOWER_OR_EXIT",
        reasons: clearanceDecision.reasons,
        reviewDays: 3,
      };
    }
    return {
      code: "INVENTORY_EXIT_ONLY",
      action: "HOLD",
      reasons: [
        ...clearanceDecision.reasons,
        "Clearance quantity is zero, so normal sellable inventory price must not be reduced.",
      ],
      reviewDays: 3,
    };
  }
  if (clearanceDecision?.status === "停补观察") {
    return {
      code: "OBSERVE",
      action: "HOLD",
      reasons: clearanceDecision.reasons,
      reviewDays: 14,
    };
  }
  if (clearanceDecision?.status === "健康维持") {
    return {
      code: "HEALTHY_HOLD",
      action: "HOLD",
      reasons: clearanceDecision.reasons,
      reviewDays: 7,
    };
  }

  if (!clearanceDecision && hasPotentialClearanceRisk(input)) {
    issues.push({
      severity: "blocking",
      code: "CLEARANCE_DECISION_REQUIRED",
      message: "Potential aged, excess, surcharge, long-supply, or zero-sales risk requires amazon-inventory-clearance first.",
    });
    return {
      code: "CLEARANCE_REVIEW_REQUIRED",
      action: "NONE",
      reasons: ["Potential clearance risk exists, but no canonical clearance decision was provided."],
      reviewDays: 7,
    };
  }

  const healthLow = /understock|low inventory|low stock|below minimum|insufficient/.test(health);
  const belowMinimum =
    minimumLevel !== null && totalSupply !== null && totalSupply < minimumLevel;
  if (
    n0(units30) > 0 &&
    (healthLow || belowMinimum) &&
    (!clearanceDecision || clearanceDecision.status === "待补货")
  ) {
    return {
      code: "LOW_STOCK_PROTECTION",
      action: "RAISE",
      reasons: ["Recent sales exist and inventory is below its reported minimum or health target."],
      reviewDays: 7,
    };
  }

  if (clearanceDecision?.status === "待补货") {
    return {
      code: "HEALTHY_HOLD",
      action: "HOLD",
      reasons: [
        ...clearanceDecision.reasons,
        "Replenishment status alone does not justify a price increase without recent sales and a low-stock signal.",
      ],
      reviewDays: 7,
    };
  }

  if (alert.includes("low traffic") || (sessions !== null && sessions < rules.minimumSessions)) {
    return {
      code: "OBSERVE",
      action: "HOLD",
      reasons: ["Traffic sample is insufficient and inventory has not entered a clearance state."],
      reviewDays: 14,
    };
  }
  return { code: "HEALTHY_HOLD", action: "HOLD", reasons: ["No inventory-led repricing trigger is present."], reviewDays: 7 };
}

function validateIdentityAndFreshness(input, asOfDate, issues, rules) {
  const inventory = input.inventory || {};
  if (!input.sku) {
    issues.push({ severity: "blocking", code: "SKU_MISSING", message: "Top-level SKU is required." });
  }
  if (inventory.seller_sku && input.sku && inventory.seller_sku !== input.sku) {
    issues.push({ severity: "blocking", code: "SKU_CONFLICT", message: "Inventory row SKU does not match requested SKU." });
  }
  if (inventory.asin && input.asin && inventory.asin !== input.asin) {
    issues.push({ severity: "blocking", code: "ASIN_CONFLICT", message: "Inventory row ASIN does not match requested ASIN." });
  }
  const snapshot = parseDate(inventory.inventory_age_snapshot_date, "inventory_age_snapshot_date");
  if (!snapshot) {
    issues.push({ severity: "blocking", code: "SNAPSHOT_DATE_MISSING", message: "Inventory age snapshot date is required." });
    return null;
  }
  const ageDays = dayDiff(asOfDate, snapshot);
  if (ageDays < 0 || ageDays > rules.inventoryMaxAgeDays) {
    issues.push({
      severity: "blocking",
      code: "INVENTORY_REPORT_STALE",
      message: `Inventory age snapshot is ${ageDays} days old; allowed range is 0–${rules.inventoryMaxAgeDays} days.`,
    });
  }
  return { snapshot_date: dateText(snapshot), snapshot_age_days: ageDays };
}

function contributionAtPrice(price, input, costResult) {
  if (price === null || costResult.landed_cost_usd === null || costResult.fixed_variable_fees === null) return null;
  const referralRate = numberOrNull(input.fees?.referral_fee_rate);
  if (referralRate === null) return null;
  return roundMoney(
    price * (1 - referralRate) - costResult.fixed_variable_fees - costResult.landed_cost_usd
  );
}

function applicableCostFloor(statusCode, costs, prefix = "") {
  const key = statusCode === "URGENT_EXIT"
    ? "urgent_floor"
    : statusCode === "ACTIVE_CLEARANCE"
      ? "active_floor"
      : "normal_floor";
  return costs[`${prefix}${key}`] ?? null;
}

function priceValidUntil(freshness, status, competitorContext, rules) {
  const expiries = [];
  if (freshness?.snapshot_date) {
    const snapshot = parseDate(freshness.snapshot_date, "inventory snapshot");
    if (snapshot) expiries.push(addDays(snapshot, rules.inventoryMaxAgeDays));
  }
  const benchmark = status.code === "URGENT_EXIT"
    ? competitorContext?.urgentBenchmark
    : competitorContext?.activeBenchmark;
  const asins = new Set(benchmark?.asins ?? []);
  for (const row of competitorContext?.rows ?? []) {
    if (!asins.has(row.asin) || !row.captured_at) continue;
    const captured = parseDate(row.captured_at, "competitor captured_at");
    if (captured) expiries.push(addDays(captured, rules.competitorMaxAgeDays));
  }
  if (!expiries.length) return null;
  return dateText(new Date(Math.min(...expiries.map((date) => date.getTime()))));
}

function undercutTarget(benchmark, percent, maxAmount) {
  const undercut = Math.min(benchmark * percent, maxAmount);
  return roundMoney(benchmark - undercut);
}

function makeMarketTarget(status, context, currentPrice, rules) {
  if (status.code === "ACTIVE_CLEARANCE") {
    if (context.activeBenchmark) {
      return {
        value: undercutTarget(
          context.activeBenchmark.value,
          rules.activeUndercutPct,
          rules.activeUndercutMaxUsd
        ),
        method: `${context.activeBenchmark.type}_MINUS_1_PERCENT_MAX_0_30`,
        benchmark: context.activeBenchmark,
      };
    }
    return { value: null, method: "A_GRADE_REFERENCE_REQUIRED", benchmark: null };
  }
  if (status.code === "URGENT_EXIT") {
    if (context.urgentBenchmark) {
      return {
        value: undercutTarget(
          context.urgentBenchmark.value,
          rules.urgentUndercutPct,
          rules.urgentUndercutMaxUsd
        ),
        method: `${context.urgentBenchmark.type}_MINUS_2_PERCENT_MAX_0_50`,
        benchmark: context.urgentBenchmark,
      };
    }
    return { value: null, method: "A_GRADE_REFERENCE_REQUIRED", benchmark: null };
  }
  if (["HEALTHY_HOLD", "OBSERVE"].includes(status.code) && context.activeBenchmark) {
    return {
      value: context.activeBenchmark.value < currentPrice
        ? roundMoney(context.activeBenchmark.value)
        : currentPrice,
      method: context.activeBenchmark.value < currentPrice
        ? `${context.activeBenchmark.type}_MATCH_LOWER_COMPETITOR`
        : `${context.activeBenchmark.type}_CURRENT_PRICE_ALREADY_COMPETITIVE`,
      benchmark: context.activeBenchmark,
    };
  }
  return { value: null, method: null, benchmark: null };
}

function choosePrice(input, status, costs, context, issues, rules) {
  const pricing = input.pricing || {};
  const performance = input.performance || {};
  const currentPrice =
    numberOrNull(pricing.current_effective_price) ??
    numberOrNull(pricing.sale_price) ??
    numberOrNull(pricing.standard_price);
  if (!(currentPrice > 0)) {
    issues.push({ severity: "blocking", code: "CURRENT_PRICE_MISSING", message: "Current effective price is required." });
  }

  const result = {
    current_effective_price: currentPrice,
    recommended_price: currentPrice,
    price_action: status.action,
    market_target: null,
    market_method: null,
    applied_floor: null,
    held_reason: null,
    cannot_match_reason: null,
  };
  if (!(currentPrice > 0)) return result;

  if (
    [
      "NO_SELLABLE_INVENTORY",
      "CLEARANCE_REVIEW_REQUIRED",
      "INVENTORY_EXIT_ONLY",
    ].includes(status.code)
  ) {
    result.price_action = status.code === "NO_SELLABLE_INVENTORY" ? "NONE" : "HOLD";
    return result;
  }

  if (status.code === "LOW_STOCK_PROTECTION") {
    const primaryFba = context.activeBenchmark?.type === "A_FBA_PRIMARY"
      ? context.activeBenchmark.value
      : null;
    if (primaryFba !== null && primaryFba < currentPrice) {
      result.market_target = roundMoney(primaryFba);
      result.market_method = "LOWER_A_FBA_MATCH_OVERRIDES_LOW_STOCK_RAISE";
      result.applied_floor = costs.normal_floor;
      const protectedTarget = costs.normal_floor === null
        ? primaryFba
        : Math.max(primaryFba, costs.normal_floor);
      if (protectedTarget < currentPrice) {
        result.price_action = "MATCH_LOWER_A_FBA";
        result.recommended_price = roundMoney(protectedTarget);
      } else {
        result.price_action = "HOLD";
        result.held_reason = "The non-loss floor prevents matching the lower A-grade FBA price.";
        result.cannot_match_reason = "Market target is below the applicable cash/operating floor.";
      }
      return result;
    }
    const target = currentPrice * (1 + rules.lowStockRaisePct);
    const cap = primaryFba === null
      ? target
      : primaryFba * (1 + rules.lowStockCompetitorCapPct);
    if (primaryFba === null) {
      issues.push({
        severity: "blocking",
        code: "NO_A_FBA_FOR_RAISE",
        message: "Low-stock price increase is provisional because no fresh A-grade FBA anchor exists.",
      });
    }
    if (cap <= currentPrice) {
      result.price_action = "HOLD";
      result.held_reason = "A-grade FBA market cap does not allow an increase.";
    } else {
      result.recommended_price = roundMoney(Math.min(target, cap));
      result.market_target = result.recommended_price;
      result.market_method = primaryFba === null ? "OWN_PRICE_PLUS_2_PERCENT_PROVISIONAL" : "LOW_STOCK_PLUS_2_PERCENT";
    }
    return result;
  }

  const market = makeMarketTarget(status, context, currentPrice, rules);
  result.market_target = market.value;
  result.market_method = market.method;
  const floor = status.code === "URGENT_EXIT"
    ? costs.urgent_floor
    : status.code === "ACTIVE_CLEARANCE"
      ? costs.active_floor
      : costs.normal_floor;
  result.applied_floor = floor;
  if (market.value === null) {
    if (["ACTIVE_CLEARANCE", "URGENT_EXIT", "HEALTHY_HOLD", "OBSERVE"].includes(status.code)) {
      issues.push({
        severity: "blocking",
        code: "CONFIRMED_A_COMPETITOR_MISSING",
        message: "A fresh, confirmed A-grade competitor is required for a formal repricing decision.",
      });
    }
    result.price_action = "HOLD";
    result.held_reason = "No fresh, confirmed A-grade competitor anchor is available.";
    return result;
  }

  if (currentPrice <= market.value) {
    result.price_action = "HOLD";
    result.recommended_price = currentPrice;
    result.held_reason = "Current price is already at or below the selected A-grade market target.";
    return result;
  }

  const floorProtected = floor === null ? market.value : Math.max(market.value, floor);
  if (floor !== null && floor > market.value) {
    result.cannot_match_reason = "Market target is below the applicable cash/operating floor.";
  }
  if (floorProtected >= currentPrice) {
    result.price_action = status.code === "URGENT_EXIT" ? "EXIT_COMPARE" : "HOLD";
    result.recommended_price = currentPrice;
    result.held_reason = "The applicable loss floor is at or above the current price.";
    return result;
  }
  result.recommended_price = roundMoney(floorProtected);
  result.price_action = status.code === "ACTIVE_CLEARANCE"
    ? "UNDERCUT_A_REFERENCE"
    : status.code === "URGENT_EXIT"
      ? "URGENT_UNDERCUT_A_REFERENCE"
      : "MATCH_LOWER_A_REFERENCE";
  return result;
}

function applyNoRaiseOverride(input, priceDecision) {
  const currentPrice = numberOrNull(priceDecision.current_effective_price);
  const recommendedPrice = numberOrNull(priceDecision.recommended_price);
  if (
    input.pricing?.no_raise_this_run !== true
    || currentPrice === null
    || recommendedPrice === null
    || recommendedPrice <= currentPrice
  ) {
    return {
      ...priceDecision,
      no_raise_this_run: input.pricing?.no_raise_this_run === true,
      no_raise_override_applied: false,
      pre_override_recommended_price: recommendedPrice,
    };
  }
  return {
    ...priceDecision,
    recommended_price: currentPrice,
    price_action: "HOLD",
    held_reason: [priceDecision.held_reason, "Current-run no-raise override; keep the current effective price."]
      .filter(Boolean).join(" "),
    no_raise_this_run: true,
    no_raise_override_applied: true,
    pre_override_recommended_price: recommendedPrice,
  };
}

function buildPreview(input, status, priceDecision) {
  const pricing = input.pricing || {};
  const actions = [];
  if (!["HOLD", "NONE", "EXIT_COMPARE"].includes(priceDecision.price_action) &&
      priceDecision.recommended_price !== priceDecision.current_effective_price) {
    if (n0(pricing.sale_price) > 0) {
      actions.push({ action: "CLEAR_SALE_PRICE", fields: ["sale_price", "sale_start_date", "sale_end_date"] });
    }
    actions.push({ action: "SET_STANDARD_PRICE", value: priceDecision.recommended_price });
  }
  return {
    actions,
    requires_explicit_confirmation: actions.length > 0,
    coupon_actions: [],
    note: actions.length
      ? "Preview only. Never apply without the user's explicit confirmation in the current turn."
      : "No price write is proposed.",
  };
}

function maximumProcurementCostCny(price, input, costs) {
  if (!(price > 0) || !(costs.conservative_usd_cny_rate > 0) || costs.fixed_variable_fees === null) return null;
  const referralRate = numberOrNull(input.fees?.referral_fee_rate);
  if (!(referralRate >= 0 && referralRate < 1)) return null;
  const netUsdBeforeLandedCost = price * (1 - referralRate) - costs.fixed_variable_fees;
  return roundMoney(Math.max(0, netUsdBeforeLandedCost * costs.conservative_usd_cny_rate - costs.first_leg_cost_cny));
}

function purchaseViability(status, price, input, costs, blockingIssues) {
  if (["ACTIVE_CLEARANCE", "URGENT_EXIT", "OBSERVE", "INVENTORY_EXIT_ONLY", "NO_SELLABLE_INVENTORY"].includes(status.code)) {
    return {
      status: "暂不进货",
      reason: "当前库存状态不允许继续采购。",
      max_procurement_cost_cny: maximumProcurementCostCny(price, input, costs),
    };
  }
  const maximum = maximumProcurementCostCny(price, input, costs);
  const procurement = numberOrNull(input.costs?.procurement_cost_cny);
  if (blockingIssues.length || maximum === null || procurement === null) {
    return {
      status: "数据不足",
      reason: "缺少正式价格、准确费用、采购成本、汇率或有效竞品证据。",
      max_procurement_cost_cny: maximum,
    };
  }
  if (procurement <= maximum) {
    return {
      status: "可按当前成本进货",
      reason: "目标价可以覆盖采购、头程和准确 Amazon 费用。",
      max_procurement_cost_cny: maximum,
    };
  }
  return {
    status: "暂不进货",
    reason: "按当前采购成本销售会低于不亏要求。",
    max_procurement_cost_cny: maximum,
  };
}

function buildPriceDiscountAlternative(input, clearanceDecision, status, priceDecision, costs) {
  const pricing = input.pricing || {};
  const inventory = input.inventory || {};
  const available = n0(inventory.available);
  const clearanceQty = numberOrNull(clearanceDecision?.recommended_clearance_quantity);
  const clearanceMode = ["ACTIVE_CLEARANCE", "URGENT_EXIT"].includes(status.code);
  const clearanceDecisionComplete =
    clearanceDecision !== null &&
    ["高", "中"].includes(clearanceDecision.confidence) &&
    Boolean(clearanceDecision.source_file) &&
    clearanceDecision.reasons.length > 0 &&
    clearanceDecision.seller_sku === input.sku &&
    clearanceDecision.asin === input.asin &&
    clearanceDecision.inventory_age_snapshot_date === inventory.inventory_age_snapshot_date;
  const applicableFloor = status.code === "URGENT_EXIT" ? costs.urgent_floor : costs.active_floor;
  const priceMoves = ["LOWER", "LOWER_OR_EXIT", "UNDERCUT_A_REFERENCE", "URGENT_UNDERCUT_A_REFERENCE"].includes(priceDecision.price_action) &&
    priceDecision.recommended_price < priceDecision.current_effective_price;
  const eligible =
    clearanceMode &&
    clearanceDecisionComplete &&
    clearanceQty > 0 &&
    priceMoves &&
    applicableFloor !== null &&
    pricing.reference_price_validated === true &&
    pricing.price_discount_eligible === true &&
    pricing.price_discount_fee_known === true &&
    n0(pricing.sale_price) <= 0 &&
    pricing.own_coupon_active !== true;
  return {
    eligible_as_alternative: eligible,
    duration_days: eligible ? (status.code === "URGENT_EXIT" ? { min: 3, max: 7 } : { min: 7, max: 14 }) : null,
    max_units: eligible ? Math.min(available, clearanceQty) : 0,
    displayed_fee: eligible ? numberOrNull(pricing.price_discount_fee) : null,
    requires_explicit_confirmation: eligible,
    reason:
      !clearanceMode || !(clearanceQty > 0)
        ? "Price Discount requires a positive clearance quantity from amazon-inventory-clearance."
        : !clearanceDecisionComplete
          ? "Price Discount requires a complete, matching, non-low-confidence clearance decision."
        : eligible
          ? "Validated clearance quantity, reference price, eligibility, and displayed fee are available."
          : "Direct price remains the default; one or more Price Discount safeguards are not satisfied.",
  };
}

function calculate(input, asOfOverride) {
  const rules = { ...DEFAULT_RULES };
  const issues = [];
  const asOfDate = parseDate(asOfOverride || input.as_of_date, "as_of_date");
  if (!asOfDate) throw new Error("as_of_date is required.");

  const freshness = validateIdentityAndFreshness(input, asOfDate, issues, rules);
  const clearanceDecision = validateClearanceDecision(input, issues);
  const status = determineStatus(input, clearanceDecision, issues, rules);
  const costs = computeCosts(input, issues, rules);
  const competitors = status.code === "CLEARANCE_REVIEW_REQUIRED"
    ? {
        rows: [],
        activeBenchmark: null,
        urgentBenchmark: null,
        hasFreshAFba: false,
        skipped_reason: "Run amazon-inventory-clearance before competitor discovery.",
      }
    : buildCompetitorContext(input, asOfDate, rules, issues);
  const priceDecision = applyNoRaiseOverride(
    input,
    choosePrice(input, status, costs, competitors, issues, rules)
  );
  const preview = buildPreview(input, status, priceDecision);
  const priceDiscount = buildPriceDiscountAlternative(input, clearanceDecision, status, priceDecision, costs);

  const unfulfillable = n0(input.inventory?.unfulfillable);
  const stranded = n0(input.inventory?.stranded);
  const separateActions = [];
  if (unfulfillable > 0) separateActions.push({ type: "UNFULFILLABLE", units: unfulfillable, action: "Review removal or disposal separately." });
  if (stranded > 0) separateActions.push({ type: "STRANDED", units: stranded, action: "Fix the offer or review removal separately." });
  if (input.pricing?.own_coupon_active === true) {
    issues.push({
      severity: "blocking",
      code: "OWN_COUPON_ACTIVE",
      message: "An own-store Coupon is active. Do not create or recommend another discount until it is manually resolved.",
    });
  }

  const blocking = issues.filter((issue) => issue.severity === "blocking");
  const moved = preview.actions.length > 0;
  const executable = moved && blocking.length === 0;
  const expectedContribution = contributionAtPrice(priceDecision.recommended_price, input, costs);
  const available = n0(input.inventory?.available);
  const clearanceQuantity = numberOrNull(clearanceDecision?.recommended_clearance_quantity);
  const evaluationQuantity = ["ACTIVE_CLEARANCE", "URGENT_EXIT"].includes(status.code)
    ? Math.min(available, clearanceQuantity ?? 0)
    : available;

  const purchasing = purchaseViability(
    status,
    priceDecision.recommended_price,
    input,
    costs,
    blocking
  );
  const priceConfidence = blocking.length
    ? "LOW"
    : costs.operating_costs_complete
      ? "HIGH"
      : "MEDIUM_OPERATING_PROFIT_PENDING";
  const validUntil = priceValidUntil(freshness, status, competitors, rules);
  const cashFloor = applicableCostFloor(status.code, costs, "cash_");
  const operatingFloor = applicableCostFloor(status.code, costs, "operating_");

  return {
    seller_id: input.seller_id || null,
    marketplace: input.marketplace || null,
    sku: input.sku || null,
    asin: input.asin || null,
    as_of_date: dateText(asOfDate),
    inventory_freshness: freshness,
    source_priority: [
      "inventory_age_report",
      "amazon_inventory_clearance_decision",
      "backend_performance",
      "costs_and_official_fees",
      "front_end_competitor_reference",
    ],
    clearance_decision: clearanceDecision,
    status,
    costs,
    competitor_context: competitors,
    price_decision: {
      ...priceDecision,
      cash_floor: cashFloor,
      operating_floor: operatingFloor,
      operating_cost_completeness: costs.operating_cost_completeness,
      price_confidence: priceConfidence,
      price_valid_until: validUntil,
      expected_contribution_per_unit: expectedContribution,
      evaluation_quantity: evaluationQuantity,
      expected_batch_contribution:
        expectedContribution === null ? null : roundMoney(expectedContribution * evaluationQuantity),
      next_review_date: dateText(addDays(asOfDate, status.reviewDays)),
    },
    price_discount_alternative: priceDiscount,
    purchase_viability: purchasing,
    separate_inventory_actions: separateActions,
    data_issues: issues,
    executable_after_confirmation: executable,
    preview,
    permanent_rules: {
      own_store_coupon: "PERMANENTLY_DISABLED",
      automatic_pricing: "DISABLED",
      competitor_front_end_role: "REFERENCE_ONLY",
    },
    rules,
  };
}

function assert(condition, message) {
  if (!condition) throw new Error(`Self-test failed: ${message}`);
}

function baseFixture() {
  return {
    seller_id: "56321",
    marketplace: "US",
    sku: "OZ-S1IA-VJCA",
    asin: "B0GHFVQSGM",
    as_of_date: "2026-07-26",
    inventory: {
      seller_sku: "OZ-S1IA-VJCA",
      asin: "B0GHFVQSGM",
      inventory_age_snapshot_date: "2026-07-24",
      available: 4,
      unfulfillable: 1,
      age_0_90: 0,
      age_91_180: 4,
      age_181_270: 0,
      estimated_excess_quantity: 4,
      sell_through: 0,
      days_of_supply: 999,
      alert: "Low traffic",
    },
    clearance_decision: {
      seller_sku: "OZ-S1IA-VJCA",
      asin: "B0GHFVQSGM",
      status: "主动清货",
      recommended_clearance_quantity: 4,
      confidence: "高",
      reasons: ["The canonical clearance plan classified this SKU as active clearance."],
      inventory_age_snapshot_date: "2026-07-24",
      source_file: "/tmp/clearance-plan-20260726.xlsx",
    },
    performance: { units_30d: 0, units_60d: 0, units_90d: 0, sessions_30d: 0, orders_30d: 0 },
    costs: { procurement_cost_cny: 40, first_leg_cost_cny: 10, usd_cny_rate: 7.2 },
    fees: {
      exact: true,
      referral_fee_rate: 0.15,
      fulfillment_fee: 4.5,
      storage_per_unit: 0.2,
      return_reserve_per_unit: 0,
      future_ad_cost_per_order: 0,
      other_variable_fee_per_unit: 0,
    },
    pricing: {
      standard_price: 33.99,
      sale_price: 27.99,
      current_effective_price: 27.99,
      own_fulfillment: "FBA",
      own_delivery_days: 2,
      reference_price_validated: false,
      price_discount_eligible: false,
      price_discount_fee_known: false,
      own_coupon_active: false,
    },
    competitors: [
      { asin: "B0G6JL3KCD", grade: "A", confirmation_status: "USER_CONFIRMED", price_role: "PRIMARY", price: 22.99, coupon_amount: 0, shipping: 0, fulfillment: "FBA", delivery_days: 2, in_stock: true, captured_at: "2026-07-26" },
      { asin: "B0GQSPQJZS", grade: "A", confirmation_status: "USER_CONFIRMED", price_role: "REFERENCE", price: 23.99, coupon_amount: 0, shipping: 0, fulfillment: "FBM", delivery_days: 12, direct_from_china: true, in_stock: true, captured_at: "2026-07-26" },
      { asin: "B0G1KT7Y9S", grade: "A", confirmation_status: "USER_CONFIRMED", price_role: "LOWER_BOUND", price: 19.99, coupon_amount: 0, shipping: 0, fulfillment: "FBA", delivery_days: 2, in_stock: true, captured_at: "2026-07-26" },
    ],
  };
}

function runSelfTest() {
  const active = calculate(baseFixture());
  assert(active.status.code === "ACTIVE_CLEARANCE", "trial SKU should be active clearance");
  assert(active.price_decision.recommended_price === 22.76, "active clearance should undercut A FBA by 1%");
  assert(active.price_decision.evaluation_quantity === 4, "clearance batch must use the canonical clearance quantity");
  assert(active.separate_inventory_actions[0].units === 1, "unfulfillable unit must be separate");
  assert(active.preview.actions.some((row) => row.action === "CLEAR_SALE_PRICE"), "sale price must be cleared in preview");
  assert(active.preview.coupon_actions.length === 0, "own Coupon actions must stay empty");

  const missingClearanceInput = baseFixture();
  delete missingClearanceInput.clearance_decision;
  const missingClearance = calculate(missingClearanceInput);
  assert(missingClearance.status.code === "CLEARANCE_REVIEW_REQUIRED", "risky inventory must require the clearance skill");
  assert(missingClearance.competitor_context.rows.length === 0, "competitor analysis must be skipped until clearance review");
  assert(missingClearance.preview.actions.length === 0, "missing clearance output must not create a price preview");

  const canonicalHealthyInput = baseFixture();
  canonicalHealthyInput.clearance_decision.status = "健康维持";
  canonicalHealthyInput.clearance_decision.recommended_clearance_quantity = 0;
  canonicalHealthyInput.clearance_decision.reasons = ["The canonical clearance plan requires no clearance action."];
  const canonicalHealthy = calculate(canonicalHealthyInput);
  assert(canonicalHealthy.status.code === "HEALTHY_HOLD", "canonical healthy state should remain authoritative");
  assert(canonicalHealthy.price_decision.recommended_price === 22.99, "healthy inventory must match a lower A FBA price");
  assert(canonicalHealthy.preview.actions.length === 2, "healthy follow-down must produce a preview only");

  const urgentInput = baseFixture();
  urgentInput.clearance_decision.status = "紧急清退";
  urgentInput.clearance_decision.reasons = ["The canonical clearance plan classified this SKU as urgent exit."];
  urgentInput.inventory.age_91_180 = 0;
  urgentInput.inventory.age_181_270 = 4;
  urgentInput.pricing.standard_price = 22.49;
  urgentInput.pricing.sale_price = 0;
  urgentInput.pricing.current_effective_price = 22.49;
  const urgent = calculate(urgentInput);
  assert(urgent.status.code === "URGENT_EXIT", "canonical urgent-exit status should map to urgent pricing");
  assert(urgent.price_decision.recommended_price === 19.59, "urgent target should use the lowest credible A FBA minus 2%");

  const activeFloorInput = baseFixture();
  activeFloorInput.competitors = [
    {
      asin: "B0ACTIVEFLOOR",
      grade: "A",
      price_role: "PRIMARY",
      price: 5,
      shipping: 0,
      fulfillment: "FBA",
      exact_variant_confirmed: true,
      in_stock: true,
      captured_at: "2026-07-26",
    },
  ];
  const activeFloor = calculate(activeFloorInput);
  assert(
    activeFloor.price_decision.recommended_price === activeFloor.costs.active_floor,
    "active clearance must not cross the 15% loss floor"
  );

  const urgentFloorInput = baseFixture();
  urgentFloorInput.clearance_decision.status = "紧急清退";
  urgentFloorInput.clearance_decision.reasons = ["Canonical urgent-exit decision."];
  urgentFloorInput.competitors = [
    {
      asin: "B0URGENTFLOOR",
      grade: "A",
      price_role: "LOWER_BOUND",
      price: 5,
      shipping: 0,
      fulfillment: "FBA",
      exact_variant_confirmed: true,
      in_stock: true,
      captured_at: "2026-07-26",
    },
  ];
  const urgentFloor = calculate(urgentFloorInput);
  assert(
    urgentFloor.price_decision.recommended_price === urgentFloor.costs.urgent_floor,
    "urgent exit must not cross the 30% loss floor"
  );

  const exitOnlyInput = baseFixture();
  exitOnlyInput.clearance_decision.status = "紧急清退";
  exitOnlyInput.clearance_decision.recommended_clearance_quantity = 0;
  exitOnlyInput.clearance_decision.reasons = ["Only unfulfillable inventory requires disposal review."];
  exitOnlyInput.inventory.age_91_180 = 0;
  exitOnlyInput.inventory.age_0_90 = 4;
  exitOnlyInput.inventory.estimated_excess_quantity = 0;
  exitOnlyInput.inventory.days_of_supply = 30;
  exitOnlyInput.performance.units_30d = 3;
  exitOnlyInput.performance.units_60d = 7;
  const exitOnly = calculate(exitOnlyInput);
  assert(exitOnly.status.code === "INVENTORY_EXIT_ONLY", "zero-quantity urgent output must remain an inventory-only action");
  assert(exitOnly.preview.actions.length === 0, "unfulfillable-only risk must not reduce sellable inventory price");

  const healthyInput = baseFixture();
  delete healthyInput.clearance_decision;
  healthyInput.inventory.unfulfillable = 0;
  healthyInput.inventory.age_91_180 = 0;
  healthyInput.inventory.age_0_90 = 4;
  healthyInput.inventory.estimated_excess_quantity = 0;
  healthyInput.inventory.sell_through = 1;
  healthyInput.inventory.days_of_supply = 45;
  healthyInput.inventory.alert = "";
  healthyInput.performance.units_30d = 3;
  healthyInput.performance.units_60d = 7;
  healthyInput.performance.sessions_30d = 100;
  healthyInput.performance.orders_30d = 3;
  const healthy = calculate(healthyInput);
  assert(healthy.status.code === "HEALTHY_HOLD", "healthy inventory should keep its inventory route");
  assert(healthy.price_decision.recommended_price === 22.99, "lower A-grade FBA must trigger a healthy follow suggestion");
  assert(healthy.purchase_viability.status === "可按当前成本进货", "non-loss healthy target should allow current-cost purchasing");

  const staleInput = baseFixture();
  staleInput.inventory.inventory_age_snapshot_date = "2026-07-01";
  staleInput.clearance_decision.inventory_age_snapshot_date = "2026-07-01";
  const stale = calculate(staleInput);
  assert(stale.executable_after_confirmation === false, "stale inventory report must block execution");

  const noAInput = baseFixture();
  noAInput.competitors = [];
  const noA = calculate(noAInput);
  assert(noA.price_decision.recommended_price === 27.99, "active clearance without A must not fabricate a discount");
  assert(noA.data_issues.some((issue) => issue.code === "CONFIRMED_A_COMPETITOR_MISSING"), "missing A must block formal pricing");

  const lowStockInput = baseFixture();
  delete lowStockInput.clearance_decision;
  lowStockInput.inventory.available = 2;
  lowStockInput.inventory.unfulfillable = 0;
  lowStockInput.inventory.age_91_180 = 0;
  lowStockInput.inventory.age_0_90 = 2;
  lowStockInput.inventory.estimated_excess_quantity = 0;
  lowStockInput.inventory.sell_through = 1;
  lowStockInput.inventory.days_of_supply = 5;
  lowStockInput.inventory.inventory_health_status = "Understock";
  lowStockInput.inventory.fba_minimum_inventory_level = 5;
  lowStockInput.inventory.inbound = 0;
  lowStockInput.inventory.alert = "";
  lowStockInput.performance.units_30d = 3;
  lowStockInput.performance.units_60d = 7;
  lowStockInput.performance.sessions_30d = 100;
  lowStockInput.performance.orders_30d = 3;
  lowStockInput.pricing.standard_price = 20.99;
  lowStockInput.pricing.sale_price = 0;
  lowStockInput.pricing.current_effective_price = 20.99;
  const lowStock = calculate(lowStockInput);
  assert(lowStock.status.code === "LOW_STOCK_PROTECTION", "understock with sales should trigger protection");
  assert(lowStock.price_decision.recommended_price === 21.41, "low-stock first raise should be 2%");

  const lowStockLowerCompetitorInput = structuredClone(lowStockInput);
  lowStockLowerCompetitorInput.competitors[0].price = 19.99;
  const lowStockLowerCompetitor = calculate(lowStockLowerCompetitorInput);
  assert(
    lowStockLowerCompetitor.price_decision.recommended_price === 19.99,
    "lower A FBA must override the low-stock price increase"
  );

  const mismatchInput = baseFixture();
  mismatchInput.clearance_decision.inventory_age_snapshot_date = "2026-07-23";
  const mismatch = calculate(mismatchInput);
  assert(
    mismatch.data_issues.some((issue) => issue.code === "CLEARANCE_SNAPSHOT_CONFLICT"),
    "clearance and repricing snapshots must match"
  );
  assert(mismatch.executable_after_confirmation === false, "snapshot mismatch must block execution");

  const lowConfidenceInput = baseFixture();
  lowConfidenceInput.clearance_decision.confidence = "低";
  lowConfidenceInput.pricing.sale_price = 0;
  lowConfidenceInput.pricing.reference_price_validated = true;
  lowConfidenceInput.pricing.price_discount_eligible = true;
  lowConfidenceInput.pricing.price_discount_fee_known = true;
  const lowConfidence = calculate(lowConfidenceInput);
  assert(lowConfidence.executable_after_confirmation === false, "low-confidence clearance output must remain provisional");
  assert(
    lowConfidence.price_discount_alternative.eligible_as_alternative === false,
    "low-confidence clearance output must not enable Price Discount"
  );

  const discountInput = baseFixture();
  discountInput.pricing.sale_price = 0;
  discountInput.pricing.current_effective_price = 27.99;
  discountInput.pricing.reference_price_validated = true;
  discountInput.pricing.price_discount_eligible = true;
  discountInput.pricing.price_discount_fee_known = true;
  discountInput.pricing.price_discount_fee = 2;
  const discount = calculate(discountInput);
  assert(discount.price_discount_alternative.eligible_as_alternative === true, "valid Price Discount should remain available");
  assert(discount.price_discount_alternative.max_units === 4, "Price Discount must use the canonical clearance quantity");

  const discountNoQuantityInput = baseFixture();
  discountNoQuantityInput.clearance_decision.recommended_clearance_quantity = 0;
  discountNoQuantityInput.pricing.sale_price = 0;
  discountNoQuantityInput.pricing.current_effective_price = 27.99;
  discountNoQuantityInput.pricing.reference_price_validated = true;
  discountNoQuantityInput.pricing.price_discount_eligible = true;
  discountNoQuantityInput.pricing.price_discount_fee_known = true;
  const discountNoQuantity = calculate(discountNoQuantityInput);
  assert(
    discountNoQuantity.price_discount_alternative.eligible_as_alternative === false,
    "Price Discount must require a positive canonical clearance quantity"
  );
  assert(discountNoQuantity.price_discount_alternative.max_units === 0, "Price Discount must never fall back to all inventory");

  const feeMissingInput = baseFixture();
  feeMissingInput.fees.exact = false;
  const feeMissing = calculate(feeMissingInput);
  assert(feeMissing.executable_after_confirmation === false, "missing exact fees must block execution");
  assert(feeMissing.price_discount_alternative.eligible_as_alternative === false, "Price Discount needs a cost floor");

  const couponInput = baseFixture();
  couponInput.pricing.own_coupon_active = true;
  const coupon = calculate(couponInput);
  assert(coupon.executable_after_confirmation === false, "active own Coupon must block execution");
  assert(coupon.preview.coupon_actions.length === 0, "the skill must never create Coupon actions");

  const tempAInput = baseFixture();
  tempAInput.competitors = tempAInput.competitors.map((row) => ({
    ...row,
    confirmation_status: "TEMP_A",
    exact_variant_confirmed: true,
  }));
  const tempA = calculate(tempAInput);
  assert(
    tempA.data_issues.some((issue) => issue.code === "TEMP_A_COMPETITOR_ONLY"),
    "TEMP_A-only competitors must keep the market target provisional"
  );
  assert(tempA.executable_after_confirmation === false, "TEMP_A-only pricing must remain blocked");

  const bOnlyInput = baseFixture();
  bOnlyInput.competitors = bOnlyInput.competitors.map((row) => ({
    ...row,
    grade: "B",
    confirmation_status: "AGENT_CONFIRMED",
  }));
  const bOnly = calculate(bOnlyInput);
  assert(bOnly.competitor_context.activeBenchmark === null, "B-grade competitors must not become price anchors");
  assert(
    bOnly.price_decision.market_method === "A_GRADE_REFERENCE_REQUIRED",
    "B-grade competitors must not generate a formal target"
  );

  const promotedBInput = baseFixture();
  promotedBInput.competitors = [{
    ...promotedBInput.competitors[0],
    grade: "B",
    original_grade: "B",
    user_promoted_to_a: true,
    effective_grade: "A",
  }];
  const promotedB = calculate(promotedBInput);
  assert(promotedB.competitor_context.activeBenchmark !== null, "a user-promoted B competitor should act as A for the exact pair");
  assert(promotedB.competitor_context.rows[0].original_grade === "B", "the original B grade must remain auditable");

  const cashOnlyInput = baseFixture();
  delete cashOnlyInput.fees.return_reserve_per_unit;
  delete cashOnlyInput.fees.future_ad_cost_per_order;
  const cashOnly = calculate(cashOnlyInput);
  assert(cashOnly.costs.cash_normal_floor > 0, "cash floor must remain available when operating costs are incomplete");
  assert(cashOnly.costs.operating_normal_floor === null, "operating floor must remain blank when operating costs are incomplete");
  assert(
    cashOnly.price_decision.price_confidence === "MEDIUM_OPERATING_PROFIT_PENDING",
    "cash-only formal pricing must disclose pending operating profit"
  );

  const unknownFbmInput = baseFixture();
  unknownFbmInput.competitors = [{
    ...unknownFbmInput.competitors[1],
    direct_from_china: false,
    delivery_days: null,
  }];
  const unknownFbm = calculate(unknownFbmInput);
  assert(
    unknownFbm.data_issues.some((issue) => issue.code === "COMPETITOR_FULFILLMENT_UNVERIFIED"),
    "FBM without delivery evidence must remain a weak reference"
  );

  const unverifiedVariantInput = baseFixture();
  unverifiedVariantInput.competitors = [{
    ...unverifiedVariantInput.competitors[0],
    confirmation_status: "AGENT_CONFIRMED",
    exact_variant_confirmed: false,
  }];
  const unverifiedVariant = calculate(unverifiedVariantInput);
  assert(
    unverifiedVariant.data_issues.some((issue) => issue.code === "COMPETITOR_VARIANT_UNVERIFIED"),
    "appearance-only A candidates must not become formal anchors"
  );
  assert(active.price_decision.price_valid_until === "2026-07-30", "price validity must use the earlier inventory/competitor expiry");

  const maxUndercutInput = baseFixture();
  maxUndercutInput.competitors[0].price = 99.99;
  maxUndercutInput.pricing.current_effective_price = 120;
  maxUndercutInput.pricing.sale_price = 0;
  const maxUndercut = calculate(maxUndercutInput);
  assert(maxUndercut.price_decision.recommended_price === 99.69, "active undercut must be capped at $0.30");

  const competitorCouponDisplayPriceInput = baseFixture();
  competitorCouponDisplayPriceInput.competitors = [{
    ...competitorCouponDisplayPriceInput.competitors[0],
    price: 22.99,
    coupon_amount: 5,
    shipping: 0,
    fulfillment: "FBA",
  }];
  const competitorCouponDisplayPrice = calculate(competitorCouponDisplayPriceInput);
  assert(
    competitorCouponDisplayPrice.competitor_context.rows[0].effective_price === 22.99,
    "competitor Coupon must not be deducted from the displayed FBA price"
  );

  const fbmLandedInput = baseFixture();
  fbmLandedInput.competitors = [{
    ...fbmLandedInput.competitors[1],
    price: 20,
    coupon_amount: 5,
    shipping: 4.99,
    fulfillment: "FBM",
    delivery_days: 12,
  }];
  const fbmLanded = calculate(fbmLandedInput);
  assert(
    fbmLanded.competitor_context.rows[0].effective_price === 24.99,
    "FBM landed price must equal displayed price plus shipping"
  );

  const fbaOwnDeliveryUnknownInput = structuredClone(fbmLandedInput);
  fbaOwnDeliveryUnknownInput.pricing.own_delivery_days = null;
  fbaOwnDeliveryUnknownInput.competitors[0].direct_from_china = false;
  const fbaOwnDeliveryUnknown = calculate(fbaOwnDeliveryUnknownInput);
  assert(
    fbaOwnDeliveryUnknown.competitor_context.rows[0].delivery_premium === 2,
    "own FBA must receive the 8–14 day FBM premium even when own delivery days are missing"
  );
  assert(
    fbaOwnDeliveryUnknown.competitor_context.rows[0].delivery_premium_basis === "FBA_VS_FBM_8_14_DAYS",
    "FBM premium basis must remain auditable"
  );

  const fbaSlowFbmInput = structuredClone(fbmLandedInput);
  fbaSlowFbmInput.pricing.own_delivery_days = null;
  fbaSlowFbmInput.competitors[0].direct_from_china = false;
  fbaSlowFbmInput.competitors[0].delivery_days = 20;
  const fbaSlowFbm = calculate(fbaSlowFbmInput);
  assert(fbaSlowFbm.competitor_context.rows[0].delivery_premium === 3, "FBM over 14 days must receive a $3 premium");

  const noRaiseInput = structuredClone(lowStockInput);
  noRaiseInput.pricing.no_raise_this_run = true;
  const noRaise = calculate(noRaiseInput);
  assert(noRaise.price_decision.recommended_price === 20.99, "run-only no-raise must keep the current price");
  assert(noRaise.price_decision.pre_override_recommended_price === 21.41, "run-only no-raise must preserve the blocked target");
  assert(noRaise.price_decision.no_raise_override_applied === true, "run-only no-raise override must be disclosed");

  process.stdout.write("Self-test passed: 30 scenarios.\n");
}

function main() {
  const args = parseArgs(process.argv);
  if (args.selfTest) {
    runSelfTest();
    return;
  }
  if (!args.input || !args.output) {
    throw new Error("Usage: calculate_repricing.cjs --input input.json --output output.json [--as-of-date YYYY-MM-DD]");
  }
  const input = JSON.parse(fs.readFileSync(args.input, "utf8"));
  const result = calculate(input, args["as-of-date"]);
  fs.writeFileSync(args.output, `${JSON.stringify(result, null, 2)}\n`, "utf8");
}

module.exports = {
  calculate,
  runSelfTest,
};

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}
