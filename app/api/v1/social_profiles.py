"""Social profiles API endpoints."""
from fastapi import APIRouter, HTTPException
from uuid import UUID
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def list_social_profiles():
    """List all social profiles."""
    return []

@router.post("/")
async def create_social_profile():
    """Create a new social profile."""
    raise HTTPException(status_code=501, detail="Not implemented yet")