import { assertEquals } from "jsr:@std/assert@1";
import { sendMessage } from "./telegram.ts";

type Call = { url: string; body: unknown };

function fakeFetch(respond: () => Response | Promise<Response>, calls: Call[] = []): typeof fetch {
  return (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), body: JSON.parse(String(init?.body)) });
    return await respond();
  }) as typeof fetch;
}

Deno.test("a sent message posts HTML without link previews and reports 200", async () => {
  const calls: Call[] = [];

  const outcome = await sendMessage("123:abc", 111, "<b>hi</b>", fakeFetch(() => Response.json({ ok: true }), calls));

  assertEquals(outcome, { status: 200, error: null });
  assertEquals(calls, [{
    url: "https://api.telegram.org/bot123:abc/sendMessage",
    body: { chat_id: 111, text: "<b>hi</b>", parse_mode: "HTML", link_preview_options: { is_disabled: true } },
  }]);
});

Deno.test("a refused message reports Telegram's status and description", async () => {
  const blocked = () =>
    Response.json({ ok: false, description: "Forbidden: bot was blocked by the user" }, { status: 403 });

  assertEquals(await sendMessage("123:abc", 111, "hi", fakeFetch(blocked)), {
    status: 403,
    error: "Forbidden: bot was blocked by the user",
  });
});

Deno.test("a refusal without a JSON body reports the status text", async () => {
  const down = () => new Response("<html>", { status: 502, statusText: "Bad Gateway" });

  assertEquals(await sendMessage("123:abc", 111, "hi", fakeFetch(down)), { status: 502, error: "Bad Gateway" });
});

Deno.test("no response at all reports a null status", async () => {
  const unreachable = () => Promise.reject(new TypeError("error sending request"));

  assertEquals(await sendMessage("123:abc", 111, "hi", fakeFetch(unreachable)), {
    status: null,
    error: "TypeError: error sending request",
  });
});
