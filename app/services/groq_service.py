"""Groq LLM integration for outfit recommendations.

The prompt is constrained so the model can ONLY choose from the provided
candidate item IDs. All returned IDs are validated by the outfit engine, so
hallucinated garments are rejected regardless of what the model says.
"""
import json

from groq import Groq

from app.config import settings

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


SYSTEM_PROMPT = (
    "You are Wardrobe AI, a professional fashion stylist. You build outfits "
    "STRICTLY from a provided list of the user's own clean clothing items. "
    "CRITICAL RULES:\n"
    "- NEVER invent, imagine, or reference any clothing that is not in the "
    "provided candidate list.\n"
    "- Only reference items by their exact numeric item_id from the list.\n"
    "- Every outfit must include an Upper, a Lower, and Shoes when such items "
    "exist in the candidates. Add Outerwear/Accessories only from candidates.\n"
    "- Respect this priority order: 1) Weather 2) Occasion 3) Color harmony "
    "4) Skin tone 5) Body type 6) User preferences 7) Wear frequency.\n"
    "- Return valid JSON only, no prose outside JSON."
)


def _build_user_prompt(context: dict, candidates: list[dict], count: int) -> str:
    return (
        f"Build exactly {count} DISTINCT outfit options.\n\n"
        f"CONTEXT (weather, occasion, user profile, preferences):\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        f"CANDIDATE ITEMS (the ONLY items you may use):\n"
        f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        "Respond with JSON of this exact shape:\n"
        "{\n"
        '  "outfits": [\n'
        "    {\n"
        '      "upper_id": <item_id or null>,\n'
        '      "lower_id": <item_id or null>,\n'
        '      "shoes_id": <item_id or null>,\n'
        '      "outerwear_id": <item_id or null>,\n'
        '      "accessory_ids": [<item_id>, ...],\n'
        '      "reasoning": "why this outfit works",\n'
        '      "color_explanation": "color harmony explanation",\n'
        '      "weather_suitability": "how it suits the weather",\n'
        '      "occasion_suitability": "how it suits the occasion",\n'
        '      "styling_tips": "practical styling tips",\n'
        '      "confidence_score": <integer 0-100>\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Every *_id MUST be a numeric item_id that exists in CANDIDATE ITEMS."
    )


ATTRIBUTE_SYSTEM_PROMPT = (
    "You are a fashion taxonomy expert. Given a clothing category and "
    "subcategory, produce a concise list of practical attributes a person would "
    "use to describe and filter that item. Return JSON only."
)


def generate_attribute_schema(category: str, subcategory: str | None) -> list[dict]:
    """Ask Groq for 4-8 filterable attributes for a category/subcategory.

    Returns a list of field defs: {key, label, type:'select'|'text', options?}.
    Raises on API/parse errors so the caller can fall back to builtins.
    """
    client = _get_client()
    target = f"{subcategory} ({category})" if subcategory else category
    user_prompt = (
        f"Clothing type: {target}.\n"
        "List 4-8 attributes useful for filtering a personal wardrobe. Prefer "
        "'select' fields with 3-6 concrete options; use 'text' only when options "
        "are open-ended. Use short snake_case keys and human labels. Avoid "
        "duplicating these already-captured fields: name, brand, color, pattern, "
        "material, fit, size, season, weather, occasion, sleeve, neck.\n"
        "Respond as JSON of this exact shape:\n"
        '{ "attributes": [ {"key": "sole_type", "label": "Sole Type", '
        '"type": "select", "options": ["Rubber", "EVA", "Leather"]} ] }'
    )
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": ATTRIBUTE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    data = json.loads(content)
    attrs = data.get("attributes", [])
    if not isinstance(attrs, list):
        return []
    # Sanitize each field def.
    cleaned: list[dict] = []
    for a in attrs:
        if not isinstance(a, dict) or not a.get("key") or not a.get("label"):
            continue
        ftype = a.get("type") if a.get("type") in ("select", "text") else "text"
        field = {"key": str(a["key"]), "label": str(a["label"]), "type": ftype}
        if ftype == "select":
            opts = a.get("options") or []
            opts = [str(o) for o in opts if isinstance(o, (str, int, float))]
            if not opts:
                field["type"] = "text"
            else:
                field["options"] = opts[:8]
        cleaned.append(field)
    return cleaned[:8]


def generate_outfits(context: dict, candidates: list[dict], count: int) -> list[dict]:
    """Call Groq and return the raw list of outfit dicts (unvalidated)."""
    client = _get_client()
    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(context, candidates, count)},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    data = json.loads(content)
    outfits = data.get("outfits", [])
    if not isinstance(outfits, list):
        return []
    return outfits
