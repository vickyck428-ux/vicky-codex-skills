const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { prepareRawData } = require("./prepare_clearance_input.cjs");

async function main() {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "clearance-merge-"));
  const apiPath = path.join(tempDir, "api.json");
  const inventoryPath = path.join(tempDir, "inventory.csv");
  const agePath = path.join(tempDir, "age.csv");
  const costPath = path.join(tempDir, "cost.csv");
  await fs.writeFile(
    apiPath,
    JSON.stringify({
      scope: { sellerId: "56321", marketplace: "US" },
      asOfDate: "2026-07-26",
      windows: { u90: ["2026-04-28", "2026-07-26"] },
      api: {
        base: [{ sellerSku: "SKU-BASE", asin: "BASE", productTitle: "Base Item" }],
        u7: [{ sellerSku: "SKU-REPORT", units: 7 }],
        u15: [{ sellerSku: "SKU-REPORT", units: 15 }],
        u30: [{ sellerSku: "SKU-REPORT", units: 30, revenue: 300, adCost: 20 }],
        u60: [{ sellerSku: "SKU-REPORT", units: 60 }],
        u90: [
          {
            sellerSku: "SKU-REPORT",
            asin: "REPORT",
            productTitle: "Women Tote Bag",
            units: 90,
            supplyInstock: 1000,
            supplyInbound: 999,
            supplyTotal: 1000,
          },
          {
            sellerSku: "SKU-MISSING",
            asin: "MISSING",
            productTitle: "Missing Inventory Row",
            units: 1,
            supplyInstock: 1000,
            supplyTotal: 1000,
          },
        ],
        prev15: [{ sellerSku: "SKU-REPORT", units: 15 }],
      },
    }),
  );
  await fs.writeFile(
    inventoryPath,
    [
      "snapshot-date,sku,asin,product-name,available,Total Reserved Quantity,inbound-quantity,Inventory Supply at FBA",
      "2026-07-26,SKU-REPORT,REPORT,Women Tote Bag,5,2,1,8",
      "2026-07-26,SKU-INV,INV,Inventory Only,3,0,0,3",
    ].join("\n"),
  );
  await fs.writeFile(
    agePath,
    [
      "snapshot-date,sku,asin,product-name,inv-age-181-to-270-days,quantity-to-be-charged-ais-181-210-days,estimated-ais-181-210-days,unfulfillable-quantity",
      "2026-07-24,SKU-REPORT,REPORT,Women Tote Bag,5,2,1.5,0",
      "2026-07-24,SKU-AGE,AGE,Age Only,1,1,0.5,0",
    ].join("\n"),
  );
  await fs.writeFile(
    costPath,
    [
      "Cost master title",
      "seller_sku,unit_contribution,purchase_cost_cny",
      "SKU-REPORT,2,5",
    ].join("\n"),
  );

  const result = await prepareRawData({
    apiJson: apiPath,
    inventoryReport: inventoryPath,
    ageReport: agePath,
    cost: costPath,
    sellerId: "56321",
    marketplace: "US",
    asOfDate: "2026-07-26",
    feeSnapshotDate: "2026-08-15",
  });
  const index = Object.fromEntries(result.headers.map((header, position) => [header, position]));
  const rows = new Map(
    result.rows.map((row) => [String(row[index.seller_sku]), row]),
  );
  assert.deepEqual(
    [...rows.keys()].sort(),
    ["SKU-AGE", "SKU-BASE", "SKU-INV", "SKU-MISSING", "SKU-REPORT"],
  );
  assert.equal(rows.get("SKU-BASE")[index.units_7d], 0);
  assert.equal(rows.get("SKU-AGE")[index.units_90d], 0);
  assert.equal(rows.get("SKU-REPORT")[index.supply_instock], 5);
  assert.equal(rows.get("SKU-REPORT")[index.supply_inbound], 1);
  assert.equal(rows.get("SKU-REPORT")[index.supply_total], 8);
  assert.equal(rows.get("SKU-REPORT")[index.api_supply_instock], 1000);
  assert.equal(rows.get("SKU-REPORT")[index.api_inventory_suspect], "是");
  assert.equal(rows.get("SKU-REPORT")[index.api_inventory_mismatch], "是");
  assert.equal(rows.get("SKU-REPORT")[index.unit_contribution], 2);
  assert.equal(rows.get("SKU-REPORT")[index.cost_data_present], "是");
  assert.equal(rows.get("SKU-MISSING")[index.supply_instock], null);
  assert.equal(rows.get("SKU-MISSING")[index.inventory_report_present], "否");
  assert.match(
    rows.get("SKU-MISSING")[index.inventory_reconciliation_issue],
    /未采用/,
  );
  assert.equal(rows.get("SKU-AGE")[index.age_report_present], "是");
  assert.equal(rows.get("SKU-INV")[index.age_report_present], "否");
  assert.equal(result.metadata.inventorySkuCount, 2);
  assert.equal(result.metadata.ageSkuCount, 2);
  assert.equal(result.metadata.costSkuCount, 1);
  console.log("clearance raw merge tests passed");
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
