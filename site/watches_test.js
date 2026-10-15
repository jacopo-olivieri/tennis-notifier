import { assertEquals } from "jsr:@std/assert@1";
import { changes, gridHours, keyOf, londonNow, nextDates, watchLines, weekCell } from "./watches.js";

// Thu 15 Oct 2026, 09:30 London; window_end is today + 34.
const NOW = { date: "2026-10-15", hour: 9 };
const WINDOW_END = "2026-11-18";
const row = (date, hour, free = []) => ({ date, hour, free_courts: free, status: free.length ? "free" : "booked" });

Deno.test("London's date and hour follow summer and winter time", () => {
  assertEquals(londonNow(new Date("2026-10-15T23:30:00Z")), { date: "2026-10-16", hour: 0 });
  assertEquals(londonNow(new Date("2026-11-15T23:30:00Z")), { date: "2026-11-15", hour: 23 });
});

Deno.test("the next five dates skip today once the hour has started", () => {
  assertEquals(nextDates(4, 10, NOW), ["2026-10-15", "2026-10-22", "2026-10-29", "2026-11-05", "2026-11-12"]);
  assertEquals(nextDates(4, 9, NOW), ["2026-10-22", "2026-10-29", "2026-11-05", "2026-11-12", "2026-11-19"]);
  assertEquals(nextDates(1, 8, NOW)[0], "2026-10-19");
});

Deno.test("a cell has one entry per week: free courts, booked, no session or not open", () => {
  const avail = [row("2026-10-22", 9, [2, 3]), row("2026-10-29", 9), { date: "2026-11-05", hour: 9, free_courts: [], status: "no session" }];
  const cell = weekCell(avail, 4, 9, NOW, WINDOW_END);
  assertEquals(cell.weeks.map(w => [w.date, w.status, w.free]), [
    ["2026-10-22", "free", [2, 3]],
    ["2026-10-29", "booked", []],
    ["2026-11-05", "no session", []],
    ["2026-11-12", "no session", []], // not scanned and inside the window
    ["2026-11-19", "not open", []],
  ]);
  assertEquals(cell.dashed, false);
});

Deno.test("a cell with no session in any of its weeks is dashed", () => {
  const dark = d => ({ date: d, hour: 18, free_courts: [], status: "no session" });
  const avail = ["2026-10-15", "2026-10-22", "2026-10-29", "2026-11-05", "2026-11-12"].map(dark);
  assertEquals(weekCell(avail, 4, 18, NOW, WINDOW_END).dashed, true);
  // A week that's only "not open" doesn't count as a session either.
  assertEquals(weekCell([], 4, 9, NOW, WINDOW_END).dashed, true);
});

Deno.test("the grid's hours are the scanned hours plus any watched hour", () => {
  const avail = [row("2026-10-16", 8), row("2026-10-16", 10), row("2026-10-17", 9)];
  assertEquals(gridHours(avail, new Set(["w2-20", "d2026-10-30-6"])), [8, 9, 10, 20]);
});

Deno.test("before the first scan the grid shows 07:00 to 21:00", () => {
  assertEquals(gridHours([], new Set()), [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]);
});

Deno.test("weekly hours merge into runs, and days with the same run share a line", () => {
  const draft = new Set(["w6-8", "w6-9", "w7-8", "w7-9", "w2-18", "w4-18", "w4-20"]);
  const { weekly, single } = watchLines(draft, []);
  assertEquals(weekly.map(l => [l.label, l.time]), [
    ["Tue · Thu", "18:00–19:00"],
    ["Thu", "20:00–21:00"],
    ["Sat · Sun", "08:00–10:00"],
  ]);
  assertEquals(single, []);
  assertEquals(weekly[2].keys.sort(), ["w6-8", "w6-9", "w7-8", "w7-9"]);
});

Deno.test("single-date hours merge into runs per date, in date order", () => {
  const draft = new Set(["d2026-10-31-11", "d2026-10-31-10", "d2026-10-24-15"]);
  assertEquals(watchLines(draft, []).single.map(l => [l.label, l.time, l.keys.length]), [
    ["Sat 24 Oct", "15:00–16:00", 1],
    ["Sat 31 Oct", "10:00–12:00", 2],
  ]);
});

Deno.test("each line counts the courts free on its hours right now", () => {
  const avail = [
    row("2026-10-17", 8, [1, 2]), row("2026-10-18", 9, [3]), row("2026-10-24", 8), row("2026-10-17", 10, [1]),
    row("2026-10-31", 10, [2]),
  ];
  const { weekly, single } = watchLines(new Set(["w6-8", "w6-9", "w7-8", "w7-9", "d2026-10-31-10"]), avail);
  assertEquals(weekly[0].free, 3);
  assertEquals(single[0].free, 1);
});

Deno.test("changes are the draft's hours not saved, and the saved hours not in the draft", () => {
  const saved = new Set([keyOf({ weekday: 2, hour: 18 }), keyOf({ date: "2026-10-31", hour: 10 })]);
  const draft = new Set([keyOf({ weekday: 2, hour: 18 }), keyOf({ weekday: 6, hour: 8 })]);
  assertEquals(changes(saved, draft), {
    added: [{ weekday: 6, hour: 8 }],
    removed: [{ date: "2026-10-31", hour: 10 }],
  });
  assertEquals(changes(saved, new Set(saved)), { added: [], removed: [] });
});
