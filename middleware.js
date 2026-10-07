// Vercel Routing Middleware: password-protects the whole site (dashboard AND data files).
// Credentials live only in Vercel environment variables, never in this repo:
//   DASHBOARD_USER      e.g. your email
//   DASHBOARD_PASSWORD  a strong password
// If either variable is missing, the site stays locked (fails closed).

export const config = { matcher: "/:path*" };

function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function unauthorized() {
  return new Response("Login required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Job Search Tracker", charset="UTF-8"',
               "Cache-Control": "no-store" },
  });
}

export default function middleware(request) {
  const user = process.env.DASHBOARD_USER;
  const pass = process.env.DASHBOARD_PASSWORD;
  if (!user || !pass) return unauthorized();

  const header = request.headers.get("authorization") || "";
  if (!header.startsWith("Basic ")) return unauthorized();
  let decoded = "";
  try {
    decoded = new TextDecoder().decode(Uint8Array.from(atob(header.slice(6)), c => c.charCodeAt(0)));
  } catch {
    return unauthorized();
  }
  const sep = decoded.indexOf(":");
  if (sep < 0) return unauthorized();
  const ok = safeEqual(decoded.slice(0, sep).toLowerCase(), user.toLowerCase()) &&
             safeEqual(decoded.slice(sep + 1), pass);
  return ok ? undefined : unauthorized(); // undefined = continue to the requested file
}
