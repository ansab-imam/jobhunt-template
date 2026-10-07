# Job Search Tracker

> **Start with [WORKFLOW.md](WORKFLOW.md)** (and [SEARCH.md](SEARCH.md) for how jobs are found). It describes how we actually work and overrides this README where they differ.

A plain-text job search tracker for any role and any country. Everything is CSV, Markdown or
JSON, so a human and an AI assistant (Claude Code) can both edit it through git. There's no
database, no server code, no login and no paid services. It runs on Windows 11 with Python's
standard library.

```
config/profile.json   searches, deal-breakers, goals, follow-up rules  (edit to change direction)
config/fx.json        currency → USD rates (edit by hand)
profile.md            human-readable profile + pitch
data/jobs.csv         one row per opportunity (main tracker)
data/tasks.csv        to-dos (auto-generated + manual)
data/contacts.csv     recruiters / hiring managers / referrers
data/activity.csv     append-only log of every event
data/daily-log.csv    per-day summary numbers (rebuilt by report.py)
shortlists/           YYYY-MM-DD.md: daily jobs found by the AI
reports/              week-YYYY-WW.md, month-YYYY-MM.md
drafts/               ready-to-send emails/DMs (you always press Send yourself)
resumes/              generic.pdf + Company-Role.pdf versions
templates/            cover note, recruiter DM, follow-ups, thank-you, salary reply
dashboard/index.html  static dashboard (no build step)
scripts/              generate_tasks.py, report.py, validate.py, notify.ps1, install_reminder.ps1
```

## 5-minute setup (Windows 11)
oct6

1. **Install Python and Git** if you don't have them (PowerShell):
   ```powershell
   winget install -e --id Python.Python.3.12
   winget install -e --id Git.Git
   ```
   Close and reopen PowerShell afterwards.
2. **Clone the repo:**
   ```powershell
   cd $HOME
   git clone https://github.com/<your-username>/jobhunt.git
   cd jobhunt
   ```
3. **Open the dashboard:**
   ```powershell
   python -m http.server 8000
   ```
   Then visit <http://localhost:8000/dashboard/>. Leave the window open. Double-clicking
   `index.html` won't work because browsers block it from reading the CSV files.
4. **Install the daily reminder** (a toast at 10:00 that opens the dashboard when clicked):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1
   ```
   - Change the time: run it again with `-Time 18:30`. Remember that your day starts with US hours.
   - Remove it: `powershell -ExecutionPolicy Bypass -File scripts\install_reminder.ps1 -Remove`
   - Test it now: `powershell -ExecutionPolicy Bypass -File scripts\notify.ps1`

   The reminder also starts the dashboard server in the background, so clicking the toast works
   even if you didn't start it yourself.
5. **Each morning:** run `git pull` to get the AI's new shortlist and tasks.

> **Don't turn on GitHub Pages for this repo.** On a free account, Pages sites are public, so it
> would publish your contacts and applications. Use the local server above, or Vercel below.

## Online dashboard with a login (Vercel, free)
The repo stays **private**. Vercel serves the site, and `middleware.js` asks for a username and
password before *any* file loads, including the dashboard and the CSV data.

1. vercel.com → **Add New → Project** → import your `jobhunt` repo. Framework: **Other**.
   Leave the build command and output directory empty. Deploy.
2. Project → **Settings → Environment Variables**, add for *Production*:
   - `DASHBOARD_USER` = your email
   - `DASHBOARD_PASSWORD` = a strong password (not your email password)
3. **Deployments → ⋯ → Redeploy** so the variables take effect.
4. Open the `*.vercel.app` URL. The browser shows a login box. Every push to `main` redeploys.

To change the password, edit the variable and redeploy. Until both variables are set, the site
stays locked for everyone.

## Your daily workflow (about 10 minutes of admin)

1. `git pull`, then open the dashboard. The **Today** tab shows what's due, with overdue items in red.
2. Read `shortlists/<today>.md` (or **All jobs → Status: Shortlisted**) and apply to the good ones.
3. Tell the AI what you did, in plain words:
   - "applied to 20261006-01, 20261006-04"
   - "got a reply from EXAMPLE Corp, screening call Thursday 7pm PKT"
   - "rejected by X", "skip 20261006-03, commission only"
4. Sending follow-ups: each one has a draft. Click **Copy text** or **Open in email**, check it
   and press Send yourself. Then click **Mark sent**. The dashboard can't save files, so a yellow
   bar appears. Either:
   - click **Download tasks.csv / activity.csv** and replace the files in `data/`, then commit, **or**
   - just tell the AI "mark T0012 sent" and it updates the files.
5. Ticking a checkbox works the same way (**Mark done**).

### Editing by hand
Open any CSV in Excel or VS Code. Rules:
- Dates are `YYYY-MM-DD`.
- `status` must be one of: Shortlisted, Approved, Applied, Screening, Interview, Offer, Accepted,
  Rejected, Ghosted, Withdrawn, Skipped, On-hold.
- **Interviews:** set `status=Interview`, `next_action=Interview with <who>` and
  `next_action_date=<interview date>`. You get a prep task the day before, an "Interview today"
  task on the day, and a thank-you task with a draft afterwards.
- Run `python scripts\validate.py` after hand edits. It catches typos, duplicate URLs and bad dates.

> Excel tip: Excel can reformat dates and drop leading zeros. If you edit in Excel, save as
> **CSV UTF-8** and run `validate.py` afterwards.

## Scripts

| Command | What it does |
|---|---|
| `python scripts\generate_tasks.py` | Builds today's tasks and follow-up drafts, syncs follow-up counts, recomputes USD pay. Safe to run many times. |
| `python scripts\generate_tasks.py --summary` | One-line summary (used by the toast) |
| `python scripts\report.py` | Rebuilds `daily-log.csv` plus this week's and this month's reports |
| `python scripts\report.py week 2026-41` / `month 2026-10` | A specific period |
| `python scripts\validate.py` | Checks headers, ids, duplicate URLs, statuses, dates (exit 1 on errors) |

To test as if it were another day: `$env:JOBTRACKER_TODAY="2026-10-20"; python scripts\generate_tasks.py`
(then `Remove-Item Env:JOBTRACKER_TODAY`).

### Task rules (`generate_tasks.py`)
| Rule | Task |
|---|---|
| Any `Shortlisted` jobs | One "Review N new jobs" task |
| `Approved` (kept on the dashboard) | **Apply** to <role> at <company>, due today |
| Applied, no contact for `follow_up_days[0]` (6) days | **Follow-up #1** + draft from `templates/follow-up-1.md` |
| Applied, 1 follow-up sent, `follow_up_days[1]` (14) days since applying | **Follow-up #2** + draft |
| Applied `ghost_after_days` (30) days ago, no reply | Suggest marking **Ghosted** |
| Interview tomorrow / today / passed | **Interview-prep** / **Interview** / **Thank-you** + draft |
| Any job with `next_action_date` ≤ today | Task for that `next_action` |
| Daily goals | "Apply to N more jobs today", "Send N outreach messages" (N = goal − already logged today) |

Every auto task starts its `details` with a tag like `[auto:fu1]`, which prevents duplicates.
Auto tasks close themselves when they stop applying. For example, an Apply task becomes Done once
the job is Applied, and tasks for Rejected or Ghosted jobs are cancelled. Daily-goal tasks from
earlier days are cancelled. Marking a Follow-up task Done raises the job's `follow_up_count`.
Drafts that already exist are never overwritten, so your edits are safe.

### How numbers are counted (reports + dashboard)
- **Applied:** jobs whose `date_applied` is in the period.
- **Replies:** of those, jobs that got any human response: status Screening, Interview, Offer
  or Accepted, or a Reply, Interview, Offer or Rejected row in `activity.csv`.
- **Response rate** = replies ÷ applied. **Avg days to first reply** uses the first such activity row.
- `pay_usd_month_est` is a conservative estimate. It uses `pay_min` × the rate in `config/fx.json`
  × the period. Hourly pay assumes 173 h/month for full-time and 87 h/month for part-time
  (configurable in `profile.json`).

## Changing direction (no code edits)
Everything search-related lives in `config/profile.json`:
- Add a search, or switch the UK/AU search on with `"active": true`.
- Change keywords, countries, pay floor, deal-breakers, daily goals, follow-up days or ghost days.
- New currency? Add it to `config/fx.json`.
- New role type? Just use a new `role_category` value. Reports and filters pick it up automatically.

---

## Dashboard workflow (online version)
On the Vercel site, clicks are **saved straight to this repo** (one git commit per batch of clicks):
- **Review tab:** jobs the AI found. Open the job, then click **✓ Keep** or **✗ Skip** (pick a reason). Kept jobs become `Approved`.
- **To apply tab:** kept jobs with your tailored resume and cover note. Apply, then click **✓ I applied**.
- **Add job box:** paste any job link you found yourself. It goes straight into *To apply*, and the AI fills in the details.
- Ticking tasks and **Mark sent** on drafts are saved too.

This needs a `GITHUB_TOKEN` environment variable in Vercel: a fine-grained token with
**Contents: Read and write** on this repo only. Data-only commits (`data/`, `drafts/`,
`shortlists/`, `reports/`) don't trigger a redeploy (see `vercel.json`), because the dashboard
reads data live through `/api/file`.

## For the AI assistant

Read **WORKFLOW.md** first, then this section, at the start of every session. **Hard rules from the user:**
- Never access or log in to personal accounts (Gmail, LinkedIn, OneDrive). Ask the user to paste things.
- **Never invent facts** on resumes or applications: no fake numbers, tools, dates or titles.
  Use only `profile.md` and the resume. If something is missing, ask.
- **Never send** emails or messages. Write drafts only; the user sends them.
- When unsure, ask short questions with options.

### Pipeline and file conventions
- Status flow: `Shortlisted` (waiting for the user's review) → `Approved` (kept; prepare the application)
  → `Applied` → Screening/Interview/Offer/Accepted, or Rejected/Ghosted/Withdrawn/**Skipped**/On-hold.
- Fill `date_posted` (and `date_updated` if the page shows a last-updated date) from the posting itself. Leave it blank if not shown, never guess. Job pages almost never show a time of day, only a date.
- `notes` for shortlisted jobs: `Why: <one line> | Red flags: <one line or none>`. The dashboard shows both.
- For every `Approved` job, create `drafts/<job_id>-cover-note.md` (template `cover-note.md`) and,
  if there's a named contact, `drafts/<job_id>-recruiter-dm.md`. Put a tailored resume in
  `resumes/<Company>-<Role>.pdf` (true facts only) and set `resume_used`. Rows added from the
  dashboard have `(to fill)` company/role, so fill them in from the job page.
- **Always `git pull` before editing.** The dashboard commits to `main` too.
- Search settings: `config/profile.json` → `searches` (by priority, US first),
  `excluded_employer_countries`, `search_rules`, `search_schedule_pkt` (19:00 and 23:00 PKT).

### Daily workflow
1. **Morning shortlist**
   - Read `config/profile.json`. For each search with `"active": true`, search job boards for
     roles that match the active searches (see SEARCH.md).
   - Skip URLs already in `jobs.csv` (normalise trailing `/`) and anything matching
     `deal_breakers`. Skip "must live in US/CA" roles, or record them as `location_rule=Local-only`
     and `status=Skipped`.
   - Write `shortlists/<today>.md` with 10–15 jobs in a table: Company | Role | Country | Link |
     Pay | Location rule | Fit | Why | Red flags.
   - Don't send the list in chat. The user reviews it on the dashboard's Review tab.
   - Append the jobs to `jobs.csv` as `Shortlisted`, with ids `YYYYMMDD-NN` (never reuse one),
     `fit_score` 1–5 and `priority`. Add a `Shortlisted` row to `activity.csv` for each.
   - Run `python scripts/generate_tasks.py` and `python scripts/validate.py`.
   - Commit `shortlist: <date>` and push.
2. **"Applied to X, Y"**
   - Set `status=Applied`, `date_applied`, `resume_used`, `last_updated`.
   - Add an `Applied` row to `activity.csv` (and `Outreach` rows for any DMs sent).
   - Regenerate tasks, validate, then commit `applied: <date>`.
3. **Replies and interviews**
   - Update `status`, `last_contact_date` and `next_action` / `next_action_date`.
   - Add or link the contact in `contacts.csv` and log the event in `activity.csv`.
   - Regenerate tasks and drafts, then commit `update: <summary>`.
4. **"Mark T00xx sent/done"**
   - Set the task to `Done` with `done_date`.
   - Append to `activity.csv` (type `Follow-up`, `Outreach` or `Note`, with `task_id`).
   - Regenerate tasks, then commit `tasks: <summary>`.
5. **Friday**
   - Run `python scripts/report.py`.
   - Summarise the week for the user in 5 bullet points.
   - Commit `report: week <YYYY-WW>`.

Commit format: `<type>: <summary>`, where type is one of shortlist, applied, update, tasks,
report or chore. Always run `validate.py` before committing.

### Fit score guide
- **5:** Matches the user's target role, location rule and pay floor exactly, with no red flags.
- **4:** Strong fit with one gap (pay unclear, or a tool he hasn't used like HubSpot or Dialpad).
- **3:** Workable, but pay is below target or the role is only partly sales.
- **1–2:** Big gaps. Usually don't shortlist these.
- Red flags to call out: commission-only, upfront fees or "buy your own leads", vague company,
  unrealistic pay, requests for ID or bank details before an offer, "must reside in US/CA".
