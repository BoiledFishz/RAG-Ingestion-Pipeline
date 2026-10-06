import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook } from '@oai/artifact-tool';

const root = 'C:/Users/zacha/Documents/Ingestion Pipeline';
const rows = JSON.parse(await fs.readFile(path.join(root, 'audit/project2-v1/revised_scenarios_intermediate.json'), 'utf8'));
const headers = Object.keys(rows[0]);
const values = [headers, ...rows.map(row => headers.map(header => row[header]))];
const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Acceptance');
const range = sheet.getRangeByIndexes(0, 0, values.length, headers.length);
range.values = values;
workbook.recalculate();
const authored = range.values;
if (JSON.stringify(authored) !== JSON.stringify(values)) throw new Error('Authored values changed');
const csv = '\uFEFF' + authored.map(row => row.map(value => '"' + String(value ?? '').replaceAll('"', '""') + '"').join(',')).join('\r\n') + '\r\n';
await fs.writeFile(path.join(root, 'specs/project2/v0.2/acceptance_scenarios.csv'), csv, 'utf8');
console.log(`WROTE scenarios=${rows.length}; original query strings preserved; implementation status pending`);
