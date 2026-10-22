"""Durable stated taste. Wear logs stay the behavioral memory."""
from datetime import datetime

from app.models import User

MAX_MEMORIES = 20


def as_list(user: User | None) -> list[dict]:
    if not user:
        return []
    out = []
    for raw in user.style_memories or []:
        if isinstance(raw, dict) and (raw.get("text") or "").strip():
            out.append(
                {
                    "text": str(raw["text"]).strip()[:180],
                    "source": raw.get("source") or "chat",
                    "created_at": raw.get("created_at") or "",
                }
            )
    return out[:MAX_MEMORIES]


def add_memory(user: User, text: str, source: str = "chat") -> tuple[bool, str]:
    cleaned = " ".join((text or "").split())[:180]
    if len(cleaned) < 3:
        return False, "Say a little more about the preference."
    current = as_list(user)
    if any(m["text"].lower() == cleaned.lower() for m in current):
        return True, "Already remembered."
    if len(current) >= MAX_MEMORIES:
        return False, "Memory is full (20). Delete one on Profile first."
    current.append(
        {
            "text": cleaned,
            "source": source,
            "created_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
    )
    user.style_memories = current
    return True, "Remembered."


def delete_at(user: User, index: int) -> bool:
    current = as_list(user)
    if index < 0 or index >= len(current):
        return False
    del current[index]
    user.style_memories = current
    return True
