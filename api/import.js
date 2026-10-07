// POST /api/import  { files: { "data/jobs.csv": "<csv text>", ... } }
// Restores a backup made with the dashboard's Export button. Only data/*.csv files are accepted,
// each must keep its expected header, and everything is written in ONE git commit (so it can be reverted).
import { commitFiles, headSha, readFile, sendJSON } from "./_lib.js";

const ALLOWED = ["jobs", "tasks", "contacts", "activity", "daily-log", "questions", "answer-bank", "requests"]
  .map(n => `data/${n}.csv`);

export default async function handler(req, res) {
  if (req.method !== "POST") return sendJSON(res, 405, { error: "POST only" });
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const files = body?.files && typeof body.files === "object" ? body.files : null;
  if (!files) return sendJSON(res, 400, { error: "not a backup file" });
  const out = {}, skipped = [];
  try {
    const sha = await headSha();
    for (const [path, text] of Object.entries(files)) {
      if (!ALLOWED.includes(path) || typeof text !== "string" || text.length > 5_000_000) { skipped.push(path); continue; }
      // header must match the current file's header (protects against importing a wrong/old format)
      const current = await readFile(path, sha).catch(() => null);
      const head = s => s.replace(/^﻿/, "").split(/\r?\n/)[0].trim();
      if (current && head(current) !== head(text)) { skipped.push(`${path} (different columns)`); continue; }
      out[path] = text.endsWith("\n") ? text : text + "\n";
    }
    if (!Object.keys(out).length) return sendJSON(res, 400, { error: "nothing to import", skipped });
    const commit = await commitFiles(sha, out, `update: restore backup (${Object.keys(out).length} files)`);
    return sendJSON(res, 200, { ok: true, restored: Object.keys(out), skipped, commit });
  } catch (e) {
    return sendJSON(res, 500, { ok: false, error: e.message });
  }
}
