#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const bundleModules = process.env.CODEX_BUNDLED_NODE_MODULES;
if (!bundleModules) throw new Error("CODEX_BUNDLED_NODE_MODULES 未设置；先调用 load_workspace_dependencies");
const require = createRequire(path.join(bundleModules, "package.json"));
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

function argsOf(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) continue;
    result[key.slice(2)] = argv[index + 1] && !argv[index + 1].startsWith("--") ? argv[++index] : true;
  }
  return result;
}

const args = argsOf(process.argv.slice(2));
if (!args.input || !args["output-dir"]) {
  throw new Error("usage: build_wfs_manifest.mjs --input <handoffs.json> --output-dir <dir> [--batch <key>] [--store1-template <xlsx>] [--store2-template <xlsx>] [--platform-mapping <json>]");
}

const inputPath = path.resolve(String(args.input));
const outputDir = path.resolve(String(args["output-dir"]));
const batchKey = String(args.batch || `WFS-US-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}`);
const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));
const rows = Array.isArray(raw) ? raw : Array.isArray(raw.handoffs) ? raw.handoffs : Array.isArray(raw.wfsShippingHandoffs) ? raw.wfsShippingHandoffs : [];
await fs.mkdir(outputDir, { recursive: true });

const COLORS = {
  navy: "#17365D", blue: "#2F75B5", lightBlue: "#D9EAF7", green: "#D9EAD3",
  yellow: "#FFF2CC", red: "#F4CCCC", gray: "#E7E6E6", white: "#FFFFFF", ink: "#24364B",
};

const value = (row, ...keys) => {
  for (const key of keys) if (row[key] !== undefined && row[key] !== null && row[key] !== "") return row[key];
  return "";
};
const text = (row, ...keys) => String(value(row, ...keys) ?? "");
const num = (row, ...keys) => {
  const parsed = Number(value(row, ...keys));
  return Number.isFinite(parsed) ? parsed : 0;
};
const jsonList = (row, ...keys) => {
  const item = value(row, ...keys);
  if (Array.isArray(item)) return item;
  if (typeof item === "string") {
    try { const parsed = JSON.parse(item); return Array.isArray(parsed) ? parsed : item ? [item] : []; } catch { return item ? [item] : []; }
  }
  return [];
};
const normalize = (row) => ({
  handoffKey: text(row, "handoff_key", "handoffKey"), sourceType: text(row, "source_type", "sourceType"),
  sourceRecordKey: text(row, "source_record_key", "sourceRecordKey"), candidateId: text(row, "candidate_id", "candidateId"),
  productGroupKey: text(row, "product_group_key", "productGroupKey"), storeName: text(row, "store_name", "storeName"),
  market: text(row, "market") || "US", sku: text(row, "sku"), itemId: text(row, "item_id", "itemId"),
  gtin: text(row, "gtin"), title: text(row, "title"), variant: text(row, "variant"), imageRef: text(row, "image_ref", "imageRef"),
  supplierDetailId: text(row, "supplier_detail_id", "supplierDetailId"), supplierOrderNo: text(row, "supplier_order_no", "supplierOrderNo"),
  sourceOrderId: text(row, "source_order_id", "sourceOrderId"), sourceOrderDate: text(row, "source_order_date", "sourceOrderDate"),
  unitProfit: num(row, "unit_profit", "unitProfit"), evidenceObservedAt: num(row, "evidence_observed_at", "evidenceObservedAt"),
  approvalStatus: text(row, "approval_status", "approvalStatus"), approvalComment: text(row, "approval_comment", "approvalComment"),
  approvedBy: text(row, "approved_by", "approvedBy"), plannedQty: 1,
  workflowStatus: text(row, "workflow_status", "workflowStatus"), purchaseStatus: text(row, "purchase_status", "purchaseStatus"),
  receivedQty: num(row, "received_qty", "receivedQty"), estimatedWeightKg: num(row, "estimated_weight_kg", "estimatedWeightKg") || 0.4,
  actualWeightKg: num(row, "actual_weight_kg", "actualWeightKg"), lengthCm: num(row, "length_cm", "lengthCm"),
  widthCm: num(row, "width_cm", "widthCm"), heightCm: num(row, "height_cm", "heightCm"), cartonNo: text(row, "carton_no", "cartonNo"),
  transportBatchKey: text(row, "transport_batch_key", "transportBatchKey"), platformShipmentId: text(row, "platform_shipment_id", "platformShipmentId"),
  blockedReasons: jsonList(row, "blocked_reasons", "blockedReasons"), screenshotRefs: jsonList(row, "screenshot_refs", "screenshotRefs"),
  feishuRecordId: text(row, "feishu_record_id", "feishuRecordId"),
});
const normalized = rows.map(normalize).filter((row) => !row.transportBatchKey || row.transportBatchKey === batchKey);

const cartonStores = new Map();
for (const row of normalized) if (row.cartonNo) {
  if (!cartonStores.has(row.cartonNo)) cartonStores.set(row.cartonNo, new Set());
  cartonStores.get(row.cartonNo).add(row.storeName);
}
const sharedCartons = new Set([...cartonStores.entries()].filter(([, stores]) => stores.size > 1).map(([carton]) => carton));

function issues(row) {
  const result = [...row.blockedReasons];
  if (row.approvalStatus !== "APPROVED") result.push("未批准T1 1件");
  if (!row.sku) result.push("缺Walmart SKU");
  if (!row.gtin) result.push("缺UPC/GTIN");
  if (!row.variant) result.push("缺具体颜色/变体");
  if (row.unitProfit < 70) result.push("利润低于70元或未计算");
  if (row.receivedQty < 1) result.push("尚未到仓");
  if (!row.actualWeightKg || !row.lengthCm || !row.widthCm || !row.heightCm) result.push("缺实测重量/尺寸");
  if (!row.cartonNo) result.push("缺箱号");
  if (!row.platformShipmentId) result.push("缺店铺Shipment ID");
  if (row.cartonNo && sharedCartons.has(row.cartonNo)) result.push("箱号跨店复用");
  return [...new Set(result.filter(Boolean))];
}
const formal = normalized.filter((row) => issues(row).length === 0);
const byStore = (store) => normalized.filter((row) => row.storeName === store);
const formalByStore = (store) => formal.filter((row) => row.storeName === store);

function col(index) {
  let n = index + 1;
  let out = "";
  while (n > 0) { n -= 1; out = String.fromCharCode(65 + (n % 26)) + out; n = Math.floor(n / 26); }
  return out;
}
function title(sheet, lastCol, heading, noteText) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastCol}1`).merge();
  sheet.getRange("A1").values = [[heading]];
  sheet.getRange(`A1:${lastCol}1`).format = { fill: COLORS.navy, font: { bold: true, color: COLORS.white, size: 17 }, verticalAlignment: "center" };
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight = 36;
  sheet.getRange(`A2:${lastCol}2`).merge();
  sheet.getRange("A2").values = [[noteText]];
  sheet.getRange(`A2:${lastCol}2`).format = { fill: COLORS.lightBlue, font: { color: COLORS.ink, italic: true }, wrapText: true };
}
function header(range) {
  range.format = { fill: COLORS.blue, font: { bold: true, color: COLORS.white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "inside", style: "thin", color: "#D4DEE8" } };
  range.format.rowHeight = 30;
}
function writeSheet(workbook, name, heading, noteText, headers, data, widths = {}) {
  const sheet = workbook.worksheets.add(name);
  const last = col(headers.length - 1);
  title(sheet, last, heading, noteText);
  sheet.getRange(`A4:${last}4`).values = [headers];
  header(sheet.getRange(`A4:${last}4`));
  const safeData = data.length ? data : [headers.map((_, index) => index === 0 ? "暂无记录" : "")];
  sheet.getRange(`A5:${last}${safeData.length + 4}`).values = safeData;
  sheet.getRange(`A5:${last}${safeData.length + 4}`).format = { wrapText: true, verticalAlignment: "top", borders: { preset: "inside", style: "thin", color: "#E4EAF0" } };
  sheet.freezePanes.freezeRows(4);
  sheet.freezePanes.freezeColumns(Math.min(2, headers.length));
  for (const [letter, width] of Object.entries(widths)) sheet.getRange(`${letter}:${letter}`).format.columnWidth = width;
  return sheet;
}

const workbook = Workbook.create();
const summary = workbook.worksheets.add("批次总览");
title(summary, "H", `美国WFS合运总表｜${batchKey}`, "内部合运总表。100kg只是运输池目标；平台货件、箱号、标签与Shipment ID按店铺隔离。0.4kg只用于到仓前预测。");
summary.getRange("A4:H4").values = [["店铺", "记录数", "批准T1件数", "已到仓件数", "预计重量kg", "实测重量kg", "可进入平台映射", "异常数"]];
header(summary.getRange("A4:H4"));
const stores = ["美国站1", "美国站2"];
const summaryRows = stores.map((store) => {
  const storeRows = byStore(store);
  return [store, storeRows.length, storeRows.filter((row) => row.approvalStatus === "APPROVED").length, storeRows.reduce((sum, row) => sum + row.receivedQty, 0), storeRows.reduce((sum, row) => sum + row.estimatedWeightKg * row.plannedQty, 0), storeRows.reduce((sum, row) => sum + row.actualWeightKg * Math.max(row.receivedQty, 0), 0), formalByStore(store).length, storeRows.filter((row) => issues(row).length).length];
});
summaryRows.push(["两店合计", ...Array(7).fill(0)]);
summary.getRange("A5:H7").values = summaryRows;
summary.getRange("B7:H7").formulas = [["=SUM(B5:B6)", "=SUM(C5:C6)", "=SUM(D5:D6)", "=SUM(E5:E6)", "=SUM(F5:F6)", "=SUM(G5:G6)", "=SUM(H5:H6)"]];
summary.getRange("A7:H7").format = { fill: COLORS.green, font: { bold: true, color: COLORS.ink } };
summary.getRange("A9:D9").values = [["运输目标kg", "预计重量kg", "距离100kg", "预计完成度"]];
header(summary.getRange("A9:D9"));
summary.getRange("A10:D10").values = [[100, 0, 0, 0]];
summary.getRange("B10:D10").formulas = [["=E7", "=MAX(0,A10-B10)", "=MIN(1,B10/A10)"]];
summary.getRange("D10").format.numberFormat = "0.0%";
summary.getRange("A12:H12").merge();
summary.getRange("A12").values = [["正式文件门禁：审批通过 + 到仓1件 + 实测重量/尺寸 + 店铺独立箱号 + 店铺独立Shipment ID。系统不会自动采购或创建平台货件。"]];
summary.getRange("A12:H12").format = { fill: COLORS.yellow, font: { bold: true, color: "#7F6000" }, wrapText: true };
summary.freezePanes.freezeRows(4);
for (const [letter, width] of Object.entries({ A: 20, B: 14, C: 16, D: 16, E: 16, F: 16, G: 18, H: 14 })) summary.getRange(`${letter}:${letter}`).format.columnWidth = width;

const detailHeaders = ["来源", "candidate_id", "产品组ID", "SKU", "Item ID", "UPC/GTIN", "商品", "颜色/变体", "T1数量", "审批", "流程", "利润RMB", "预计kg", "实测kg", "长cm", "宽cm", "高cm", "箱号", "国家批次", "Shipment ID"];
const detail = (row) => [row.sourceType, row.candidateId, row.productGroupKey, row.sku, row.itemId, row.gtin, row.title, row.variant, 1, row.approvalStatus, row.workflowStatus, row.unitProfit, row.estimatedWeightKg, row.actualWeightKg || "", row.lengthCm || "", row.widthCm || "", row.heightCm || "", row.cartonNo, row.transportBatchKey || batchKey, row.platformShipmentId];
for (const store of stores) writeSheet(workbook, `${store}待发`, `${store}｜WFS待发明细`, "每行一个具体颜色/变体，首次T1固定1件。", detailHeaders, byStore(store).map(detail), { A: 23, B: 22, C: 22, D: 20, E: 16, F: 18, G: 34, H: 18, I: 10, J: 14, K: 22, L: 14, M: 12, N: 12, O: 10, P: 10, Q: 10, R: 16, S: 19, T: 20 });

writeSheet(workbook, "按箱拣货", "按箱拣货表", "两个店可以同批国际运输，但不得共用箱号。", ["店铺", "箱号", "商品", "颜色/变体", "SKU", "UPC/GTIN", "数量", "Shipment ID"], formal.map((row) => [row.storeName, row.cartonNo, row.title, row.variant, row.sku, row.gtin, 1, row.platformShipmentId]), { A: 16, B: 16, C: 36, D: 18, E: 20, F: 18, G: 10, H: 20 });

const cartons = [...new Set(formal.map((row) => `${row.storeName}|${row.cartonNo}`))].map((key) => {
  const [store, carton] = key.split("|");
  const items = formal.filter((row) => row.storeName === store && row.cartonNo === carton);
  return [store, carton, new Set(items.map((row) => row.sku)).size, items.length, items.reduce((sum, row) => sum + row.actualWeightKg, 0), items.map((row) => `${row.sku}×1`).join("；"), items[0]?.platformShipmentId || ""];
});
writeSheet(workbook, "箱内SKU明细", "箱内SKU明细", "正式箱重以实际整箱称重为准；本表商品重量合计仅用于复核。", ["店铺", "箱号", "SKU种数", "件数", "商品实测重合计kg", "SKU明细", "Shipment ID"], cartons, { A: 16, B: 16, C: 12, D: 10, E: 20, F: 48, G: 20 });

const gaps = normalized.filter((row) => row.approvalStatus === "APPROVED" && (row.purchaseStatus !== "PURCHASED" || row.receivedQty < 1 || !row.actualWeightKg));
writeSheet(workbook, "采购到货缺口", "采购与到货缺口", "这里只记录已真实发生的采购/到仓状态；审批不等于采购。", ["店铺", "SKU", "商品", "变体", "采购状态", "到仓数", "缺口", "交接键"], gaps.map((row) => [row.storeName, row.sku, row.title, row.variant, row.purchaseStatus, row.receivedQty, row.purchaseStatus !== "PURCHASED" ? "未采购" : row.receivedQty < 1 ? "未到仓" : "待实测", row.handoffKey]), { A: 16, B: 20, C: 34, D: 18, E: 18, F: 12, G: 18, H: 46 });

const exceptions = normalized.filter((row) => issues(row).length);
writeSheet(workbook, "异常与缺失数据", "异常与缺失数据", "缺关键字段时不得猜测；修复后重新生成工作簿。", ["店铺", "SKU", "商品", "变体", "审批", "流程", "异常/缺失", "交接键"], exceptions.map((row) => [row.storeName, row.sku, row.title, row.variant, row.approvalStatus, row.workflowStatus, issues(row).join("；"), row.handoffKey]), { A: 16, B: 20, C: 34, D: 18, E: 14, F: 22, G: 50, H: 46 });

writeSheet(workbook, "证据索引", "原始订单与选品证据索引", "来源统计独立：沃FBM首单与M7不得混算成功率、利润或库存损失。", ["来源", "来源记录", "沃订单号", "订单日期", "candidate_id", "1688 detail_id", "飞书记录ID", "证据时间", "截图/证据引用"], normalized.map((row) => [row.sourceType, row.sourceRecordKey, row.sourceOrderId, row.sourceOrderDate, row.candidateId, row.supplierDetailId, row.feishuRecordId, row.evidenceObservedAt ? new Date(row.evidenceObservedAt) : "", row.screenshotRefs.join("\n")]), { A: 25, B: 25, C: 20, D: 15, E: 24, F: 20, G: 22, H: 20, I: 60 });

async function exportWorkbook(book, filePath) {
  const file = await SpreadsheetFile.exportXlsx(book);
  await file.save(filePath);
}
const safeBatch = batchKey.replace(/[^A-Za-z0-9_-]/g, "_");
const internalPath = path.join(outputDir, `美国WFS合运总表_${safeBatch}.xlsx`);
await exportWorkbook(workbook, internalPath);

const mapping = args["platform-mapping"] ? JSON.parse(await fs.readFile(path.resolve(String(args["platform-mapping"])), "utf8")) : null;
async function platformFile(store, templatePath) {
  const storeRows = formalByStore(store);
  const suffix = templatePath && mapping ? "平台模板" : "平台字段待映射";
  const filePath = path.join(outputDir, `${store}_${safeBatch}_${suffix}.xlsx`);
  if (templatePath && mapping) {
    const book = await SpreadsheetFile.importXlsx(await FileBlob.load(path.resolve(String(templatePath))));
    const sheet = book.worksheets.getItem(mapping.sheet || book.worksheets.items[0].name);
    const headerRow = Number(mapping.headerRow || 1);
    const used = sheet.getUsedRange(true).values;
    const headers = used[headerRow - 1].map((item) => String(item ?? "").trim());
    const columns = mapping.columns || {};
    const data = storeRows.map((row) => headers.map((header) => {
      const field = Object.entries(columns).find(([, target]) => String(target) === header)?.[0];
      if (!field) return "";
      const aliases = { planned_qty: "plannedQty", carton_no: "cartonNo", platform_shipment_id: "platformShipmentId", item_id: "itemId" };
      return row[aliases[field] || field] ?? "";
    }));
    if (data.length) sheet.getRangeByIndexes(headerRow, 0, data.length, headers.length).values = data;
    await exportWorkbook(book, filePath);
  } else {
    const book = Workbook.create();
    writeSheet(book, "待映射", `${store}｜平台字段待映射`, "这不是官方上传模板。请提供当前WFS后台下载的模板和字段映射后再导出正式文件。", ["SKU", "Item ID", "UPC/GTIN", "数量", "箱号", "Shipment ID", "商品", "颜色/变体"], storeRows.map((row) => [row.sku, row.itemId, row.gtin, 1, row.cartonNo, row.platformShipmentId, row.title, row.variant]), { A: 22, B: 18, C: 18, D: 10, E: 16, F: 22, G: 38, H: 20 });
    await exportWorkbook(book, filePath);
  }
  return filePath;
}

const store1Path = await platformFile("美国站1", args["store1-template"]);
const store2Path = await platformFile("美国站2", args["store2-template"]);
const qaDir = path.join(outputDir, "qa");
await fs.mkdir(qaDir, { recursive: true });
const preview = await workbook.render({ sheetName: "批次总览", range: "A1:H12", scale: 1, format: "png" });
const previewPath = path.join(qaDir, `批次总览_${safeBatch}.png`);
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const inspect = await workbook.inspect({ kind: "table", range: "批次总览!A1:H12", include: "values,formulas", tableMaxRows: 15, tableMaxCols: 8, maxChars: 5000 });
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 2000 });
const validation = {
  batchKey, inputCount: normalized.length, formalCount: formal.length, exceptionCount: exceptions.length,
  sharedCartons: [...sharedCartons], internalPath, store1Path, store2Path, previewPath,
  inspect: inspect.ndjson, formulaErrors: errors.ndjson,
};
const validationPath = path.join(outputDir, `validation_${safeBatch}.json`);
await fs.writeFile(validationPath, `${JSON.stringify(validation, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ ...validation, validationPath })}\n`);
