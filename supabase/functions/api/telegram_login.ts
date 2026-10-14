// Checks a Telegram Login Widget payload: https://core.telegram.org/widgets/login#checking-authorization

export type TelegramUser = { id: number; first_name: string; username?: string };

const MAX_AGE_SECONDS = 24 * 3600;
const CLOCK_SKEW_SECONDS = 60;
const encoder = new TextEncoder();

// The user, if `payload` was signed with `botToken` no more than 24 hours before `now`
// (and not more than a minute after it); otherwise null.
export async function verifyTelegramLogin(
  payload: Record<string, unknown>,
  botToken: string,
  now: Date,
): Promise<TelegramUser | null> {
  const { hash, ...fields } = payload;
  if (typeof hash !== "string" || !/^[0-9a-f]{64}$/.test(hash)) return null;

  // Every field the widget sent, sorted, as key=value lines; keyed by SHA-256 of the bot token.
  const dataCheckString = Object.keys(fields).sort()
    .filter((k) => fields[k] !== undefined && fields[k] !== null)
    .map((k) => `${k}=${fields[k]}`)
    .join("\n");
  const secret = await crypto.subtle.digest("SHA-256", encoder.encode(botToken));
  const key = await crypto.subtle.importKey("raw", secret, { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const signature = Uint8Array.from(hash.match(/../g)!, (h) => parseInt(h, 16));
  if (!await crypto.subtle.verify("HMAC", key, signature, encoder.encode(dataCheckString))) return null;

  const age = now.getTime() / 1000 - Number(fields.auth_date);
  if (!(age >= -CLOCK_SKEW_SECONDS && age <= MAX_AGE_SECONDS)) return null;
  const user: TelegramUser = { id: Number(fields.id), first_name: String(fields.first_name) };
  if (typeof fields.username === "string") user.username = fields.username;
  return user;
}
