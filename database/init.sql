-- Database initialization script for Toggl Client Reports
-- This script creates the initial database schema

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS toggl_reports;

-- Use the database
\c toggl_reports;

-- Create clients table
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    toggl_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    notes TEXT,
    external_reference VARCHAR(255),
    archived BOOLEAN DEFAULT FALSE,
    workspace_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    toggl_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    client_id INTEGER REFERENCES clients(id),
    workspace_id INTEGER NOT NULL,
    billable BOOLEAN DEFAULT FALSE,
    is_private BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    color VARCHAR(7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create members table
CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    toggl_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    workspace_id INTEGER NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create rates table (for hourly rates)
CREATE TABLE IF NOT EXISTS rates (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id),
    client_id INTEGER REFERENCES clients(id), -- NULL for default rate
    hourly_rate_usd DECIMAL(10, 2),
    hourly_rate_eur DECIMAL(10, 2),
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(member_id, client_id, effective_date)
);

-- Create time_entries cache table
CREATE TABLE IF NOT EXISTS time_entries_cache (
    id SERIAL PRIMARY KEY,
    toggl_id INTEGER UNIQUE NOT NULL,
    description TEXT,
    duration INTEGER NOT NULL, -- in seconds
    start_time TIMESTAMP NOT NULL,
    stop_time TIMESTAMP,
    user_id INTEGER NOT NULL,
    user_name VARCHAR(255),
    project_id INTEGER,
    project_name VARCHAR(255),
    client_id INTEGER,
    client_name VARCHAR(255),
    workspace_id INTEGER NOT NULL,
    billable BOOLEAN DEFAULT FALSE,
    tags TEXT[], -- PostgreSQL array of tags
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_date DATE DEFAULT CURRENT_DATE -- for tracking when data was last synced
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_clients_workspace_id ON clients(workspace_id);
CREATE INDEX IF NOT EXISTS idx_clients_toggl_id ON clients(toggl_id);

CREATE INDEX IF NOT EXISTS idx_projects_workspace_id ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);
CREATE INDEX IF NOT EXISTS idx_projects_toggl_id ON projects(toggl_id);

CREATE INDEX IF NOT EXISTS idx_members_workspace_id ON members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_members_toggl_id ON members(toggl_id);

CREATE INDEX IF NOT EXISTS idx_rates_member_id ON rates(member_id);
CREATE INDEX IF NOT EXISTS idx_rates_client_id ON rates(client_id);
CREATE INDEX IF NOT EXISTS idx_rates_effective_date ON rates(effective_date);

CREATE INDEX IF NOT EXISTS idx_time_entries_workspace_id ON time_entries_cache(workspace_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_user_id ON time_entries_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries_cache(project_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_client_id ON time_entries_cache(client_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_start_time ON time_entries_cache(start_time);
CREATE INDEX IF NOT EXISTS idx_time_entries_sync_date ON time_entries_cache(sync_date);
CREATE INDEX IF NOT EXISTS idx_time_entries_toggl_id ON time_entries_cache(toggl_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_clients_updated_at ON clients;
CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_members_updated_at ON members;
CREATE TRIGGER update_members_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_rates_updated_at ON rates;
CREATE TRIGGER update_rates_updated_at
    BEFORE UPDATE ON rates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_time_entries_cache_updated_at ON time_entries_cache;
CREATE TRIGGER update_time_entries_cache_updated_at
    BEFORE UPDATE ON time_entries_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for testing (optional)
-- This will be useful for initial testing without needing live Toggl data

-- Sample client
INSERT INTO clients (toggl_id, name, workspace_id, notes) 
VALUES (1, 'Sample Client', 1, 'This is a sample client for testing')
ON CONFLICT (toggl_id) DO NOTHING;

-- Sample member
INSERT INTO members (toggl_id, name, email, workspace_id) 
VALUES (1, 'Sample Member', 'sample@example.com', 1)
ON CONFLICT (toggl_id) DO NOTHING;

-- Sample default rate
INSERT INTO rates (member_id, client_id, hourly_rate_usd, hourly_rate_eur) 
VALUES (1, NULL, 75.00, 70.00)
ON CONFLICT (member_id, client_id, effective_date) DO NOTHING;

-- Sample client-specific rate
INSERT INTO rates (member_id, client_id, hourly_rate_usd, hourly_rate_eur) 
VALUES (1, 1, 90.00, 85.00)
ON CONFLICT (member_id, client_id, effective_date) DO NOTHING;