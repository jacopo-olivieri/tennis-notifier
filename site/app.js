// Court Watch: signing in with Telegram. The session token lives in localStorage
// for its 30 days; everything else comes from the Edge Function.

const SESSION_KEY = "court-watch-session";
const UNREACHABLE = "Couldn't reach the server. Try again in a minute.";
const S = { screen: "loading", state: null, stranger: null, menu: false, busy: false, error: "" };

const BALL = `<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="14" fill="var(--acc)"/><path d="M5 6.5c5 3 6.5 12 0 17M25 6.5c-5 3-6.5 12 0 17" fill="none" stroke="var(--acc-fg)" stroke-width="1.6" stroke-linecap="round"/></svg>`;
const PLANE = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff" aria-hidden="true"><path d="M21.9 4.3 18.6 19.9c-.2 1.1-.9 1.4-1.8.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1 9.3-8.4c.4-.4-.1-.6-.6-.2L5.9 13.4l-4.9-1.5c-1.1-.3-1.1-1.1.2-1.6L20.5 2.9c.9-.3 1.7.2 1.4 1.4z"/></svg>`;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const handle = u => u.username ? `@${u.username}` : u.first_name;

// localStorage can be missing or throw (private windows); then the session lasts until the tab closes.
let memorySession = null;
const session = {
  get() { try { return localStorage.getItem(SESSION_KEY); } catch { return memorySession; } },
  set(v) { memorySession = v; try { v ? localStorage.setItem(SESSION_KEY, v) : localStorage.removeItem(SESSION_KEY); } catch {} },
};

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = session.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(CONFIG.api + path, { method, headers, body: body && JSON.stringify(body) });
  return { status: res.status, body: await res.json().catch(() => ({})) };
}

// ---------- flows ----------

async function load() {
  if (!session.get()) return show("signedout");
  try {
    const res = await api("GET", "/state");
    if (res.status === 200) return show("member", { state: res.body });
    if (res.status === 401) session.set(null);
    show("signedout", res.status === 401 ? {} : { error: UNREACHABLE });
  } catch {
    show("signedout", { error: UNREACHABLE });
  }
}

function logIn() {
  if (!window.Telegram?.Login) return show("signedout", { error: "Telegram's login didn't load. Reload the page." });
  // The widget's popup. request_access=write is what lets the bot message the member.
  Telegram.Login.auth({ bot_id: CONFIG.botId, request_access: "write", lang: "en" }, async user => {
    if (!user) return;
    show("signedout", { busy: true });
    try {
      const res = await api("POST", "/login", { user });
      if (res.status === 200) {
        session.set(res.body.session);
        return show("member", { state: res.body.state });
      }
      if (res.body.error === "not_member") return show("notinvited", { stranger: user });
      show("signedout", { error: "That login didn't go through. Try again." });
    } catch {
      show("signedout", { error: UNREACHABLE });
    }
  });
}

function logOut() {
  session.set(null);
  show("signedout");
}

function show(screen, extra = {}) {
  Object.assign(S, { screen, menu: false, busy: false, error: "" }, extra);
  render();
}

// ---------- views ----------

function gate() {
  const [title, text, button, fine] = {
    signedout: [`Court Watch`, `A Telegram message whenever a Lincoln's Inn Fields court you want frees up.`, true, `Invite-only. Logging in lets the bot message you.`],
    notinvited: [`This one's invite-only`, `You're logged in as ${esc(S.stranger && handle(S.stranger))}, but you're not in the group. Ask Jacopo for an invite link.`, false, ``],
  }[S.screen];
  return `<div class="wrap gate"><div class="card">${BALL}<h1>${title}</h1><p>${text}</p>
    ${button
      ? `<button class="tgbtn" data-act="login" ${S.busy ? "disabled" : ""}>${PLANE} ${S.busy ? "Logging in…" : "Log in with Telegram"}</button>`
      : `<button class="btn" data-act="logout">Use a different account</button>`}
    ${fine ? `<p class="fine">${fine}</p>` : ""}
    ${S.error ? `<p class="error">${esc(S.error)}</p>` : ""}</div></div>`;
}

function member() {
  const m = S.state.member;
  return `<div class="wrap"><header><div class="brand">${BALL}<div><b>Court Watch</b><span>Lincoln's Inn Fields · 3 courts</span></div></div>
    <div class="menu"><button class="avatar" data-act="menu" aria-label="Account" aria-expanded="${S.menu}">${esc(m.first_name.slice(0, 1).toUpperCase())}</button>
    ${S.menu ? `<div class="menu-pop"><div>${esc(m.first_name)}${m.username ? ` · @${esc(m.username)}` : ""}<br>Alerts go to your Telegram DMs.</div><button data-act="logout">Log out</button></div>` : ""}</div></header>
    <div class="card"><h2>You're in, ${esc(m.first_name)}</h2><p class="sub">Picking the hours you want to play is coming next.</p></div>
    <footer>Booking stays on Camden Active.</footer></div>`;
}

function render() {
  const app = document.getElementById("app");
  app.innerHTML = S.screen === "loading" ? "" : S.screen === "member" ? member() : gate();
}

document.addEventListener("click", e => {
  const act = e.target.closest("[data-act]")?.dataset.act;
  if (act === "login") return logIn();
  if (act === "logout") return logOut();
  if (act === "menu") { S.menu = !S.menu; return render(); }
  if (S.menu && !e.target.closest(".menu-pop")) { S.menu = false; render(); }
});

load();
