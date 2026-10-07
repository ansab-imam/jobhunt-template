# How Claude searches for jobs

Run this when the user clicks **🔎 Pull latest jobs** (a row in `data/requests.csv`) or asks in chat.
First read `profile.md` ("What I'm searching for"), `config/profile.json` (`me.location`, `searches`, `deal_breakers`,
`excluded_employer_countries`, `max_posting_age_days`) and `resumes/master.json` (who the user is).

## Run every search where `"active": true`
Each search in `config/profile.json` sets its own rules: `keywords`, `target_countries`, `cities`, `work_mode`,
`employment_types`, `pay_floor`, `sources` and `employer_country_rule`. There are two kinds:
- **Local search** (has `cities`): jobs in those cities, on-site, hybrid or remote as listed. Any employer country is fine unless the search says otherwise.
  Good sources: LinkedIn public job pages (`linkedin.com/jobs/search?keywords=...&location=<city>`, then open each `/jobs/view/` page), national job boards
  (e.g. Indeed for your country, Naukri for India, Seek for Australia), and company career pages.
- **International remote search**: remote jobs open to someone living in the user's country (`me.location`).
  Good sources: Himalayas, We Work Remotely, Remote OK, Remotive, Working Nomads, Dynamite Jobs, Wellfound, Remote.co,
  and the public Greenhouse/Lever/Ashby APIs (`boards-api.greenhouse.io/v1/boards/<co>/jobs?content=true`, `api.lever.co/v0/postings/<co>`,
  `api.ashbyhq.com/posting-api/job-board/<co>`).
Public pages only. If a site needs a login or blocks automated access, skip it and say so in the result.

## Keep a job only if ALL of these are true
1. **Posted (or updated) within `max_posting_age_days`** (default 10), going by the date on the posting. If no date is shown, skip it.
2. **The location fits.** Local: in one of the search's cities. Remote: open to the user's country, going by the posting's own location or country list,
   not the job board's tag. If the posting lists allowed countries and the user's country isn't one of them, skip it.
3. **The employer's country is allowed** (`employer_country_rule`, `excluded_employer_countries`). Skip low-paying staffing or BPO mills.
4. **It matches the search's roles/keywords** and the user's background in `resumes/master.json`.
5. **Pay is at or above `pay_floor`, or not listed** (flag "pay not listed"). Skip anything listed below the floor, anything commission-only, and every `deal_breaker`.
6. **A real company, still open.** No fees, no "buy your own leads", no requests for ID or bank details.
7. **Never the same job twice.** Skip it if it's in `data/seen-jobs.csv` (the permanent list of every job ever found, including skipped ones
   and jobs from before any reset) or in `data/jobs.csv`. A job counts as the same if **either**:
   - it has the same `job_url` (ignoring a trailing `/`, `?query` and tracking parameters), **or**
   - it has the same company and the same role title (case and punctuation ignored, as in `job_key()` in scripts/common.py). This catches reposts with a new link.
   The same company with a **different** role that fits the profile is fine.

Always prefer the **latest and most relevant** jobs. Any number is fine (1, 5 or 20). Never pad the list with weak jobs.

## What to write for each job (append to data/jobs.csv)
- `id` (YYYYMMDD-NN, never reused), `date_found`, `date_posted`, `date_updated`, `company`, `company_url`
  (the company's own website, checked to load; otherwise its LinkedIn company page), `role`, `role_category`, `job_url`, `source`, `country`,
  `location_rule`, `work_mode`, `employment_type`, `hours_timezone`, `pay_min`/`pay_max`/`currency`/`pay_period`, `fit_score` 1–5, `priority`,
  `status=Shortlisted`, `follow_up_count=0`, `last_updated`.
- Company profile from public sources (company site, public LinkedIn company page, Crunchbase/ZoomInfo snippets; write "Unknown" rather than guess):
  `company_size` (e.g. "51-200"), `company_hq`, `company_locations` (all offices found), `foreign_presence` ("Yes: ..." / "No: ..." / "Unclear: ...").
- `notes`: `Why: <one honest line about the fit> | Red flags: <one line or none>`.
- Add a `Shortlisted` row to `data/activity.csv` and a row to `data/seen-jobs.csv` for each job.
- Run `scripts/generate_tasks.py` and `scripts/validate.py` (0 errors). Commit `shortlist: <date> (<n> jobs)` and push.
- Don't post the list in chat. The user reviews it on the dashboard. Mark the request row `Done` with a short result, e.g. "8 jobs added (5 local, 3 remote)".
