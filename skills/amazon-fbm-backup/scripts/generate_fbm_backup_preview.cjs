#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

function parseArgs(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (!argv[index].startsWith("--")) continue;
    const key = argv[index].slice(2);
    const next = argv[index + 1];
    out[key] = next && !next.startsWith("--") ? next : true;
    if (out[key] !== true) index += 1;
  }
  return out;
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

function daysOfSupply(row) {
  const direct = num(row.fba_days_of_supply);
  if (direct !== null) return direct;
  const daily = num(row.weighted_daily_sales);
  const b1 = num(row.b1) || 1;
  const stock = num(row.fba_available);
  if (stock === null || daily === null || daily <= 0 || b1 <= 0) return null;
  return stock / (daily * b1);
}

function analyzeRow(row) {
  const fbaSku = String(row.fba_sku || row.seller_sku || "").trim();
  const asin = String(row.asin || "").trim();
  const fbaAvailable = Math.max(0, num(row.fba_available) || 0);
  const supplyDays = daysOfSupply(row);
  const timelyInboundInsufficient = !bool(row.timely_fba_inbound_sufficient, false);
  const clearanceStatus = String(row.clearance_status || "").trim();
  const blockers = [];

  if (!asin || !fbaSku) blockers.push("缺少 ASIN 或 Seller SKU");
  if (supplyDays === null) blockers.push("FBA 支撑天数无法计算");

  let reminder = "NO_REMINDER";
  let urgency = "普通";
  let reason = "当前未达到 FBA 断货备份提醒阈值";

  if (["紧急清退", "主动清货", "停补观察"].includes(clearanceStatus)) {
    reminder = "NO_REMINDER";
    reason = `清货/停补状态为${clearanceStatus}，不生成 FBM 备份提醒`;
  } else if (blockers.length) {
    reminder = "DATA_ISSUE";
    reason = blockers.join("；");
  } else if (fbaAvailable === 0 && timelyInboundInsufficient) {
    reminder = "URGENT_BACKUP_REMINDER";
    urgency = "紧急";
    reason = "FBA 可售为 0，且及时到达的 FBA 在途不足";
  } else if (supplyDays <= 5 && timelyInboundInsufficient) {
    reminder = "BACKUP_REMINDER";
    urgency = "高";
    reason = "FBA 支撑不超过 5 天，且及时到达的 FBA 在途不足";
  }

  return {
    asin,
    seller_sku: fbaSku,
    reminder,
    urgency,
    fba_available: fbaAvailable,
    fba_days_of_supply: supplyDays === null ? null : Number(supplyDays.toFixed(2)),
    timely_fba_inbound_sufficient: !timelyInboundInsufficient,
    fbm_shipping_policy_cny: 98,
    reason,
    blockers,
    prohibited_outputs: [
      "不得输出 Offer 激活/关闭步骤",
      "不得输出改价或改数量步骤",
      "不得计算 FBM 利润、亏损、成本底线或目标价",
    ],
    coupon_policy: "OWN_COUPON_PERMANENTLY_DISABLED",
    captured_at: row.captured_at || new Date().toISOString(),
  };
}

function analyze(payload) {
  const inputRows = Array.isArray(payload) ? payload : payload.sku_pairs || [];
  return {
    generated_at: new Date().toISOString(),
    mode: "REMINDER_ONLY",
    fbm_shipping_policy_cny: 98,
    coupon_policy: "OWN_COUPON_PERMANENTLY_DISABLED",
    previews: inputRows.map(analyzeRow),
  };
}

if (require.main === module) {
  const args = parseArgs(process.argv);
  if (!args.input || !args.output) {
    console.error("Usage: generate_fbm_backup_preview.cjs --input input.json --output preview.json");
    process.exit(2);
  }
  const payload = JSON.parse(fs.readFileSync(args.input, "utf8"));
  const result = analyze(payload);
  fs.mkdirSync(path.dirname(path.resolve(args.output)), { recursive: true });
  fs.writeFileSync(args.output, `${JSON.stringify(result, null, 2)}\n`);
  console.log(`Wrote ${result.previews.length} reminder(s) to ${args.output}`);
}

module.exports = {
  analyze,
  analyzeRow,
  daysOfSupply,
};
