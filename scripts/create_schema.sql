-- Advocacy CMS Database Schema
-- Version: 1.0
-- Description: Creates the cms_core schema and all required tables

-- Create schema
CREATE SCHEMA IF NOT EXISTS cms_core;

-- Set search path
SET search_path TO cms_core, public;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

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
    contact_id UUID REFERENCES contacts(contact_id) ON DELETE CASCADE NOT NULL,
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

-- Create indexes for performance
CREATE INDEX idx_contacts_email ON contacts(email) WHERE email IS NOT NULL;
CREATE INDEX idx_contacts_organization ON contacts(organization) WHERE organization IS NOT NULL;
CREATE INDEX idx_contacts_full_name ON contacts(lower(first_name || ' ' || last_name));
CREATE INDEX idx_contact_group_contact ON contact_group_memberships(contact_id);
CREATE INDEX idx_contact_group_group ON contact_group_memberships(group_id);
CREATE INDEX idx_social_profiles_contact ON social_profiles(contact_id);
CREATE INDEX idx_social_profiles_platform ON social_profiles(platform);
CREATE INDEX idx_shared_content_contact ON shared_content_log(contact_id) WHERE contact_id IS NOT NULL;
CREATE INDEX idx_shared_content_group ON shared_content_log(group_id) WHERE group_id IS NOT NULL;
CREATE INDEX idx_shared_content_shared_at ON shared_content_log(shared_at);

-- Create update triggers
CREATE TRIGGER update_groups_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_social_profiles_updated_at BEFORE UPDATE ON social_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_shared_content_log_updated_at BEFORE UPDATE ON shared_content_log
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Grant permissions (adjust as needed for your user)
GRANT ALL ON SCHEMA cms_core TO postgres;
GRANT USAGE ON SCHEMA cms_core TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA cms_core TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA cms_core TO postgres;

-- Add comments for documentation
COMMENT ON SCHEMA cms_core IS 'Core schema for Advocacy CMS application';
COMMENT ON TABLE groups IS 'Groups for organizing contacts (e.g., Union Activists, Tech Reporters)';
COMMENT ON TABLE contacts IS 'Individual contacts - activists, influencers, reporters';
COMMENT ON TABLE contact_group_memberships IS 'Many-to-many relationship between contacts and groups';
COMMENT ON TABLE social_profiles IS 'Social media profiles linked to contacts';
COMMENT ON TABLE shared_content_log IS 'Log of content shared with contacts or groups';

-- Verify schema creation
DO $$
BEGIN
    RAISE NOTICE 'Schema cms_core created successfully';
    RAISE NOTICE 'All tables and indexes created';
END $$;