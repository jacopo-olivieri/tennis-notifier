// Sends the bot's DMs through the Telegram Bot API, as notifier/telegram.py does for the poller.

export type SendOutcome = { status: number | null; error: string | null };

// Sends one HTML message without link previews. {status: 200, error: null} when sent;
// on failure the status is null if no response came back. The SQL side decides what a failure means.
export async function sendMessage(
  botToken: string,
  chatId: number,
  text: string,
  fetchFn: typeof fetch = fetch,
): Promise<SendOutcome> {
  let res: Response;
  try {
    res = await fetchFn(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        parse_mode: "HTML",
        link_preview_options: { is_disabled: true },
      }),
      signal: AbortSignal.timeout(30_000),
    });
  } catch (e) {
    return { status: null, error: `${(e as Error).name}: ${(e as Error).message}` };
  }
  if (res.ok) {
    await res.body?.cancel();
    return { status: res.status, error: null };
  }
  const description = await res.json().then((b) => b?.description).catch(() => null);
  return { status: res.status, error: description || res.statusText };
}
