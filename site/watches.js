// What the week grid, the Single dates calendar and the "Your watches" panel show, from the server's state.
// Pure functions, so `deno test` covers them; app.js only renders and handles clicks.
// A watch is {weekday, hour} (ISO weekday, Mon = 1) or {date, hour}; drafts hold their keys.

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const hh = h => `${String(h).padStart(2, "0")}:00`;
const addDays = (d, n) => {
  const t = new Date(`${d}T12:00:00Z`);
  t.setUTCDate(t.getUTCDate() + n);
  return t.toISOString().slice(0, 10);
};
const weekdayOf = d => (new Date(`${d}T12:00:00Z`).getUTCDay() + 6) % 7 + 1;
export const dayLabel = d => `${WEEKDAYS[weekdayOf(d) - 1]} ${Number(d.slice(8))} ${MONTHS[Number(d.slice(5, 7)) - 1]}`;

export const keyOf = w => w.weekday ? `w${w.weekday}-${w.hour}` : `d${w.date}-${w.hour}`;
function watchOf(key) {
  const cut = key.lastIndexOf("-"), hour = Number(key.slice(cut + 1));
  return key[0] === "w" ? { weekday: Number(key.slice(1, cut)), hour } : { date: key.slice(1, cut), hour };
}

// London's date and hour now, which is the clock the availability view uses.
export function londonNow(at = new Date()) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/London", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23",
  }).formatToParts(at).map(x => [x.type, x.value]));
  return { date: `${p.year}-${p.month}-${p.day}`, hour: Number(p.hour) };
}

// The next n dates of a weekday whose hour hasn't started yet.
export function nextDates(weekday, hour, now, n = 5) {
  let d = addDays(now.date, (weekday - weekdayOf(now.date) + 7) % 7);
  if (d === now.date && hour <= now.hour) d = addDays(d, 7);
  return Array.from({ length: n }, (_, i) => addDays(d, 7 * i));
}

export const byDateHour = avail => new Map(avail.map(a => [`${a.date}|${a.hour}`, a]));

// One grid cell: each of the next five weeks with its free courts and status. A date with
// no availability row is "not open" past window_end, otherwise "no session". A cell is
// dashed when no scanned week has a court running that hour.
export function weekCell(avail, weekday, hour, now, windowEnd, index = byDateHour(avail)) {
  const rows = nextDates(weekday, hour, now).map(date => [date, index.get(`${date}|${hour}`)]);
  const weeks = rows.map(([date, a]) => ({
    date,
    status: a ? a.status : date > windowEnd ? "not open" : "no session",
    free: a ? a.free_courts : [],
  }));
  return { weeks, dashed: !rows.some(([, a]) => a && a.status !== "no session") };
}

// The grid's rows: every hour some court runs, plus watched weekly hours so they can be
// clicked off. Before the first scan there's nothing to go on, so 07:00–21:00.
export function gridHours(avail, draft) {
  const hours = new Set(avail.map(a => a.hour));
  if (!hours.size) for (let h = 7; h <= 21; h++) hours.add(h);
  for (const k of draft) if (k[0] === "w") hours.add(watchOf(k).hour);
  return [...hours].sort((a, b) => a - b);
}

// The Single dates calendar: seven weeks from this Monday. Each day counts the courts free
// on its hours still to come; days after window_end aren't open, days before today are past.
export function calendar(avail, draft, now, windowEnd) {
  const start = addDays(now.date, 1 - weekdayOf(now.date));
  const free = new Map();
  for (const a of avail) free.set(a.date, (free.get(a.date) ?? 0) + a.free_courts.length);
  const watched = new Set([...draft].filter(k => k[0] === "d").map(k => watchOf(k).date));
  return Array.from({ length: 49 }, (_, i) => addDays(start, i)).map(date => ({
    date,
    past: date < now.date,
    notOpen: date > windowEnd,
    free: free.get(date) ?? 0, // availability has only hours still to come
    watching: watched.has(date),
  }));
}

// A day's hours: those a court runs, plus that date's watched hours. A day past window_end that
// wasn't scanned takes its weekday's latest scanned hours. Each hour is "weekly" (covered
// by a weekly watch, so not clickable), "watching", or what availability says about it.
export function dayHours(avail, draft, date, windowEnd) {
  const courtRuns = a => a.status !== "no session";
  const rows = new Map(avail.filter(a => a.date === date).map(a => [a.hour, a]));
  let hours = [...rows.values()].filter(courtRuns).map(a => a.hour);
  if (date > windowEnd && !hours.length) {
    const ref = avail.filter(a => courtRuns(a) && a.date < date && weekdayOf(a.date) === weekdayOf(date))
      .reduce((latest, a) => a.date > latest ? a.date : latest, "");
    hours = ref ? avail.filter(a => a.date === ref && courtRuns(a)).map(a => a.hour) : gridHours(avail, []);
  }
  const weekly = h => draft.has(keyOf({ weekday: weekdayOf(date), hour: h }));
  const watching = h => draft.has(keyOf({ date, hour: h }));
  for (const k of draft) if (watchOf(k).date === date) hours.push(watchOf(k).hour);
  return [...new Set(hours)].sort((a, b) => a - b).map(hour => {
    const a = rows.get(hour);
    const free = date > windowEnd || !a ? 0 : a.free_courts.length;
    const state = weekly(hour) ? "weekly" : watching(hour) ? "watching"
      : date > windowEnd ? "not open" : a ? a.status : "no session";
    return { hour, state, free };
  });
}

// Booking for a date opens at midnight as many days before it as window_end is after today.
export const opensOn = (date, now, windowEnd) => {
  let opens = date;
  for (let d = now.date; d < windowEnd; d = addDays(d, 1)) opens = addDays(opens, -1);
  return opens;
};

// The watch keys still to come: a single-date hour that has started is past, so the site
// hides it until housekeeping deletes it.
export const upcoming = (keys, now) => [...keys].filter(k => {
  if (k[0] === "w") return true;
  const { date, hour } = watchOf(k);
  return date > now.date || (date === now.date && hour > now.hour);
});

// Contiguous hours per day (a weekday or a date) as {day, from, to}, `to` exclusive.
function runs(watches, dayOf) {
  const byDay = new Map();
  for (const w of watches) byDay.set(dayOf(w), [...(byDay.get(dayOf(w)) ?? []), w.hour]);
  const out = [];
  for (const [day, hours] of byDay) {
    hours.sort((a, b) => a - b);
    let from = hours[0];
    hours.forEach((h, i) => {
      if (hours[i + 1] !== h + 1) { out.push({ day, from, to: h + 1 }); from = hours[i + 1]; }
    });
  }
  return out;
}

// The panel's two lists. Weekly days with the same run share a line ("Sat · Sun 08:00–10:00").
// Each line counts the courts free on its hours now, and carries its keys for ×.
export function watchLines(draft, avail) {
  const watches = [...draft].map(watchOf);
  const hours = (from, to) => Array.from({ length: to - from }, (_, i) => from + i);
  const time = (from, to) => `${hh(from)}–${hh(to)}`;
  const freeOn = match => avail.reduce((n, a) => n + (match(a) ? a.free_courts.length : 0), 0);

  const groups = new Map();
  for (const r of runs(watches.filter(w => w.weekday), w => w.weekday)) {
    const g = groups.get(`${r.from}-${r.to}`) ?? { from: r.from, to: r.to, days: [] };
    g.days.push(r.day);
    groups.set(`${r.from}-${r.to}`, g);
  }
  const weekly = [...groups.values()]
    .map(g => ({ ...g, days: g.days.sort((a, b) => a - b) }))
    .sort((a, b) => a.days[0] - b.days[0] || a.from - b.from)
    .map(({ days, from, to }) => ({
      label: days.map(d => WEEKDAYS[d - 1]).join(" · "),
      time: time(from, to),
      free: freeOn(a => days.includes(weekdayOf(a.date)) && a.hour >= from && a.hour < to),
      keys: days.flatMap(weekday => hours(from, to).map(hour => keyOf({ weekday, hour }))),
    }));

  const single = runs(watches.filter(w => w.date), w => w.date)
    .sort((a, b) => a.day.localeCompare(b.day) || a.from - b.from)
    .map(({ day: date, from, to }) => ({
      label: dayLabel(date),
      time: time(from, to),
      free: freeOn(a => a.date === date && a.hour >= from && a.hour < to),
      keys: hours(from, to).map(hour => keyOf({ date, hour })),
    }));

  return { weekly, single };
}

// What saving would send: the draft's hours not saved yet, and the saved hours dropped.
export function changes(saved, draft) {
  return {
    added: [...draft].filter(k => !saved.has(k)).map(watchOf),
    removed: [...saved].filter(k => !draft.has(k)).map(watchOf),
  };
}
