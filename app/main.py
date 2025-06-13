"""FastAPI application entry point."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from app.config import settings
from app.database import test_connection, health_check

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    logger.info("Starting Advocacy CMS application...")
    
    # Test database connection
    if not test_connection():
        logger.warning("Database connection failed - some features may be unavailable")
    else:
        logger.info("Database connection established successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Advocacy CMS application...")

# Create FastAPI instance
app = FastAPI(
    title="Advocacy CMS",
    description="Contact Management System for Advocacy",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Setup templates
import os
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    db_health = health_check()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": "1.0.0",
        "environment": settings.app_env,
        "database": db_health
    }

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirects to dashboard or shows landing page."""
    # For now, redirect to dashboard
    return RedirectResponse(url="/dashboard", status_code=302)

# Dashboard endpoint
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page."""
    # Get statistics from database
    from app.database import execute_query
    
    stats = {
        "total_contacts": 0,
        "total_groups": 0,
        "total_social_profiles": 0,
        "recent_shares": 0
    }
    
    try:
        # Get counts
        contacts_count = execute_query("SELECT COUNT(*) as count FROM cms_core.contacts", fetch_one=True)
        if contacts_count:
            stats["total_contacts"] = contacts_count["count"]
        
        groups_count = execute_query("SELECT COUNT(*) as count FROM cms_core.groups", fetch_one=True)
        if groups_count:
            stats["total_groups"] = groups_count["count"]
        
        profiles_count = execute_query("SELECT COUNT(*) as count FROM cms_core.social_profiles", fetch_one=True)
        if profiles_count:
            stats["total_social_profiles"] = profiles_count["count"]
        
        # Recent shares (last 7 days)
        recent_shares = execute_query("""
            SELECT COUNT(*) as count 
            FROM cms_core.shared_content_log 
            WHERE shared_at > NOW() - INTERVAL '7 days'
        """, fetch_one=True)
        if recent_shares:
            stats["recent_shares"] = recent_shares["count"]
    except Exception as e:
        logger.error(f"Failed to get dashboard statistics: {e}")
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request,
            "stats": stats,
            "app_env": settings.app_env
        }
    )

# Groups list page
@app.get("/groups", response_class=HTMLResponse)
async def groups_list(request: Request):
    """Groups list page."""
    from app.database import execute_query
    
    groups = []
    try:
        # Get all groups with member counts
        groups_data = execute_query("""
            SELECT 
                g.group_id,
                g.group_name,
                g.description,
                g.created_at,
                COUNT(DISTINCT cgm.contact_id) as member_count
            FROM cms_core.groups g
            LEFT JOIN cms_core.contact_group_memberships cgm ON g.group_id = cgm.group_id
            GROUP BY g.group_id, g.group_name, g.description, g.created_at
            ORDER BY g.group_name
        """)
        
        if groups_data:
            groups = groups_data
    except Exception as e:
        logger.error(f"Failed to get groups: {e}")
    
    return templates.TemplateResponse(
        "groups/list.html",
        {
            "request": request,
            "groups": groups
        }
    )

# New group page
@app.get("/groups/new", response_class=HTMLResponse)
async def new_group(request: Request):
    """New group creation page."""
    return templates.TemplateResponse(
        "groups/new.html",
        {"request": request}
    )

# Edit group page
@app.get("/groups/{group_id}/edit", response_class=HTMLResponse)
async def edit_group(request: Request, group_id: str):
    """Edit group page."""
    import httpx
    
    try:
        # Fetch group data from API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/api/v1/groups/{group_id}",
                timeout=30.0
            )
            response.raise_for_status()
            group_data = response.json()
        
        return templates.TemplateResponse(
            "groups/edit.html",
            {
                "request": request,
                "group": group_data
            }
        )
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
        logger.error(f"Failed to fetch group {group_id}: {e}")
        return templates.TemplateResponse(
            "groups/edit.html",
            {
                "request": request,
                "error": "Failed to load group data. Please try again."
            },
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching group {group_id}: {e}")
        return templates.TemplateResponse(
            "groups/edit.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            },
            status_code=500
        )

# Create new group
@app.post("/groups/new")
async def create_group(request: Request):
    """Create a new group from form data."""
    import httpx
    from fastapi.responses import RedirectResponse
    
    try:
        # Get form data
        form_data = await request.form()
        group_data = {
            "group_name": form_data.get("group_name"),
            "description": form_data.get("description") or None
        }
        
        # Make API call to create group
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8000/api/v1/groups/",
                json=group_data,
                timeout=30.0
            )
            response.raise_for_status()
        
        # Redirect to groups list on success
        return RedirectResponse(url="/groups", status_code=302)
        
    except httpx.HTTPError as e:
        logger.error(f"Failed to create group: {e}")
        # Return to form with error (in production, would show error message)
        return templates.TemplateResponse(
            "groups/new.html",
            {
                "request": request,
                "error": "Failed to create group. Please try again."
            },
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error creating group: {e}")
        return templates.TemplateResponse(
            "groups/new.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            },
            status_code=500
        )

# Update group
@app.post("/groups/{group_id}/edit")
async def update_group(request: Request, group_id: str):
    """Update a group from form data."""
    import httpx
    from fastapi.responses import RedirectResponse
    
    try:
        # Get form data
        form_data = await request.form()
        group_data = {
            "group_name": form_data.get("group_name"),
            "description": form_data.get("description") or None
        }
        
        # Make API call to update group
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://localhost:8000/api/v1/groups/{group_id}",
                json=group_data,
                timeout=30.0
            )
            response.raise_for_status()
        
        # Redirect to groups list on success
        return RedirectResponse(url="/groups", status_code=302)
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
        logger.error(f"Failed to update group {group_id}: {e}")
        
        # Try to fetch group data to redisplay form with error
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/v1/groups/{group_id}",
                    timeout=30.0
                )
                group_data = response.json() if response.status_code == 200 else None
        except:
            group_data = None
        
        return templates.TemplateResponse(
            "groups/edit.html",
            {
                "request": request,
                "group": group_data,
                "error": "Failed to update group. Please try again."
            },
            status_code=500
        )
    except Exception as e:
        logger.error(f"Unexpected error updating group {group_id}: {e}")
        
        # Try to fetch group data to redisplay form with error
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/v1/groups/{group_id}",
                    timeout=30.0
                )
                group_data = response.json() if response.status_code == 200 else None
        except:
            group_data = None
        
        return templates.TemplateResponse(
            "groups/edit.html",
            {
                "request": request,
                "group": group_data,
                "error": "An unexpected error occurred. Please try again."
            },
            status_code=500
        )

# Contacts list page
@app.get("/contacts", response_class=HTMLResponse)
async def contacts_list(request: Request):
    """Contacts list page."""
    from app.database import execute_query
    
    contacts = []
    try:
        # Get all contacts with group counts
        contacts_data = execute_query("""
            SELECT 
                c.contact_id,
                c.full_name,
                c.email,
                c.organization,
                c.created_at,
                COUNT(DISTINCT cgm.group_id) as group_count
            FROM cms_core.contacts c
            LEFT JOIN cms_core.contact_group_memberships cgm ON c.contact_id = cgm.contact_id
            GROUP BY c.contact_id, c.full_name, c.email, c.organization, c.created_at
            ORDER BY c.full_name
        """)
        
        if contacts_data:
            contacts = contacts_data
    except Exception as e:
        logger.error(f"Failed to get contacts: {e}")
    
    return templates.TemplateResponse(
        "contacts/list.html",
        {
            "request": request,
            "contacts": contacts
        }
    )

# New contact page
@app.get("/contacts/new", response_class=HTMLResponse)
async def new_contact(request: Request):
    """New contact creation page."""
    return templates.TemplateResponse(
        "contacts/new.html",
        {"request": request}
    )

# Create new contact
@app.post("/contacts/new")
async def create_contact(request: Request):
    """Create a new contact from form data."""
    from fastapi.responses import RedirectResponse
    from app.database import execute_query
    
    try:
        # Get form data
        form_data = await request.form()
        
        # Handle influence_score (convert to int if provided)
        influence_score = form_data.get("influence_score")
        if influence_score and influence_score.isdigit():
            influence_score = int(influence_score)
        else:
            influence_score = None
        
        # Insert directly into database
        insert_query = """
            INSERT INTO cms_core.contacts (
                full_name, email, phone, organization, job_title, bio,
                location, website_url, influence_score, contact_status, tags, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING contact_id
        """
        
        result = execute_query(insert_query, (
            form_data.get("full_name"),
            form_data.get("email"),
            form_data.get("phone") or None,
            form_data.get("organization") or None,
            form_data.get("job_title") or None,
            form_data.get("bio") or None,
            form_data.get("location") or None,
            form_data.get("website_url") or None,
            influence_score,
            form_data.get("contact_status", "active"),
            form_data.get("tags") or None,
            form_data.get("notes") or None
        ), fetch_one=True)
        
        if result:
            logger.info(f"Created contact: {result['contact_id']}")
            # Redirect to contacts list on success
            return RedirectResponse(url="/contacts", status_code=302)
        else:
            raise Exception("Failed to insert contact")
        
    except Exception as e:
        logger.error(f"Failed to create contact: {e}")
        return templates.TemplateResponse(
            "contacts/new.html",
            {
                "request": request,
                "error": "Failed to create contact. Please check your input and try again."
            },
            status_code=500
        )

# Edit contact page
@app.get("/contacts/{contact_id}/edit", response_class=HTMLResponse)
async def edit_contact(request: Request, contact_id: str):
    """Edit contact page."""
    from app.database import execute_query
    
    try:
        # Fetch contact data from database
        contact_query = """
            SELECT contact_id, full_name, email, phone, organization, job_title, bio,
                   location, website_url, influence_score, contact_status, tags, notes,
                   created_at, updated_at, version
            FROM cms_core.contacts
            WHERE contact_id = %s
        """
        
        contact_data = execute_query(contact_query, (contact_id,), fetch_one=True)
        
        if not contact_data:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
        
        return templates.TemplateResponse(
            "contacts/edit.html",
            {
                "request": request,
                "contact": contact_data
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error fetching contact {contact_id}: {e}")
        return templates.TemplateResponse(
            "contacts/edit.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            },
            status_code=500
        )

# Update contact
@app.post("/contacts/{contact_id}/edit")
async def update_contact(request: Request, contact_id: str):
    """Update a contact from form data."""
    from fastapi.responses import RedirectResponse
    from app.database import execute_query
    
    try:
        # Get form data
        form_data = await request.form()
        
        # Handle influence_score (convert to int if provided)
        influence_score = form_data.get("influence_score")
        if influence_score and influence_score.isdigit():
            influence_score = int(influence_score)
        else:
            influence_score = None
        
        # Update contact in database
        update_query = """
            UPDATE cms_core.contacts SET
                full_name = %s, email = %s, phone = %s, organization = %s, job_title = %s, bio = %s,
                location = %s, website_url = %s, influence_score = %s, contact_status = %s, tags = %s, notes = %s,
                updated_at = CURRENT_TIMESTAMP, version = COALESCE(version, 0) + 1
            WHERE contact_id = %s
            RETURNING contact_id
        """
        
        result = execute_query(update_query, (
            form_data.get("full_name"),
            form_data.get("email"),
            form_data.get("phone") or None,
            form_data.get("organization") or None,
            form_data.get("job_title") or None,
            form_data.get("bio") or None,
            form_data.get("location") or None,
            form_data.get("website_url") or None,
            influence_score,
            form_data.get("contact_status", "active"),
            form_data.get("tags") or None,
            form_data.get("notes") or None,
            contact_id
        ), fetch_one=True)
        
        if result:
            logger.info(f"Updated contact: {result['contact_id']}")
            # Redirect to contacts list on success
            return RedirectResponse(url="/contacts", status_code=302)
        else:
            raise Exception("Contact not found or failed to update")
        
    except Exception as e:
        logger.error(f"Failed to update contact {contact_id}: {e}")
        
        # Try to fetch contact data to redisplay form with error
        try:
            contact_query = """
                SELECT contact_id, full_name, email, phone, organization, job_title, bio,
                       location, website_url, influence_score, contact_status, tags, notes,
                       created_at, updated_at, version
                FROM cms_core.contacts
                WHERE contact_id = %s
            """
            contact_data = execute_query(contact_query, (contact_id,), fetch_one=True)
        except:
            contact_data = None
        
        return templates.TemplateResponse(
            "contacts/edit.html",
            {
                "request": request,
                "contact": contact_data,
                "error": "Failed to update contact. Please check your input and try again."
            },
            status_code=500
        )

# Contact detail page
@app.get("/contacts/{contact_id}/detail", response_class=HTMLResponse)
async def contact_detail(request: Request, contact_id: str):
    """Contact detail page with social profiles."""
    import httpx
    from app.database import execute_query
    
    try:
        # Get contact details from database
        contact_query = """
            SELECT contact_id, full_name, email, phone, organization, job_title, bio,
                   location, website_url, influence_score, contact_status, tags, notes,
                   created_at, updated_at, version
            FROM cms_core.contacts
            WHERE contact_id = %s
        """
        
        contact_data = execute_query(contact_query, (contact_id,), fetch_one=True)
        
        if not contact_data:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404
            )
        
        # Get group memberships for this contact
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
        groups_data = execute_query(groups_query, (contact_id,))
        contact_data["groups"] = groups_data if groups_data else []
        
        # Get social profiles for this contact using API
        async with httpx.AsyncClient() as client:
            profiles_response = await client.get(
                f"http://localhost:8000/api/v1/social-profiles/?contact_id={contact_id}",
                timeout=30.0
            )
            profiles_response.raise_for_status()
            social_profiles = profiles_response.json()
        
        return templates.TemplateResponse(
            "contacts/detail.html",
            {
                "request": request,
                "contact": contact_data,
                "social_profiles": social_profiles
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch social profiles for contact {contact_id}: {e}")
        return templates.TemplateResponse(
            "contacts/detail.html",
            {
                "request": request,
                "contact": contact_data if 'contact_data' in locals() else None,
                "social_profiles": [],
                "error": "Failed to load social profiles."
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching contact {contact_id}: {e}")
        return templates.TemplateResponse(
            "contacts/detail.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            },
            status_code=500
        )

# Create new social profile for contact
@app.post("/contacts/{contact_id}/social-profiles/new")
async def create_contact_social_profile(request: Request, contact_id: str):
    """Create a new social profile for a contact from form data."""
    import httpx
    from fastapi.responses import RedirectResponse
    
    try:
        # Get form data
        form_data = await request.form()
        profile_data = {
            "contact_id": contact_id,
            "platform": form_data.get("platform"),
            "username_or_handle": form_data.get("username_or_handle") or None,
            "profile_url": form_data.get("profile_url"),
            "notes": form_data.get("notes") or None
        }
        
        # Make API call to create social profile
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:8000/api/v1/social-profiles/",
                json=profile_data,
                timeout=30.0
            )
            response.raise_for_status()
        
        # Redirect back to contact detail page on success
        return RedirectResponse(url=f"/contacts/{contact_id}/detail", status_code=302)
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to create social profile for contact {contact_id}: {e}")
        # Redirect back with error (in a real app we'd show the error message)
        return RedirectResponse(url=f"/contacts/{contact_id}/detail", status_code=302)
    except Exception as e:
        logger.error(f"Unexpected error creating social profile for contact {contact_id}: {e}")
        return RedirectResponse(url=f"/contacts/{contact_id}/detail", status_code=302)

# API v1 routes will be registered here
from app.api.v1 import groups, social_profiles, shared_content

app.include_router(groups.router, prefix=f"{settings.api_v1_prefix}/groups", tags=["groups"])
# Temporarily disabled due to permission issue: app.include_router(contacts.router, prefix=settings.api_v1_prefix, tags=["contacts"])
app.include_router(social_profiles.router, prefix=f"{settings.api_v1_prefix}/social-profiles", tags=["social-profiles"])
app.include_router(shared_content.router, prefix=f"{settings.api_v1_prefix}/shared-content", tags=["shared-content"])

# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    if request.url.path.startswith("/api/"):
        return {"error": "Resource not found"}, 404
    
    return templates.TemplateResponse(
        "404.html",
        {"request": request},
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {exc}")
    
    if request.url.path.startswith("/api/"):
        return {"error": "Internal server error"}, 500
    
    return templates.TemplateResponse(
        "500.html",
        {"request": request},
        status_code=500
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development
    )