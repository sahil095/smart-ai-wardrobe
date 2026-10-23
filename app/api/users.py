"""User CRUD API."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, own
from app.models import User
from app.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(user: User = Depends(current_user)):
    return [user]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, user: User = Depends(current_user)):
    raise HTTPException(
        status_code=403,
        detail="Create an account from the sign-in page",
    )


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    own(user, user_id)
    found = db.get(User, user_id)
    if not found:
        raise HTTPException(status_code=404, detail="User not found")
    return found


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    own(user, user_id)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    own(user, user_id)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    request.session.clear()
    db.delete(user)
    db.commit()
