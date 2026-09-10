const assert = require("node:assert/strict");
const { analyze, analyzeRow } = require("./generate_fbm_backup_preview.cjs");

const urgent = analyzeRow({
  asin: "B0TEST0001",
  fba_sku: "TEST-SKU",
  fba_available: 0,
  weighted_daily_sales: 2,
  b1: 1,
  timely_fba_inbound_sufficient: false,
  clearance_status: "待补货",
  purchase_cost_cny: 20,
  fba_price: 30,
  configured_fbm_quantity: 10000,
});
assert.equal(urgent.reminder, "URGENT_BACKUP_REMINDER");
assert.equal(urgent.fbm_shipping_policy_cny, 98);
assert.equal("target_customer_total_price" in urgent, false);
assert.equal("suggested_listing_quantity" in urgent, false);
assert.equal("manual_steps" in urgent, false);

const lowCoverage = analyzeRow({
  asin: "B0TEST0002",
  fba_sku: "TEST-SKU-2",
  fba_available: 8,
  weighted_daily_sales: 2,
  b1: 1,
  timely_fba_inbound_sufficient: false,
  clearance_status: "待补货",
});
assert.equal(lowCoverage.reminder, "BACKUP_REMINDER");

const clearance = analyzeRow({
  asin: "B0TEST0003",
  fba_sku: "TEST-SKU-3",
  fba_available: 0,
  weighted_daily_sales: 2,
  b1: 1,
  timely_fba_inbound_sufficient: false,
  clearance_status: "主动清货",
});
assert.equal(clearance.reminder, "NO_REMINDER");

const missingDemand = analyzeRow({
  asin: "B0TEST0004",
  fba_sku: "TEST-SKU-4",
  fba_available: 1,
  weighted_daily_sales: 0,
  timely_fba_inbound_sufficient: false,
});
assert.equal(missingDemand.reminder, "DATA_ISSUE");

const result = analyze({ sku_pairs: [urgent, lowCoverage] });
assert.equal(result.mode, "REMINDER_ONLY");
assert.equal(result.fbm_shipping_policy_cny, 98);
assert.equal(JSON.stringify(result).includes("ACTIVATE"), false);
assert.equal(JSON.stringify(result).includes("cost_floor"), false);

console.log("fbm backup reminder tests passed");
