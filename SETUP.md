# Set up your own Job Hunt dashboard

A private job-search dashboard plus an AI assistant (Claude) that finds jobs for **your** profile, tailors your
resume and helps you apply. Your copy is completely separate: your own GitHub repo, your own website, your own login.
Nobody else sees your data.

**What you need:** a GitHub account, a free Vercel account, and the Claude desktop app (with Claude Code) on your computer.
Everything else is free.

## 1. Make your own copy (5 min)
1. On the template repo's GitHub page, click **Use this template → Create a new repository**.
   Name it `jobhunt` and set it to **Private**. This is important, because your resume and job data will live here.
2. On your computer, clone it into a folder of your choice (for example `C:\Users\<you>\JobHunt`).

## 2. Put the dashboard online with a login (10 min)
1. **vercel.com → Add New → Project →** import your `jobhunt` repo. Framework preset: **Other**. Leave build settings empty. Deploy.
2. **GitHub → Settings → Developer settings → Fine-grained tokens → Generate new token.**
   Repository access: **only your jobhunt repo**. Permissions: **Contents: Read and write**. Copy the token.
3. **Vercel → your project → Settings → Environment Variables** (Production):
   | Name | Value |
   |---|---|
   | `DASHBOARD_USER` | your email (your login name) |
   | `DASHBOARD_PASSWORD` | a strong password, 12+ characters, not used anywhere else |
   | `GITHUB_TOKEN` | the token from step 2 |
   | `GITHUB_REPO` | `your-github-username/jobhunt` |
4. **Deployments → ⋯ → Redeploy.** Open your `*.vercel.app/dashboard/` link and log in.
5. *(Optional)* **Settings → Git → Deploy Hooks:** create one for branch `main`. Save the URL in a file named `.vercel-deploy-hook`,
   **next to** (outside) your repo folder. Claude uses it to redeploy after code changes. Never commit it.

> Free Vercel plans only build commits made by the account owner. Tell Claude your GitHub name and noreply email,
> and Claude will commit as you (with a "Co-Authored-By: Claude" line).

## 3. Let Claude set you up (10 min)
Open the Claude desktop app → **Code** → choose your `jobhunt` folder, then say:

> **Set me up. My resume is attached.** (attach your PDF or paste the text)

Claude follows `ONBOARDING.md`. It reads your resume, asks you a few short questions (target roles, cities or countries,
remote or on-site, minimum pay, deal-breakers), and fills in your profile. It never invents anything about you.

## 4. Use it
- On the dashboard, click **🔎 Pull latest jobs**, then review the jobs in **① Review**: Keep or Skip.
- **② To apply** shows your tailored resume and cover note. Click **🤖 Apply for me**.
- **③ Applying**: edit and approve the drafted answers, then click **Send to Ready**. Claude submits after you say "submit" in chat.
- **👤 My Info** holds the answers forms keep asking for (notice period, salary expectation...). **⬇️ Export** saves a backup.
- Optional: ask Claude to "check the dashboard every 30 minutes" so button clicks are picked up automatically while the app is open.

Read `WORKFLOW.md` for the full process and `SEARCH.md` for how jobs are found.
