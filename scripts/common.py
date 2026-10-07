"""Shared helpers for the job tracker scripts. Standard library only."""
import csv
import json
import os
import re
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

JOB_FIELDS = ["id", "date_found", "date_posted", "date_updated", "company", "company_url", "company_size", "company_hq", "company_locations", "foreign_presence", "role", "role_category", "job_url", "source",
              "country", "location_rule", "work_mode", "employment_type", "hours_timezone",
              "pay_min", "pay_max", "currency", "pay_period", "pay_usd_month_est",
              "fit_score", "priority", "status", "date_applied", "resume_used", "contact_id",
              "last_contact_date", "next_action", "next_action_date", "follow_up_count",
              "last_updated", "notes"]
TASK_FIELDS = ["id", "created", "due_date", "type", "job_id", "contact_id", "title",
               "details", "draft_file", "status", "done_date"]
CONTACT_FIELDS = ["id", "name", "title", "company", "email", "linkedin_url", "phone",
                  "related_job_ids", "last_contacted", "next_follow_up", "notes"]
ACTIVITY_FIELDS = ["date", "type", "job_id", "contact_id", "channel", "summary", "task_id"]
QUESTION_FIELDS = ["id", "job_id", "question", "kind", "options", "required", "answer", "status",
                   "asked", "answered", "notes", "key"]
# Open = needs the user; Draft = Claude's suggestion; Answered = edited, not approved; Approved; Used = typed into the form
QUESTION_STATUSES = ["Open", "Draft", "Answered", "Approved", "Used"]
SEEN_FIELDS = ["job_url", "company", "role", "first_seen", "job_id"]
REQUEST_FIELDS = ["id", "requested_at", "type", "status", "done_at", "result"]
BANK_FIELDS = ["key", "label", "answer", "source_qid", "updated"]
DAILY_FIELDS = ["date", "shortlisted", "applied", "outreach", "follow_ups", "replies",
                "interviews", "notes"]

STATUSES = ["Shortlisted", "Approved", "Applying", "Ready", "Applied", "Screening", "Interview", "Offer", "Accepted",
            "Rejected", "Ghosted", "Withdrawn", "Skipped", "On-hold"]
CLOSED_STATUSES = {"Accepted", "Rejected", "Ghosted", "Withdrawn", "Skipped"}
REPLY_STATUSES = {"Screening", "Interview", "Offer", "Accepted"}
LOCATION_RULES = ["Worldwide", "Country-OK", "Region-OK", "Unclear", "Local-only"]
PRIORITIES = ["High", "Medium", "Low"]
TASK_TYPES = ["Apply", "Follow-up", "Reply", "Interview-prep", "Interview", "Thank-you",
              "Outreach", "Custom"]
TASK_STATUSES = ["Open", "Done", "Snoozed", "Cancelled"]
ACTIVITY_TYPES = ["Shortlisted", "Applied", "Outreach", "Follow-up", "Reply", "Interview",
                  "Offer", "Rejected", "Status-change", "Note"]
PAY_PERIODS = ["hour", "day", "week", "month", "year"]

FILES = {
    "jobs.csv": JOB_FIELDS,
    "tasks.csv": TASK_FIELDS,
    "contacts.csv": CONTACT_FIELDS,
    "activity.csv": ACTIVITY_FIELDS,
    "daily-log.csv": DAILY_FIELDS,
    "questions.csv": QUESTION_FIELDS,
    "answer-bank.csv": BANK_FIELDS,
    "requests.csv": REQUEST_FIELDS,
    "seen-jobs.csv": SEEN_FIELDS,
}


def path(*parts):
    return os.path.join(ROOT, *parts)


def read_csv(name):
    """Return (header, rows) for data/<name>. Rows are dicts of strings."""
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return list(FILES[name]), []
    with open(p, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [{k: (v or "").strip() for k, v in r.items() if k is not None} for r in reader]
        return list(reader.fieldnames or FILES[name]), rows


def write_csv(name, rows, fields=None):
    fields = fields or FILES[name]
    p = os.path.join(DATA, name)
    tmp = p + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(tmp, p)


def load_json(*parts):
    with open(path(*parts), encoding="utf-8-sig") as f:
        return json.load(f)


def today():
    """Today's date; override with env JOBTRACKER_TODAY=YYYY-MM-DD for testing."""
    forced = os.environ.get("JOBTRACKER_TODAY")
    return parse_date(forced) if forced else date.today()


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def iso(d):
    return d.isoformat() if d else ""


def to_float(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def usd_month_estimate(job, fx, hours_per_month=173):
    """Conservative monthly USD estimate: uses pay_min (or pay_max if min is empty)."""
    amount = to_float(job.get("pay_min")) or to_float(job.get("pay_max"))
    if amount is None:
        return ""
    rate = fx.get("usd_per_unit", {}).get((job.get("currency") or "USD").upper())
    if rate is None:
        return ""
    per_month = {"hour": hours_per_month, "day": 21.7, "week": 4.33, "month": 1,
                 "year": 1 / 12}.get((job.get("pay_period") or "month").lower())
    if per_month is None:
        return ""
    return str(int(round(amount * rate * per_month)))


def fill(template_text, values):
    """Replace {placeholders}; unknown ones are left visible so a human notices them."""
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), template_text)


def next_id(existing_ids, prefix, width=4):
    nums = [int(i[len(prefix):]) for i in existing_ids
            if i.startswith(prefix) and i[len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"


def job_key(company, role):
    """Normalised company+role, used to spot the same job reposted under a new link."""
    norm = lambda t: re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()
    return norm(company) + "|" + norm(role)


def days_between(a, b):
    return (b - a).days if a and b else None


__all__ = [n for n in dir() if not n.startswith("_")] + ["timedelta"]
