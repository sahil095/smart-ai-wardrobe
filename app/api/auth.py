"""Sign in, create an account, and claim an existing wardrobe."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models import User
from app.schemas import UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(..., min_length=1, max_length=40)
    password: str = Field(..., min_length=1, max_length=200)


class RegisterIn(Credentials):
    name: str = Field(..., min_length=1, max_length=120)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=200)


def _login(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = user.id


def _apply_login(user: User, username: str, password: str) -> None:
    user.username = username
    user.password_hash = auth_service.hash_password(password)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Whether an existing wardrobe still needs its first username."""
    return {"needs_claim": auth_service.oldest_unclaimed(db) is not None}


@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    try:
        username = auth_service.normalize_username(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if auth_service.username_taken(db, username):
        raise HTTPException(status_code=409, detail="That username is taken")
    user = User(name=payload.name.strip(), username=username)
    try:
        user.password_hash = auth_service.hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is taken") from exc
    db.refresh(user)
    _login(request, user)
    return user


@router.post("/claim", response_model=UserOut)
def claim(payload: Credentials, request: Request, db: Session = Depends(get_db)):
    """Attach a login to the existing wardrobe that has no password yet."""
    user = auth_service.oldest_unclaimed(db)
    if not user:
        raise HTTPException(status_code=404, detail="No wardrobe is waiting for a login")
    try:
        username = auth_service.normalize_username(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if auth_service.username_taken(db, username, except_id=user.id):
        raise HTTPException(status_code=409, detail="That username is taken")
    try:
        _apply_login(user, username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is taken") from exc
    db.refresh(user)
    _login(request, user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: Credentials, request: Request, db: Session = Depends(get_db)):
    try:
        username = auth_service.normalize_username(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Wrong username or password") from exc
    user = db.scalar(select(User).where(User.username == username))
    if not user or not auth_service.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Wrong username or password")
    _login(request, user)
    return user


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.session.clear()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/password", status_code=204)
def change_password(
    payload: PasswordChange,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not auth_service.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is wrong")
    try:
        user.password_hash = auth_service.hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
