# GETTING STARTED: Advocacy CMS

## Prerequisites

Before starting, ensure you have the following installed:

- **Docker** - Check with `docker --version`
- **Docker Compose** - Check with `docker-compose --version`
- **Git** - For version control
- **Python 3.11+** (optional for local development) - Check with `python --version`
- **Make** (optional) - For simplified commands

## Quick Start with Docker (3 minutes)

```bash
# 1. Clone or create the project directory
mkdir advocacy-app && cd advocacy-app
git init

# 2. Copy environment configuration
cp .env.example .env

# 3. Generate a secure secret key
echo "SECRET_KEY=$(openssl rand -base64 32)" >> .env

# 4. Build and start the application
docker-compose up -d

# 5. Check that everything is running
docker-compose ps
docker-compose logs app

# 6. Access the application
# API Documentation: http://localhost:8000/docs
# Health Check: http://localhost:8000/health
# Main Application: http://localhost:8000/
```

## Quick Start for Local Development (5 minutes)

```bash
# 1. Clone or create the project directory
mkdir advocacy-app && cd advocacy-app
git init

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Create initial requirements.txt
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
jinja2==3.1.2
python-multipart==0.0.6
aiofiles==23.2.1
httpx==0.25.2
EOF

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file from example
cp .env.example .env

# 6. Generate secure secret key
python -c "import secrets; print(f'SECRET_KEY={secrets.token_urlsafe(32)}')" >> .env
```

## Detailed Setup Instructions

### Step 1: Database Setup

The application uses an external PostgreSQL database. The connection details are configured in the `.env` file.

#### Using Docker Compose (Recommended)
```bash
# The docker-compose.yml includes a db-init service that automatically:
# 1. Checks database connectivity
# 2. Creates the schema if it doesn't exist
# 3. Seeds initial data (if provided)

# Run database initialization
docker-compose run --rm db-init

# Or run everything at once
docker-compose up -d
```

#### Manual Database Setup
```bash
# Connect to the PostgreSQL instance
psql postgresql://postgres:aBmnBHPN8pCiQ82wtYMcJq34oDqiu7@100.101.93.9:5434/postgres

# Create the database if it doesn't exist
CREATE DATABASE advocacy_cms;

# Exit psql
\q

# Run the schema creation script
psql postgresql://postgres:aBmnBHPN8pCiQ82wtYMcJq34oDqiu7@100.101.93.9:5434/advocacy_cms -f scripts/create_schema.sql

# Verify schema creation
psql postgresql://postgres:aBmnBHPN8pCiQ82wtYMcJq34oDqiu7@100.101.93.9:5434/advocacy_cms -c "\dt cms_core.*"
```

### Step 2: Project Structure Creation

Create the following directory structure:
```bash
mkdir -p app/{api/v1,models,repositories,services,templates/{contacts,groups,shared},static/{css,js}}
mkdir -p tests/{unit,integration,e2e,fixtures}
mkdir -p scripts
```

### Step 3: Initialize Core Files

#### Create `app/__init__.py`:
```python
"""Advocacy CMS Application Package."""
__version__ = "1.0.0"
```

#### Create `app/config.py`:
```python
"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    # UI
    templates_dir: str = "app/templates"
    static_dir: str = "app/static"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

#### Create `app/database.py`:
```python
"""Database connection management."""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from app.config import settings

@contextmanager
def get_db_connection():
    """Get database connection."""
    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_db_cursor(commit=True):
    """Get database cursor with automatic commit."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

def test_connection():
    """Test database connectivity."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print("✓ Database connection successful")
        return result
```

#### Create `app/main.py`:
```python
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings

# Create FastAPI instance
app = FastAPI(
    title="Advocacy CMS",
    description="Contact Management System for Advocacy",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

# Setup templates
templates = Jinja2Templates(directory=settings.templates_dir)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint - redirects to dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")

# Register routers (will be added as features are implemented)
# from app.api.v1 import groups, contacts, social_profiles, shared_content
# app.include_router(groups.router, prefix=settings.api_v1_prefix)
# app.include_router(contacts.router, prefix=settings.api_v1_prefix)
```

### Step 4: Create Database Schema

Create `scripts/create_schema.sql`:
```sql
-- Create schema
CREATE SCHEMA IF NOT EXISTS cms_core;

-- Set search path
SET search_path TO cms_core, public;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create update trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = NEW.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Groups table
CREATE TABLE IF NOT EXISTS groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL
);

-- Contacts table
CREATE TABLE IF NOT EXISTS contacts (
    contact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone_number TEXT,
    organization TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL
);

-- Contact-Group relationships
CREATE TABLE IF NOT EXISTS contact_group_memberships (
    contact_id UUID REFERENCES contacts(contact_id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(group_id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    PRIMARY KEY (contact_id, group_id)
);

-- Social profiles
CREATE TABLE IF NOT EXISTS social_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(contact_id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN (
        'Twitter', 'BlueSky', 'LinkedIn', 'Facebook', 
        'Instagram', 'Threads', 'TikTok', 'RSS', 
        'Podcast', 'Website', 'Other'
    )),
    username_or_handle TEXT,
    profile_url TEXT NOT NULL,
    notes TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    UNIQUE(contact_id, profile_url)
);

-- Shared content log
CREATE TABLE IF NOT EXISTS shared_content_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES contacts(contact_id) ON DELETE SET NULL,
    group_id UUID REFERENCES groups(group_id) ON DELETE SET NULL,
    content_description TEXT NOT NULL,
    content_url_or_text TEXT,
    shared_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    pitch_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    CHECK (contact_id IS NOT NULL OR group_id IS NOT NULL)
);

-- Create indexes
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_organization ON contacts(organization);
CREATE INDEX idx_contact_group_contact ON contact_group_memberships(contact_id);
CREATE INDEX idx_contact_group_group ON contact_group_memberships(group_id);
CREATE INDEX idx_social_profiles_contact ON social_profiles(contact_id);
CREATE INDEX idx_shared_content_contact ON shared_content_log(contact_id);
CREATE INDEX idx_shared_content_group ON shared_content_log(group_id);

-- Create update triggers
CREATE TRIGGER update_groups_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_social_profiles_updated_at BEFORE UPDATE ON social_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Grant permissions (adjust as needed)
GRANT ALL ON SCHEMA cms_core TO postgres;
GRANT USAGE ON SCHEMA cms_core TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA cms_core TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA cms_core TO postgres;
```

### Step 5: Create Base Templates

Create `app/templates/base.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Advocacy CMS{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link href="{{ url_for('static', path='/css/custom.css') }}" rel="stylesheet">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">Advocacy CMS</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/dashboard">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/contacts">Contacts</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/groups">Groups</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Main Content -->
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Advocacy CMS v1.0 | Built with FastAPI & Bootstrap</span>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### Step 6: Run the Application

#### Using Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose build app
docker-compose up -d
```

#### Local Development
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the make command if you have a Makefile
make run-dev
```

## Verification Steps

After setup, verify everything is working:

### 1. Check Docker Services
```bash
# Check all containers are running
docker-compose ps

# Check application health
curl http://localhost:8000/health

# View application logs
docker-compose logs app
```

### 2. Test Database Connection
```bash
# Using Docker
docker-compose exec app python -c "from app.database import test_connection; test_connection()"

# Or directly
psql postgresql://postgres:aBmnBHPN8pCiQ82wtYMcJq34oDqiu7@100.101.93.9:5434/advocacy_cms -c "SELECT 1"
```

### 3. Access the Application
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Main Application: http://localhost:8000/

## Common Issues and Solutions

### Docker Issues
```bash
# Container not starting
docker-compose logs app
docker-compose down && docker-compose up -d

# Permission issues
# Ensure proper ownership
sudo chown -R $USER:$USER .

# Port already in use
# Check what's using port 8000
sudo lsof -i :8000
# Change port in docker-compose.yml if needed
```

### Database Connection Errors
```bash
# Check database connectivity
pg_isready -h 100.101.93.9 -p 5434

# Verify credentials in .env
cat .env | grep DATABASE_URL

# Test connection directly
psql postgresql://postgres:aBmnBHPN8pCiQ82wtYMcJq34oDqiu7@100.101.93.9:5434/advocacy_cms -c "SELECT 1"

# Check from within Docker container
docker-compose exec app psql $DATABASE_URL -c "SELECT 1"
```

### Import Errors
```bash
# Ensure virtual environment is activated
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Permission Errors
```bash
# Fix file permissions
chmod +x scripts/*.py
chmod -R 755 app/
```

## Next Steps

1. **Implement Groups Feature** (Phase 2 of IMPLEMENTATION_PLAN.md)
   ```bash
   # Start with Task 2.1: Group Pydantic Models
   # Follow the implementation plan step by step
   ```

2. **Run Progress Check**
   ```bash
   python scripts/check_progress.py
   ```

3. **Start Development Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Development Workflow

### Daily Development Cycle with Docker
```bash
# 1. Start your day
git pull origin main
docker-compose pull

# 2. Create feature branch
git checkout -b feature/implement-groups

# 3. Start Docker services
docker-compose up -d

# 4. Watch logs while developing
docker-compose logs -f app

# 5. Make changes following IMPLEMENTATION_PLAN.md
# (Docker will auto-reload due to volume mounts)

# 6. Test your changes
docker-compose exec app python scripts/validate_component.py groups
docker-compose exec app pytest tests/

# 7. Commit and push
git add .
git commit -m "feat: implement groups CRUD operations"
git push origin feature/implement-groups
```

### Daily Development Cycle (Local)
```bash
# 1. Start your day
source venv/bin/activate
git pull origin main

# 2. Create feature branch
git checkout -b feature/implement-groups

# 3. Run development server
uvicorn app.main:app --reload --host 0.0.0.0

# 4. Make changes following IMPLEMENTATION_PLAN.md

# 5. Test your changes
python scripts/validate_component.py groups
pytest tests/

# 6. Commit and push
git add .
git commit -m "feat: implement groups CRUD operations"
git push origin feature/implement-groups
```

### Useful Docker Commands

```bash
# Run tests in Docker
docker-compose exec app pytest

# Check code quality
docker-compose exec app python scripts/check_code_quality.py

# Validate specific component
docker-compose exec app python scripts/validate_component.py contact

# Check implementation progress
docker-compose exec app python scripts/check_progress.py

# Run health checks
docker-compose exec app python app/health_check.py

# Access container shell
docker-compose exec app /bin/bash

# View real-time logs
docker-compose logs -f app

# Restart services
docker-compose restart app

# Rebuild after requirements change
docker-compose build --no-cache app
```

### Useful Local Commands

```bash
# Run tests
pytest

# Check code quality
python scripts/check_code_quality.py

# Validate specific component
python scripts/validate_component.py contact

# Check implementation progress
python scripts/check_progress.py

# Run health checks
python app/health_check.py
```

## Support Resources

- **Project Documentation**: See PROJECT_ANALYSIS.md
- **Development Standards**: See CLAUDE.md
- **Implementation Guide**: See IMPLEMENTATION_PLAN.md
- **Testing Guide**: See TESTING_FRAMEWORK.md
- **MCP Setup**: See MCP_RECOMMENDATIONS.md

## Troubleshooting Checklist

- [ ] Python 3.11+ installed and active
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] PostgreSQL running and accessible
- [ ] Database schema created
- [ ] .env file configured correctly
- [ ] No import errors when running the app
- [ ] Can access http://localhost:8000/docs

If you encounter issues not covered here, check the logs:
```bash
# Application logs
tail -f app.log

# PostgreSQL logs (if using Docker)
docker logs advocacy-postgres

# Python traceback
python -m traceback app.main:app
```

Happy coding! 🚀