"""Stylist chat and style-ideas API."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StylistMessage, User, WardrobeItem
from app.services import inspiration_service, memory_service, stylist_agent

router = APIRouter(tags=["stylist"])


class ChatIn(BaseModel):
    user_id: int
    message: str = Field(..., min_length=1, max_length=2000)


def _message_out(row: StylistMessage) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "extras": row.extras or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/api/stylist/messages")
def list_messages(user_id: int, db: Session = Depends(get_db)):
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    rows = db.scalars(
        select(StylistMessage)
        .where(StylistMessage.user_id == user_id)
        .order_by(StylistMessage.created_at.asc(), StylistMessage.id.asc())
    ).all()
    return [_message_out(row) for row in rows]


@router.delete("/api/stylist/messages", status_code=204)
def clear_messages(user_id: int, db: Session = Depends(get_db)):
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    db.execute(delete(StylistMessage).where(StylistMessage.user_id == user_id))
    db.commit()


@router.post("/api/stylist/chat")
async def chat(payload: ChatIn, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message is empty")

    history_rows = db.scalars(
        select(StylistMessage)
        .where(StylistMessage.user_id == user.id)
        .order_by(StylistMessage.created_at.asc(), StylistMessage.id.asc())
    ).all()
    history = [{"role": row.role, "content": row.content} for row in history_rows]

    try:
        result = await stylist_agent.reply(db, user, history, text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Stylist unavailable: {exc}"
        ) from exc

    extras = {}
    if result.get("outfits"):
        extras["outfits"] = result["outfits"]
    if result.get("ideas"):
        extras["ideas"] = result["ideas"]

    db.add(StylistMessage(user_id=user.id, role="user", content=text))
    assistant = StylistMessage(
        user_id=user.id,
        role="assistant",
        content=result.get("content") or "",
        extras=extras or None,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return _message_out(assistant)


@router.get("/api/style-ideas")
async def style_ideas(
    user_id: int,
    item_id: int | None = None,
    query: str | None = None,
    db: Session = Depends(get_db),
):
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    text = (query or "").strip()
    if item_id:
        item = db.get(WardrobeItem, item_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=404, detail="Item not found")
        text = inspiration_service.query_for_item(item)
    result = await inspiration_service.search(db, text)
    result["caption"] = "Similar looks. Not your photo."
    return result


@router.delete("/api/users/{user_id}/memories/{index}", status_code=204)
def delete_memory(user_id: int, index: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not memory_service.delete_at(user, index):
        raise HTTPException(status_code=404, detail="Memory not found")
    db.commit()
