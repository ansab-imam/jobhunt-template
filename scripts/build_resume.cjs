// Builds ATS-friendly tailored resumes (.docx) from resumes/master.json + resumes/tailor.json.
// ATS rules: one column, no tables/text boxes/images, standard headings, real bullets, plain contact line.
//
//   set NODE_PATH=..\jobhunt-tools\node_modules   (where the "docx" npm package is installed)
//   node scripts/build_resume.cjs            -> builds every entry in tailor.json
//   node scripts/build_resume.cjs 20261006-01
// Then scripts/docx_to_pdf.ps1 makes PDFs with Microsoft Word.
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, AlignmentType, BorderStyle, LevelFormat, TabStopType } = require("docx");

const ROOT = path.join(__dirname, "..");
const master = JSON.parse(fs.readFileSync(path.join(ROOT, "resumes", "master.json"), "utf8"));
const tailor = JSON.parse(fs.readFileSync(path.join(ROOT, "resumes", "tailor.json"), "utf8"));

// Plain, human file name (e.g. "Jane-Doe-Resume") so employers never see a tailored name.
const PERSON = master.name.split(/\s+/).map(w => w[0] + w.slice(1).toLowerCase()).join(" ");
const FILE_BASE = PERSON.replace(/[^A-Za-z0-9]+/g, "-") + "-Resume";
const FONT = "Calibri", BODY = 20; // half-points (10pt)
const RIGHT = 12240 - 2 * 900;     // text width for the right-aligned date tab (Letter, 0.625" margins)

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || BODY, bold: o.bold, italics: o.italics });
const para = (children, o = {}) => new Paragraph({ children, spacing: { after: o.after ?? 40, before: o.before ?? 0 },
  alignment: o.align, tabStops: o.tabs, keepNext: o.keepNext });
const heading = text => new Paragraph({
  children: [run(text.toUpperCase(), { bold: true, size: 23 })],
  spacing: { before: 110, after: 50 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "444444", space: 1 } },
});
const bullet = text => new Paragraph({ children: [run(text)], numbering: { reference: "bullets", level: 0 }, spacing: { after: 20 } });

function build(id, t) {
  const kids = [];
  kids.push(para([run(master.name, { bold: true, size: 36 })], { align: AlignmentType.CENTER, after: 20 }));
  kids.push(para([run(t.headline || master.default_headline, { bold: true, size: 22 })], { align: AlignmentType.CENTER, after: 20 }));
  kids.push(para([run(master.contact)], { align: AlignmentType.CENTER, after: 20 }));
  kids.push(para([run(master.availability, { italics: true })], { align: AlignmentType.CENTER, after: 80 }));

  kids.push(heading("Professional Summary"));
  kids.push(para([run(t.summary)], { after: 60 }));

  kids.push(heading("Professional Experience"));
  for (const job of master.experience) {
    // tailor.skip_companies hides a whole employer (e.g. own agency when applying to a tech/AI company)
    if ((t.skip_companies || []).includes(job.company)) continue;
    kids.push(para([run(job.company, { bold: true }), run(` | ${job.location}`)], { before: 60, after: 10, keepNext: true }));
    for (const role of job.roles) {
      kids.push(para([run(role.title, { bold: true, italics: true }), new TextRun({ children: ["\t"], font: FONT }), run(role.dates)],
        { tabs: [{ type: TabStopType.RIGHT, position: RIGHT }], after: 20, keepNext: true }));
      const order = (t.bullet_order || {})[role.key] || Object.keys(role.bullets);
      for (const k of order) {
        if (!role.bullets[k]) throw new Error(`${id}: unknown bullet ${role.key}.${k}`);
        kids.push(bullet(role.bullets[k]));
      }
    }
  }

  kids.push(heading("Skills"));
  for (const [group, items] of Object.entries(master.skills)) {
    const first = ((t.skills_first || {})[group] || []).filter(s => {
      if (!items.includes(s)) throw new Error(`${id}: skill "${s}" not in master.json`);
      return true;
    });
    const list = [...first, ...items.filter(s => !first.includes(s))].slice(0, group === "Sales" ? 12 : 99);
    kids.push(para([run(group + ": ", { bold: true }), run(list.join(", "))], { after: 40 }));
  }

  kids.push(heading("Education & Certifications"));
  for (const e of master.education) kids.push(para([run(e)], { after: 30 }));

  return new Document({
    creator: PERSON, title: `${PERSON} - Resume`, lastModifiedBy: PERSON,
    styles: { default: { document: { run: { font: FONT, size: BODY } } } },
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 220 } } } }] }] },
    sections: [{ properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 600, bottom: 560, left: 900, right: 900 } } }, children: kids }],
  });
}

(async () => {
  const only = process.argv[2];
  for (const [id, t] of Object.entries(tailor)) {
    if (id.startsWith("_") || (only && id !== only)) continue;
    // One folder per job; the file itself is always named plainly so employers never see a tailored name.
    const dir = path.join(ROOT, "resumes", id); fs.mkdirSync(dir, { recursive: true });
    const out = path.join(dir, `${FILE_BASE}.docx`);
    fs.writeFileSync(out, await Packer.toBuffer(build(id, t)));
    console.log("wrote", path.relative(ROOT, out));
  }
})().catch(e => { console.error(e.message); process.exit(1); });
