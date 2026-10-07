# Onboarding a new user (instructions for Claude)

Run this when the user says "set me up" (or when `resumes/master.json` still has the example name "Jane Doe").

1. **Get the resume.** Ask the user to attach a PDF/DOCX or paste the text. Read all of it. Never invent anything:
   no numbers, tools, dates or titles that aren't in the resume or stated by the user.
2. **Ask a few short questions** (with options) about anything the resume doesn't answer:
   - Target roles (suggest 4–6 based on the resume) and seniority
   - Where: which cities for local jobs (on-site, hybrid or remote?) and/or which countries for international remote jobs
   - Full-time and/or part-time; hours or time zones they can work
   - Minimum pay (amount, currency, per month or year)
   - Deal-breakers (e.g. commission-only, night shifts, relocation)
   - How they want to be presented (their strengths; anything to avoid mentioning to certain employers)
3. **Write the profile files:**
   - `resumes/master.json`: every true fact from the resume (name, contact line, experience with bullet keys, skills, education). Same structure as the example.
   - `config/profile.json`: `me` (name, first_name, email, phone, linkedin, location, availability) and `searches`
     (one entry per local city group and/or one for international remote, with keywords, target_countries, cities, work_mode,
     employment_types, pay_floor, sources, employer_country_rule), plus `deal_breakers`, `excluded_employer_countries`, `daily_goals`, `max_posting_age_days`.
   - `profile.md`: a short readable profile, a **"How to present me"** section, and a **"What I'm searching for"** section.
   - Copy their original resume to `resumes/generic.pdf` if they gave a PDF.
4. **Personal details for forms** (date of birth, notice period, salary expectation...): don't ask for these now.
   Tell the user to fill **👤 My Info** on the dashboard whenever they like. Never store government ID numbers or passwords.
5. Set the repo's git author to the user (GitHub name and `<id>+<username>@users.noreply.github.com`) if they're on Vercel's free plan.
6. Run `python scripts/validate.py`, commit `chore: onboarding for <name>`, push, and redeploy if they set up a deploy hook.
7. Tell the user in 3–4 lines what you set up, and that they can now click **🔎 Pull latest jobs**.
