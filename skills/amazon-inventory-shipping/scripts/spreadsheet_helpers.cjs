const fs = require("node:fs/promises");
const path = require("node:path");
const { FileBlob, SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

async function readTable(filePath) {
  const suffix = path.extname(filePath).toLowerCase();
  let workbook;
  if (suffix === ".csv") {
    const text = await fs.readFile(filePath, "utf8");
    workbook = await Workbook.fromCSV(text, { sheetName: "Data" });
  } else if (suffix === ".xlsx" || suffix === ".xlsm") {
    workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  } else {
    throw new Error("Input must be CSV or XLSX.");
  }

  const sheet = workbook.worksheets.getItemAt(0);
  const used = sheet.getUsedRange(true);
  const values = used ? used.values : [];
  if (!values || values.length === 0) {
    throw new Error(`${filePath} is empty.`);
  }
  const headers = values[0].map((value) => String(value ?? "").trim());
  const rows = values.slice(1).filter((row) => row.some((value) => value !== null && value !== ""));
  return { workbook, sheet, headers, rows };
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

function parseNumber(value) {
  if (value === null || value === undefined || value === "") return 0;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseBoolean(value, blankDefault = true) {
  if (value === null || value === undefined || String(value).trim() === "") return blankDefault;
  if (typeof value === "boolean") return value;
  return !new Set(["0", "false", "no", "n", "否", "不选"]).has(String(value).trim().toLowerCase());
}

function parseDate(value) {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()));
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    const excelEpoch = Date.UTC(1899, 11, 30);
    return new Date(excelEpoch + Math.round(value) * 86400000);
  }
  const text = String(value ?? "").trim();
  if (!text) return null;
  const normalized = text
    .replace(/[年/.]/g, "-")
    .replace(/月/g, "-")
    .replace(/日/g, "")
    .replace(/-+/g, "-");
  const match = normalized.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (!match) return null;
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (
    date.getUTCFullYear() !== Number(match[1]) ||
    date.getUTCMonth() !== Number(match[2]) - 1 ||
    date.getUTCDate() !== Number(match[3])
  ) {
    return null;
  }
  return date;
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

async function exportWorkbook(workbook, outputPath) {
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const file = await SpreadsheetFile.exportXlsx(workbook);
  await file.save(outputPath);
}

function applyBaseTableStyle(sheet, lastRow, lastCol) {
  const lastColumn = columnLetter(lastCol);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: "#16324F",
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#16324F" },
  };
  sheet.getRange(`A1:${lastColumn}1`).format.rowHeight = 34;
  if (lastRow >= 2) {
    sheet.getRange(`A2:${lastColumn}${lastRow}`).format = {
      font: { color: "#1F2933" },
      verticalAlignment: "center",
      borders: {
        bottom: { style: "thin", color: "#E4E9EE" },
      },
    };
    sheet.getRange(`A2:${lastColumn}${lastRow}`).format.rowHeight = 25;
  }
}

module.exports = {
  Workbook,
  applyBaseTableStyle,
  columnLetter,
  exportWorkbook,
  findHeader,
  normalizeHeader,
  parseArgs,
  parseBoolean,
  parseDate,
  parseNumber,
  readTable,
};
