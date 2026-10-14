// The site's whole API: thin wiring from HTTP to the SQL functions, which hold the logic.
// Deployed with JWT verification off (scripts/sign_in.sh): the site sends its own
// session token as "Authorization: Bearer <token>", never a Supabase key.

import { createClient } from "npm:@supabase/supabase-js@2";
import { sessionToken } from "./session_token.ts";
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

// GET /state → the member's state, or 401 once the session has expired or they've been removed.
async function state(req: Request): Promise<Response> {
  const token = req.headers.get("Authorization")?.replace(/^Bearer /, "") ?? "";
  const memberId = await sessionToken.verify(token, SESSION_SECRET, new Date());
  const result = memberId === null ? null : await rpc("member_state", { member_id: memberId });
  return result ? json(result) : json({ error: "signed_out" }, 401);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  // Supabase serves this at /functions/v1/api/<route>, and passes /api/<route> through.
  const route = `${req.method} ${new URL(req.url).pathname.replace(/^.*?\/api(?=\/|$)/, "")}`;
  try {
    if (route === "POST /login") return await login(req);
    if (route === "GET /state") return await state(req);
    return json({ error: "not_found" }, 404);
  } catch (e) {
    console.error(e);
    return json({ error: "server_error" }, 500);
  }
});
