"""Group models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class GroupBase(BaseModel):
    """Base group model."""
    group_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class GroupCreate(GroupBase):
    """Model for creating a group."""
    pass

class GroupUpdate(BaseModel):
    """Model for updating a group."""
    group_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class Group(GroupBase):
    """Complete group model."""
    group_id: UUID
    created_at: datetime
    updated_at: datetime
    version: int
    member_count: Optional[int] = 0
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True