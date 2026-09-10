const assert = require("node:assert/strict");
const { calculateClearance } = require("./clearance_math.cjs");

const complete = {
  units7: 7,
  units15: 15,
  units30: 30,
  units60: 60,
  previous15: 15,
  oldestAgeDays: 30,
  nextSnapshotAgedUnits: 0,
  daysToSnapshot: 20,
};

const urgent = calculateClearance({
  ...complete,
  units7: 0,
  units15: 0,
  units30: 0,
  units60: 0,
  previous15: 0,
  supplyInstock: 40,
  oldestAgeDays: 190,
  nextSnapshotAgedUnits: 40,
  unitContribution: null,
});
assert.equal(urgent.status, "紧急清退");
assert.equal(urgent.feeRiskQty, 40);
assert.equal(urgent.clearanceTargetQty, 40);
assert.equal(urgent.quantityStatus, "暂定-缺经济数据");
assert.equal(urgent.riskConfidence, "中");
assert.equal(urgent.economicConfidence, "低");

const active = calculateClearance({
  ...complete,
  supplyInstock: 100,
});
assert.equal(active.status, "主动清货");
assert.ok(active.coverageDays > 90);
assert.ok(active.potentialExcessQty > 0);
assert.ok(active.clearanceTargetQty > 0);

const observe = calculateClearance({
  ...complete,
  supplyInstock: 80,
  unitContribution: 2,
});
assert.equal(observe.status, "停补观察");
assert.ok(observe.potentialExcessQty > 0);
assert.equal(observe.clearanceTargetQty, 0);
assert.equal(observe.quantityStatus, "已计算");

const replenish = calculateClearance({
  ...complete,
  units7: 18,
  units15: 35,
  units30: 62,
  units60: 120,
  previous15: 27,
  supplyInstock: 12,
  oldestAgeDays: 45,
  unitContribution: 4,
});
assert.equal(replenish.status, "待补货");
assert.equal(replenish.clearanceTargetQty, 0);

const healthy = calculateClearance({
  ...complete,
  supplyInstock: 59.8,
  unitContribution: 2,
});
assert.equal(healthy.status, "健康维持");
assert.equal(healthy.clearanceTargetQty, 0);

const declining = calculateClearance({
  ...complete,
  units7: 3,
  units15: 8,
  units30: 20,
  units60: 45,
  previous15: 20,
  supplyInstock: 25,
  unitContribution: 2,
});
assert.equal(declining.status, "停补观察");

const agedInput = {
  ...complete,
  units7: 70,
  units15: 150,
  units30: 300,
  units60: 600,
  previous15: 150,
  supplyInstock: 20,
  oldestAgeDays: 170,
  nextSnapshotAgedUnits: 20,
  daysToSnapshot: 3,
  unitContribution: 2,
};
const agedCanSellThrough = calculateClearance(agedInput);
assert.equal(agedCanSellThrough.feeRiskQty, 0);
assert.notEqual(agedCanSellThrough.status, "紧急清退");

const agedCannotSellThrough = calculateClearance({
  ...agedInput,
  daysToSnapshot: 1,
});
assert.equal(agedCannotSellThrough.feeRiskQty, 10);
assert.equal(agedCannotSellThrough.status, "紧急清退");

const zeroSales = calculateClearance({
  ...complete,
  units7: 0,
  units15: 0,
  units30: 0,
  units60: 0,
  previous15: 0,
  supplyInstock: 10,
  oldestAgeDays: 120,
});
assert.equal(zeroSales.status, "主动清货");

const missingInventory = calculateClearance({
  ...complete,
  supplyInstock: null,
  unitContribution: 2,
});
assert.equal(missingInventory.status, "停补观察");
assert.equal(missingInventory.clearanceTargetQty, null);
assert.equal(missingInventory.quantityStatus, "需要人工确认-缺库存");

const missingFeeDate = calculateClearance({
  ...complete,
  supplyInstock: 100,
  daysToSnapshot: null,
  unitContribution: 2,
});
assert.equal(missingFeeDate.status, "停补观察");
assert.equal(missingFeeDate.clearanceTargetQty, 0);
assert.equal(missingFeeDate.riskConfidence, "低");

const missingAgeReport = calculateClearance({
  ...complete,
  supplyInstock: 100,
  inventoryReportPresent: "是",
  ageReportPresent: "否",
  unitContribution: 2,
});
assert.equal(missingAgeReport.status, "停补观察");
assert.equal(missingAgeReport.clearanceTargetQty, 0);
assert.equal(missingAgeReport.riskConfidence, "低");

const knownRiskWithoutCost = calculateClearance({
  ...complete,
  supplyInstock: 60,
  unitContribution: null,
});
assert.equal(knownRiskWithoutCost.riskConfidence, "高");
assert.equal(knownRiskWithoutCost.economicConfidence, "低");
assert.equal(knownRiskWithoutCost.quantityStatus, "暂定-缺经济数据");

const urgentPriority = calculateClearance({
  ...complete,
  units15: 3,
  previous15: 20,
  supplyInstock: 10,
  strandedUnits: 1,
  unitContribution: 2,
});
assert.equal(urgentPriority.status, "紧急清退");

console.log("clearance math tests passed");
