import { assertEquals, assertNotEquals } from "jsr:@std/assert@1";
import { sessionToken } from "./session_token.ts";

const SECRET = "test-session-secret";
const NOW = new Date("2026-10-15T09:00:00Z");
const DAY = 24 * 3600 * 1000;
const later = (ms: number) => new Date(NOW.getTime() + ms);

Deno.test("a signed token verifies to its member", async () => {
  const token = await sessionToken.sign(42, SECRET, NOW);

  assertEquals(await sessionToken.verify(token, SECRET, later(DAY)), 42);
});

Deno.test("a token lasts 30 days", async () => {
  const token = await sessionToken.sign(42, SECRET, NOW);

  assertEquals(await sessionToken.verify(token, SECRET, later(30 * DAY - 1000)), 42);
  assertEquals(await sessionToken.verify(token, SECRET, later(30 * DAY)), null);
});

Deno.test("a tampered token is rejected", async () => {
  const token = await sessionToken.sign(42, SECRET, NOW);
  const [, expires, signature] = token.split(".");

  assertNotEquals(token, `43.${expires}.${signature}`);
  assertEquals(await sessionToken.verify(`43.${expires}.${signature}`, SECRET, NOW), null);
  assertEquals(await sessionToken.verify(`42.${Number(expires) + DAY}.${signature}`, SECRET, NOW), null);
  assertEquals(await sessionToken.verify(token.slice(0, -2), SECRET, NOW), null);
});

Deno.test("a token signed with another secret is rejected", async () => {
  const token = await sessionToken.sign(42, "another-secret", NOW);

  assertEquals(await sessionToken.verify(token, SECRET, NOW), null);
});

Deno.test("garbage is rejected", async () => {
  for (const token of ["", "42", "42.x.y", "a.b.c.d", "-1.1.AAAA"]) {
    assertEquals(await sessionToken.verify(token, SECRET, NOW), null);
  }
});
