// Invite links and the owner's Members tab: pure helpers, so `deno test` covers them.
// The landing URL carries the raw token as ?invite=, which the site keeps through login.

export function inviteLink(page, token) {
  const url = new URL(page);
  url.search = new URLSearchParams({ invite: token }).toString();
  url.hash = "";
  return url.href;
}

export const inviteToken = page => new URL(page).searchParams.get("invite") || null;

export function withoutInvite(page) {
  const url = new URL(page);
  url.searchParams.delete("invite");
  return url.href;
}

export function memberLine(m) {
  const hours = m.hours === 0 ? "no hours" : `${m.hours} hour${m.hours === 1 ? "" : "s"}`;
  return { name: m.first_name, detail: m.username ? `@${m.username} · ${hours}` : hours };
}
