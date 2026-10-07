// GET /api/file?path=data/jobs.csv  -> latest file content straight from GitHub (no redeploy needed).
// Protected by middleware.js like every other route.
import { gh, readFile, sendJSON } from "./_lib.js";

const ALLOWED = /^(data|drafts|config|shortlists|reports|templates)\/[A-Za-z0-9._\-\/]+$/;
const BINARY = /^resumes\/(\d{8}-\d{2}\/)?[A-Za-z0-9._\-]+\.(pdf|docx)$/;
const TYPES = { pdf: "application/pdf", docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" };

export default async function handler(req, res) {
  const path = String(req.query.path || "");
  if (path.includes("..") || !(ALLOWED.test(path) || BINARY.test(path))) return sendJSON(res, 400, { error: "path not allowed" });
  try {
    if (BINARY.test(path)) {   // resume download, original file name
      const buf = Buffer.from(await (await gh(`/contents/${encodeURI(path)}`, { headers: { Accept: "application/vnd.github.raw" } })).arrayBuffer());
      res.statusCode = 200;
      res.setHeader("Content-Type", TYPES[path.split(".").pop()]);
      const how = req.query.download ? "attachment" : "inline";   // inline = open in the browser's viewer
      res.setHeader("Content-Disposition", `${how}; filename="${path.split("/").pop()}"`);
      res.setHeader("Cache-Control", "no-store");
      return res.end(buf);
    }
    const text = await readFile(path);
    res.statusCode = 200;
    res.setHeader("Content-Type", path.endsWith(".json") ? "application/json; charset=utf-8" : "text/plain; charset=utf-8");
    res.setHeader("Cache-Control", "no-store");
    res.end(text);
  } catch (e) {
    sendJSON(res, e.status === 404 ? 404 : 500, { error: e.message });
  }
}
