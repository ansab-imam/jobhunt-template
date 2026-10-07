// Shared helpers for the Vercel API routes (files starting with "_" are not routes).
// All data lives in the GitHub repo; these routes read/write it with GITHUB_TOKEN.

// Repo that holds the data. Set GITHUB_REPO="owner/name" in Vercel; otherwise Vercel's own git info is used.
const REPO = process.env.GITHUB_REPO ||
  (process.env.VERCEL_GIT_REPO_OWNER && process.env.VERCEL_GIT_REPO_SLUG ? `${process.env.VERCEL_GIT_REPO_OWNER}/${process.env.VERCEL_GIT_REPO_SLUG}` : "");
const BRANCH = process.env.GITHUB_BRANCH || "main";
const GH = `https://api.github.com/repos/${REPO}`;

export const JOB_FIELDS = ["id", "date_found", "date_posted", "date_updated", "company", "company_url", "company_size", "company_hq", "company_locations", "foreign_presence", "role", "role_category", "job_url", "source",
  "country", "location_rule", "work_mode", "employment_type", "hours_timezone", "pay_min", "pay_max",
  "currency", "pay_period", "pay_usd_month_est", "fit_score", "priority", "status", "date_applied",
  "resume_used", "contact_id", "last_contact_date", "next_action", "next_action_date",
  "follow_up_count", "last_updated", "notes"];
export const TASK_FIELDS = ["id", "created", "due_date", "type", "job_id", "contact_id", "title",
  "details", "draft_file", "status", "done_date"];
export const ACT_FIELDS = ["date", "type", "job_id", "contact_id", "channel", "summary", "task_id"];
export const Q_FIELDS = ["id", "job_id", "question", "kind", "options", "required", "answer", "status", "asked", "answered", "notes", "key"];
export const REQUEST_FIELDS = ["id", "requested_at", "type", "status", "done_at", "result"];
export const BANK_FIELDS = ["key", "label", "answer", "source_qid", "updated"];
export const STATUSES = ["Shortlisted", "Approved", "Applying", "Ready", "Applied", "Screening", "Interview", "Offer",
  "Accepted", "Rejected", "Ghosted", "Withdrawn", "Skipped", "On-hold"];

export function ghHeaders(extra = {}) {
  const token = process.env.GITHUB_TOKEN;
  if (!token) throw Object.assign(new Error("GITHUB_TOKEN is not set in Vercel"), { status: 500 });
  if (!REPO) throw Object.assign(new Error("GITHUB_REPO is not set in Vercel (e.g. yourname/jobhunt)"), { status: 500 });
  return { Authorization: `Bearer ${token}`, "X-GitHub-Api-Version": "2022-11-28",
           "User-Agent": "jobhunt-dashboard", ...extra };
}

export async function gh(path, opts = {}) {
  const r = await fetch(GH + path, { ...opts, headers: ghHeaders(opts.headers) });
  if (!r.ok) {
    const body = await r.text();
    throw Object.assign(new Error(`GitHub ${opts.method || "GET"} ${path}: ${r.status} ${body.slice(0, 200)}`),
                        { status: r.status });
  }
  return r;
}

export async function readFile(path, ref = BRANCH) {
  const r = await gh(`/contents/${encodeURI(path)}?ref=${encodeURIComponent(ref)}`,
                     { headers: { Accept: "application/vnd.github.raw" } });
  return r.text();
}

export async function headSha() {
  const r = await gh(`/git/ref/heads/${BRANCH}`);
  return (await r.json()).object.sha;
}

/** One commit with several changed files; fails (409/422) if the branch moved meanwhile. */
export async function commitFiles(parentSha, files, message) {
  const parent = await (await gh(`/git/commits/${parentSha}`)).json();
  const tree = await (await gh(`/git/trees`, { method: "POST", body: JSON.stringify({
    base_tree: parent.tree.sha,
    tree: Object.entries(files).map(([path, content]) => ({ path, mode: "100644", type: "blob", content })),
  }) })).json();
  const commit = await (await gh(`/git/commits`, { method: "POST", body: JSON.stringify({
    message, tree: tree.sha, parents: [parentSha] }) })).json();
  await gh(`/git/refs/heads/${BRANCH}`, { method: "PATCH", body: JSON.stringify({ sha: commit.sha, force: false }) });
  return commit.sha;
}

// ---- CSV ----
export function parseCSV(text) {
  const rows = []; let row = [], f = "", q = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
      else f += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(f); f = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(f); f = ""; if (row.some(x => x !== "")) rows.push(row); row = [];
    } else f += c;
  }
  if (f !== "" || row.length) { row.push(f); if (row.some(x => x !== "")) rows.push(row); }
  const head = (rows.shift() || []).map(h => h.trim());
  const out = rows.map(r => Object.fromEntries(head.map((h, i) => [h, (r[i] || "").trim()])));
  out.header = head;   // keep the file's own column order when writing back
  return out;
}
const cell = v => /[",\n\r]/.test(v = String(v ?? "")) ? '"' + v.replace(/"/g, '""') + '"' : v;
/** Writes the file's existing columns first, then any known fields it lacks, so no column is ever dropped. */
export const toCSV = (fields, rows) => {
  fields = [...(rows.header || []), ...fields.filter(f => !(rows.header || []).includes(f))];
  return [fields.join(","), ...rows.map(r => fields.map(k => cell(r[k])).join(","))].join("\n") + "\n";
};

/** Fallback date (YYYY-MM-DD) when the browser doesn't send its own local date. Set TRACKER_TZ in Vercel to change. */
export function todayPKT() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: process.env.TRACKER_TZ || "UTC" }).format(new Date());
}

export function sendJSON(res, status, obj) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(obj));
}
