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
templates = Jinja2Templates(directory=settings.templates_dir)

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

# API v1 routes will be registered here
from app.api.v1 import groups, contacts, social_profiles, shared_content

app.include_router(groups.router, prefix=f"{settings.api_v1_prefix}/groups", tags=["groups"])
app.include_router(contacts.router, prefix=settings.api_v1_prefix)
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