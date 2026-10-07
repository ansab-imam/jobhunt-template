"""Build today's tasks from data/jobs.csv + the rules in config/profile.json.

Safe to run many times: every auto task carries a tag like "[auto:fu1]" at the start of
its `details`, and a tag is never created twice for the same job.

Also keeps data in sync:
  * recomputes pay_usd_month_est from config/fx.json
  * when a Follow-up task is marked Done, bumps the job's follow_up_count / last_contact_date
  * closes auto tasks whose reason has gone away (e.g. Apply task once the job is Applied)

Usage:  python scripts/generate_tasks.py            (prints what changed + today's list)
        python scripts/generate_tasks.py --summary  (prints one line, used by notify.ps1)
Env:    JOBTRACKER_TODAY=YYYY-MM-DD to pretend it's another day (testing).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (CLOSED_STATUSES, days_between, fill, iso, load_json, next_id, parse_date,
                    path, read_csv, timedelta, today, usd_month_estimate, write_csv)

TAG_RE = re.compile(r"^\[auto:([^\]]+)\]")


def tag_of(task):
    m = TAG_RE.match(task.get("details", ""))
    return m.group(1) if m else None


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def guess_type(action):
    a = action.lower()
    for word, t in (("thank", "Thank-you"), ("prep", "Interview-prep"), ("interview", "Interview"),
                    ("follow", "Follow-up"), ("reply", "Reply"), ("respond", "Reply"),
                    ("apply", "Apply"), ("message", "Outreach"), ("dm", "Outreach"),
                    ("outreach", "Outreach"), ("connect", "Outreach")):
        if word in a:
            return t
    return "Custom"


def main():
    quiet = "--summary" in sys.argv
    t = today()
    profile = load_json("config", "profile.json")
    fx = load_json("config", "fx.json")
    me = profile.get("me", {})
    fu_days = profile.get("follow_up_days", [6, 14])
    ghost_days = profile.get("ghost_after_days", 30)
    goals = profile.get("daily_goals", {})

    _, jobs = read_csv("jobs.csv")
    _, tasks = read_csv("tasks.csv")
    _, contacts = read_csv("contacts.csv")
    _, activity = read_csv("activity.csv")
    contacts_by_id = {c["id"]: c for c in contacts}
    jobs_by_id = {j["id"]: j for j in jobs}
    log = []

    # ---- 1. sync job fields -------------------------------------------------------------
    jobs_changed = False
    for j in jobs:
        hours = (profile.get("hourly_hours_per_month_part_time", 87)
                 if "part" in j.get("employment_type", "").lower()
                 else profile.get("hourly_hours_per_month", 173))
        est = usd_month_estimate(j, fx, hours)
        if est != j.get("pay_usd_month_est", ""):
            j["pay_usd_month_est"] = est
            jobs_changed = True
    for task in tasks:
        tg = tag_of(task) or ""
        j = jobs_by_id.get(task.get("job_id"))
        if not j or task["status"] != "Done" or tg not in ("fu1", "fu2"):
            continue
        n = 1 if tg == "fu1" else 2
        if int(j.get("follow_up_count") or 0) < n:
            j["follow_up_count"] = str(n)
            jobs_changed = True
            log.append(f"job {j['id']}: follow_up_count -> {n}")
        done = task.get("done_date") or iso(t)
        if (j.get("last_contact_date") or "") < done:
            j["last_contact_date"] = done
            j["last_updated"] = iso(t)
            jobs_changed = True

    # ---- 2. close auto tasks that no longer apply ---------------------------------------
    def close(task, status, why):
        task["status"] = status
        task["done_date"] = iso(t)
        log.append(f"{status.lower()}: {task['id']} {task['title']} ({why})")

    for task in tasks:
        tg = tag_of(task)
        if not tg or task["status"] not in ("Open", "Snoozed"):
            continue
        j = jobs_by_id.get(task.get("job_id"))
        if tg.startswith("goal-") or tg.startswith("review:"):
            if tg.split(":", 1)[1] < iso(t):
                close(task, "Cancelled", "goal day passed")
            continue
        if not j:
            continue
        status = j["status"]
        fcount = int(j.get("follow_up_count") or 0)
        if status in CLOSED_STATUSES:
            close(task, "Cancelled", f"job is {status}")
        elif tg == "apply" and status not in ("Approved", "Applying", "Ready"):
            close(task, "Done", f"job is {status}")
        elif tg in ("fu1", "fu2") and fcount >= (1 if tg == "fu1" else 2):
            close(task, "Done", "follow-up recorded")
        elif tg in ("fu1", "fu2", "ghost") and status != "Applied":
            close(task, "Cancelled", f"job moved to {status}")
        elif tg.split(":")[0] in ("prep", "interview") and tg.split(":", 1)[1] < iso(t):
            close(task, "Cancelled", "interview date passed")
        elif tg.startswith("next:"):
            if tg != next_tag(j):
                close(task, "Cancelled", "next action changed")

    # ---- 3. create tasks from rules -----------------------------------------------------
    existing = {(task.get("job_id", ""), tag_of(task)) for task in tasks if tag_of(task)}

    def ensure(tag, job, ttype, title, details, due=None, draft_template=None, extra=None):
        jid = job["id"] if job else ""
        if (jid, tag) in existing:
            return None
        draft_rel = ""
        if draft_template:
            draft_rel = make_draft(draft_template, job, contacts_by_id, me, extra or {})
        task = {
            "id": next_id([x["id"] for x in tasks], "T"),
            "created": iso(t), "due_date": iso(due or t), "type": ttype,
            "job_id": jid, "contact_id": job.get("contact_id", "") if job else "",
            "title": title, "details": f"[auto:{tag}] {details}".strip(),
            "draft_file": draft_rel, "status": "Open", "done_date": "",
        }
        tasks.append(task)
        existing.add((jid, tag))
        log.append(f"new: {task['id']} {title}" + (f"  (draft: {draft_rel})" if draft_rel else ""))
        return task

    for j in jobs:
        status, label = j["status"], f"{j['role']} at {j['company']}"
        applied = parse_date(j.get("date_applied"))
        last_touch = max(filter(None, [applied, parse_date(j.get("last_contact_date"))]), default=None)
        fcount = int(j.get("follow_up_count") or 0)
        nad = parse_date(j.get("next_action_date"))
        action = j.get("next_action", "")
        is_interview = status == "Interview" and "interview" in action.lower() and nad

        if status == "Approved":
            ensure("apply", j, "Apply", f"Apply to {label}", j.get("job_url", ""))

        if status == "Applied" and applied:
            if fcount == 0 and days_between(last_touch, t) >= fu_days[0]:
                ensure("fu1", j, "Follow-up", f"Follow-up #1: {label}",
                       f"Applied {iso(applied)}, no reply for {days_between(last_touch, t)} days",
                       draft_template="follow-up-1.md")
            if fcount == 1 and days_between(applied, t) >= fu_days[1]:
                ensure("fu2", j, "Follow-up", f"Follow-up #2: {label}",
                       f"Applied {iso(applied)}, one follow-up sent, still no reply",
                       draft_template="follow-up-2.md")
            if days_between(applied, t) >= ghost_days:
                ensure("ghost", j, "Custom", f"Mark as Ghosted? {label}",
                       f"No reply {days_between(applied, t)} days after applying. "
                       f"Tell the AI 'ghosted {j['id']}' or set status=Ghosted.")

        if is_interview:
            d = iso(nad)
            if nad - t == timedelta(days=1):
                ensure(f"prep:{d}", j, "Interview-prep", f"Prepare for interview: {label}",
                       f"Interview on {d}. Review job post, company, your pitch and questions.")
            if nad == t:
                ensure(f"interview:{d}", j, "Interview", f"Interview today: {label}", action)
            if nad < t:
                ensure(f"thanks:{d}", j, "Thank-you", f"Send thank-you note: {label}",
                       f"Interview was on {d}. Then update status/next_action.",
                       draft_template="thank-you-after-interview.md")
        elif nad and nad <= t and action and status not in CLOSED_STATUSES:
            ensure(next_tag(j), j, guess_type(action), f"{action}: {label}",
                   f"next_action_date {iso(nad)}", due=nad)

    # one task to review today's new shortlist on the dashboard
    to_review = [j for j in jobs if j["status"] == "Shortlisted"]
    rtag = f"review:{iso(t)}"
    current = next((x for x in tasks if tag_of(x) == rtag), None)
    rtitle = f"Review {len(to_review)} new job(s) on the dashboard (Review tab)"
    if to_review and current is None:
        ensure(rtag, None, "Custom", rtitle, "Open each link, Skip the ones you don't like, Keep the rest")
    elif current is not None and current["status"] == "Open":
        if not to_review:
            close(current, "Done", "nothing left to review")
        else:
            current["title"] = rtitle

    # daily goals
    applied_today = {j["id"] for j in jobs if j.get("date_applied") == iso(t)}
    applied_today |= {a["job_id"] for a in activity if a["date"] == iso(t) and a["type"] == "Applied"}
    outreach_today = sum(1 for a in activity if a["date"] == iso(t) and a["type"] == "Outreach")
    for key, goal, done_n, ttype, label in (
            ("apply", goals.get("applications", 0), len(applied_today), "Apply", "more jobs today"),
            ("outreach", goals.get("outreach_messages", 0), outreach_today, "Outreach",
             "outreach messages today")):
        tag = f"goal-{key}:{iso(t)}"
        left = max(0, goal - done_n)
        verb = "Apply to" if key == "apply" else "Send"
        title = f"{verb} {left} {label} ({done_n}/{goal} done)"
        current = next((x for x in tasks if tag_of(x) == tag), None)
        if current is None and left > 0:
            ensure(tag, None, ttype, title, f"Daily goal {goal}")
        elif current is not None and current["status"] == "Open":
            if left == 0:
                current["title"] = title
                close(current, "Done", "goal reached")
            elif current["title"] != title:
                current["title"] = title

    # ---- 4. save + report ---------------------------------------------------------------
    if jobs_changed:
        write_csv("jobs.csv", jobs)
    write_csv("tasks.csv", tasks)

    due = [x for x in tasks if x["status"] == "Open" and x["due_date"] and x["due_date"] <= iso(t)]
    counts = {}
    for x in due:
        counts[x["type"]] = counts.get(x["type"], 0) + 1
    names = {"Follow-up": "follow-ups", "Apply": "apply tasks", "Interview-prep": "interview prep",
             "Interview": "interviews", "Thank-you": "thank-you notes", "Reply": "replies",
             "Outreach": "outreach tasks", "Custom": "other"}
    summary = ", ".join(f"{n} {names.get(k, k)}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    summary = f"Job search: {summary or 'nothing due'} today"

    if quiet:
        print(summary)
        return
    for line in log:
        print(line)
    print(f"\n{summary}")
    for x in sorted(due, key=lambda x: (x["due_date"], x["type"])):
        late = "  (OVERDUE)" if x["due_date"] < iso(t) else ""
        print(f"  [{x['type']}] {x['title']}{late}")


def next_tag(job):
    return f"next:{job.get('next_action_date', '')}:{slug(job.get('next_action', ''))}"


def make_draft(template_name, job, contacts_by_id, me, extra):
    c = contacts_by_id.get(job.get("contact_id", ""), {})
    name = c.get("name", "")
    values = {
        "company": job.get("company", ""), "role": job.get("role", ""),
        "job_url": job.get("job_url", ""), "date_applied": job.get("date_applied", ""),
        "contact_name": name or "Hiring Team",
        "contact_first_name": name.split()[0] if name else "Hiring Team",
        "contact_email": c.get("email", ""),
        "my_name": me.get("name", ""), "my_first_name": me.get("first_name", ""),
        "my_email": me.get("email", ""), "my_phone": me.get("phone", ""),
        "my_linkedin": me.get("linkedin", ""),
    }
    values.update(extra)
    kind = template_name.replace(".md", "")
    rel = f"drafts/{job['id']}-{kind}.md"
    out = path(*rel.split("/"))
    if not os.path.exists(out):  # never overwrite a draft a human may have edited
        with open(path("templates", template_name), encoding="utf-8") as f:
            text = fill(f.read(), values)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return rel


if __name__ == "__main__":
    main()
