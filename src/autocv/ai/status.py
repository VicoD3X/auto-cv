from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class LocalAiStatus:
    online: bool
    message: str


def check_local_ai_status(base_url: str) -> LocalAiStatus:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=2)
        response.raise_for_status()
    except Exception as exc:
        return LocalAiStatus(online=False, message=f"offline: {exc}")
    return LocalAiStatus(online=True, message="online")
