"use strict";

const DAY_MS = 86_400_000;

function rows(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.competitors || payload?.snapshots || payload?.competitor_snapshots || [];
}

function text(value) {
  return String(value ?? "").trim();
}

function upper(value, fallback = "") {
  return text(value || fallback).toUpperCase();
}

function number(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function bool(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (value === null || value === undefined || value === "") return fallback;
  return !["0", "false", "no", "n", "否"].includes(text(value).toLowerCase());
}

function isoDate(value) {
  const candidate = text(value).slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(candidate) ? candidate : null;
}

function daysBetween(later, earlier) {
  const end = Date.parse(`${later}T00:00:00Z`);
  const start = Date.parse(`${earlier}T00:00:00Z`);
  return Number.isFinite(end) && Number.isFinite(start) ? Math.round((end - start) / DAY_MS) : null;
}

function competitorSellerId(row) {
  return text(
    row.competitor_seller_id
    ?? row.merchant_id
    ?? row.merchant_token
    ?? row.offer_seller_id
    ?? row.seller_id,
  );
}

function sellerName(row) {
  return text(row.seller_name ?? row.competitor_seller_name ?? row.merchant_name);
}

function normalizedName(value) {
  return text(value).normalize("NFKC").toLowerCase().replace(/\s+/g, " ");
}

function sellerIdentity(row, knownIdsByName = new Map()) {
  const id = competitorSellerId(row);
  const name = sellerName(row);
  if (id) return { key: `ID:${id}`, id, name, status: "STABLE_ID" };
  const normalized = normalizedName(name);
  if (!normalized) return { key: "", id: "", name: "", status: "MISSING" };
  if ((knownIdsByName.get(normalized)?.size ?? 0) > 0) {
    return { key: "", id: "", name, status: "NAME_CONFLICT_WITH_STABLE_ID" };
  }
  return { key: `NAME_ONLY:${normalized}`, id: "", name, status: "NAME_ONLY" };
}

function familyKey(row) {
  const explicit = text(row.product_family_id ?? row.competitor_parent_asin ?? row.parent_asin);
  return explicit ? `FAMILY:${explicit.toUpperCase()}` : "";
}

function asinOf(row) {
  return upper(row.competitor_asin ?? row.asin);
}

function candidateIdOf(row) {
  return text(row.candidate_id ?? row.candidateId);
}

function ownSkuOf(row) {
  return text(row.own_sku ?? row.seller_sku ?? row.sellerSku);
}

function subjectIdentity(row) {
  const candidateId = candidateIdOf(row);
  const ownSku = ownSkuOf(row);
  const requestedType = upper(row.subject_type ?? row.subjectType);
  const subjectType = ["CANDIDATE", "SKU"].includes(requestedType)
    ? requestedType
    : ownSku ? "SKU" : "CANDIDATE";
  const subjectId = text(row.subject_id ?? row.subjectId)
    || (subjectType === "SKU" ? ownSku : candidateId);
  return {
    subject_type: subjectType,
    subject_id: subjectId,
    candidate_id: candidateId,
    own_sku: ownSku,
    lineage_key: candidateId ? `CANDIDATE:${candidateId}` : ownSku ? `SKU:${ownSku}` : "",
  };
}

function capturedAt(row, fallback) {
  return isoDate(row.captured_at ?? row.observed_at ?? row.snapshot_date) ?? fallback;
}

function historyEntry(row, fallbackDate, knownIdsByName) {
  const identity = sellerIdentity(row, knownIdsByName);
  const asin = asinOf(row);
  const fulfillment = upper(row.fulfillment, "UNKNOWN");
  const date = capturedAt(row, fallbackDate);
  if (!identity.key || !asin || !date || !["FBA", "FBM"].includes(fulfillment)) return null;
  return {
    seller_key: identity.key,
    competitor_seller_id: identity.id,
    seller_name: identity.name,
    seller_identity_status: identity.status,
    competitor_asin: asin,
    competitor_parent_asin: text(row.competitor_parent_asin ?? row.parent_asin).toUpperCase(),
    product_family_id: text(row.product_family_id),
    fulfillment,
    captured_at: date,
  };
}

function dedupeHistory(entries) {
  const byKey = new Map();
  for (const entry of entries.filter(Boolean)) {
    const key = [entry.seller_key, entry.competitor_asin, entry.fulfillment, entry.captured_at].join("|");
    byKey.set(key, entry);
  }
  return [...byKey.values()].sort((left, right) => (
    left.captured_at.localeCompare(right.captured_at)
    || left.seller_key.localeCompare(right.seller_key)
    || left.competitor_asin.localeCompare(right.competitor_asin)
  ));
}

function transitionRows(history) {
  const groups = new Map();
  for (const entry of history) {
    const key = `${entry.seller_key}|${entry.competitor_asin}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  }
  const transitions = [];
  for (const values of groups.values()) {
    values.sort((left, right) => left.captured_at.localeCompare(right.captured_at));
    let previous = null;
    for (const current of values) {
      if (previous && previous.fulfillment !== current.fulfillment) {
        transitions.push({
          seller_key: current.seller_key,
          competitor_seller_id: current.competitor_seller_id,
          seller_name: current.seller_name,
          competitor_asin: current.competitor_asin,
          old_fulfillment: previous.fulfillment,
          new_fulfillment: current.fulfillment,
          captured_at: current.captured_at,
        });
      }
      previous = current;
    }
  }
  return transitions;
}

function buildProfiles(history, currentRows, knownIdsByName, asOfDate) {
  const grouped = new Map();
  for (const entry of history) {
    if (!grouped.has(entry.seller_key)) grouped.set(entry.seller_key, []);
    grouped.get(entry.seller_key).push(entry);
  }
  const transitions = transitionRows(history);
  const currentBySeller = new Map();
  for (const row of currentRows) {
    const identity = sellerIdentity(row, knownIdsByName);
    if (!identity.key) continue;
    if (!currentBySeller.has(identity.key)) currentBySeller.set(identity.key, []);
    currentBySeller.get(identity.key).push(row);
  }
  const profiles = [];
  for (const [key, entries] of grouped) {
    const current = currentBySeller.get(key) ?? [];
    const fbaAsins = new Set(entries.filter((item) => item.fulfillment === "FBA").map((item) => item.competitor_asin));
    const fbmAsins = new Set(entries.filter((item) => item.fulfillment === "FBM").map((item) => item.competitor_asin));
    const currentFba = new Set(current.filter((item) => upper(item.fulfillment) === "FBA").map(asinOf));
    const currentFbm = new Set(current.filter((item) => upper(item.fulfillment) === "FBM").map(asinOf));
    const sellerTransitions = transitions.filter((item) => item.seller_key === key);
    const recentTransitions = sellerTransitions.filter((item) => {
      const age = daysBetween(asOfDate, item.captured_at);
      return age !== null && age >= 0 && age <= 90 && item.new_fulfillment === "FBA";
    });
    const totalObserved = new Set([...fbaAsins, ...fbmAsins]).size;
    profiles.push({
      seller_key: key,
      competitor_seller_id: entries.find((item) => item.competitor_seller_id)?.competitor_seller_id ?? "",
      seller_name: entries.find((item) => item.seller_name)?.seller_name ?? "",
      seller_identity_status: entries[0]?.seller_identity_status ?? "MISSING",
      first_seen_at: entries[0]?.captured_at ?? null,
      last_seen_at: entries.at(-1)?.captured_at ?? null,
      first_seen_fba_at: entries.find((item) => item.fulfillment === "FBA")?.captured_at ?? null,
      last_seen_fba_at: [...entries].reverse().find((item) => item.fulfillment === "FBA")?.captured_at ?? null,
      first_seen_fbm_at: entries.find((item) => item.fulfillment === "FBM")?.captured_at ?? null,
      last_seen_fbm_at: [...entries].reverse().find((item) => item.fulfillment === "FBM")?.captured_at ?? null,
      observed_asin_count: totalObserved,
      historical_fba_asin_count: fbaAsins.size,
      historical_fbm_asin_count: fbmAsins.size,
      current_fba_asin_count: currentFba.size,
      current_fbm_asin_count: currentFbm.size,
      fba_asin_ratio: totalObserved ? Math.round((fbaAsins.size / totalObserved) * 1000) / 1000 : 0,
      fulfillment_transition_count: sellerTransitions.length,
      fbm_to_fba_transition_count_90d: recentTransitions.length,
    });
  }
  return { profiles, transitions };
}

function priorRowFor(current, previousRows) {
  const asin = asinOf(current);
  const id = competitorSellerId(current);
  const subject = subjectIdentity(current);
  return previousRows.find((row) => (
    asinOf(row) === asin
    && (
      subjectIdentity(row).lineage_key === subject.lineage_key
      || (subject.own_sku && subjectIdentity(row).own_sku === subject.own_sku)
    )
    && (!id || competitorSellerId(row) === id)
  )) ?? null;
}

function accelerationSignals(current, previous) {
  if (!previous) return [];
  const signals = [];
  const oldDelivery = number(previous.delivery_days);
  const newDelivery = number(current.delivery_days);
  if (oldDelivery !== null && newDelivery !== null && oldDelivery - newDelivery >= 3) signals.push("DELIVERY_SHORTENED");
  const oldReviews = number(previous.reviews);
  const newReviews = number(current.reviews);
  if (oldReviews !== null && newReviews !== null && newReviews > oldReviews) signals.push("REVIEWS_INCREASED");
  if (!bool(previous.sponsored) && bool(current.sponsored)) signals.push("SPONSORED_STARTED");
  if (!bool(previous.in_stock) && bool(current.in_stock)) signals.push("STOCK_RECOVERED");
  return signals;
}

function assessRow(row, context) {
  const subject = subjectIdentity(row);
  const fulfillment = upper(row.fulfillment, "UNKNOWN");
  const identity = sellerIdentity(row, context.knownIdsByName);
  const profile = context.profileByKey.get(identity.key) ?? null;
  const asin = asinOf(row);
  const family = familyKey(row);
  const previous = priorRowFor(row, context.previousRows);
  const signals = accelerationSignals(row, previous);
  const historical = context.history.filter((item) => item.seller_key === identity.key);
  const exactAsinWasFba = historical.some((item) => item.competitor_asin === asin && item.fulfillment === "FBA");
  const sameFamilyFba = Boolean(family) && context.currentRows.some((candidate) => {
    const candidateIdentity = sellerIdentity(candidate, context.knownIdsByName);
    return candidate !== row
      && candidateIdentity.key === identity.key
      && familyKey(candidate) === family
      && upper(candidate.fulfillment) === "FBA";
  });
  const reasons = [];
  let risk = "LOW";
  let cadence = "WEEKLY";

  if (!subject.subject_id || !asin) {
    risk = "REVIEW";
    cadence = "MANUAL_REVIEW";
    reasons.push("缺少监控主体或精确竞品 ASIN，只能进入待补证状态");
  } else if (fulfillment === "UNKNOWN" || bool(row.data_conflict)) {
    risk = "REVIEW";
    cadence = "MANUAL_REVIEW";
    reasons.push("履约字段未知或证据冲突，不能推断 FBA 转仓风险");
  } else if (fulfillment === "FBA") {
    risk = "HIGH";
    cadence = "DAILY";
    reasons.push("当前精确 Offer 已为 FBA");
  } else if (exactAsinWasFba) {
    risk = "HIGH";
    cadence = "DAILY";
    reasons.push("当前 ASIN 历史上出现过 FBA");
  } else if (sameFamilyFba) {
    risk = "HIGH";
    cadence = "DAILY";
    reasons.push("同一卖家同父体或同产品系列已有 FBA");
  } else if ((profile?.fbm_to_fba_transition_count_90d ?? 0) >= 2) {
    risk = "HIGH";
    cadence = "DAILY";
    reasons.push("同一卖家近 90 天发生过多次 FBM→FBA");
  } else if ((profile?.current_fba_asin_count ?? 0) >= 2) {
    risk = "HIGH";
    cadence = "DAILY";
    reasons.push("当前卖家已批量经营 FBA 商品");
  } else if ((profile?.historical_fba_asin_count ?? 0) > 0) {
    risk = "MEDIUM";
    cadence = "TWICE_WEEKLY";
    reasons.push("同一卖家有其他 FBA 经营记录");
  } else if (signals.includes("DELIVERY_SHORTENED") && signals.length >= 2) {
    risk = "MEDIUM";
    cadence = "TWICE_WEEKLY";
    reasons.push("配送明显缩短且伴随评论、广告或库存恢复信号");
  } else {
    reasons.push("暂未发现历史 FBA、同系列 FBA 或组合加速信号");
  }

  const identityConfirmed = identity.status === "STABLE_ID";
  if (!identityConfirmed && risk !== "REVIEW") {
    reasons.push("缺少稳定 Amazon Seller ID，当前结论仅为候选提示");
  }
  const transitionedToFba = fulfillment === "FBA" && previous && upper(previous.fulfillment) === "FBM";
  return {
    ...row,
    ...subject,
    competitor_seller_id: identity.id,
    seller_name: identity.name || sellerName(row),
    seller_identity_status: identity.status,
    competitor_parent_asin: text(row.competitor_parent_asin ?? row.parent_asin).toUpperCase(),
    fba_transition_risk: risk,
    fba_transition_risk_label: ({ HIGH: "高", MEDIUM: "中", LOW: "低", REVIEW: "待复核" })[risk],
    fba_transition_assessment_status: identityConfirmed ? "FORMAL" : "PROVISIONAL",
    selection_evidence_status: subject.subject_id && asin && identityConfirmed && fulfillment !== "UNKNOWN" && !bool(row.data_conflict)
      ? "COMPLETE"
      : "NEEDS_EVIDENCE",
    fba_transition_risk_reasons: reasons,
    fba_monitor_cadence: cadence,
    requires_seller_id_confirmation: !identityConfirmed,
    recommended_order_action: risk === "HIGH"
      ? "建议缩量试单，保留原建议量并由人工确认保守试单量"
      : risk === "MEDIUM"
        ? "订货前复核卖家 FBA 能力与近期动作"
        : risk === "REVIEW"
          ? "补齐 Seller ID、精确履约与详情页证据后再判断"
          : "按常规订货门禁执行",
    application_stages: ["SELECTION", "PRE_ORDER_24_48H", "IN_TRANSIT", "ON_SALE"],
    fba_transition_stress_test_required: risk === "HIGH",
    fba_transition_stress_test_assumption: risk === "HIGH"
      ? "假设竞品立即转为 FBA 且保持当前到手价，复核本店利润和配送优势"
      : null,
    fulfillment_changed_to_fba: transitionedToFba,
    route_repricing_review: transitionedToFba,
    route_replenishment_recalculation: transitionedToFba || risk === "HIGH",
    route_clearance_review: false,
    clearance_route_rule: "只有本店库存命中超量、滞销或库龄门禁时才允许进入清货分析",
    seller_profile: profile,
    acceleration_signals: signals,
  };
}

function assessFbaTransitionRisk({ currentRows = [], previousPayloads = [], asOfDate = null } = {}) {
  const current = rows(currentRows);
  const previous = previousPayloads.flatMap((payload) => rows(payload));
  const resolvedDate = isoDate(asOfDate)
    ?? current.map((row) => capturedAt(row)).filter(Boolean).sort().at(-1)
    ?? new Date().toISOString().slice(0, 10);
  const allRows = [...previous, ...current];
  const knownIdsByName = new Map();
  for (const row of allRows) {
    const id = competitorSellerId(row);
    const name = normalizedName(sellerName(row));
    if (!id || !name) continue;
    if (!knownIdsByName.has(name)) knownIdsByName.set(name, new Set());
    knownIdsByName.get(name).add(id);
  }
  const carriedHistory = previousPayloads.flatMap((payload) => payload?.competitor_fulfillment_history ?? []);
  const normalizedCarried = carriedHistory.map((entry) => historyEntry(entry, resolvedDate, knownIdsByName));
  const observedHistory = allRows.map((row) => historyEntry(row, resolvedDate, knownIdsByName));
  const history = dedupeHistory([...normalizedCarried, ...observedHistory]);
  const { profiles, transitions } = buildProfiles(history, current, knownIdsByName, resolvedDate);
  const context = {
    history,
    currentRows: current,
    previousRows: previous,
    knownIdsByName,
    profileByKey: new Map(profiles.map((profile) => [profile.seller_key, profile])),
  };
  const snapshots = current.map((row) => assessRow(row, context));
  const collectionQueue = snapshots.map((row) => {
    const checks = ["DETAIL_EXACT_OFFER", "OTHER_OFFERS"];
    if (!row.competitor_seller_id) checks.push("CAPTURE_STABLE_SELLER_ID");
    if (!row.competitor_parent_asin && !row.product_family_id) checks.push("CAPTURE_PARENT_AND_SIBLING_VARIANTS");
    if (["HIGH", "MEDIUM"].includes(row.fba_transition_risk)) checks.push("CHECK_SELLER_RELATED_ASINS");
    return {
      task_key: [row.lineage_key, asinOf(row)].join("|"),
      subject_type: row.subject_type,
      subject_id: row.subject_id,
      candidate_id: row.candidate_id,
      lineage_key: row.lineage_key,
      own_sku: row.own_sku,
      competitor_asin: asinOf(row),
      competitor_seller_id: row.competitor_seller_id,
      seller_name: row.seller_name,
      priority: row.fba_transition_risk === "HIGH" || row.requires_seller_id_confirmation ? "HIGH" : row.fba_transition_risk,
      cadence: row.fba_monitor_cadence,
      checks: [...new Set(checks)],
      primary_zip: "75201",
      secondary_zips: row.fba_transition_risk === "HIGH" || row.fulfillment_changed_to_fba
        ? ["10001", "90001"]
        : [],
      browser_environment: "ZINIAO_VOCUER_US_ONLY",
      write_mode: "READ_ONLY",
      reason: row.fba_transition_risk_reasons.join("；"),
    };
  });
  return {
    as_of_date: resolvedDate,
    snapshots,
    seller_profiles: profiles,
    fulfillment_history: history,
    fulfillment_transitions: transitions,
    collection_queue: collectionQueue,
    summary: {
      high: snapshots.filter((row) => row.fba_transition_risk === "HIGH").length,
      medium: snapshots.filter((row) => row.fba_transition_risk === "MEDIUM").length,
      low: snapshots.filter((row) => row.fba_transition_risk === "LOW").length,
      review: snapshots.filter((row) => row.fba_transition_risk === "REVIEW").length,
      formal: snapshots.filter((row) => row.fba_transition_assessment_status === "FORMAL").length,
      provisional: snapshots.filter((row) => row.fba_transition_assessment_status === "PROVISIONAL").length,
      collection_high_priority: collectionQueue.filter((row) => row.priority === "HIGH").length,
    },
  };
}

module.exports = {
  assessFbaTransitionRisk,
  candidateIdOf,
  competitorSellerId,
  sellerIdentity,
  subjectIdentity,
};
