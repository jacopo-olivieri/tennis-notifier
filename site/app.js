// Court Watch: signing in with Telegram, then the member's watches. The session
// token lives in localStorage for its 30 days; everything else comes from the Edge Function.

const SESSION_KEY = "court-watch-session";
const UNREACHABLE = "Couldn't reach the server. Try again in a minute.";
const S = {
  screen: "loading", state: null, stranger: null, menu: false, busy: false, error: "",
  // Unsaved changes: hours to add and to remove, as {weekday, hour} or {date, hour}.
  added: [], removed: [], form: { kind: "weekly", weekday: 1, date: "", hour: "" }, note: "",
};

const BALL = `<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="14" fill="var(--acc)"/><path d="M5 6.5c5 3 6.5 12 0 17M25 6.5c-5 3-6.5 12 0 17" fill="none" stroke="var(--acc-fg)" stroke-width="1.6" stroke-linecap="round"/></svg>`;
const PLANE = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff" aria-hidden="true"><path d="M21.9 4.3 18.6 19.9c-.2 1.1-.9 1.4-1.8.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1 9.3-8.4c.4-.4-.1-.6-.6-.2L5.9 13.4l-4.9-1.5c-1.1-.3-1.1-1.1.2-1.6L20.5 2.9c.9-.3 1.7.2 1.4 1.4z"/></svg>`;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const handle = u => u.username ? `@${u.username}` : u.first_name;

// ---------- watches ----------

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const pad = h => String(h).padStart(2, "0");
const key = w => w.weekday ? `w${w.weekday}-${w.hour}` : `d${w.date}-${w.hour}`;
const dayLabel = d => new Date(`${d}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).replace(",", "");
const label = w => w.weekday ? `Weekly ${WEEKDAYS[w.weekday - 1]} ${pad(w.hour)}:00` : `${dayLabel(w.date)} ${pad(w.hour)}:00`;
const order = (a, b) => (a.weekday ? 0 : 1) - (b.weekday ? 0 : 1) || (a.weekday ?? 0) - (b.weekday ?? 0)
  || String(a.date ?? "").localeCompare(String(b.date ?? "")) || a.hour - b.hour;
const londonToday = () => new Date().toLocaleDateString("en-CA", { timeZone: "Europe/London" });

// The hours some court runs, from the availability the server sent; a sensible span before the first scan.
function sessionHours() {
  const hours = [...new Set((S.state.availability ?? []).filter(a => a.status !== "no session").map(a => a.hour))];
  return hours.length ? hours.sort((a, b) => a - b) : Array.from({ length: 15 }, (_, i) => i + 7);
}

// The member's watches as they'd be after saving, each flagged if it's a pending addition.
function shownWatches() {
  const removed = new Set(S.removed.map(key));
  return [
    ...S.state.watches.filter(w => !removed.has(key(w))),
    ...S.added.map(w => ({ ...w, unsaved: true })),
  ].sort(order);
}

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

function addWatch() {
  const f = S.form;
  if (f.hour === "" || (f.kind === "single" && !f.date)) return;
  const w = f.kind === "weekly" ? { weekday: Number(f.weekday), hour: Number(f.hour) } : { date: f.date, hour: Number(f.hour) };
  const k = key(w);
  if (S.removed.some(r => key(r) === k)) S.removed = S.removed.filter(r => key(r) !== k);
  else if (!shownWatches().some(x => key(x) === k)) S.added.push(w);
  S.note = "";
  render();
}

function removeWatch(k) {
  if (S.added.some(w => key(w) === k)) S.added = S.added.filter(w => key(w) !== k);
  else S.removed.push(S.state.watches.find(w => key(w) === k));
  S.note = "";
  render();
}

async function saveWatches() {
  S.busy = true;
  render();
  try {
    const res = await api("POST", "/watches", {
      added: S.added,
      removed: S.removed.map(({ weekday, date, hour }) => weekday ? { weekday, hour } : { date, hour }),
    });
    if (res.status === 401) return logOut();
    if (res.status !== 200) return show("member", { error: "That didn't save. Try again.", added: S.added, removed: S.removed });
    show("member", {
      state: res.body.state, added: [], removed: [],
      note: {
        sent: "Saved. What's free now on those hours is in your Telegram.",
        failed: "Saved, but the bot couldn't message you what's free now.",
        none: "Saved. Nothing's free on those hours right now.",
      }[res.body.alert],
    });
  } catch {
    show("member", { error: UNREACHABLE, added: S.added, removed: S.removed });
  }
}

function logOut() {
  session.set(null);
  show("signedout", { added: [], removed: [], note: "" });
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

function watchesCard() {
  const f = S.form;
  const watches = shownWatches();
  const changes = S.added.length + S.removed.length;
  const select = (field, options, value) => `<select data-field="${field}">${options.map(([v, t]) =>
    `<option value="${v}" ${String(v) === String(value) ? "selected" : ""}>${t}</option>`).join("")}</select>`;
  return `<div class="card"><h2>Your watches</h2>
    <p class="sub">You get a Telegram message whenever a court frees up at one of these hours.</p>
    ${watches.length
      ? `<ul class="watches">${watches.map(w => `<li${w.unsaved ? ` class="unsaved"` : ""}><span>${esc(label(w))}${w.unsaved ? ` <em>new</em>` : ""}</span>
          <button class="x" data-act="remove" data-key="${esc(key(w))}" aria-label="Stop watching ${esc(label(w))}">×</button></li>`).join("")}</ul>`
      : `<p class="empty">No watches yet. Add the hours you want to play.</p>`}
    <div class="add">
      ${select("kind", [["weekly", "Every week"], ["single", "One date"]], f.kind)}
      ${f.kind === "weekly"
        ? select("weekday", WEEKDAYS.map((d, i) => [i + 1, d]), f.weekday)
        : `<input type="date" data-field="date" min="${londonToday()}" value="${esc(f.date)}">`}
      ${select("hour", [["", "Hour"], ...sessionHours().map(h => [h, `${pad(h)}:00`])], f.hour)}
      <button class="btn" data-act="add">Add</button>
    </div>
    ${changes ? `<div class="bar"><span>${changes} unsaved change${changes === 1 ? "" : "s"}</span>
      <button class="btn" data-act="discard" ${S.busy ? "disabled" : ""}>Discard</button>
      <button class="btn primary" data-act="save" ${S.busy ? "disabled" : ""}>${S.busy ? "Saving…" : "Save"}</button></div>` : ""}
    ${S.note ? `<p class="note">${esc(S.note)}</p>` : ""}
    ${S.error ? `<p class="error">${esc(S.error)}</p>` : ""}</div>`;
}

function member() {
  const m = S.state.member;
  return `<div class="wrap"><header><div class="brand">${BALL}<div><b>Court Watch</b><span>Lincoln's Inn Fields · 3 courts</span></div></div>
    <div class="menu"><button class="avatar" data-act="menu" aria-label="Account" aria-expanded="${S.menu}">${esc(m.first_name.slice(0, 1).toUpperCase())}</button>
    ${S.menu ? `<div class="menu-pop"><div>${esc(m.first_name)}${m.username ? ` · @${esc(m.username)}` : ""}<br>Alerts go to your Telegram DMs.</div><button data-act="logout">Log out</button></div>` : ""}</div></header>
    ${watchesCard()}
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
  if (act === "add") return addWatch();
  if (act === "remove") return removeWatch(e.target.closest("[data-key]").dataset.key);
  if (act === "discard") { Object.assign(S, { added: [], removed: [], note: "", error: "" }); return render(); }
  if (act === "save") return saveWatches();
  if (S.menu && !e.target.closest(".menu-pop")) { S.menu = false; render(); }
});

// The add form's fields keep their values across renders.
document.addEventListener("change", e => {
  const field = e.target.dataset?.field;
  if (!field) return;
  S.form[field] = e.target.value;
  if (field === "kind") render();
});

load();
