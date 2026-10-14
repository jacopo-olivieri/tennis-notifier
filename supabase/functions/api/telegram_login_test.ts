import { assertEquals } from "jsr:@std/assert@1";
import { verifyTelegramLogin } from "./telegram_login.ts";

const BOT_TOKEN = "123456789:TEST-not-a-real-bot-token";
const AUTH_DATE = 1792000000;
const at = (secondsAfterAuth: number) => new Date((AUTH_DATE + secondsAfterAuth) * 1000);

// Signed with BOT_TOKEN by an independent implementation (Python's hmac), as the widget would.
const GOOD = {
  id: 111,
  first_name: "Jacopo",
  username: "jacopo",
  photo_url: "https://t.me/i/userpic/320/jacopo.jpg",
  auth_date: AUTH_DATE,
  hash: "d55000a62e6ddbf077a37e54619354f5c71cfabee6135b23443f8d12b33fc194",
};

Deno.test("a payload signed with the bot token is accepted", async () => {
  assertEquals(await verifyTelegramLogin(GOOD, BOT_TOKEN, at(60)), {
    id: 111,
    first_name: "Jacopo",
    username: "jacopo",
  });
});

Deno.test("a tampered field is rejected", async () => {
  assertEquals(await verifyTelegramLogin({ ...GOOD, id: 222 }, BOT_TOKEN, at(60)), null);
  assertEquals(await verifyTelegramLogin({ ...GOOD, last_name: "Added" }, BOT_TOKEN, at(60)), null);
});

Deno.test("a payload signed for another bot is rejected", async () => {
  assertEquals(await verifyTelegramLogin(GOOD, "987654321:another-bot", at(60)), null);
});

Deno.test("a missing or malformed hash is rejected", async () => {
  const { hash: _, ...unsigned } = GOOD;
  assertEquals(await verifyTelegramLogin(unsigned, BOT_TOKEN, at(60)), null);
  assertEquals(await verifyTelegramLogin({ ...GOOD, hash: "not-hex" }, BOT_TOKEN, at(60)), null);
});

Deno.test("an auth_date up to 24 hours old is accepted, and older is stale", async () => {
  assertEquals((await verifyTelegramLogin(GOOD, BOT_TOKEN, at(24 * 3600)))?.id, 111);
  assertEquals(await verifyTelegramLogin(GOOD, BOT_TOKEN, at(24 * 3600 + 1)), null);
});

Deno.test("a missing or future auth_date is rejected", async () => {
  const { auth_date: _, ...undated } = GOOD;
  assertEquals(await verifyTelegramLogin(undated, BOT_TOKEN, at(60)), null);
  // Signed in the future by more than a minute's clock skew: GOOD seen 2 minutes before its auth_date.
  assertEquals(await verifyTelegramLogin(GOOD, BOT_TOKEN, at(-120)), null);
  assertEquals((await verifyTelegramLogin(GOOD, BOT_TOKEN, at(-30)))?.id, 111);
});
