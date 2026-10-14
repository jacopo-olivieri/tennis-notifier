// The site's session: "<member_id>.<expires, unix seconds>.<HMAC-SHA256, base64url>",
// signed with the Edge Function's own session secret.

const LIFETIME_SECONDS = 30 * 24 * 3600;
const encoder = new TextEncoder();

function key(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, [
    "sign",
    "verify",
  ]);
}

function base64url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64url(text: string): Uint8Array<ArrayBuffer> | null {
  if (!/^[A-Za-z0-9_-]+$/.test(text)) return null;
  try {
    return Uint8Array.from(atob(text.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
  } catch {
    return null;
  }
}

// A token for `memberId`, valid for 30 days from `now`.
async function sign(memberId: number, secret: string, now: Date): Promise<string> {
  const body = `${memberId}.${Math.floor(now.getTime() / 1000) + LIFETIME_SECONDS}`;
  return `${body}.${base64url(await crypto.subtle.sign("HMAC", await key(secret), encoder.encode(body)))}`;
}

// The member the token was signed for, or null if it's forged, tampered with or expired at `now`.
async function verify(token: string, secret: string, now: Date): Promise<number | null> {
  const match = /^([1-9][0-9]*)\.([0-9]+)\.([^.]+)$/.exec(token);
  if (!match) return null;
  const [, memberId, expires, signature] = match;
  const bytes = fromBase64url(signature);
  if (!bytes) return null;
  if (!await crypto.subtle.verify("HMAC", await key(secret), bytes, encoder.encode(`${memberId}.${expires}`))) {
    return null;
  }
  if (now.getTime() / 1000 >= Number(expires)) return null;
  return Number(memberId);
}

export const sessionToken = { sign, verify };
