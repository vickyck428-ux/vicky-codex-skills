#!/usr/bin/env node
import fs from "node:fs";

const input = JSON.parse(fs.readFileSync(process.argv[2] ?? 0, "utf8"));
const groups = input.groups ?? {};
const ids = (name) => (groups[name] ?? []).map(String);
const duplicates = (values) => [...new Set(values.filter((v, i) => values.indexOf(v) !== i))];
const a = ids("amazonAUs");
const b = ids("amazonBUkDe");
const crossBrand = a.filter((id) => new Set(b).has(id));
const all = Object.values(groups).flat().map(String);

const result = {
  ok: crossBrand.length === 0 && a.length <= 15 && b.length <= 15,
  counts: Object.fromEntries(Object.entries(groups).map(([key, value]) => [key, Array.isArray(value) ? value.length : 0])),
  crossBrand,
  repeatedAssignments: duplicates(all),
};

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
