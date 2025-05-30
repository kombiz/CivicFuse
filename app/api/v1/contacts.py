"""Contact management API endpoints."""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.models.contact import (
    Contact,
    ContactCreate,
    ContactUpdate,
    ContactWithGroups,
    ContactListResponse,
    ContactGroupMembershipCreate
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=ContactListResponse)
async def list_contacts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, email, or organization"),
    group_id: Optional[UUID] = Query(None, description="Filter by group membership"),
    status: Optional[str] = Query(None, regex="^(active|inactive|archived)$", description="Filter by status"),
    db=Depends(get_db_connection)
) -> ContactListResponse:
    """List contacts with pagination and filtering.
    
    Args:
        page: Page number (1-based)
        per_page: Number of contacts per page
        search: Search term for name, email, or organization
        group_id: Filter contacts by group membership
        status: Filter by contact status
        db: Database connection
        
    Returns:
        Paginated list of contacts
        
    Raises:
        HTTPException: If database query fails
    """
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Build WHERE clause
            where_conditions = []
            params = []
            
            if search:
                where_conditions.append(
                    "(c.full_name ILIKE %s OR c.email ILIKE %s OR c.organization ILIKE %s)"
                )
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])
            
            if group_id:
                where_conditions.append(
                    "EXISTS (SELECT 1 FROM cms_core.contact_group_memberships cgm "
                    "WHERE cgm.contact_id = c.contact_id AND cgm.group_id = %s "
                    "AND cgm.membership_status = 'active')"
                )
                params.append(str(group_id))
            
            if status:
                where_conditions.append("c.contact_status = %s")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Count total records
            count_query = f"""
                SELECT COUNT(*) as total
                FROM cms_core.contacts c
                {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()["total"]
            
            # Calculate pagination
            offset = (page - 1) * per_page
            has_next = total > page * per_page
            has_prev = page > 1
            
            # Fetch contacts
            contacts_query = f"""
                SELECT 
                    c.contact_id,
                    c.full_name,
                    c.email,
                    c.phone,
                    c.organization,
                    c.job_title,
                    c.bio,
                    c.location,
                    c.website_url,
                    c.influence_score,
                    c.contact_status,
                    c.tags,
                    c.notes,
                    c.created_at,
                    c.updated_at,
                    c.version
                FROM cms_core.contacts c
                {where_clause}
                ORDER BY c.full_name
                LIMIT %s OFFSET %s
            """
            params.extend([per_page, offset])
            cursor.execute(contacts_query, params)
            contact_rows = cursor.fetchall()
            
            contacts = [Contact(**dict(row)) for row in contact_rows]
            
            return ContactListResponse(
                contacts=contacts,
                total=total,
                page=page,
                per_page=per_page,
                has_next=has_next,
                has_prev=has_prev
            )
            
    except Exception as e:
        logger.error(f"Failed to list contacts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contacts"
        )


@router.post("/", response_model=Contact, status_code=status.HTTP_201_CREATED)
async def create_contact(
    contact_data: ContactCreate,
    db=Depends(get_db_connection)
) -> Contact:
    """Create a new contact.
    
    Args:
        contact_data: Contact information
        db: Database connection
        
    Returns:
        Created contact with generated ID and timestamps
        
    Raises:
        HTTPException: If email already exists or database insertion fails
    """
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check for duplicate email
            cursor.execute(
                "SELECT contact_id FROM cms_core.contacts WHERE email = %s",
                (contact_data.email,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Contact with email {contact_data.email} already exists"
                )
            
            # Insert new contact
            insert_query = """
                INSERT INTO cms_core.contacts (
                    full_name, email, phone, organization, job_title, bio,
                    location, website_url, influence_score, contact_status, tags, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """
            
            cursor.execute(insert_query, (
                contact_data.full_name,
                contact_data.email,
                contact_data.phone,
                contact_data.organization,
                contact_data.job_title,
                contact_data.bio,
                contact_data.location,
                str(contact_data.website_url) if contact_data.website_url else None,
                contact_data.influence_score,
                contact_data.contact_status,
                contact_data.tags,
                contact_data.notes
            ))
            
            contact_row = cursor.fetchone()
            db.commit()
            
            logger.info(f"Created contact: {contact_row['contact_id']}")
            return Contact(**dict(contact_row))
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create contact: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create contact"
        )


@router.get("/{contact_id}", response_model=ContactWithGroups)
async def get_contact(
    contact_id: UUID,
    db=Depends(get_db_connection)
) -> ContactWithGroups:
    """Get a specific contact with group memberships.
    
    Args:
        contact_id: Contact UUID
        db: Database connection
        
    Returns:
        Contact details with group memberships
        
    Raises:
        HTTPException: If contact not found
    """
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get contact details
            contact_query = """
                SELECT 
                    contact_id, full_name, email, phone, organization, job_title,
                    bio, location, website_url, influence_score, contact_status,
                    tags, notes, created_at, updated_at, version
                FROM cms_core.contacts
                WHERE contact_id = %s
            """
            cursor.execute(contact_query, (str(contact_id),))
            contact_row = cursor.fetchone()
            
            if not contact_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact not found"
                )
            
            # Get group memberships
            groups_query = """
                SELECT 
                    g.group_id,
                    g.group_name,
                    g.description,
                    cgm.joined_at,
                    cgm.membership_status,
                    cgm.notes as membership_notes
                FROM cms_core.contact_group_memberships cgm
                JOIN cms_core.groups g ON cgm.group_id = g.group_id
                WHERE cgm.contact_id = %s
                ORDER BY g.group_name
            """
            cursor.execute(groups_query, (str(contact_id),))
            group_rows = cursor.fetchall()
            
            contact_data = dict(contact_row)
            contact_data["groups"] = [dict(row) for row in group_rows]
            
            return ContactWithGroups(**contact_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contact {contact_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contact"
        )


@router.put("/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: UUID,
    contact_data: ContactUpdate,
    db=Depends(get_db_connection)
) -> Contact:
    """Update an existing contact.
    
    Args:
        contact_id: Contact UUID
        contact_data: Updated contact information
        db: Database connection
        
    Returns:
        Updated contact
        
    Raises:
        HTTPException: If contact not found or email conflict
    """
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if contact exists
            cursor.execute(
                "SELECT version FROM cms_core.contacts WHERE contact_id = %s",
                (str(contact_id),)
            )
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact not found"
                )
            
            # Check for email conflicts (if email is being updated)
            if contact_data.email:
                cursor.execute(
                    "SELECT contact_id FROM cms_core.contacts WHERE email = %s AND contact_id != %s",
                    (contact_data.email, str(contact_id))
                )
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Contact with email {contact_data.email} already exists"
                    )
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            for field, value in contact_data.dict(exclude_unset=True).items():
                if field == "website_url" and value:
                    value = str(value)
                update_fields.append(f"{field} = %s")
                params.append(value)
            
            if not update_fields:
                # No fields to update
                cursor.execute(
                    "SELECT * FROM cms_core.contacts WHERE contact_id = %s",
                    (str(contact_id),)
                )
                return Contact(**dict(cursor.fetchone()))
            
            update_fields.append("updated_at = NOW()")
            update_fields.append("version = version + 1")
            params.append(str(contact_id))
            
            update_query = f"""
                UPDATE cms_core.contacts
                SET {', '.join(update_fields)}
                WHERE contact_id = %s
                RETURNING *
            """
            
            cursor.execute(update_query, params)
            updated_row = cursor.fetchone()
            db.commit()
            
            logger.info(f"Updated contact: {contact_id}")
            return Contact(**dict(updated_row))
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update contact {contact_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update contact"
        )


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    db=Depends(get_db_connection)
):
    """Delete a contact and all related data.
    
    Args:
        contact_id: Contact UUID
        db: Database connection
        
    Raises:
        HTTPException: If contact not found
    """
    try:
        with db.cursor() as cursor:
            # Check if contact exists
            cursor.execute(
                "SELECT 1 FROM cms_core.contacts WHERE contact_id = %s",
                (str(contact_id),)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact not found"
                )
            
            # Delete group memberships first (foreign key constraint)
            cursor.execute(
                "DELETE FROM cms_core.contact_group_memberships WHERE contact_id = %s",
                (str(contact_id),)
            )
            
            # Delete contact
            cursor.execute(
                "DELETE FROM cms_core.contacts WHERE contact_id = %s",
                (str(contact_id),)
            )
            
            db.commit()
            logger.info(f"Deleted contact: {contact_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete contact {contact_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete contact"
        )


@router.post("/{contact_id}/groups", status_code=status.HTTP_201_CREATED)
async def add_contact_to_group(
    contact_id: UUID,
    membership_data: ContactGroupMembershipCreate,
    db=Depends(get_db_connection)
):
    """Add a contact to a group.
    
    Args:
        contact_id: Contact UUID
        membership_data: Group membership details
        db: Database connection
        
    Raises:
        HTTPException: If contact/group not found or membership exists
    """
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify contact exists
            cursor.execute(
                "SELECT 1 FROM cms_core.contacts WHERE contact_id = %s",
                (str(contact_id),)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact not found"
                )
            
            # Verify group exists
            cursor.execute(
                "SELECT 1 FROM cms_core.groups WHERE group_id = %s",
                (str(membership_data.group_id),)
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Group not found"
                )
            
            # Check if membership already exists
            cursor.execute(
                "SELECT 1 FROM cms_core.contact_group_memberships WHERE contact_id = %s AND group_id = %s",
                (str(contact_id), str(membership_data.group_id))
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Contact is already a member of this group"
                )
            
            # Add membership
            cursor.execute(
                """
                INSERT INTO cms_core.contact_group_memberships 
                (contact_id, group_id, membership_status, notes)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    str(contact_id),
                    str(membership_data.group_id),
                    membership_data.membership_status,
                    membership_data.notes
                )
            )
            
            db.commit()
            logger.info(f"Added contact {contact_id} to group {membership_data.group_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add contact to group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add contact to group"
        )


@router.delete("/{contact_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact_from_group(
    contact_id: UUID,
    group_id: UUID,
    db=Depends(get_db_connection)
):
    """Remove a contact from a group.
    
    Args:
        contact_id: Contact UUID
        group_id: Group UUID
        db: Database connection
        
    Raises:
        HTTPException: If membership not found
    """
    try:
        with db.cursor() as cursor:
            # Remove membership
            cursor.execute(
                "DELETE FROM cms_core.contact_group_memberships WHERE contact_id = %s AND group_id = %s",
                (str(contact_id), str(group_id))
            )
            
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact is not a member of this group"
                )
            
            db.commit()
            logger.info(f"Removed contact {contact_id} from group {group_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove contact from group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove contact from group"
        )