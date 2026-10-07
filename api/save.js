// POST /api/save  { actions: [...] }  -> applies them to the CSVs and makes ONE git commit.
// Actions:
//   { type: "status",    job_id, status, reason? }      Keep (Approved) / Skip / Applied / ...
//   { type: "task_done", task_id, sent? }               tick a task / "Mark sent" on a draft
//   { type: "add_job",   url, note? }                   quick-add a job link (AI fills details later)
//   { type: "answer",    qid, answer }                  answer a question Claude asked while applying
//   { type: "approve_q", qid, answer }                  approve one answer (saved to the answer bank if it has a key)
//   { type: "bank_set",  key, label, answer }          My Info tab: add/edit a saved answer
//   { type: "request_search" }                          "Pull latest jobs" button
//   { type: "bank_delete", key }                        My Info tab: remove a saved answer
//   { type: "approve_answers", job_id }                 all answers approved -> job moves to "Ready"
import { ACT_FIELDS, BANK_FIELDS, REQUEST_FIELDS, JOB_FIELDS, Q_FIELDS, STATUSES, TASK_FIELDS, commitFiles, headSha, parseCSV, readFile,
         sendJSON, toCSV, todayPKT } from "./_lib.js";

const norm = u => String(u || "").trim().replace(/\/+$/, "").toLowerCase();

function apply(actions, jobs, tasks, activity, questions, bank, requests, today) {
  const results = [], touched = new Set(), summary = [];
  const log = (type, job_id, text, extra = {}) => {
    activity.push({ date: today, type, job_id, contact_id: "", channel: "Dashboard", summary: text, task_id: "", ...extra });
    touched.add("activity");
  };
  for (const a of actions) {
    try {
      if (a.type === "status") {
        const j = jobs.find(x => x.id === a.job_id);
        if (!j) throw new Error(`job ${a.job_id} not found`);
        if (!STATUSES.includes(a.status)) throw new Error(`bad status ${a.status}`);
        const from = j.status;
        j.status = a.status; j.last_updated = today;
        if (a.status === "Applied") {
          if (!j.date_applied) j.date_applied = today;
          log("Applied", j.id, `Applied (dashboard): ${j.role} at ${j.company}`);
        } else {
          const why = a.reason ? ` - ${a.reason}` : "";
          if (a.status === "Skipped" && a.reason) j.notes = [j.notes, `Skipped: ${a.reason}`].filter(Boolean).join(" | ");
          log("Status-change", j.id, `${from} -> ${a.status}${why}`);
        }
        touched.add("jobs"); summary.push(`${a.status.toLowerCase()} ${j.id}`);
      } else if (a.type === "task_done") {
        const t = tasks.find(x => x.id === a.task_id);
        if (!t) throw new Error(`task ${a.task_id} not found`);
        if (t.status !== "Done") {
          t.status = "Done"; t.done_date = today; touched.add("tasks");
          const actType = { "Follow-up": "Follow-up", "Thank-you": "Follow-up", Outreach: "Outreach" }[t.type];
          if (a.sent || actType) {
            activity.push({ date: today, type: actType || "Note", job_id: t.job_id, contact_id: t.contact_id,
              channel: a.sent ? "Email" : "", summary: (a.sent ? "Sent: " : "Done: ") + t.title, task_id: t.id });
            touched.add("activity");
          }
          summary.push(`done ${t.id}`);
        }
      } else if (a.type === "add_job") {
        const url = String(a.url || "").trim();
        if (!/^https?:\/\/\S+$/i.test(url)) throw new Error("not a valid link");
        const dup = jobs.find(x => norm(x.job_url) === norm(url));
        if (dup) throw new Error(`already in tracker as ${dup.id} (${dup.status})`);
        const prefix = today.replaceAll("-", "") + "-";
        const n = Math.max(0, ...jobs.filter(x => x.id.startsWith(prefix)).map(x => +x.id.slice(9) || 0)) + 1;
        const id = prefix + String(n).padStart(2, "0");
        let host = ""; try { host = new URL(url).hostname.replace(/^www\./, ""); } catch {}
        jobs.push(Object.fromEntries(JOB_FIELDS.map(k => [k, ""])));
        Object.assign(jobs[jobs.length - 1], {
          id, date_found: today, company: "(to fill)", role: "(to fill)", job_url: url, source: "Manual",
          status: "Shortlisted", follow_up_count: "0", last_updated: today,
          notes: ["Added from dashboard - AI to fill details", a.note].filter(Boolean).join(" | ") + (host ? ` | ${host}` : ""),
        });
        log("Shortlisted", id, `Added from dashboard: ${url}`);
        touched.add("jobs"); summary.push(`add ${id}`);
        results.push({ ok: true, id }); continue;
      } else if (a.type === "answer") {
        const q = questions.find(x => x.id === a.qid);
        if (!q) throw new Error(`question ${a.qid} not found`);
        q.answer = String(a.answer ?? "").slice(0, 4000);
        q.status = q.answer.trim() ? "Answered" : "Open";
        q.answered = q.answer.trim() ? today : "";
        touched.add("questions"); summary.push(`answer ${q.id}`);
      } else if (a.type === "approve_q") {
        const q = questions.find(x => x.id === a.qid);
        if (!q) throw new Error(`question ${a.qid} not found`);
        if (a.answer !== undefined) q.answer = String(a.answer).slice(0, 4000);
        if (q.required === "yes" && !q.answer.trim()) throw new Error("answer is empty");
        q.status = "Approved"; q.answered = today; touched.add("questions");
        if (q.key && q.answer.trim()) {   // remember reusable facts (date of birth, nationality, notice period...)
          const b = bank.find(x => x.key === q.key);
          if (b) Object.assign(b, { answer: q.answer, source_qid: q.id, updated: today });
          else bank.push({ key: q.key, label: q.question.slice(0, 120), answer: q.answer, source_qid: q.id, updated: today });
          touched.add("bank");
        }
        summary.push(`approve ${q.id}`);
      } else if (a.type === "request_search") {
        if (!requests.some(x => x.type === "search" && x.status === "Open")) {
          const n = Math.max(0, ...requests.map(x => +String(x.id).replace(/\D/g, "") || 0)) + 1;
          requests.push({ id: "R" + String(n).padStart(4, "0"), requested_at: new Date().toISOString(), type: "search", status: "Open", done_at: "", result: "" });
          touched.add("requests");
        }
        summary.push("search requested");
      } else if (a.type === "bank_set") {
        const key = String(a.key || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_|_$/g, "").slice(0, 60);
        if (!key) throw new Error("missing key");
        const row = bank.find(x => x.key === key);
        const vals = { label: String(a.label || key).slice(0, 200), answer: String(a.answer ?? "").slice(0, 4000), source_qid: "my-info", updated: today };
        if (row) Object.assign(row, vals); else bank.push({ key, ...vals });
        touched.add("bank"); summary.push(`my-info ${key}`);
      } else if (a.type === "bank_delete") {
        const i = bank.findIndex(x => x.key === a.key);
        if (i >= 0) { bank.splice(i, 1); touched.add("bank"); summary.push(`my-info delete ${a.key}`); }
      } else if (a.type === "approve_answers") {
        const qs = questions.filter(x => x.job_id === a.job_id && x.status !== "Used");
        const missing = qs.filter(x => x.status !== "Approved");
        if (missing.length) throw new Error(`${missing.length} question(s) not approved yet`);
        qs.forEach(x => { x.status = "Approved"; });
        const job = jobs.find(x => x.id === a.job_id);
        if (job && job.status === "Applying") { job.status = "Ready"; job.last_updated = today; touched.add("jobs"); }
        log("Note", a.job_id, "Answers approved on the dashboard");
        touched.add("questions"); summary.push(`approve answers ${a.job_id}`);
      } else throw new Error(`unknown action ${a.type}`);
      results.push({ ok: true });
    } catch (e) { results.push({ ok: false, error: e.message }); }
  }
  return { results, touched, summary };
}

export default async function handler(req, res) {
  if (req.method !== "POST") return sendJSON(res, 405, { error: "POST only" });
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const actions = Array.isArray(body?.actions) ? body.actions.slice(0, 200) : [];
  if (!actions.length) return sendJSON(res, 400, { error: "no actions" });
  const today = /^\d{4}-\d{2}-\d{2}$/.test(body?.today || "") ? body.today : todayPKT();   // user's local date from the browser
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      const sha = await headSha();
      const empty = { "data/questions.csv": Q_FIELDS, "data/answer-bank.csv": BANK_FIELDS, "data/requests.csv": REQUEST_FIELDS };
      const [j, t, a, q, bk, rq] = await Promise.all(["data/jobs.csv", "data/tasks.csv", "data/activity.csv", "data/questions.csv", "data/answer-bank.csv", "data/requests.csv"]
        .map(p => readFile(p, sha).catch(e => { if (e.status === 404 && empty[p]) return empty[p].join(",") + "\n"; throw e; })));
      const jobs = parseCSV(j), tasks = parseCSV(t), activity = parseCSV(a), questions = parseCSV(q), bank = parseCSV(bk), requests = parseCSV(rq);
      const { results, touched, summary } = apply(actions, jobs, tasks, activity, questions, bank, requests, today);
      if (!touched.size) return sendJSON(res, 200, { ok: true, results, commit: null });
      const files = {};
      if (touched.has("jobs")) files["data/jobs.csv"] = toCSV(JOB_FIELDS, jobs);
      if (touched.has("tasks")) files["data/tasks.csv"] = toCSV(TASK_FIELDS, tasks);
      if (touched.has("activity")) files["data/activity.csv"] = toCSV(ACT_FIELDS, activity);
      if (touched.has("questions")) files["data/questions.csv"] = toCSV(Q_FIELDS, questions);
      if (touched.has("bank")) files["data/answer-bank.csv"] = toCSV(BANK_FIELDS, bank);
      if (touched.has("requests")) files["data/requests.csv"] = toCSV(REQUEST_FIELDS, requests);
      try {
        const commit = await commitFiles(sha, files, `update: dashboard - ${summary.join(", ").slice(0, 120)}`);
        return sendJSON(res, 200, { ok: true, results, commit });
      } catch (e) {
        if (![409, 422].includes(e.status) || attempt === 2) throw e;   // branch moved: retry on fresh data
      }
    }
  } catch (e) {
    return sendJSON(res, 500, { ok: false, error: e.message });
  }
}
