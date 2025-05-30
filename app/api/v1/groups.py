"""Groups API endpoints."""
from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID
import logging
from app.models.group import Group, GroupCreate, GroupUpdate
from app.database import execute_query, get_db_cursor

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(group_data: GroupCreate):
    """Create a new group."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO cms_core.groups (group_name, description)
                VALUES (%s, %s)
                RETURNING group_id, group_name, description, created_at, updated_at, version
            """, (group_data.group_name, group_data.description))
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create group")
            
            return Group(**result, member_count=0)
    
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Group with name '{group_data.group_name}' already exists"
            )
        logger.error(f"Failed to create group: {e}")
        raise HTTPException(status_code=500, detail="Failed to create group")

@router.get("/", response_model=List[Group])
async def list_groups():
    """List all groups."""
    try:
        groups = execute_query("""
            SELECT 
                g.group_id,
                g.group_name,
                g.description,
                g.created_at,
                g.updated_at,
                g.version,
                COUNT(DISTINCT cgm.contact_id) as member_count
            FROM cms_core.groups g
            LEFT JOIN cms_core.contact_group_memberships cgm ON g.group_id = cgm.group_id
            GROUP BY g.group_id, g.group_name, g.description, g.created_at, g.updated_at, g.version
            ORDER BY g.group_name
        """)
        
        return [Group(**group) for group in (groups or [])]
    
    except Exception as e:
        logger.error(f"Failed to list groups: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve groups")

@router.get("/{group_id}", response_model=Group)
async def get_group(group_id: UUID):
    """Get a specific group."""
    try:
        result = execute_query("""
            SELECT 
                g.group_id,
                g.group_name,
                g.description,
                g.created_at,
                g.updated_at,
                g.version,
                COUNT(DISTINCT cgm.contact_id) as member_count
            FROM cms_core.groups g
            LEFT JOIN cms_core.contact_group_memberships cgm ON g.group_id = cgm.group_id
            WHERE g.group_id = %s
            GROUP BY g.group_id, g.group_name, g.description, g.created_at, g.updated_at, g.version
        """, (str(group_id),), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Group not found")
        
        return Group(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve group")

@router.put("/{group_id}", response_model=Group)
async def update_group(group_id: UUID, group_data: GroupUpdate):
    """Update a group."""
    try:
        # Build update query dynamically based on provided fields
        update_fields = []
        values = []
        
        if group_data.group_name is not None:
            update_fields.append("group_name = %s")
            values.append(group_data.group_name)
        
        if group_data.description is not None:
            update_fields.append("description = %s")
            values.append(group_data.description)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        values.append(str(group_id))
        
        with get_db_cursor() as cursor:
            cursor.execute(f"""
                UPDATE cms_core.groups 
                SET {', '.join(update_fields)}
                WHERE group_id = %s
                RETURNING group_id, group_name, description, created_at, updated_at, version
            """, values)
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Get member count
            cursor.execute("""
                SELECT COUNT(*) as member_count 
                FROM cms_core.contact_group_memberships 
                WHERE group_id = %s
            """, (str(group_id),))
            
            member_count = cursor.fetchone()['member_count']
            
            return Group(**result, member_count=member_count)
    
    except HTTPException:
        raise
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Group with name '{group_data.group_name}' already exists"
            )
        logger.error(f"Failed to update group: {e}")
        raise HTTPException(status_code=500, detail="Failed to update group")

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: UUID):
    """Delete a group."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                DELETE FROM cms_core.groups 
                WHERE group_id = %s
                RETURNING group_id
            """, (str(group_id),))
            
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Group not found")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete group: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete group")