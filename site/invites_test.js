import { assertEquals } from "jsr:@std/assert@1";
import { inviteLink, inviteToken, memberLine, withoutInvite } from "./invites.js";

const SITE = "https://jacopo.github.io/tennis_notifier/";

Deno.test("an invite link carries the raw token in its query string", () => {
  assertEquals(inviteLink(`${SITE}?x=1#top`, "abc123"), `${SITE}?invite=abc123`);
});

Deno.test("the landing page reads the token back, or null without one", () => {
  assertEquals(inviteToken(`${SITE}?invite=abc123`), "abc123");
  assertEquals(inviteToken(SITE), null);
  assertEquals(inviteToken(`${SITE}?invite=`), null);
});

Deno.test("once used, the token comes off the address, keeping anything else", () => {
  assertEquals(withoutInvite(`${SITE}?invite=abc123`), SITE);
  assertEquals(withoutInvite(`${SITE}?a=1&invite=abc123#x`), `${SITE}?a=1#x`);
});

Deno.test("a member's line is their name, handle and hours watched", () => {
  assertEquals(memberLine({ first_name: "Ada", username: "ada", hours: 3 }), { name: "Ada", detail: "@ada · 3 hours" });
  assertEquals(memberLine({ first_name: "Bo", username: null, hours: 1 }), { name: "Bo", detail: "1 hour" });
  assertEquals(memberLine({ first_name: "Cy", username: "cy", hours: 0 }), { name: "Cy", detail: "@cy · no hours" });
});
