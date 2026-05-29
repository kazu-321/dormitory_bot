from __future__ import annotations

import json
import urllib.error
import urllib.request


class DiscordSendError(RuntimeError):
    pass


def _post_json(url: str, token: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "menu-bot/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiscordSendError(f"Discord API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network dependent
        raise DiscordSendError(f"Discord request failed: {exc}") from exc


def create_dm_channel(token: str, user_id: str) -> dict:
    url = "https://discord.com/api/v10/users/@me/channels"
    return _post_json(url, token, {"recipient_id": str(user_id)})


def send_channel_message(
    token: str,
    channel_id: str,
    *,
    content: str | None = None,
    embeds: list[dict] | None = None,
) -> dict:
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload: dict = {}
    if content is not None:
        payload["content"] = content
    if embeds is not None:
        payload["embeds"] = embeds
    return _post_json(url, token, payload)


def send_dm_message(
    token: str,
    user_id: str,
    *,
    content: str | None = None,
    embeds: list[dict] | None = None,
) -> dict:
    dm_channel = create_dm_channel(token, user_id)
    channel_id = dm_channel.get("id")
    if not channel_id:
        raise DiscordSendError("Discord did not return a DM channel id.")
    return send_channel_message(token, channel_id, content=content, embeds=embeds)
