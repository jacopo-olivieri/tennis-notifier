// Court Watch: signing in with Telegram, then the member's watched hours: a week grid for
// weekly ones and a calendar for single dates. The session token lives in localStorage for
// its 30 days; everything else comes from the Edge Function. What the grid, calendar and
// panel show is worked out in watches.js.

import {
  WEEKDAYS, byDateHour, calendar, changes, dayHours, dayLabel, gridHours, hh, keyOf, londonNow, opensOn, upcoming,
  watchLines, weekCell,
} from "./watches.js";

const SESSION_KEY = "court-watch-session";
const UNREACHABLE = "Couldn't reach the server. Try again in a minute.";
const WEEKDAY_PLURALS = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"];
const S = {
  screen: "loading", state: null, stranger: null, menu: false, busy: false, error: "", note: "",
  // The member's hours as saved and as they'd be after saving, as watch keys (watches.js).
  saved: new Set(), draft: new Set(),
  focus: null, // the grid cell whose detail shows: {weekday, hour}
  tab: "weekly", date: null, // the Single dates tab's chosen day
};

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
    if (res.status === 200) return showMember(res.body);
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
        return showMember(res.body.state);
      }
      if (res.body.error === "not_member") return show("notinvited", { stranger: user });
      show("signedout", { error: "That login didn't go through. Try again." });
    } catch {
      show("signedout", { error: UNREACHABLE });
    }
  });
}

// A fresh state from the server replaces the member's saved and draft hours. Single-date
// hours that have started are left out until housekeeping deletes them.
function showMember(state, extra = {}) {
  const saved = new Set(upcoming(state.watches.map(keyOf), londonNow()));
  show("member", { state, saved, draft: new Set(saved), ...extra });
}

function toggleDated(date, hour) {
  const k = keyOf({ date, hour });
  S.draft.has(k) ? S.draft.delete(k) : S.draft.add(k);
  Object.assign(S, { note: "", error: "" });
}

function toggle(weekday, hour, on) {
  const k = keyOf({ weekday, hour });
  (on ?? !S.draft.has(k)) ? S.draft.add(k) : S.draft.delete(k);
  Object.assign(S, { focus: { weekday, hour }, note: "", error: "" });
}

let noteShown = 0; // which save's note is up, so an older timer doesn't clear a newer one
async function saveWatches() {
  S.busy = true;
  render();
  try {
    const batch = changes(S.saved, S.draft);
    const res = await api("POST", "/watches", batch);
    if (res.status === 401) return logOut();
    if (res.status !== 200) return show("member", { error: "That didn't save. Try again." });
    showMember(res.body.state, {
      focus: S.focus, date: S.date,
      note: !batch.added.length ? "Saved." : {
        sent: "Saved. What's free now on those hours is in your Telegram.",
        failed: "Saved, but the bot couldn't message you what's free now.",
        none: "Saved. Nothing's free on those hours right now.",
      }[res.body.alert],
    });
    const shown = ++noteShown;
    setTimeout(() => { if (shown === noteShown && S.note) { S.note = ""; render(); } }, 4000);
  } catch {
    show("member", { error: UNREACHABLE });
  }
}

function logOut() {
  session.set(null);
  show("signedout", { state: null, saved: new Set(), draft: new Set(), focus: null, tab: "weekly", date: null, note: "" });
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

// Worked out once per render; hovering reuses it to redraw only the detail.
let view = null;
function grid() {
  const { availability: avail, window_end: windowEnd } = S.state;
  const now = londonNow();
  const index = byDateHour(avail);
  const hours = gridHours(avail, S.draft), cells = new Map();
  for (const hour of hours)
    for (let weekday = 1; weekday <= 7; weekday++) cells.set(`${weekday}|${hour}`, weekCell(avail, weekday, hour, now, windowEnd, index));
  return { hours, cells };
}

function weeklyCard() {
  const dot = w => `<i class="dot ${w.status === "free" ? "f" : w.status === "booked" ? "" : "n"}"></i>`;
  const cells = view.hours.map(hour => `<div class="th">${hh(hour)}</div>` + WEEKDAYS.map((_, i) => {
    const weekday = i + 1, cell = view.cells.get(`${weekday}|${hour}`), on = S.draft.has(keyOf({ weekday, hour }));
    const focus = S.focus?.weekday === weekday && S.focus?.hour === hour;
    return `<button class="cell ${on ? "on" : ""} ${cell.dashed ? "dim" : ""} ${focus ? "focus" : ""}" data-weekday="${weekday}" data-hour="${hour}"
      aria-pressed="${on}" aria-label="${WEEKDAY_PLURALS[i]} ${hh(hour)}">${cell.dashed ? "" : cell.weeks.map(dot).join("")}</button>`;
  }).join("")).join("");
  return `<div class="card"><h2>Weekly</h2><p class="sub">Click the hours you want to play (weekly).</p>
    <div class="legend"><span><i class="sq" style="background:var(--acc)"></i>Watching</span><span><i style="background:var(--acc)"></i>Free that week</span><span><i style="background:var(--booked)"></i>Booked</span><span><i class="hollow"></i>No session or not open yet</span><span><i class="sq" style="border:1px dashed var(--line)"></i>No court that hour</span></div>
    <div class="grid"><div></div>${WEEKDAYS.map(d => `<div class="dh">${d}</div>`).join("")}${cells}</div>
    <p class="small muted" style="margin:12px 0 0">Each dot is one of the next 5 weeks, left to right.</p>
    <div class="narrow" id="detail-narrow">${detailCard(true)}</div></div>`;
}

// The next five dates behind a cell. On a phone it sits under the grid; wider, beside it.
function detailCard(inline) {
  const cls = inline ? "" : "card wide";
  if (!S.focus) return inline ? "" : `<div class="${cls}"><h2>Next five weeks</h2><p class="sub" style="margin:0">Tap or hover an hour to see each week's courts.</p></div>`;
  const { weekday, hour } = S.focus, on = S.draft.has(keyOf(S.focus));
  const cell = view.cells.get(`${weekday}|${hour}`);
  const chip = w => w.status === "free" ? `<span class="chip f">${w.free.map(c => `Court ${c}`).join(", ")} free</span>`
    : `<span class="chip">${{ booked: "All booked", "no session": "No session", "not open": "Not open yet" }[w.status]}</span>`;
  return `<div class="${cls}"><h2>${WEEKDAY_PLURALS[weekday - 1]} at ${hh(hour)}</h2>
    <p class="sub">${on ? "You are watching this hour." : "Not watched. Tap the hour to watch it."}</p>
    <div class="rows">${cell ? cell.weeks.map(w => `<div><span>${dayLabel(w.date)}</span>${chip(w)}</div>`).join("") : ""}</div></div>`;
}

function tabs() {
  const { weekly, single } = watchLines(S.draft, S.state.availability);
  const tab = (key, label, n) => `<button role="tab" class="${S.tab === key ? "on" : ""}" data-tab="${key}" aria-selected="${S.tab === key}">${label}${n ? `<span class="count">${n}</span>` : ""}</button>`;
  return `<div class="tabs" role="tablist">${tab("weekly", "Weekly", weekly.length)}${tab("dates", "Single dates", single.length)}</div>`;
}

function datesCard() {
  const { availability: avail, window_end: windowEnd } = S.state;
  const days = calendar(avail, S.draft, londonNow(), windowEnd);
  const cells = days.map((d, i) => {
    const month = i === 0 || d.date.endsWith("-01") ? `<span class="m">${dayLabel(d.date).split(" ")[2]}</span>` : "";
    const [long, short] = d.notOpen ? ["not open", "·"] : d.free ? [`${d.free} free`, d.free] : ["full", "full"];
    return `<button class="day ${d.notOpen ? "later" : ""} ${S.date === d.date ? "sel" : ""} ${d.watching ? "has" : ""}" data-date="${d.date}"
      ${d.past ? "disabled" : ""} aria-label="${dayLabel(d.date)}, ${d.past ? "past" : long}${d.watching ? ", watching" : ""}">
      <span class="n">${Number(d.date.slice(8))}${month}</span>
      <span class="c ${d.free && !d.notOpen ? "" : "zero"}"><span class="l">${long}</span><span class="s">${short}</span></span></button>`;
  }).join("");
  return `<div class="card"><h2>Single dates</h2><p class="sub">Click a day, then the hours you want to play.</p>
    <div class="legend"><span><i style="background:var(--acc)"></i>You're watching hours that day</span><span><i class="sq" style="border:1px dashed var(--line)"></i>Not bookable yet</span></div>
    <div class="cal">${WEEKDAYS.map(d => `<div class="dh">${d}</div>`).join("")}${cells}</div></div>`;
}

// The chosen day's hours. A day not open yet says when booking opens.
function dayCard() {
  if (!S.date) return `<div class="card"><h2>Pick a day</h2><p class="sub" style="margin:0">Click a day, then the hours you want to play.</p></div>`;
  const { availability: avail, window_end: windowEnd } = S.state;
  const notOpen = S.date > windowEnd;
  const hour = h => {
    if (h.state === "weekly") return `<div class="hour cov" title="Already in your Weekly hours"><b>${hh(h.hour)}</b><span>✓ Weekly</span></div>`;
    const label = h.state === "watching" ? "✓ Watching" : h.state === "free" ? `${h.free} free`
      : { booked: "Booked", "not open": "Not open", "no session": "No session" }[h.state];
    return `<button class="hour ${h.state === "watching" ? "on" : h.state === "free" ? "free" : ""}" data-hour="${h.hour}" ${S.busy ? "disabled" : ""}
      aria-pressed="${h.state === "watching"}"><b>${hh(h.hour)}</b><span>${label}</span></button>`;
  };
  const hours = dayHours(avail, S.draft, S.date, windowEnd);
  return `<div class="card"><h2>${dayLabel(S.date)}</h2>
    <p class="sub">${hours.length ? "Click the hours you want to play." : "No court hours left that day."}${notOpen ? ` Booking opens at midnight on ${dayLabel(opensOn(S.date, londonNow(), windowEnd))}.` : ""}</p>
    <div class="hours">${hours.map(hour).join("")}</div></div>`;
}

function watchesCard() {
  const { weekly, single } = watchLines(S.draft, S.state.availability);
  const line = l => `<div><span>${l.label} <span class="muted">${l.time}</span></span><span class="row-r">
    ${l.free ? `<span class="chip f">${l.free} free</span>` : ""}
    <button class="x" data-act="remove" ${S.busy ? "disabled" : ""} data-keys="${esc(l.keys.join(" "))}" aria-label="Stop watching ${l.label} ${l.time}">×</button></span></div>`;
  const section = (title, lines) => lines.length ? `<div class="sec">${title}</div><div class="rows">${lines.map(line).join("")}</div>` : "";
  return `<div class="card"><h2>Your watches</h2>
    ${weekly.length || single.length ? section("Weekly", weekly) + section("Single dates", single) : `<p class="empty">Nothing yet. Click an hour to start.</p>`}</div>`;
}

function footer() {
  const { last_check: at, window_end: windowEnd } = S.state;
  const checked = !at ? "Courts not checked yet"
    : `Courts last checked at ${at.slice(11, 16)} ${at.slice(0, 10) === londonNow().date ? "today" : `on ${dayLabel(at.slice(0, 10))}`}`;
  return `<footer>${checked} · Bookable up to ${dayLabel(windowEnd)} · Booking stays on Camden Active</footer>`;
}

function bottomBar() {
  const { added, removed } = changes(S.saved, S.draft), n = added.length + removed.length;
  if (n) return `<div class="savebar"><div class="t">${n} unsaved change${n === 1 ? "" : "s"}
      <small>${S.error ? esc(S.error) : "Saving sends you anything already free for the new hours."}</small></div>
    <button class="btn ghost" data-act="discard" ${S.busy ? "disabled" : ""}>Discard</button>
    <button class="btn primary" data-act="save" ${S.busy ? "disabled" : ""}>${S.busy ? "Saving…" : "Save"}</button></div>`;
  return S.note || S.error ? `<div class="toast ${S.error ? "bad" : ""}">${esc(S.error || S.note)}</div>` : "";
}

function member() {
  const m = S.state.member;
  view = grid();
  return `<div class="wrap"><header><div class="brand">${BALL}<div><b>Court Watch</b><span>Lincoln's Inn Fields · 3 courts</span></div></div>
    <div class="menu"><button class="avatar" data-act="menu" aria-label="Account" aria-expanded="${S.menu}">${esc(m.first_name.slice(0, 1).toUpperCase())}</button>
    ${S.menu ? `<div class="menu-pop"><div>${esc(m.first_name)}${m.username ? ` · @${esc(m.username)}` : ""}<br>Alerts go to your Telegram DMs.</div><button data-act="logout">Log out</button></div>` : ""}</div></header>
    ${S.state.unreachable_since ? `<div class="banner" role="alert"><b>The bot can't message you.</b> Unblock it in Telegram to get alerts again. This goes away once a message gets through.</div>` : ""}
    ${tabs()}
    ${S.tab === "weekly"
      ? `<div class="layout"><div>${weeklyCard()}</div><div class="side"><div id="detail-wide">${detailCard(false)}</div>${watchesCard()}</div></div>`
      : `<div class="layout"><div>${datesCard()}</div><div class="side">${dayCard()}${watchesCard()}</div></div>`}
    ${footer()}</div>${bottomBar()}`;
}

function render() {
  const app = document.getElementById("app");
  app.innerHTML = S.screen === "loading" ? "" : S.screen === "member" ? member() : gate();
}

// Hovering changes only the detail and the focus outline, so the grid isn't rebuilt under the pointer.
function refreshDetail() {
  document.getElementById("detail-wide").innerHTML = detailCard(false);
  document.getElementById("detail-narrow").innerHTML = detailCard(true);
  document.querySelectorAll(".cell.focus").forEach(c => c.classList.remove("focus"));
  document.querySelector(`.cell[data-weekday="${S.focus.weekday}"][data-hour="${S.focus.hour}"]`)?.classList.add("focus");
}

// ---------- events ----------

// With a mouse, pressing a cell toggles it and dragging paints the same value across cells.
// Touch and keyboard toggle on click. Pressing re-renders the grid, so the click that follows
// may land elsewhere or not at all: a cell click straight after a mouse toggle is ignored.
let paint = null, mouseToggledAt = -Infinity;
const cellAt = e => {
  const c = e.target.closest?.(".cell");
  return c && { weekday: Number(c.dataset.weekday), hour: Number(c.dataset.hour) };
};
document.addEventListener("pointerdown", e => {
  const c = cellAt(e);
  if (!c || e.pointerType !== "mouse" || S.busy) return;
  paint = !S.draft.has(keyOf(c));
  mouseToggledAt = e.timeStamp;
  toggle(c.weekday, c.hour, paint);
  render();
  e.preventDefault();
});
document.addEventListener("pointerover", e => {
  const c = cellAt(e);
  if (!c) return;
  if (paint !== null && !(e.buttons & 1)) paint = null; // released outside the window
  if (paint !== null) {
    if (S.draft.has(keyOf(c)) !== paint) { toggle(c.weekday, c.hour, paint); render(); }
    return;
  }
  if (e.pointerType === "mouse" && (S.focus?.weekday !== c.weekday || S.focus?.hour !== c.hour)) {
    S.focus = c;
    refreshDetail();
  }
});
document.addEventListener("pointerup", () => { paint = null; });
document.addEventListener("pointercancel", () => { paint = null; });

document.addEventListener("click", e => {
  const c = cellAt(e);
  if (c) {
    if (e.timeStamp - mouseToggledAt < 1000 || S.busy) return;
    toggle(c.weekday, c.hour);
    render();
    return document.querySelector(`.cell[data-weekday="${c.weekday}"][data-hour="${c.hour}"]`)?.focus();
  }
  const tab = e.target.closest("[data-tab]");
  if (tab) { S.tab = tab.dataset.tab; S.menu = false; return render(); }
  const day = e.target.closest(".day");
  if (day) { S.date = day.dataset.date; return render(); }
  const hour = e.target.closest(".hour[data-hour]");
  if (hour) {
    if (S.busy) return;
    toggleDated(S.date, Number(hour.dataset.hour));
    render();
    return document.querySelector(`.hour[data-hour="${hour.dataset.hour}"]`)?.focus();
  }
  const target = e.target.closest("[data-act]");
  const act = target?.dataset.act;
  if (act === "login") return logIn();
  if (act === "logout") return logOut();
  if (act === "menu") { S.menu = !S.menu; return render(); }
  if (act === "remove") {
    if (S.busy) return;
    target.dataset.keys.split(" ").forEach(k => S.draft.delete(k));
    Object.assign(S, { note: "", error: "" });
    return render();
  }
  if (act === "discard") { Object.assign(S, { draft: new Set(S.saved), note: "", error: "" }); return render(); }
  if (act === "save") return saveWatches();
  if (S.menu && !e.target.closest(".menu-pop")) { S.menu = false; render(); }
});

load();
