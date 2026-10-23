"""Signed-in user, and a check that a wardrobe id is theirs."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if not user or not user.password_hash:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def own(user: User, user_id: int) -> User:
    """Refuse a request that names somebody else's wardrobe."""
    if int(user_id) != user.id:
        raise HTTPException(status_code=403, detail="That wardrobe is private")
    return user
