"""Contact models for the Advocacy CMS."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class ContactBase(BaseModel):
    """Base contact model with common fields."""
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    organization: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    website_url: Optional[HttpUrl] = None
    influence_score: Optional[int] = Field(None, ge=1, le=10)
    contact_status: str = Field("active", regex="^(active|inactive|archived)$")
    tags: Optional[str] = None
    notes: Optional[str] = None


class ContactCreate(ContactBase):
    """Model for creating a new contact."""
    pass


class ContactUpdate(BaseModel):
    """Model for updating an existing contact."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    organization: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    website_url: Optional[HttpUrl] = None
    influence_score: Optional[int] = Field(None, ge=1, le=10)
    contact_status: Optional[str] = Field(None, regex="^(active|inactive|archived)$")
    tags: Optional[str] = None
    notes: Optional[str] = None


class Contact(ContactBase):
    """Complete contact model with database fields."""
    contact_id: UUID
    created_at: datetime
    updated_at: datetime
    version: int
    group_memberships: Optional[List[str]] = []

    class Config:
        from_attributes = True


class ContactWithGroups(Contact):
    """Contact model with group details."""
    groups: List[dict] = []


class ContactGroupMembership(BaseModel):
    """Model for contact-group relationships."""
    contact_id: UUID
    group_id: UUID
    joined_at: datetime
    membership_status: str = Field("active", regex="^(active|inactive)$")
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ContactGroupMembershipCreate(BaseModel):
    """Model for creating contact-group membership."""
    group_id: UUID
    membership_status: str = Field("active", regex="^(active|inactive)$")
    notes: Optional[str] = None


class ContactListResponse(BaseModel):
    """Response model for contact list with pagination."""
    contacts: List[Contact]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool