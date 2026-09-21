"""Metadata API: exposes dropdown/option lists to the frontend."""
from fastapi import APIRouter

from app import constants

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/options")
def get_options():
    return constants.all_options()
