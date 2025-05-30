# PostgreSQL Database Creation Rules for Agents

## Overview
This document provides rules and guidelines for AI agents creating new databases in the PostgreSQL knowledge store system.

## Database Creation Rules

### 1. Database Naming Convention
- Use **lowercase_with_underscores** format
- Be descriptive but concise (e.g., `customer_analytics`, `document_store`)
- Avoid special characters except underscores
- Maximum 63 characters (PostgreSQL limit)

### 2. Required Database Configuration
```sql
CREATE DATABASE your_database_name WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;
```

### 3. Mandatory Extensions
After creating the database, enable these extensions:
```sql
\c your_database_name
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query statistics
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram text search
```

### 4. Required Schemas
Every database must have these schemas:
```sql
CREATE SCHEMA IF NOT EXISTS raw;       -- For incoming unprocessed data
CREATE SCHEMA IF NOT EXISTS processed; -- For cleaned/standardized data
CREATE SCHEMA IF NOT EXISTS archive;   -- For historical data
CREATE SCHEMA IF NOT EXISTS api;       -- For public views/functions
```

### 5. Standard Table Requirements
ALL tables must include these columns:
```sql
id BIGSERIAL PRIMARY KEY,
created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
version INTEGER DEFAULT 1 NOT NULL
```

### 6. User Permissions
Grant appropriate permissions:
```sql
-- Grant connect permission
GRANT CONNECT ON DATABASE your_database_name TO app_writer, app_reader, analyst;

-- Grant schema usage
GRANT USAGE ON SCHEMA raw, processed, archive, api TO app_writer, app_reader, analyst;

-- Set default privileges for new tables
ALTER DEFAULT PRIVILEGES IN SCHEMA raw, processed 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw, processed, archive, api 
    GRANT SELECT ON TABLES TO app_reader, analyst;
```

### 7. Create Update Trigger
Add this trigger to all tables:
```sql
-- First create the trigger function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Then apply to each table
CREATE TRIGGER update_[table_name]_updated_at
    BEFORE UPDATE ON [schema].[table_name]
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

### 8. Data Type Standards
Use these data types consistently:
- **Text**: Use `TEXT` (not VARCHAR with limits)
- **IDs**: Use `BIGSERIAL` for local IDs, `UUID` for distributed systems
- **Money**: Use `NUMERIC(19,4)` (never FLOAT)
- **Timestamps**: Always use `TIMESTAMPTZ` (never TIMESTAMP)
- **JSON**: Use `JSONB` (not JSON)
- **Booleans**: `BOOLEAN NOT NULL DEFAULT FALSE`

### 9. Index Requirements
- Create index on ALL foreign key columns
- Create index on columns used in WHERE clauses
- Use partial indexes for filtered queries
- Name indexes: `idx_tablename_columnname`

### 10. Database Connection Information

#### Connection Options
Agents can connect to the database using any of these endpoints:

1. **Direct Database Connections:**
   ```
   # Internal Docker network
   postgresql://postgres:changeme@postgres:5432/[database_name]
   
   # Local IP
   postgresql://postgres:changeme@localhost:5434/[database_name]
   
   # Tailscale network
   postgresql://postgres:changeme@db-swarm3.ts:5434/[database_name]
   ```

2. **PostgREST API Connection:**
   ```
   # REST API endpoint
   https://postgrest.onlyarag.com
   
   # Authentication header required:
   Authorization: Bearer [JWT_TOKEN]
   ```

#### Available Users and Roles
- **postgres** (superuser): Full database access
- **app_writer**: Read/write access to application schemas
- **app_reader**: Read-only access to all schemas
- **analyst**: Read-only access for data analysis
- **anon**: Anonymous role for PostgREST (limited access)

#### Authentication Details
- **Database Password**: `aBmnBHPN8pCiQ82wtYMcJq34oDqiu7` (update in production)
- **JWT Secret for PostgREST**: `TqsZvH2qvb76RHo5PqZu1g86Jx6XJoOf6n7cKa+AZpw=`
- **PostgREST Schemas**: `public,api`
- **PostgREST Anonymous Role**: `anon`

#### Service Endpoints
- **PostgreSQL Direct**: 
  - Internal: `postgres:5432`
  - External: `localhost:5434` or `db-swarm3.ts:5434`
- **PostgREST API**: 
  - Internal: `postgrest:3000`
  - External: `localhost:3001`
  - Public: `https://postgrest.onlyarag.com`

#### Connection String Examples
```bash
# Direct connection from within Docker network
psql postgresql://postgres:changeme@postgres:5432/main

# Direct connection from host machine
psql postgresql://postgres:changeme@localhost:5434/main

# Direct connection via Tailscale
psql postgresql://postgres:changeme@db-swarm3.ts:5434/main

# Using PostgREST API
curl -X GET https://postgrest.onlyarag.com/your_table \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Complete Example

Here's a complete example of creating a new database:

```sql
-- 1. Create the database
CREATE DATABASE customer_analytics WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TEMPLATE = template0;

-- 2. Connect to the new database
\c customer_analytics

-- 3. Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 4. Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS processed;
CREATE SCHEMA IF NOT EXISTS archive;
CREATE SCHEMA IF NOT EXISTS api;

-- 5. Create update function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. Create a sample table
CREATE TABLE raw.customer_events (
    id BIGSERIAL PRIMARY KEY,
    customer_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    source_system TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL
);

-- 7. Create indexes
CREATE INDEX idx_customer_events_customer_id ON raw.customer_events(customer_id);
CREATE INDEX idx_customer_events_event_type ON raw.customer_events(event_type);
CREATE INDEX idx_customer_events_created_at ON raw.customer_events(created_at);

-- 8. Create trigger
CREATE TRIGGER update_customer_events_updated_at
    BEFORE UPDATE ON raw.customer_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 9. Grant permissions
GRANT CONNECT ON DATABASE customer_analytics TO app_writer, app_reader, analyst;
GRANT USAGE ON SCHEMA raw, processed, archive, api TO app_writer, app_reader, analyst;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA raw TO app_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA raw, processed, archive, api TO app_reader, analyst;
```

## Important Notes for Agents

1. **Never use FLOAT for money** - Always use NUMERIC(19,4)
2. **Never use TIMESTAMP** - Always use TIMESTAMPTZ
3. **Always add the 4 required columns** to every table
4. **Always create indexes on foreign keys**
5. **Follow the naming convention** strictly
6. **Test your CREATE statements** before running in production
7. **Document your database purpose** in comments

## Validation Checklist

Before considering database creation complete:
- [ ] Database name follows convention
- [ ] All required extensions enabled
- [ ] All required schemas created
- [ ] All tables have the 4 required columns
- [ ] Update triggers created on all tables
- [ ] Indexes created on foreign keys
- [ ] Permissions granted appropriately
- [ ] Connection tested successfully