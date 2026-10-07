"""Weekly / monthly reports + daily-log.csv.

Usage:
  python scripts/report.py                 # rebuild daily-log + this week's + this month's report
  python scripts/report.py week            # this ISO week
  python scripts/report.py week 2026-40    # a specific ISO week
  python scripts/report.py month 2026-10   # a specific month

How numbers are counted ("cohort" view, same as the dashboard):
  applied   = jobs whose date_applied falls in the period
  replies   = of those, jobs that got any human response (status Screening/Interview/Offer/
              Accepted, or a Reply/Interview/Offer/Rejected row in activity.csv)
  interviews/offers/rejected/ghosted = of those, where they are now
  outreach / follow-ups = rows in activity.csv dated inside the period
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (REPLY_STATUSES, iso, load_json, parse_date, path, read_csv, timedelta, today,
                    write_csv)

RESPONSE_EVENTS = {"Reply", "Interview", "Offer", "Rejected"}


def week_range(year, week):
    start = date.fromisocalendar(year, week, 1)
    return start, start + timedelta(days=6)


def month_range(year, month):
    start = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return start, nxt - timedelta(days=1)


def first_response(job_id, activity):
    ds = [parse_date(a["date"]) for a in activity
          if a["job_id"] == job_id and a["type"] in RESPONSE_EVENTS]
    ds = [d for d in ds if d]
    return min(ds) if ds else None


def responded(job, activity):
    if job["status"] in REPLY_STATUSES:
        return True
    return first_response(job["id"], activity) is not None


def stats(jobs, activity, start, end):
    cohort = [j for j in jobs if (d := parse_date(j.get("date_applied"))) and start <= d <= end]
    in_period = [a for a in activity if (d := parse_date(a["date"])) and start <= d <= end]
    replied = [j for j in cohort if responded(j, activity)]
    gaps = []
    for j in cohort:
        fr = first_response(j["id"], activity)
        if fr:
            gaps.append((fr - parse_date(j["date_applied"])).days)
    return {
        "cohort": cohort,
        "applied": len(cohort),
        "replies": len(replied),
        "rate": (len(replied) / len(cohort)) if cohort else 0,
        "interviews": sum(1 for j in cohort if j["status"] in ("Interview", "Offer", "Accepted")
                          or any(a["job_id"] == j["id"] and a["type"] == "Interview"
                                 for a in activity)),
        "offers": sum(1 for j in cohort if j["status"] in ("Offer", "Accepted")),
        "rejected": sum(1 for j in cohort if j["status"] == "Rejected"),
        "ghosted": sum(1 for j in cohort if j["status"] == "Ghosted"),
        "shortlisted": sum(1 for j in jobs if (d := parse_date(j.get("date_found")))
                           and start <= d <= end),
        "outreach": sum(1 for a in in_period if a["type"] == "Outreach"),
        "follow_ups": sum(1 for a in in_period if a["type"] == "Follow-up"),
        "avg_days_to_reply": (sum(gaps) / len(gaps)) if gaps else None,
    }


def breakdown(cohort, activity, field):
    groups = {}
    for j in cohort:
        groups.setdefault(j.get(field) or "(blank)", []).append(j)
    rows = []
    for k, js in groups.items():
        r = sum(1 for j in js if responded(j, activity))
        rows.append((k, len(js), r, r / len(js)))
    return sorted(rows, key=lambda x: (-x[1], x[0]))


def pct(x):
    return f"{x * 100:.0f}%"


def insights(s, activity, profile, days):
    out = []
    src = [r for r in breakdown(s["cohort"], activity, "source") if r[1] >= 3]
    if src:
        best = max(src, key=lambda r: r[3])
        out.append(f"Best source: **{best[0]}** ({best[2]}/{best[1]} replied, {pct(best[3])}).")
    goal = profile.get("daily_goals", {}).get("applications", 0) * days
    if goal:
        out.append(f"Applications: {s['applied']} vs goal {goal} "
                   f"({'on track' if s['applied'] >= goal else 'behind'}).")
    if s["applied"] >= 10 and s["rate"] < 0.05:
        out.append("Response rate under 5%: tailor the resume more per job and add a recruiter "
                   "DM for every High-priority application.")
    elif s["applied"] and s["rate"] >= 0.15:
        out.append(f"Response rate {pct(s['rate'])} is healthy; keep the same targeting.")
    if s["avg_days_to_reply"] is not None:
        out.append(f"Average {s['avg_days_to_reply']:.1f} days from applying to first reply.")
    if s["outreach"] == 0 and s["applied"]:
        out.append("No outreach messages logged. Recruiter DMs usually lift reply rates.")
    if not out:
        out.append("Not enough data yet. Insights appear after a few applications.")
    return out[:3]


def write_report(kind, label, start, end, jobs, activity, profile):
    s = stats(jobs, activity, start, end)
    days = (end - start).days + 1
    workdays = sum(1 for i in range(days) if (start + timedelta(days=i)).weekday() < 5)
    goals = profile.get("daily_goals", {})
    lines = [
        f"# {kind.title()} report: {label}",
        f"_{iso(start)} to {iso(end)} · generated {iso(today())}_", "",
        "| Metric | Value |", "|---|---|",
        f"| Jobs shortlisted | {s['shortlisted']} |",
        f"| Applied | {s['applied']} |",
        f"| Replies (any response) | {s['replies']} |",
        f"| Response rate | {pct(s['rate'])} |",
        f"| Interviews | {s['interviews']} |",
        f"| Offers | {s['offers']} |",
        f"| Rejected | {s['rejected']} |",
        f"| Ghosted | {s['ghosted']} |",
        f"| Outreach messages | {s['outreach']} |",
        f"| Follow-ups sent | {s['follow_ups']} |",
        "| Avg days to first reply | "
        + (f"{s['avg_days_to_reply']:.1f}" if s['avg_days_to_reply'] is not None else "-") + " |",
        "",
    ]
    for field, title in (("country", "By country"), ("source", "By source"),
                         ("role_category", "By role category")):
        lines += [f"## {title}", "", "| | Applied | Replies | Rate |", "|---|---|---|---|"]
        rows = breakdown(s["cohort"], activity, field)
        lines += [f"| {k} | {n} | {r} | {pct(rate)} |" for k, n, r, rate in rows] or ["| - | 0 | 0 | - |"]
        lines.append("")
    lines += ["## Top insights", ""] + [f"{i}. {x}" for i, x in
                                         enumerate(insights(s, activity, profile, workdays), 1)]
    nxt_days = 5 if kind == "week" else 21
    lines += ["", "## Goals for next period", "",
              f"- Apply to {goals.get('applications', 0) * nxt_days} jobs "
              f"({goals.get('applications', 0)}/workday)",
              f"- Send {goals.get('outreach_messages', 0) * nxt_days} outreach messages",
              "- Clear every overdue follow-up on the dashboard's Today tab", ""]
    out = path("reports", f"{kind}-{label}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print(f"wrote reports/{kind}-{label}.md  (applied {s['applied']}, replies {s['replies']}, "
          f"rate {pct(s['rate'])}, interviews {s['interviews']})")


def rebuild_daily_log(jobs, activity):
    _, old = read_csv("daily-log.csv")
    notes = {r["date"]: r.get("notes", "") for r in old}
    counts = {}

    def bump(d, field):
        if d:
            counts.setdefault(d, {}).setdefault(field, 0)
            counts[d][field] += 1

    for j in jobs:
        bump(j.get("date_found"), "shortlisted")
        bump(j.get("date_applied"), "applied")
    for a in activity:
        field = {"Outreach": "outreach", "Follow-up": "follow_ups", "Reply": "replies",
                 "Interview": "interviews"}.get(a["type"])
        if field:
            bump(a["date"], field)
    rows = []
    for d in sorted(set(counts) | {k for k, v in notes.items() if v}):
        c = counts.get(d, {})
        rows.append({"date": d, **{k: str(c.get(k, 0)) for k in
                     ("shortlisted", "applied", "outreach", "follow_ups", "replies", "interviews")},
                     "notes": notes.get(d, "")})
    write_csv("daily-log.csv", rows)
    print(f"daily-log.csv: {len(rows)} day(s)")


def main():
    profile = load_json("config", "profile.json")
    _, jobs = read_csv("jobs.csv")
    _, activity = read_csv("activity.csv")
    args = sys.argv[1:]
    t = today()
    rebuild_daily_log(jobs, activity)
    kinds = [args[0]] if args else ["week", "month"]
    for kind in kinds:
        if kind == "week":
            if len(args) > 1:
                y, w = map(int, args[1].split("-"))
            else:
                y, w, _ = t.isocalendar()
            start, end = week_range(y, w)
            write_report("week", f"{y}-{w:02d}", start, end, jobs, activity, profile)
        elif kind == "month":
            y, m = map(int, args[1].split("-")) if len(args) > 1 else (t.year, t.month)
            start, end = month_range(y, m)
            write_report("month", f"{y}-{m:02d}", start, end, jobs, activity, profile)
        else:
            sys.exit(f"unknown report type '{kind}' (use week or month)")


if __name__ == "__main__":
    main()
