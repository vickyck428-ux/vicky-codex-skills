const fs = require("node:fs/promises");
const path = require("node:path");
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

async function readTable(filePath) {
  const suffix = path.extname(filePath).toLowerCase();
  let workbook;
  if (suffix === ".csv") {
    workbook = await Workbook.fromCSV(await fs.readFile(filePath, "utf8"), { sheetName: "Data" });
  } else if (suffix === ".xlsx" || suffix === ".xlsm") {
    workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  } else {
    throw new Error("Input must be CSV or XLSX.");
  }
  const sheet = workbook.worksheets.getItemAt(0);
  const used = sheet.getUsedRange(true);
  const values = used ? used.values : [];
  if (!values || values.length === 0) throw new Error(`${filePath} is empty.`);
  const headers = values[0].map((value) => String(value ?? "").trim());
  const rows = values.slice(1).filter((row) => row.some((value) => value !== null && value !== ""));
  return { headers, rows };
}

function normalizeHeader(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s_\-（）()]+/g, "");
}

function findHeader(headers, aliases) {
  const normalized = headers.map(normalizeHeader);
  for (const alias of aliases) {
    const index = normalized.indexOf(normalizeHeader(alias));
    if (index >= 0) return index;
  }
  return -1;
}

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[index + 1];
    if (next && !next.startsWith("--")) {
      args[key] = next;
      index += 1;
    } else {
      args[key] = true;
    }
  }
  return args;
}

function parseDate(value) {
  const text = String(value ?? "").trim();
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  return Number.isNaN(date.getTime()) ? null : date;
}

async function exportWorkbook(workbook, outputPath) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await (await SpreadsheetFile.exportXlsx(workbook)).save(outputPath);
}

function applyTableStyle(sheet, lastRow, lastCol) {
  const lastColumn = columnLetter(lastCol);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: "#173F5F",
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#173F5F" },
  };
  sheet.getRange(`A1:${lastColumn}1`).format.rowHeight = 38;
  if (lastRow >= 2) {
    sheet.getRange(`A2:${lastColumn}${lastRow}`).format = {
      font: { color: "#1F2937" },
      verticalAlignment: "center",
      borders: { bottom: { style: "thin", color: "#E5E7EB" } },
    };
    sheet.getRange(`A2:${lastColumn}${lastRow}`).format.rowHeight = 30;
  }
}

module.exports = {
  Workbook,
  applyTableStyle,
  columnLetter,
  exportWorkbook,
  findHeader,
  parseArgs,
  parseDate,
  readTable,
};
