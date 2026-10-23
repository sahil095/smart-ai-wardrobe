"""Stylist agent: Groq chooses tools; this process runs them.

Owned outfits only come from the outfit engine. Inspiration photos are never
wardrobe items.
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from groq import BadRequestError

from app.config import settings
from app.models import SavedOutfit, User, WardrobeItem, WearEvent
from app.services import (
    gap_service,
    groq_service,
    inspiration_service,
    memory_service,
    outfit_engine,
    outfit_log,
    weather_service,
)

logger = logging.getLogger(__name__)

MAX_ROUNDS = 4
HISTORY_TURNS = 12

STYLIST_SYSTEM = (
    "You are Wardrobe AI, a personal stylist. You can look up the user's real "
    "wardrobe, weather, wear log, saved looks, gaps, and style memories by "
    "calling tools. Rules:\n"
    "- Never invent clothing the user owns. Outfit suggestions must come from "
    "generate_outfits.\n"
    "- If the user asks what to wear, what to pack, or for an outfit from "
    "their closet, call generate_outfits. Do not call style_ideas for that.\n"
    "- If the user asks how to style or wear a piece, for inspiration, similar "
    "looks, or Pinterest, call style_ideas and do not call generate_outfits. "
    "Pass item_id when you know which owned piece they mean, otherwise a "
    "query like 'white hoodie outfit'.\n"
    "- style_ideas photos are inspiration only. Say they are similar looks, "
    "not the user's photo and not for sale. Mention the Pinterest link.\n"
    "- Call remember only when the user states a lasting preference "
    "(for example 'no skinny jeans'). Do not remember one-off questions.\n"
    "- Respect style_memories.\n"
    "- Keep replies short. Do not dump raw JSON."
)

# Questions about how a piece is worn, not which owned items to put on today.
_INSPIRE = re.compile(
    r"\b("
    r"pinterest|inspiration|inspire|similar looks|style ideas|"
    r"style (?:my|this|the|a|an)\b|"
    r"how (?:do|to|should|can|would) (?:i |people |you )?(?:style|wear)|"
    r"how (?:is|are) .{0,40} worn|"
    r"styled|outfit ideas"
    r")\b",
    re.I,
)
_FILLER = re.compile(
    r"\b("
    r"how|do|does|did|can|could|should|would|i|you|my|me|the|a|an|to|for|on|"
    r"of|with|show|see|some|please|pinterest|inspiration|inspire|style|styled|"
    r"wear|wearing|worn|ideas|idea|looks|look|similar|people|outfit|outfits|"
    r"this|that|those|these|from|into|about"
    r")\b",
    re.I,
)

def _optional_string(description: str | None = None) -> dict:
    """Groq rejects a tool call when the model sends null for a string field."""
    schema: dict = {"type": ["string", "null"]}
    if description:
        schema["description"] = description
    return schema


def _optional_int(description: str | None = None) -> dict:
    schema: dict = {"type": ["integer", "null"]}
    if description:
        schema["description"] = description
    return schema


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": _optional_string("City name. Omit when unknown."),
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_closet",
            "description": "List the user's clean wardrobe items. Optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": _optional_string(),
                    "color": _optional_string(),
                    "occasion": _optional_string(),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_outfits",
            "description": "Build 2 outfits from clothes the user owns and that are Clean.",
            "parameters": {
                "type": "object",
                "properties": {
                    "occasion": _optional_string("Occasion such as office. Omit if unknown."),
                    "location": _optional_string(
                        "City for weather. Omit when the user did not name a city."
                    ),
                    "favorite_item_id": _optional_int(
                        "Must-include item id from list_closet. Omit when not needed."
                    ),
                    "color_preference": _optional_string(),
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wardrobe_gaps",
            "description": "Missing staples based on the user's tags.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recent_wears",
            "description": "Recently worn outfits.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "saved_looks",
            "description": "Outfits the user starred.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Store one durable style preference the user just stated.",
            "parameters": {
                "type": "object",
                "properties": {"text": _optional_string()},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "style_ideas",
            "description": (
                "Inspiration photos and a Pinterest search for how a garment "
                "type is styled. Use this instead of generate_outfits when the "
                "user wants Pinterest, inspiration, or how to style a piece. "
                "Not the user's photo and not a shop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": _optional_int(),
                    "query": _optional_string("e.g. white hoodie outfit"),
                },
            },
        },
    },
]


def _compact_item(item: WardrobeItem) -> dict:
    return {
        "item_id": item.id,
        "name": item.name,
        "category": item.category,
        "subcategory": item.subcategory,
        "primary_color": item.primary_color,
        "occasion": item.occasion or [],
        "laundry_status": item.laundry_status,
    }


class StylistSession:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.outfits: list[dict] = []
        self.ideas: dict | None = None

    async def _items(self) -> list[WardrobeItem]:
        return list(
            self.db.scalars(
                select(WardrobeItem).where(WardrobeItem.user_id == self.user.id)
            ).all()
        )

    async def call(self, name: str, args: dict) -> dict:
        try:
            if name == "get_weather":
                return await self._weather(args.get("location") or "")
            if name == "list_closet":
                return await self._closet(args)
            if name == "generate_outfits":
                return await self._generate(args)
            if name == "wardrobe_gaps":
                return await self._gaps()
            if name == "recent_wears":
                return self._wears()
            if name == "saved_looks":
                return self._saved()
            if name == "remember":
                return self._remember(args.get("text") or "")
            if name == "style_ideas":
                return await self._ideas(args)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tool %s failed: %s", name, exc)
            return {"error": f"{name} failed"}
        return {"error": f"Unknown tool {name}"}

    async def _weather(self, location: str) -> dict:
        if not location.strip():
            return {"error": "location is required"}
        geo = await weather_service.geocode(location.strip())
        if not geo:
            return {"error": "City not found"}
        weather = await weather_service.get_current_weather(
            geo["latitude"], geo["longitude"], geo["name"]
        )
        return {
            "location": weather.get("location_name"),
            "temperature_c": weather.get("temperature_c"),
            "condition": weather.get("condition"),
            "bucket": weather.get("bucket"),
        }

    async def _closet(self, args: dict) -> dict:
        items = outfit_engine.get_clean_items(await self._items())
        category = (args.get("category") or "").strip().lower()
        color = (args.get("color") or "").strip().lower()
        occasion = (args.get("occasion") or "").strip()
        picked = []
        for item in items:
            if category and category not in (item.category or "").lower():
                continue
            blob = f"{item.primary_color or ''} {item.secondary_color or ''}".lower()
            if color and color not in blob:
                continue
            if occasion and item.occasion and occasion not in item.occasion:
                continue
            picked.append(_compact_item(item))
        return {"count": len(picked), "items": picked[:40]}

    async def _generate(self, args: dict) -> dict:
        items = await self._items()
        weather = None
        location = (args.get("location") or "").strip()
        if location:
            weather = await self._weather(location)
            if weather.get("error"):
                weather = None
            else:
                weather = {
                    "temperature_c": weather.get("temperature_c"),
                    "condition": weather.get("condition"),
                    "bucket": weather.get("bucket"),
                    "location_name": weather.get("location"),
                    "source": "open-meteo",
                }
        fav = args.get("favorite_item_id")
        try:
            fav = int(fav) if fav not in (None, "") else None
        except (TypeError, ValueError):
            fav = None
        ctx = {
            "occasion": args.get("occasion") or None,
            "color_preference": args.get("color_preference") or None,
            "favorite_item_id": fav,
            "recently_worn_item_ids": outfit_log.recently_worn_item_ids(
                self.db, self.user.id
            ),
            "saved_outfits": outfit_log.saved_fingerprints(self.db, self.user.id),
        }
        outfits, used_ai, note = outfit_engine.generate(self.user, items, weather, ctx)
        dumped = [o.model_dump() for o in outfits]
        self.outfits = dumped
        return {
            "used_ai": used_ai,
            "note": note,
            "outfits": [
                {
                    "upper": _piece_name(o.get("upper")),
                    "lower": _piece_name(o.get("lower")),
                    "shoes": _piece_name(o.get("shoes")),
                    "reasoning": o.get("reasoning"),
                }
                for o in dumped
            ],
        }

    async def _gaps(self) -> dict:
        items = await self._items()
        result = gap_service.analyze(self.db, self.user.id, items, refresh=False)
        cards = result.get("cards") or []
        return {
            "cards": [
                {"title": c.get("title"), "suggestion": c.get("suggestion")}
                for c in cards
            ]
        }

    def _wears(self) -> dict:
        rows = self.db.scalars(
            select(WearEvent)
            .where(WearEvent.user_id == self.user.id)
            .order_by(WearEvent.worn_at.desc())
            .limit(8)
        ).all()
        return {
            "worn": [
                {
                    "worn_at": row.worn_at.isoformat() if row.worn_at else None,
                    "names": [
                        p.get("name")
                        for p in (row.snapshot or [])
                        if isinstance(p, dict) and p.get("name")
                    ],
                }
                for row in rows
            ]
        }

    def _saved(self) -> dict:
        rows = self.db.scalars(
            select(SavedOutfit)
            .where(SavedOutfit.user_id == self.user.id)
            .order_by(SavedOutfit.created_at.desc())
            .limit(8)
        ).all()
        return {
            "saved": [
                {
                    "names": [
                        p.get("name")
                        for p in (row.snapshot or [])
                        if isinstance(p, dict) and p.get("name")
                    ]
                }
                for row in rows
            ]
        }

    def _remember(self, text: str) -> dict:
        ok, message = memory_service.add_memory(self.user, text, source="chat")
        return {"ok": ok, "message": message}

    async def _ideas(self, args: dict) -> dict:
        query = (args.get("query") or "").strip()
        item_id = args.get("item_id")
        if item_id and not query:
            try:
                item_id = int(item_id)
            except (TypeError, ValueError):
                item_id = None
            item = self.db.get(WardrobeItem, item_id) if item_id else None
            if not item or item.user_id != self.user.id:
                return {"error": "Item not in this wardrobe"}
            query = inspiration_service.query_for_item(item)
        result = await inspiration_service.search(self.db, query, commit=False)
        self.ideas = result
        return {
            "query": result.get("query"),
            "note": result.get("note"),
            "pinterest_url": result.get("pinterest_url"),
            "photo_count": len(result.get("photos") or []),
            "alts": [p.get("alt") for p in (result.get("photos") or [])[:8]],
        }


def _piece_name(piece: dict | None) -> str | None:
    if isinstance(piece, dict):
        return piece.get("name")
    return None


def wants_inspiration(text: str) -> bool:
    """True when the user wants styling photos, not a closet combination."""
    return bool(_INSPIRE.search(text or ""))


def _query_from_text(text: str) -> str:
    core = _FILLER.sub(" ", text or "")
    core = re.sub(r"[^a-z0-9\s]", " ", core.lower())
    core = " ".join(core.split())
    if not core:
        core = "outfit ideas"
    if "outfit" not in core:
        core = f"{core} outfit"
    return core


def _compact(text: str) -> str:
    """Ignore spaces and punctuation so 'pull over' matches 'pullover'."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


_COLOR_ALT = {"grey": "gray", "gray": "grey"}
_PART_SPLIT = re.compile(r"\b(?:and|&|with|plus)\b|,", re.I)


def _color_hit(color: str, blob: str) -> bool:
    name = (color or "").strip().lower()
    if not name:
        return False
    if re.search(rf"\b{re.escape(name)}\b", blob):
        return True
    alt = _COLOR_ALT.get(name)
    return bool(alt and re.search(rf"\b{re.escape(alt)}\b", blob))


def _kind_hit(kind: str, blob: str, compact_blob: str) -> bool:
    name = (kind or "").strip().lower()
    if not name:
        return False
    if name in blob:
        return True
    compact = _compact(name)
    return len(compact) >= 4 and compact in compact_blob


def _score_item(item: WardrobeItem, text: str) -> int:
    blob = (text or "").lower()
    compact_blob = _compact(text)
    points = 0
    name = (item.name or "").lower()
    if name and name in blob:
        points += 8
    for token in re.findall(r"[a-z0-9]+", name):
        if len(token) > 2 and token in blob:
            points += 2
    if _color_hit(item.primary_color or "", blob):
        points += 2
    kind = item.subcategory or item.category or ""
    if _kind_hit(kind, blob, compact_blob):
        points += 3
    return points


def _best_item(items: list[WardrobeItem], text: str) -> WardrobeItem | None:
    """Pick the owned piece named in one part of the question."""
    best: WardrobeItem | None = None
    score = 0
    for item in items:
        points = _score_item(item, text)
        if points > score:
            score = points
            best = item
    return best if score >= 3 else None


def _spoken_phrase(text: str) -> str:
    core = _FILLER.sub(" ", text or "")
    core = re.sub(r"[^a-z0-9\s]", " ", core.lower())
    return " ".join(core.split())


def _mentioned_phrases(items: list[WardrobeItem], text: str) -> list[str]:
    """Every garment the question names, not only the closest closet match."""
    parts = [part.strip() for part in _PART_SPLIT.split(text or "") if part.strip()]
    if len(parts) < 2:
        item = _best_item(items, text)
        if item:
            return [_item_phrase(item)]
        spoken = _spoken_phrase(text)
        return [spoken] if spoken else ["this piece"]

    phrases: list[str] = []
    seen: set[int] = set()
    for part in parts:
        item = _best_item(items, part)
        if item and item.id not in seen:
            seen.add(item.id)
            phrases.append(_item_phrase(item))
            continue
        spoken = _spoken_phrase(part)
        if spoken:
            phrases.append(spoken)
    return phrases or ["this piece"]


def _clean_args(raw) -> dict:
    if isinstance(raw, dict):
        args = raw
    else:
        try:
            args = json.loads(raw or "{}")
        except json.JSONDecodeError:
            args = {}
    if not isinstance(args, dict):
        return {}
    return {key: value for key, value in args.items() if value is not None}


def _failed_generation(exc: BadRequestError) -> dict | None:
    """Groq 400s include the rejected tool call. Recover it instead of failing the chat."""
    body = exc.body
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return None
    if not isinstance(body, dict):
        return None
    error = body.get("error") if isinstance(body.get("error"), dict) else {}
    failed = error.get("failed_generation")
    if isinstance(failed, str):
        try:
            failed = json.loads(failed)
        except json.JSONDecodeError:
            return None
    if isinstance(failed, dict) and failed.get("name"):
        return failed
    return None


def _tool_message(call, payload: dict) -> dict:
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "name": call.function.name,
        "content": json.dumps(payload, ensure_ascii=False)[:6000],
    }


def _item_phrase(item: WardrobeItem | None, query: str = "") -> str:
    """Short name for the Pinterest line, such as White Sneakers."""
    if item:
        color = (item.primary_color or "").strip()
        kind = (item.subcategory or item.category or "").strip()
        if color and kind:
            return f"{color} {kind}"[:80]
        named = (item.name or kind or "this piece").strip()
        return named[:80]
    text = re.sub(r"\s+outfit$", "", (query or "").strip(), flags=re.I)
    return text or "this piece"


async def _inspiration_reply(session: StylistSession, user_text: str) -> dict:
    """A Pinterest search for every piece named in the question."""
    items = await session._items()
    phrases = _mentioned_phrases(items, user_text)
    label = " and ".join(phrases)
    if len(phrases) == 1:
        item = _best_item(items, user_text)
        if item:
            await session._ideas({"item_id": item.id})
        elif not session.ideas:
            await session._ideas({"query": _query_from_text(user_text)})
    else:
        await session._ideas({"query": f"{' '.join(phrases)} outfit"})
    ideas = dict(session.ideas or {})
    ideas["label"] = label
    session.ideas = ideas
    return {
        "content": f'Find styles for your "{label}" on Pinterest.',
        "outfits": [],
        "ideas": ideas,
    }


async def reply(db: Session, user: User, history: list[dict], user_text: str) -> dict:
    """Run the tool loop. Returns assistant text plus UI extras."""
    session = StylistSession(db, user)
    if wants_inspiration(user_text):
        return await _inspiration_reply(session, user_text)
    if not settings.groq_enabled:
        return {
            "content": (
                "Groq is not configured, so I can't chat yet. "
                "Style ideas still work from a wardrobe item."
            ),
            "outfits": [],
            "ideas": None,
        }

    messages: list[dict] = [{"role": "system", "content": STYLIST_SYSTEM}]
    memories = [m["text"] for m in memory_service.as_list(user)]
    if memories:
        messages.append(
            {
                "role": "system",
                "content": "Style memories:\n- " + "\n- ".join(memories),
            }
        )
    for turn in history[-HISTORY_TURNS:]:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_text})

    client = groq_service._get_client()
    final = ""
    for round_index in range(MAX_ROUNDS):
        try:
            completion = client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.4,
            )
        except BadRequestError as exc:
            failed = _failed_generation(exc)
            if not failed:
                raise
            name = str(failed["name"])
            args = _clean_args(failed.get("arguments") or {})
            payload = await session.call(name, args)
            call_id = f"call_recovered_{round_index}"
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(payload, ensure_ascii=False)[:6000],
                }
            )
            continue
        msg = completion.choices[0].message
        calls = list(msg.tool_calls or [])
        if not calls:
            final = (msg.content or "").strip()
            break
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments or "{}",
                        },
                    }
                    for call in calls
                ],
            }
        )
        for call in calls:
            payload = await session.call(
                call.function.name, _clean_args(call.function.arguments or "{}")
            )
            messages.append(_tool_message(call, payload))
    else:
        final = final or "I couldn't finish that. Try a shorter question."

    if not final:
        if session.outfits:
            final = "Here are two looks from your clean wardrobe."
        elif session.ideas:
            final = "Similar looks for that kind of piece. These are not your photo."
        else:
            final = "I don't have a suggestion yet. Ask me what to wear, or how to style a piece."

    return {
        "content": final[:2000],
        "outfits": session.outfits,
        "ideas": session.ideas,
    }
