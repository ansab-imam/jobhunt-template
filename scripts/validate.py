"""Check the data files: headers, duplicate ids/URLs, valid statuses, dates and links.

Usage: python scripts/validate.py      -> exit code 0 if OK, 1 if any ERROR
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (ACTIVITY_TYPES, FILES, LOCATION_RULES, PAY_PERIODS, PRIORITIES, STATUSES,
                    TASK_STATUSES, TASK_TYPES, load_json, parse_date, path, read_csv, to_float)

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_enum(file, row_no, field, value, allowed, required=True):
    if not value and not required:
        return
    if value not in allowed:
        err(f"{file} row {row_no}: {field}='{value}' not in {allowed}")


def check_date(file, row_no, field, value, required=False):
    if not value:
        if required:
            err(f"{file} row {row_no}: {field} is empty")
        return
    if parse_date(value) is None:
        err(f"{file} row {row_no}: {field}='{value}' is not YYYY-MM-DD")


def main():
    data = {}
    for name, fields in FILES.items():
        header, rows = read_csv(name)
        if header != fields:
            err(f"{name}: header is\n    {','.join(header)}\n  expected\n    {','.join(fields)}")
        data[name] = rows

    fx = load_json("config", "fx.json").get("usd_per_unit", {})
    load_json("config", "profile.json")  # raises if JSON is broken

    jobs = data["jobs.csv"]
    contact_ids = {c["id"] for c in data["contacts.csv"]}
    job_ids, urls = set(), {}
    for i, j in enumerate(jobs, start=2):
        jid = j.get("id", "")
        if not jid:
            err(f"jobs.csv row {i}: id is empty")
        elif jid in job_ids:
            err(f"jobs.csv row {i}: duplicate id {jid}")
        elif len(jid) != 11 or jid[8] != "-" or not jid.replace("-", "").isdigit():
            warn(f"jobs.csv row {i}: id '{jid}' is not YYYYMMDD-NN")
        job_ids.add(jid)
        url = j.get("job_url", "").strip().rstrip("/").lower()
        if not url:
            warn(f"jobs.csv row {i} ({jid}): job_url is empty")
        elif url in urls:
            err(f"jobs.csv row {i} ({jid}): duplicate job_url (same as {urls[url]})")
        else:
            urls[url] = jid
        for f in ("company", "role"):
            if not j.get(f):
                err(f"jobs.csv row {i} ({jid}): {f} is empty")
        check_enum("jobs.csv", i, "status", j.get("status", ""), STATUSES)
        check_enum("jobs.csv", i, "priority", j.get("priority", ""), PRIORITIES, required=False)
        check_enum("jobs.csv", i, "location_rule", j.get("location_rule", ""), LOCATION_RULES,
                   required=False)
        check_enum("jobs.csv", i, "pay_period", j.get("pay_period", ""), PAY_PERIODS,
                   required=False)
        for f in ("date_found", "date_posted", "date_updated", "date_applied", "last_contact_date", "next_action_date",
                  "last_updated"):
            check_date("jobs.csv", i, f, j.get(f, ""), required=(f == "date_found"))
        if j.get("fit_score") and j["fit_score"] not in ("1", "2", "3", "4", "5"):
            err(f"jobs.csv row {i} ({jid}): fit_score '{j['fit_score']}' must be 1-5")
        for f in ("pay_min", "pay_max", "follow_up_count"):
            if j.get(f) and to_float(j[f]) is None:
                err(f"jobs.csv row {i} ({jid}): {f} '{j[f]}' is not a number")
        cur = j.get("currency", "")
        if cur and cur.upper() not in fx:
            warn(f"jobs.csv row {i} ({jid}): currency {cur} missing from config/fx.json")
        if j.get("status") not in ("Shortlisted", "Approved", "Applying", "Ready", "Skipped") and not j.get("date_applied"):
            warn(f"jobs.csv row {i} ({jid}): status {j.get('status')} but no date_applied")
        if j.get("contact_id") and j["contact_id"] not in contact_ids:
            err(f"jobs.csv row {i} ({jid}): contact_id {j['contact_id']} not in contacts.csv")
        if j.get("location_rule") == "Local-only" and j.get("status") == "Shortlisted":
            warn(f"jobs.csv row {i} ({jid}): Local-only job is Shortlisted (deal-breaker?)")

    task_ids = set()
    for i, t in enumerate(data["tasks.csv"], start=2):
        if t["id"] in task_ids:
            err(f"tasks.csv row {i}: duplicate id {t['id']}")
        task_ids.add(t["id"])
        check_enum("tasks.csv", i, "type", t.get("type", ""), TASK_TYPES)
        check_enum("tasks.csv", i, "status", t.get("status", ""), TASK_STATUSES)
        for f in ("created", "due_date", "done_date"):
            check_date("tasks.csv", i, f, t.get(f, ""))
        if t.get("job_id") and t["job_id"] not in job_ids:
            warn(f"tasks.csv row {i}: job_id {t['job_id']} not in jobs.csv")
        if t.get("status") == "Done" and not t.get("done_date"):
            warn(f"tasks.csv row {i}: Done but no done_date")
        if t.get("draft_file") and not os.path.exists(path(*t["draft_file"].split("/"))):
            warn(f"tasks.csv row {i}: draft_file {t['draft_file']} does not exist")

    seen = set()
    for i, c in enumerate(data["contacts.csv"], start=2):
        if c["id"] in seen:
            err(f"contacts.csv row {i}: duplicate id {c['id']}")
        seen.add(c["id"])
        for f in ("last_contacted", "next_follow_up"):
            check_date("contacts.csv", i, f, c.get(f, ""))

    for i, a in enumerate(data["activity.csv"], start=2):
        check_date("activity.csv", i, "date", a.get("date", ""), required=True)
        check_enum("activity.csv", i, "type", a.get("type", ""), ACTIVITY_TYPES)
        if a.get("job_id") and a["job_id"] not in job_ids:
            warn(f"activity.csv row {i}: job_id {a['job_id']} not in jobs.csv")

    for i, d in enumerate(data["daily-log.csv"], start=2):
        check_date("daily-log.csv", i, "date", d.get("date", ""), required=True)

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s). "
          f"{len(jobs)} jobs, {len(data['tasks.csv'])} tasks, {len(data['contacts.csv'])} contacts.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
