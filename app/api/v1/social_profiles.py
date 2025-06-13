"""Social profiles API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
import logging
from app.database import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for request/response validation
class SocialProfileCreate(BaseModel):
    contact_id: UUID
    platform: str = Field(..., pattern="^(Twitter|BlueSky|LinkedIn|Facebook|Instagram|Threads|TikTok|RSS|Podcast|Website|Other)$")
    username_or_handle: Optional[str] = None
    profile_url: str
    notes: Optional[str] = None

class SocialProfileUpdate(BaseModel):
    platform: Optional[str] = Field(None, pattern="^(Twitter|BlueSky|LinkedIn|Facebook|Instagram|Threads|TikTok|RSS|Podcast|Website|Other)$")
    username_or_handle: Optional[str] = None
    profile_url: Optional[str] = None
    notes: Optional[str] = None

class SocialProfileResponse(BaseModel):
    profile_id: UUID
    contact_id: UUID
    platform: str
    username_or_handle: Optional[str]
    profile_url: str
    notes: Optional[str]
    added_at: str
    updated_at: str
    version: int

@router.get("/", response_model=List[SocialProfileResponse])
async def list_social_profiles(contact_id: Optional[UUID] = Query(None, description="Filter by contact ID")):
    """List social profiles, optionally filtered by contact_id."""
    try:
        if contact_id:
            # Get profiles for specific contact
            query = """
                SELECT profile_id, contact_id, platform, username_or_handle, profile_url, notes,
                       added_at, updated_at, version
                FROM cms_core.social_profiles
                WHERE contact_id = %s
                ORDER BY platform, added_at
            """
            profiles = execute_query(query, (contact_id,))
        else:
            # Get all profiles
            query = """
                SELECT profile_id, contact_id, platform, username_or_handle, profile_url, notes,
                       added_at, updated_at, version
                FROM cms_core.social_profiles
                ORDER BY added_at DESC
            """
            profiles = execute_query(query)
        
        if not profiles:
            return []
        
        return [
            SocialProfileResponse(
                profile_id=profile["profile_id"],
                contact_id=profile["contact_id"],
                platform=profile["platform"],
                username_or_handle=profile["username_or_handle"],
                profile_url=profile["profile_url"],
                notes=profile["notes"],
                added_at=profile["added_at"].isoformat() if profile["added_at"] else "",
                updated_at=profile["updated_at"].isoformat() if profile["updated_at"] else "",
                version=profile["version"]
            )
            for profile in profiles
        ]
        
    except Exception as e:
        logger.error(f"Failed to list social profiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve social profiles")

@router.post("/", response_model=SocialProfileResponse, status_code=201)
async def create_social_profile(profile_data: SocialProfileCreate):
    """Create a new social profile."""
    try:
        # First check if contact exists
        contact_check = execute_query(
            "SELECT contact_id FROM cms_core.contacts WHERE contact_id = %s",
            (profile_data.contact_id,),
            fetch_one=True
        )
        
        if not contact_check:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        # Insert the new social profile
        insert_query = """
            INSERT INTO cms_core.social_profiles (contact_id, platform, username_or_handle, profile_url, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING profile_id, contact_id, platform, username_or_handle, profile_url, notes,
                      added_at, updated_at, version
        """
        
        result = execute_query(insert_query, (
            profile_data.contact_id,
            profile_data.platform,
            profile_data.username_or_handle,
            profile_data.profile_url,
            profile_data.notes
        ), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create social profile")
        
        logger.info(f"Created social profile: {result['profile_id']} for contact: {profile_data.contact_id}")
        
        return SocialProfileResponse(
            profile_id=result["profile_id"],
            contact_id=result["contact_id"],
            platform=result["platform"],
            username_or_handle=result["username_or_handle"],
            profile_url=result["profile_url"],
            notes=result["notes"],
            added_at=result["added_at"].isoformat() if result["added_at"] else "",
            updated_at=result["updated_at"].isoformat() if result["updated_at"] else "",
            version=result["version"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create social profile: {e}")
        if "duplicate key value" in str(e).lower():
            raise HTTPException(status_code=400, detail="Social profile URL already exists for this contact")
        raise HTTPException(status_code=500, detail="Failed to create social profile")

@router.get("/{profile_id}", response_model=SocialProfileResponse)
async def get_social_profile(profile_id: UUID):
    """Get a specific social profile by ID."""
    try:
        query = """
            SELECT profile_id, contact_id, platform, username_or_handle, profile_url, notes,
                   added_at, updated_at, version
            FROM cms_core.social_profiles
            WHERE profile_id = %s
        """
        
        result = execute_query(query, (profile_id,), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Social profile not found")
        
        return SocialProfileResponse(
            profile_id=result["profile_id"],
            contact_id=result["contact_id"],
            platform=result["platform"],
            username_or_handle=result["username_or_handle"],
            profile_url=result["profile_url"],
            notes=result["notes"],
            added_at=result["added_at"].isoformat() if result["added_at"] else "",
            updated_at=result["updated_at"].isoformat() if result["updated_at"] else "",
            version=result["version"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get social profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve social profile")

@router.put("/{profile_id}", response_model=SocialProfileResponse)
async def update_social_profile(profile_id: UUID, profile_data: SocialProfileUpdate):
    """Update a social profile."""
    try:
        # First check if profile exists
        existing_profile = execute_query(
            "SELECT profile_id FROM cms_core.social_profiles WHERE profile_id = %s",
            (profile_id,),
            fetch_one=True
        )
        
        if not existing_profile:
            raise HTTPException(status_code=404, detail="Social profile not found")
        
        # Build dynamic update query based on provided fields
        update_fields = []
        update_values = []
        
        if profile_data.platform is not None:
            update_fields.append("platform = %s")
            update_values.append(profile_data.platform)
        
        if profile_data.username_or_handle is not None:
            update_fields.append("username_or_handle = %s")
            update_values.append(profile_data.username_or_handle)
        
        if profile_data.profile_url is not None:
            update_fields.append("profile_url = %s")
            update_values.append(profile_data.profile_url)
        
        if profile_data.notes is not None:
            update_fields.append("notes = %s")
            update_values.append(profile_data.notes)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        
        # Add version increment and updated_at
        update_fields.extend(["updated_at = CURRENT_TIMESTAMP", "version = version + 1"])
        update_values.append(profile_id)
        
        update_query = f"""
            UPDATE cms_core.social_profiles SET {', '.join(update_fields)}
            WHERE profile_id = %s
            RETURNING profile_id, contact_id, platform, username_or_handle, profile_url, notes,
                      added_at, updated_at, version
        """
        
        result = execute_query(update_query, update_values, fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update social profile")
        
        logger.info(f"Updated social profile: {profile_id}")
        
        return SocialProfileResponse(
            profile_id=result["profile_id"],
            contact_id=result["contact_id"],
            platform=result["platform"],
            username_or_handle=result["username_or_handle"],
            profile_url=result["profile_url"],
            notes=result["notes"],
            added_at=result["added_at"].isoformat() if result["added_at"] else "",
            updated_at=result["updated_at"].isoformat() if result["updated_at"] else "",
            version=result["version"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update social profile {profile_id}: {e}")
        if "duplicate key value" in str(e).lower():
            raise HTTPException(status_code=400, detail="Social profile URL already exists for this contact")
        raise HTTPException(status_code=500, detail="Failed to update social profile")

@router.delete("/{profile_id}", status_code=204)
async def delete_social_profile(profile_id: UUID):
    """Delete a social profile."""
    try:
        # Check if profile exists and delete it
        delete_query = """
            DELETE FROM cms_core.social_profiles 
            WHERE profile_id = %s
            RETURNING profile_id
        """
        
        result = execute_query(delete_query, (profile_id,), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Social profile not found")
        
        logger.info(f"Deleted social profile: {profile_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete social profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete social profile")