#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { assessFbaTransitionRisk, subjectIdentity } = require("./fba_transition_risk.cjs");

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    const key = argv[i].slice(2);
    const next = argv[i + 1];
    out[key] = next && !next.startsWith("--") ? next : true;
    if (out[key] !== true) i += 1;
  }
  return out;
}

function readJson(file, fallback) {
  if (!file || !fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function rows(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.competitors || payload?.snapshots || [];
}

function num(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function bool(value, defaultValue = false) {
  if (typeof value === "boolean") return value;
  if (value === null || value === undefined || value === "") return defaultValue;
  return !["0", "false", "no", "n", "否"].includes(String(value).trim().toLowerCase());
}

function keys(row) {
  const subject = subjectIdentity(row);
  const lineages = new Set([subject.lineage_key]);
  if (subject.own_sku) lineages.add(`SKU:${subject.own_sku}`);
  return [...lineages].filter(Boolean).map((lineage) => [lineage, row.competitor_asin, row.variant || ""].join("::"));
}

function decisionKeys(row) {
  return keys({ ...row, variant: "" });
}

function normalizeSnapshot(row, userDecision = null) {
  const subject = subjectIdentity(row);
  const originalGrade = String(row.original_grade || row.grade || "").trim().toUpperCase();
  const promoted = originalGrade === "B" && (
    row.user_promoted_to_a === true || userDecision?.user_promoted_to_a === true
  );
  const effectiveGrade = promoted
    ? "A"
    : String(row.effective_grade || originalGrade).trim().toUpperCase();
  return {
    ...row,
    ...subject,
    original_grade: originalGrade,
    effective_grade: effectiveGrade,
    grade: effectiveGrade,
    user_promoted_to_a: promoted,
    user_confirmed_at: promoted
      ? (userDecision?.user_confirmed_at ?? row.user_confirmed_at ?? null)
      : null,
    confirmation_status: promoted
      ? "USER_CONFIRMED"
      : String(row.confirmation_status || (row.variant_confirmed ? "AGENT_CONFIRMED" : "TEMP_A")).toUpperCase(),
    effective_price: effectivePrice(row),
    screenshot_path: row.screenshot_path ?? row.screenshot_url ?? "",
    evidence_url: row.evidence_url ?? row.source_url ?? "",
    grade_reason: row.grade_reason ?? "",
    difference_points: Array.isArray(row.difference_points)
      ? row.difference_points
      : String(row.difference_points ?? "").split("；").filter(Boolean),
  };
}

function effectivePrice(row) {
  const price = num(row.price);
  if (price !== null) return price + (num(row.shipping) || 0);
  return num(row.effective_price);
}

function confidence(row) {
  const coreComplete =
    effectivePrice(row) !== null &&
    row.fulfillment &&
    num(row.delivery_days) !== null &&
    row.in_stock !== null &&
    row.in_stock !== undefined;
  if (!bool(row.variant_confirmed, false) || !coreComplete || bool(row.data_conflict, false)) {
    return "低";
  }
  if (bool(row.page_fields_complete, false) && String(row.zip || "") === "75201") return "高";
  return "中";
}

function event(base, type, oldValue, newValue, conf) {
  const confirmedFbmToFba = type === "FULFILLMENT_CHANGED" && oldValue === "FBM" && newValue === "FBA";
  return {
    event_type: type,
    subject_type: base.subject_type,
    subject_id: base.subject_id,
    candidate_id: base.candidate_id,
    lineage_key: base.lineage_key,
    own_sku: base.own_sku,
    competitor_asin: base.competitor_asin,
    variant: base.variant || "",
    original_grade: String(base.original_grade || base.grade || "").toUpperCase(),
    effective_grade: String(base.effective_grade || base.grade || "").toUpperCase(),
    grade: String(base.effective_grade || base.grade || "").toUpperCase(),
    old_value: oldValue,
    new_value: newValue,
    captured_at: base.captured_at || new Date().toISOString(),
    confidence: conf,
    recommendation:
      conf === "低"
        ? type === "FBA_TRANSITION_RISK_HIGH"
          ? "补齐稳定 Seller ID 并人工复核；确认前按高风险候选缩量试单，不自动修改采购量"
          : "人工复核，不同步价格"
        : type === "EFFECTIVE_PRICE_CHANGED"
          ? "人工评估是否跟价；本店不得使用 Coupon"
          : type === "FBA_TRANSITION_RISK_HIGH"
            ? "建议缩量试单；缺稳定 Seller ID 时先补证，不自动修改采购量"
          : "人工复核竞品状态并评估库存、价格或广告影响",
    requires_secondary_zip_check: true,
    source_url: base.source_url || "",
    screenshot_path: base.screenshot_path || "",
    evidence_url: base.evidence_url || base.source_url || "",
    competitor_seller_id: base.competitor_seller_id || "",
    seller_name: base.seller_name || "",
    fba_transition_risk: base.fba_transition_risk || "REVIEW",
    fba_transition_risk_label: base.fba_transition_risk_label || "待复核",
    fba_transition_risk_reasons: base.fba_transition_risk_reasons || [],
    route_repricing_review: confirmedFbmToFba,
    route_replenishment_recalculation: confirmedFbmToFba,
    route_clearance_review: false,
    clearance_route_rule: "只有本店库存命中超量、滞销或库龄门禁时才允许进入清货分析",
  };
}

function analyze(currentPayload, previousPayload, runMode) {
  const gradeByMode = { daily: "A", weekly: "B", monthly: "C" };
  const targetGrade = gradeByMode[runMode] || "A";
  const decisions = new Map();
  for (const row of currentPayload?.user_decisions || []) {
    for (const rowKey of decisionKeys(row)) decisions.set(rowKey, row);
  }
  const normalizedCurrentRows = rows(currentPayload)
    .map((row) => normalizeSnapshot(row, decisionKeys(row).map((rowKey) => decisions.get(rowKey)).find(Boolean)));
  const previousRows = rows(previousPayload).map((row) => normalizeSnapshot(row));
  const riskAssessment = assessFbaTransitionRisk({
    currentRows: normalizedCurrentRows,
    previousPayloads: [previousPayload],
    asOfDate: currentPayload?.captured_at,
  });
  const currentRows = riskAssessment.snapshots;
  const previous = new Map();
  for (const row of previousRows) {
    for (const rowKey of keys(row)) previous.set(rowKey, row);
  }
  const events = [];
  const issues = [];

  for (const current of currentRows) {
    const grade = String(current.effective_grade || current.grade || "").toUpperCase();
    const originalGrade = String(current.original_grade || grade).toUpperCase();
    const inCadence = runMode === "daily"
      ? grade === "A"
      : runMode === "weekly"
        ? originalGrade === "B" && grade !== "A"
        : originalGrade === targetGrade;
    if (!inCadence) continue;
    const conf = confidence(current);
    const old = keys(current).map((rowKey) => previous.get(rowKey)).find(Boolean);
    if (!old) {
      if (current.user_promoted_to_a) {
        events.push(event(current, "USER_PROMOTED_B_TO_A", "B", "A", conf));
      } else if (grade === "A") {
        events.push(event(current, "NEW_GRADE_A_COMPETITOR", null, current.competitor_asin, conf));
      }
      if (current.fulfillment === "FBM" && current.fba_transition_risk === "HIGH") {
        const riskConfidence = current.fba_transition_assessment_status === "FORMAL" ? conf : "低";
        events.push(event(current, "FBA_TRANSITION_RISK_HIGH", null, "HIGH", riskConfidence));
      }
      continue;
    }

    if (current.user_promoted_to_a && !old.user_promoted_to_a) {
      events.push(event(current, "USER_PROMOTED_B_TO_A", "B", "A", conf));
    }

    if (
      current.fulfillment === "FBM"
      && current.fba_transition_risk === "HIGH"
      && old.fba_transition_risk !== "HIGH"
    ) {
      const riskConfidence = current.fba_transition_assessment_status === "FORMAL" ? conf : "低";
      events.push(event(current, "FBA_TRANSITION_RISK_HIGH", old.fba_transition_risk ?? null, "HIGH", riskConfidence));
    }

    const oldPrice = effectivePrice(old);
    const newPrice = effectivePrice(current);
    if (oldPrice !== null && newPrice !== null) {
      const absolute = Math.abs(newPrice - oldPrice);
      const relative = oldPrice > 0 ? absolute / oldPrice : 0;
      if (absolute >= 0.5 || relative >= 0.03) {
        events.push(event(current, "EFFECTIVE_PRICE_CHANGED", oldPrice, newPrice, conf));
      }
    } else {
      issues.push({ subject_type: current.subject_type, subject_id: current.subject_id, candidate_id: current.candidate_id, own_sku: current.own_sku, competitor_asin: current.competitor_asin, issue: "到手价字段缺失" });
    }

    const oldCoupon = num(old.coupon_amount) || 0;
    const newCoupon = num(current.coupon_amount) || 0;
    if (oldCoupon !== newCoupon) events.push(event(current, "COMPETITOR_COUPON_CHANGED", oldCoupon, newCoupon, conf));

    const oldFulfillment = String(old.fulfillment || "UNKNOWN").toUpperCase();
    const newFulfillment = String(current.fulfillment || "UNKNOWN").toUpperCase();
    if (oldFulfillment !== newFulfillment) {
      events.push(event(current, "FULFILLMENT_CHANGED", oldFulfillment, newFulfillment, conf));
    }

    const oldStock = bool(old.in_stock);
    const newStock = bool(current.in_stock);
    if (oldStock !== newStock) {
      events.push(event(current, newStock ? "STOCK_RECOVERED" : "STOCK_OUT", oldStock, newStock, conf));
    }

    const oldDelivery = num(old.delivery_days);
    const newDelivery = num(current.delivery_days);
    if (oldDelivery !== null && newDelivery !== null && Math.abs(newDelivery - oldDelivery) >= 3) {
      events.push(event(current, "DELIVERY_DAYS_CHANGED", oldDelivery, newDelivery, conf));
    }

    if (conf === "低") {
      issues.push({ subject_type: current.subject_type, subject_id: current.subject_id, candidate_id: current.candidate_id, own_sku: current.own_sku, competitor_asin: current.competitor_asin, issue: "低置信度：变体、关键字段或来源冲突" });
    }
  }

  return {
    generated_at: new Date().toISOString(),
    run_mode: runMode,
    monitored_grade: targetGrade,
    seller_id: currentPayload?.seller_id || null,
    marketplace: currentPayload?.marketplace || null,
    coupon_policy: "OWN_COUPON_PERMANENTLY_DISABLED",
    events,
    data_issues: issues,
    snapshots: currentRows,
    seller_profiles: riskAssessment.seller_profiles,
    competitor_fulfillment_history: riskAssessment.fulfillment_history,
    fulfillment_transitions: riskAssessment.fulfillment_transitions,
    collection_queue: riskAssessment.collection_queue,
    fba_transition_risk_summary: riskAssessment.summary,
    safety_routes: {
      repricing: "RECALCULATE_AFTER_CONFIRMED_FBM_TO_FBA",
      replenishment: "RECALCULATE_AND_REQUIRE_MANUAL_QUANTITY_REVIEW",
      clearance: "ONLY_AFTER_OWN_INVENTORY_CLEARANCE_GATE",
      price_write: "FORBIDDEN",
      purchase_write: "FORBIDDEN",
    },
  };
}

function selfTest() {
  const fixture = {
    seller_id: "56321",
    marketplace: "US",
    user_decisions: [{
      own_sku: "SKU-1",
      competitor_asin: "B000000001",
      user_promoted_to_a: true,
      user_confirmed_at: "2026-08-04T10:00:00+08:00",
    }],
    competitors: [{
      own_sku: "SKU-1",
      competitor_asin: "B000000001",
      original_grade: "B",
      grade: "B",
      price: 19.99,
      coupon_amount: 1,
      shipping: 0,
      fulfillment: "FBA",
      delivery_days: 2,
      in_stock: true,
      variant_confirmed: true,
      page_fields_complete: true,
      zip: "75201",
      captured_at: "2026-08-04",
      screenshot_path: "/tmp/evidence.png",
    }],
  };
  const daily = analyze(fixture, { competitors: [] }, "daily");
  if (daily.snapshots[0].effective_price !== 19.99) {
    throw new Error("Competitor Coupon must not be deducted from displayed price");
  }
  if (daily.snapshots[0].effective_grade !== "A" || daily.snapshots[0].original_grade !== "B") {
    throw new Error("B-to-A promotion did not preserve original grade");
  }
  if (!daily.events.some((row) => row.event_type === "USER_PROMOTED_B_TO_A")) {
    throw new Error("B-to-A promotion did not enter daily A monitoring");
  }
  const unrelated = structuredClone(fixture);
  unrelated.user_decisions[0].competitor_asin = "B000000999";
  const unrelatedDaily = analyze(unrelated, { competitors: [] }, "daily");
  if (unrelatedDaily.snapshots[0].effective_grade !== "B" || unrelatedDaily.events.length !== 0) {
    throw new Error("B-to-A promotion leaked to another SKU/ASIN pair");
  }
  const sellerRisk = analyze({
    seller_id: "56321",
    marketplace: "US",
    captured_at: "2026-08-08",
    competitors: [
      { ...fixture.competitors[0], own_sku: "SKU-FBM", competitor_asin: "B000000010", competitor_seller_id: "SELLER-1", seller_name: "Same Seller", fulfillment: "FBM" },
      { ...fixture.competitors[0], own_sku: "SKU-FBA-1", competitor_asin: "B000000011", competitor_seller_id: "SELLER-1", seller_name: "Same Seller", fulfillment: "FBA" },
      { ...fixture.competitors[0], own_sku: "SKU-FBA-2", competitor_asin: "B000000012", competitor_seller_id: "SELLER-1", seller_name: "Same Seller", fulfillment: "FBA" },
    ],
  }, { competitors: [] }, "daily");
  const riskyFbm = sellerRisk.snapshots.find((row) => row.own_sku === "SKU-FBM");
  if (riskyFbm.fba_transition_risk !== "HIGH" || riskyFbm.fba_transition_assessment_status !== "FORMAL") {
    throw new Error("Seller-level FBA capability did not produce a formal high-risk assessment");
  }
  const sameNameDifferentIds = analyze({
    captured_at: "2026-08-08",
    competitors: [
      { ...fixture.competitors[0], own_sku: "SKU-A", competitor_asin: "B000000020", competitor_seller_id: "SELLER-A", seller_name: "Duplicate Name", fulfillment: "FBM" },
      { ...fixture.competitors[0], own_sku: "SKU-B", competitor_asin: "B000000021", competitor_seller_id: "SELLER-B", seller_name: "Duplicate Name", fulfillment: "FBA" },
      { ...fixture.competitors[0], own_sku: "SKU-C", competitor_asin: "B000000022", competitor_seller_id: "SELLER-B", seller_name: "Duplicate Name", fulfillment: "FBA" },
    ],
  }, { competitors: [] }, "daily");
  const separateSeller = sameNameDifferentIds.snapshots.find((row) => row.own_sku === "SKU-A");
  if (separateSeller.fba_transition_risk !== "LOW") {
    throw new Error("Same-name sellers with different stable IDs were incorrectly merged");
  }
  const estimatedFeeOnly = analyze({
    captured_at: "2026-08-08",
    competitors: [{
      ...fixture.competitors[0], own_sku: "SKU-FEE", competitor_asin: "B000000030",
      competitor_seller_id: "SELLER-FEE", fulfillment: "FBM", estimated_fba_fee: 4.76,
    }],
  }, { competitors: [] }, "daily");
  if (estimatedFeeOnly.snapshots[0].fba_transition_risk !== "LOW") {
    throw new Error("Estimated FBA fee incorrectly raised transition risk");
  }
  const candidateOnly = analyze({
    captured_at: "2026-08-08",
    competitors: [{
      ...fixture.competitors[0], own_sku: undefined, candidate_id: "candidate-1", subject_type: "CANDIDATE",
      subject_id: "candidate-1", original_grade: "A", grade: "A", competitor_asin: "B000000040",
      competitor_seller_id: "SELLER-CANDIDATE", fulfillment: "FBM",
    }],
  }, { competitors: [] }, "daily");
  if (candidateOnly.snapshots[0].subject_id !== "candidate-1" || candidateOnly.snapshots[0].own_sku !== "") {
    throw new Error("Candidate-only subject incorrectly required a Seller SKU");
  }
  const afterSkuBinding = analyze({
    captured_at: "2026-08-09",
    competitors: [{
      ...candidateOnly.snapshots[0], subject_type: "SKU", subject_id: "SKU-NEW", own_sku: "SKU-NEW", fulfillment: "FBA",
    }],
  }, { captured_at: "2026-08-08", competitors: candidateOnly.snapshots }, "daily");
  if (!afterSkuBinding.events.some((row) => row.event_type === "FULFILLMENT_CHANGED")
    || afterSkuBinding.snapshots[0].lineage_key !== "CANDIDATE:candidate-1") {
    throw new Error("Candidate-to-SKU binding did not preserve fulfillment history");
  }
  const missingEvidence = analyze({
    captured_at: "2026-08-09",
    competitors: [{ ...fixture.competitors[0], own_sku: undefined, candidate_id: "candidate-2", original_grade: "A", grade: "A", competitor_asin: "", competitor_seller_id: "" }],
  }, { competitors: [] }, "daily");
  if (missingEvidence.snapshots[0].fba_transition_risk !== "REVIEW"
    || missingEvidence.snapshots[0].selection_evidence_status !== "NEEDS_EVIDENCE") {
    throw new Error("Missing exact ASIN or Seller ID did not enter evidence-pending state");
  }
  process.stdout.write("Self-test passed: candidate/SKU lineage and competitor risk rules are valid.\n");
}

if (require.main === module) {
  const args = parseArgs(process.argv);
  if (args["self-test"] === true) {
    selfTest();
    process.exit(0);
  }
  if (!args.current || !args.output) {
    console.error("Usage: monitor_competitors.cjs --current current.json [--previous previous.json] --output events.json [--run-mode daily|weekly|monthly]");
    process.exit(2);
  }
  const result = analyze(readJson(args.current, {}), readJson(args.previous, {}), args["run-mode"] || "daily");
  fs.mkdirSync(path.dirname(path.resolve(args.output)), { recursive: true });
  fs.writeFileSync(args.output, `${JSON.stringify(result, null, 2)}\n`);
  console.log(`Wrote ${result.events.length} event(s) to ${args.output}`);
}

module.exports = { analyze, confidence, effectivePrice, normalizeSnapshot };
