"""Build a clean, shareable copy of this app (code + docs, NO personal data).

    python scripts/make_template.py <output-folder> [--forbid "word1,word2,..."]

- Copies every git-tracked file, except personal ones, which are replaced with empty or example versions.
- Then scans the output for forbidden words (your name, email, phone, employers...) and fails if any are found.
  The forbidden list is built from config/profile.json + resumes/master.json, plus anything passed via --forbid.
The output folder must not exist yet. Push it as a NEW repo (fresh history), never as a fork of this one.
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_HEADERS = ["data/jobs.csv", "data/tasks.csv", "data/contacts.csv", "data/activity.csv", "data/daily-log.csv",
                "data/questions.csv", "data/answer-bank.csv", "data/requests.csv", "data/seen-jobs.csv"]
DROP_PREFIXES = ("drafts/2", "shortlists/2", "reports/week-", "reports/month-", "resumes/2")
DROP_FILES = {"resumes/generic.pdf"}

EXAMPLE_PROFILE = {
    "me": {"name": "Jane Doe", "first_name": "Jane", "headline": "Your headline",
           "location": "City, Country", "email": "you@example.com", "phone": "+00 000 0000000",
           "linkedin": "linkedin.com/in/yourname", "availability": "Your working hours / time zones"},
    "searches": [
        {"name": "Local (example)", "active": True, "priority": 1, "keywords": ["Your target role"],
         "target_countries": ["XX"], "cities": ["Your City"], "work_mode": ["On-site", "Hybrid", "Remote"],
         "employment_types": ["Full-time", "Part-time"], "pay_floor": {"amount": 0, "currency": "USD", "period": "month"},
         "employer_country_rule": "Any", "sources": ["LinkedIn (public job pages)", "national job boards"]},
        {"name": "International remote (example)", "active": True, "priority": 2, "keywords": ["Your target role"],
         "target_countries": ["US", "CA", "UK"], "work_mode": ["Remote"], "employment_types": ["Full-time", "Contract"],
         "pay_floor": {"amount": 0, "currency": "USD", "period": "month"}},
    ],
    "deal_breakers": ["Commission-only", "Pay to apply"],
    "excluded_employer_countries": {"_note": "ISO codes of employer countries to skip for remote searches", "codes": []},
    "my_timezone": "UTC", "daily_goals": {"applications": 10, "outreach_messages": 5},
    "follow_up_days": [6, 14], "ghost_after_days": 30, "max_posting_age_days": 10,
    "hourly_hours_per_month": 173, "hourly_hours_per_month_part_time": 87,
}
EXAMPLE_MASTER = {
    "_note": "Single source of truth for every resume. Claude fills this from YOUR resume during onboarding (ONBOARDING.md).",
    "name": "JANE DOE", "contact": "City, Country | +00 000 0000000 | you@example.com | linkedin.com/in/yourname",
    "availability": "Your working hours", "default_headline": "Your Title | Key Skills",
    "experience": [{"company": "Example Company", "location": "City", "roles": [
        {"key": "example_role", "title": "Your Title", "dates": "Jan 2024 - Present",
         "bullets": {"one": "What you did, in plain words.", "two": "A real result (only if true)."}}]}],
    "skills": {"Core": ["Skill one", "Skill two"], "Tools & Platforms": ["Tool one"]},
    "education": ["Degree - University, Years"],
}
EXAMPLE_PROFILE_MD = """# My profile

Claude fills this in during onboarding (see ONBOARDING.md). Keep it short and true.

## About me
- Location, availability, languages.

## How to present me (Claude follows this for resumes, cover notes and form answers)
- Your strengths and how you want to come across.
- Anything to leave out for certain kinds of employers.
- Forms that ban AI-written answers: draft them and remind me to rewrite in my own words (or: leave them blank).

## What I'm searching for
- Roles, cities/countries, on-site/remote, full/part-time, minimum pay, deal-breakers.
"""


def forbidden_words(extra):
    words = set(w.strip() for w in extra if w.strip())
    try:
        me = json.load(open(os.path.join(ROOT, "config/profile.json"), encoding="utf-8")).get("me", {})
        words |= {me.get("email", ""), me.get("phone", "").split("(")[0].strip(), me.get("linkedin", "")}
        words |= set(me.get("name", "").split())
    except Exception:
        pass
    try:
        m = json.load(open(os.path.join(ROOT, "resumes/master.json"), encoding="utf-8"))
        words |= set(m.get("name", "").title().split())
        for job in m.get("experience", []):
            words.add(job["company"].split("(")[0].strip())
    except Exception:
        pass
    words |= {w.split()[0] for w in list(words) if " " in w}   # "Acme Holdings" -> also "Acme"
    return sorted(w for w in words if len(w) >= 4)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    extra = sys.argv[sys.argv.index("--forbid") + 1].split(",") if "--forbid" in sys.argv else []
    if os.path.exists(out):
        sys.exit(f"{out} already exists - choose a new folder")
    files = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    for f in files:
        if f in DROP_FILES or f.startswith(DROP_PREFIXES):
            continue
        dst = os.path.join(out, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src = os.path.join(ROOT, f)
        if f in DATA_HEADERS:
            with open(src, encoding="utf-8") as fh:
                open(dst, "w", encoding="utf-8", newline="\n").write(fh.readline())
        elif f == "config/profile.json":
            json.dump(EXAMPLE_PROFILE, open(dst, "w", encoding="utf-8", newline="\n"), indent=2)
        elif f == "resumes/master.json":
            json.dump(EXAMPLE_MASTER, open(dst, "w", encoding="utf-8", newline="\n"), indent=2)
        elif f == "resumes/tailor.json":
            json.dump({"_note": "Per-job tailoring, keyed by job id. Claude fills this in."}, open(dst, "w", encoding="utf-8"), indent=2)
        elif f == "profile.md":
            open(dst, "w", encoding="utf-8", newline="\n").write(EXAMPLE_PROFILE_MD)
        else:
            shutil.copy2(src, dst)

    bad = []
    words = forbidden_words(extra)
    pattern = re.compile("|".join(re.escape(w) for w in words), re.I) if words else None
    for dirpath, _, names in os.walk(out):
        for n in names:
            p = os.path.join(dirpath, n)
            try:
                text = open(p, encoding="utf-8").read()
            except UnicodeDecodeError:
                bad.append(f"{os.path.relpath(p, out)}: binary file (remove or check by hand)")
                continue
            if pattern:
                for i, line in enumerate(text.splitlines(), 1):
                    hit = pattern.search(line)
                    if hit:
                        bad.append(f"{os.path.relpath(p, out)}:{i}: '{hit.group(0)}'")
    print(f"Template written to {out} ({sum(len(f) for _, _, f in os.walk(out))} files). Checked for: {', '.join(words)}")
    if bad:
        print("\nPERSONAL INFO FOUND - do NOT share until fixed:")
        print("\n".join("  " + b for b in bad))
        sys.exit(1)
    print("Clean: no personal info found.")


if __name__ == "__main__":
    main()
