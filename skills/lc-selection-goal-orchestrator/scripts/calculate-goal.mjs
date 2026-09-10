#!/usr/bin/env node
import fs from "node:fs";

const data = JSON.parse(fs.readFileSync(process.argv[2] ?? 0, "utf8"));
const annualNetTarget = Number(data.annualNetTarget ?? 0);
const fixedCosts = Number(data.fixedCosts ?? 0);
const unitProfit = Number(data.unitProfit ?? 0);
const stableDailyOrders = Number(data.stableDailyOrders ?? 0);
const currentStable = Number(data.currentStable ?? 0);
const expectedAttrition = Number(data.expectedAttrition ?? 0);
const matureConversionRate = Number(data.matureConversionRate ?? 0);
const remainingWorkdays = Number(data.remainingWorkdays ?? 0);

const dailyContributionTarget = (annualNetTarget + fixedCosts) / 365;
const requiredDailyOrders = unitProfit > 0 ? dailyContributionTarget / unitProfit : null;
const requiredStable = requiredDailyOrders != null && stableDailyOrders > 0 ? Math.ceil(requiredDailyOrders / stableDailyOrders) : null;
const stableGap = requiredStable == null ? null : Math.max(0, requiredStable - currentStable + expectedAttrition);
const dailyTests = stableGap != null && matureConversionRate > 0 && remainingWorkdays > 0
  ? Math.ceil(stableGap / matureConversionRate / remainingWorkdays)
  : null;

process.stdout.write(`${JSON.stringify({ dailyContributionTarget, requiredDailyOrders, requiredStable, stableGap, dailyTests }, null, 2)}\n`);
