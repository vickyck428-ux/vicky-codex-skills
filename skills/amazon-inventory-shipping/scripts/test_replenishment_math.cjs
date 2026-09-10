const assert = require("node:assert/strict");
const {
  calculateReplenishment,
  calculateReplenishmentScenarios,
  splitTransport,
} = require("./replenishment_math.cjs");

const course = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 125,
  b1Override: 1.1,
  b2Override: 1.2,
  asOfDate: "2026-07-25",
  supplyInstock: 200,
  supplyReserved: 381,
  supplyInbound: 0,
  supplyTotal: 581,
  domesticReadyStock: 999,
  procurementDays: 7,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 7,
  safetyFactor: 1.2,
  clearanceStatus: "健康维持",
  unitContribution: 4,
  expressDays: 5,
  airDays: 14,
});
assert.ok(Math.abs(course.dailySales - 10) < 1e-9);
assert.ok(Math.abs(course.healthInventory - 580.8) < 1e-9);
assert.equal(course.recommendedQty, 84);
assert.equal(course.inventoryPosition, 581);
assert.equal(course.productionDays, 0);
assert.ok(Math.abs(course.coverageDays - 18.1818181818) < 1e-6);

const overstock = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 125,
  b1Override: 1.1,
  b2Override: 1.2,
  supplyInstock: 680,
  supplyTotal: 681,
  procurementDays: 7,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 7,
  safetyFactor: 1.2,
  clearanceStatus: "健康维持",
  unitContribution: 4,
});
assert.equal(Math.round(overstock.rawQty), -16);
assert.equal(overstock.recommendedQty, 0);

const bridge = splitTransport({
  totalQty: 464,
  dailySales: 10,
  b1: 1.1,
  coverageDays: 7,
  expressDays: 3,
  airDays: 14,
  seaDays: 24,
});
assert.deepEqual(bridge, { expressQty: 77, airQty: 110, seaQty: 277, stockoutDays: 0 });

const blocked = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 125,
  supplyInstock: 0,
  supplyTotal: 0,
  clearanceStatus: "主动清货",
});
assert.equal(blocked.recommendedQty, 0);
assert.equal(blocked.status, "主动清货");

const seaCanCatchUp = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 150,
  b1Override: 1.1,
  b2Override: 1.2,
  supplyInstock: 400,
  supplyTotal: 400,
  procurementDays: 7,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 30,
  safetyFactor: 1.2,
  clearanceStatus: "健康维持",
  unitContribution: 4,
  expressDays: 5,
  airDays: 14,
});
assert.equal(seaCanCatchUp.status, "待补货");
assert.equal(seaCanCatchUp.expressQty, 0);
assert.equal(seaCanCatchUp.airQty, 0);
assert.equal(seaCanCatchUp.seaQty, seaCanCatchUp.recommendedQty);

const missingCritical = calculateReplenishment({
  units7: null,
  units15: null,
  units30: null,
  supplyInstock: null,
  clearanceStatus: "健康维持",
});
assert.equal(missingCritical.status, "停补观察");
assert.equal(missingCritical.recommendedQty, 0);
assert.equal(missingCritical.confidence, "低");

const missingProfit = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 150,
  supplyInstock: 10,
  supplyTotal: 10,
  procurementDays: 7,
  seaDays: 35,
  clearanceStatus: "健康维持",
});
assert.equal(missingProfit.status, "待补货");
assert.equal(missingProfit.provisional, true);
assert.equal(missingProfit.confidence, "低");

const lateInboundExcluded = calculateReplenishment({
  units7: 70,
  units15: 150,
  units30: 300,
  previous15: 150,
  asOfDate: "2026-07-25",
  supplyInstock: 10,
  supplyReserved: 0,
  supplyInbound: 90,
  inboundReadyDate: "2026-08-20",
  supplyTotal: 100,
  procurementDays: 0,
  prepDays: 0,
  seaDays: 10,
  reviewCycleDays: 0,
  clearanceStatus: "健康维持",
  unitContribution: 4,
});
assert.equal(lateInboundExcluded.inventoryPosition, 10);

const scenarios = calculateReplenishmentScenarios({
  units7: 20,
  units15: 44,
  units30: 55,
  previous15: 11,
  asOfDate: "2026-07-26",
  supplyInstock: 29,
  supplyReserved: 4,
  supplyInbound: 15,
  supplyTotal: 48,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 7,
  safetyFactor: 1.2,
  clearanceStatus: "健康维持",
});
assert.equal(scenarios.fast7.procurementDaysUsed, 7);
assert.equal(scenarios.formal14.procurementDaysUsed, 14);
assert.equal(scenarios.fast7.recommendedQty, 147);
assert.equal(scenarios.formal14.recommendedQty, 172);

const configuredScenarios = calculateReplenishmentScenarios({
  units7: 20,
  units15: 44,
  units30: 55,
  previous15: 11,
  supplyInstock: 29,
  supplyTotal: 29,
  clearanceStatus: "健康维持",
  unitContribution: 4,
  procurementScenariosDays: [5, 12],
  productionDays: 3,
  prepDays: 2,
  seaDays: 35,
  reviewCycleDays: 7,
});
assert.equal(configuredScenarios.fast7.procurementDaysUsed, 5);
assert.equal(configuredScenarios.formal14.procurementDaysUsed, 12);
assert.equal(configuredScenarios.formal14.productionDays, 3);

const postRestockPassed = calculateReplenishment({
  units7: 20,
  units15: 44,
  units30: 55,
  previous15: 11,
  asOfDate: "2026-08-09",
  lastFbaReceiptDate: "2026-07-30",
  lastFbaReceiptUnits: 100,
  postRestockUnits: 5,
  receiptEvidenceStatus: "SYSTEM_CONFIRMED",
  supplyInstock: 29,
  supplyTotal: 29,
  clearanceStatus: "健康维持",
  unitContribution: 4,
});
const postRestockBaseline = calculateReplenishment({
  units7: 20, units15: 44, units30: 55, previous15: 11,
  asOfDate: "2026-08-09", supplyInstock: 29, supplyTotal: 29,
  clearanceStatus: "健康维持", unitContribution: 4,
});
assert.equal(postRestockPassed.recommendedQty, postRestockBaseline.recommendedQty);
assert.equal(postRestockPassed.postRestockSales.observation_days, 10);
assert.equal(postRestockPassed.postRestockSales.actual_shipped_units, 5);
assert.equal(postRestockPassed.postRestockSales.daily_sales, 0.5);
assert.equal(postRestockPassed.postRestockActionable, true);
assert.equal(postRestockPassed.blockingCodes.length, 0);

const postRestockPending = calculateReplenishment({
  units7: 20, units15: 44, units30: 55, previous15: 11,
  asOfDate: "2026-08-09", lastFbaReceiptDate: "2026-08-05",
  lastFbaReceiptUnits: 100, postRestockUnits: 1, receiptEvidenceStatus: "USER_CONFIRMED",
  supplyInstock: 0, supplyTotal: 0, clearanceStatus: "健康维持", unitContribution: 4,
});
assert.ok(postRestockPending.recommendedQty > 0);
assert.deepEqual(postRestockPending.blockingCodes, ["POST_RESTOCK_OBSERVATION_PENDING"]);

const zeroAfterRestock = calculateReplenishment({
  units7: 20, units15: 44, units30: 55, previous15: 11,
  asOfDate: "2026-08-09", lastFbaReceiptDate: "2026-07-30",
  lastFbaReceiptUnits: 100, postRestockUnits: 0, receiptEvidenceStatus: "SYSTEM_CONFIRMED",
  supplyInstock: 0, supplyTotal: 0, clearanceStatus: "健康维持", unitContribution: 4,
});
assert.equal(zeroAfterRestock.status, "停补观察");
assert.equal(zeroAfterRestock.recommendedQty, 0);
assert.deepEqual(zeroAfterRestock.blockingCodes, ["ZERO_SALES_AFTER_RESTOCK_7D"]);

const unverifiedReceipt = calculateReplenishment({
  units7: 20, units15: 44, units30: 55, previous15: 11,
  asOfDate: "2026-08-09", supplyInstock: 0, supplyTotal: 0,
  clearanceStatus: "健康维持", unitContribution: 4,
});
assert.ok(unverifiedReceipt.recommendedQty > 0);
assert.deepEqual(unverifiedReceipt.blockingCodes, ["LAST_FBA_RECEIPT_UNVERIFIED"]);

for (const invalidReceipt of [
  { lastFbaReceiptDate: "2026-08-10", lastFbaReceiptUnits: 10, postRestockUnits: 1 },
  { lastFbaReceiptDate: "2026-07-30", lastFbaReceiptUnits: 0, postRestockUnits: 1 },
  { lastFbaReceiptDate: "2026-07-30", lastFbaReceiptUnits: 10, postRestockUnits: -1 },
]) {
  const result = calculateReplenishment({
    units7: 20, units15: 44, units30: 55, previous15: 11, asOfDate: "2026-08-09",
    receiptEvidenceStatus: "SYSTEM_CONFIRMED", supplyInstock: 0, supplyTotal: 0,
    clearanceStatus: "健康维持", unitContribution: 4, ...invalidReceipt,
  });
  assert.deepEqual(result.blockingCodes, ["LAST_FBA_RECEIPT_UNVERIFIED"]);
}

console.log("replenishment math tests passed");
