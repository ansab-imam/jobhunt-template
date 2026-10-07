# How the job hunt works (you + Claude)

This is the process Claude follows. It overrides anything else in the README.
**Everything personal** (who you are, how to present you, what to search for) lives in
`profile.md`, `config/profile.json`, `resumes/master.json` and the dashboard's **My Info**.
Claude reads those files first, every session.

## The loop
| Step | Who | Where |
|---|---|---|
| 1. **Find jobs**: when you click **🔎 Pull latest jobs** (or ask in chat). Only serious, verified jobs, following `SEARCH.md`. | Claude | → **① Review** |
| 2. **Review**: read each job card (fit, company size and locations, posted date, red flags), then **✓ Approve** or **✗ Skip**. Links you paste also land here, and Claude reviews them. | You | ① Review |
| 3. **Prepare**: for each approved job, a tailored resume (true facts only), a cover note and the form questions. | Claude | → **② Applying** |
| 4. **Apply**: on **② Applying**, questions are pre-filled. You edit and approve each one, then click **Send to Ready**. Claude fills the form and submits after you say "submit" in chat. | both | ③ Applying |
| 5. **Follow up**: follow-up drafts at 6 and 14 days (red ⏰ on the card). Suggests "Lost" after 30 days. | Claude drafts, you send | Dashboard |
| 6. **Replies and interviews**: tell Claude or paste the message. Claude updates the status, preps you, and drafts replies. | both | chat → Dashboard |

Everything lives on the dashboard. The only thing Claude asks in chat is the final **"submit"**.

## Rules Claude always follows
- Never log in to your personal accounts, never create accounts, never solve CAPTCHAs, never type government ID numbers. You do those yourself.
- **Never invent facts**: no made-up numbers, tools, dates or titles. Use [brackets] for details Claude doesn't know.
- Never send messages or submit applications without your "submit" in chat.
- If unsure whether a job, company or reply is real, ask.
- `git pull` before every change, because the dashboard saves to the same repo.
- Resumes are always named plainly (`First-Last-Resume.pdf`), with no company names in the file or its hidden properties.
- Position you exactly as described in `profile.md` → "How to present me".

## Apply order
1. You click **✓ Approve** on ① Review, and the job moves to ② Applying.
2. Claude **reads** the application form without typing anything. Every question it can't answer from the resume or My Info goes on the Applying tab, pre-filled with a draft.
3. You edit and approve each answer, then click **Send to Ready**.
4. Claude opens the form fresh, fills everything in one go, and submits after you say "submit" in chat.
Sites that need a login, show a CAPTCHA or ask for government ID are left to you, with everything prepared.

## Applying tab rules (for Claude)
- Every question Claude can't answer goes in `data/questions.csv`. **Never leave an answer empty**: write a draft from true facts (status `Draft`), with [brackets] for unknown details.
- Reusable facts get a `key` (date_of_birth, nationality, notice_period, salary_expectation, ...). Approved answers are saved to
  `data/answer-bank.csv` (the **My Info** page). **Check the bank first** and pre-fill from it.
- The job moves to `Ready` only when every answer is approved and you click **Send to Ready**.
- If a form bans AI-written answers, follow what `profile.md` says about that (default: draft it, and add a note to rewrite it in your own words).

## Company info on every job
Every job card shows `company_url` (the company's own website, checked to load), `company_size`, `company_hq`,
`company_locations` and `foreign_presence`, all from public sources. If something can't be found, it says "Unknown".

## Quick commands (just say them in chat)
- "pull jobs now" / "applied to X" / "reply from X: <paste>" / "interview with X on <date>"
- "skip X because …" / "find more like X" / "change filter: …" / "submit"
