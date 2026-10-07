# Resumes

- `generic.pdf`: your original resume (optional).
- Tailored versions: `Company-Role.pdf` (e.g. `Acme-SDR.pdf`). Record the file in the job's `resume_used` column.

Tailoring only reorders or rewords **true** content from the master resume. Nothing invented.

## Building tailored resumes (ATS-friendly)
- `master.json`: every true fact (bullets, skills). Never add anything here that isn't on the real resume or stated by you.
- `tailor.json`: per job id, a headline, summary, bullet order and skills to show first.
- Build: `set NODE_PATH=<path>\jobhunt-tools\node_modules` then `node scripts/build_resume.cjs [job_id]`,
  then `powershell -ExecutionPolicy Bypass -File scripts\docx_to_pdf.ps1` (needs MS Word). Keep each one to 1 page.
- ATS format: one column, no tables, images or text boxes, standard headings, real bullets, Calibri 10pt.
