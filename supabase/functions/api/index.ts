// The site's whole API: thin wiring from HTTP to the SQL functions, which hold the logic.
// Deployed with JWT verification off (scripts/sign_in.sh): the site sends its own
// session token as "Authorization: Bearer <token>", never a Supabase key.

import { createClient } from "npm:@supabase/supabase-js@2";
import { sessionToken } from "./session_token.ts";
import { sendMessage } from "./telegram.ts";
import { verifyTelegramLogin } from "./telegram_login.ts";

const BOT_TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const SESSION_SECRET = Deno.env.get("SESSION_SECRET")!;
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false },
});

// The session travels in a header, not a cookie, so any origin may call.
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}

async function rpc(fn: string, args: Record<string, unknown>): Promise<unknown> {
  const { data, error } = await db.rpc(fn, args);
  if (error) throw new Error(`${fn}: ${error.message}`);
  return data;
}

// POST /login {user: <widget payload>, invite?: <raw token>}
// → {session, state} | {error: "not_member"} | 401 {error: "bad_login"}
async function login(req: Request): Promise<Response> {
  const body = await req.json().catch(() => null);
  const user = body?.user && typeof body.user === "object"
    ? await verifyTelegramLogin(body.user, BOT_TOKEN, new Date())
    : null;
  if (!user) return json({ error: "bad_login" }, 401);

  const result = await rpc("login", { telegram_user: user, invite_token: body.invite ?? null }) as {
    status: string;
    member_id?: number;
  };
  if (result.status !== "member") return json({ error: result.status }, 403);
  return json({
    session: await sessionToken.sign(result.member_id!, SESSION_SECRET, new Date()),
    state: await rpc("member_state", { member_id: result.member_id }),
  });
}

// The signed-in member's id, or null for a missing, forged or expired session.
function signedIn(req: Request): Promise<number | null> {
  const token = req.headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
  return sessionToken.verify(token, SESSION_SECRET, new Date());
}

// GET /state → the member's state, or 401 once the session has expired or they've been removed.
async function state(req: Request): Promise<Response> {
  const memberId = await signedIn(req);
  const result = memberId === null ? null : await rpc("member_state", { member_id: memberId });
  return result ? json(result) : json({ error: "signed_out" }, 401);
}

// POST /watches {added: [...], removed: [...]}, each hour {weekday, hour} or {date, hour}
// → {alert: "sent" | "failed" | "none", state}. The new-watch message goes out before
// the reply, and its outcome is reported like the poller's sends.
async function saveWatches(req: Request): Promise<Response> {
  const memberId = await signedIn(req);
  if (memberId === null || !await rpc("member_state", { member_id: memberId })) {
    return json({ error: "signed_out" }, 401);
  }
  const body = await req.json().catch(() => null);
  if (!Array.isArray(body?.added) || !Array.isArray(body?.removed)) return json({ error: "bad_request" }, 400);

  const saved = await db.rpc("save_watches", { member_id: memberId, added: body.added, removed: body.removed });
  // Data exceptions (22…) and constraint violations (23…): an hour that isn't one, e.g. weekday 8.
  if (/^2[23]/.test(saved.error?.code ?? "")) return json({ error: "bad_request" }, 400);
  if (saved.error) throw new Error(`save_watches: ${saved.error.message}`);
  const message = saved.data as { chat_id: number; text: string; alert_ids: number[] } | null;
  let alert = "none";
  if (message) {
    const { status, error } = await sendMessage(BOT_TOKEN, message.chat_id, message.text);
    if (status === 200) {
      await rpc("mark_sent", { alert_ids: message.alert_ids });
      alert = "sent";
    } else {
      await rpc("mark_failed", { alert_ids: message.alert_ids, http_status: status, error });
      alert = "failed";
    }
  }
  return json({ alert, state: await rpc("member_state", { member_id: memberId }) });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  // Supabase serves this at /functions/v1/api/<route>, and passes /api/<route> through.
  const route = `${req.method} ${new URL(req.url).pathname.replace(/^.*?\/api(?=\/|$)/, "")}`;
  try {
    if (route === "POST /login") return await login(req);
    if (route === "GET /state") return await state(req);
    if (route === "POST /watches") return await saveWatches(req);
    return json({ error: "not_found" }, 404);
  } catch (e) {
    console.error(e);
    return json({ error: "server_error" }, 500);
  }
});
