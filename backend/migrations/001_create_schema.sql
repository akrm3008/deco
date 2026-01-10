-- Supabase PostgreSQL Schema Migration
-- Creates tables, enums, and indexes for Interior Design Agent

-- ============================================================
-- 1. Create Enum Types
-- ============================================================

CREATE TYPE room_type AS ENUM (
    'bedroom',
    'living_room',
    'kitchen',
    'bathroom',
    'office',
    'dining_room',
    'other'
);

CREATE TYPE preference_type AS ENUM (
    'style',
    'color',
    'warmth',
    'complexity',
    'lighting',
    'furniture',
    'material',
    'other'
);

-- ============================================================
-- 2. Create Tables
-- ============================================================

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Rooms table
CREATE TABLE rooms (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    room_type room_type NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Design versions table
CREATE TABLE design_versions (
    id UUID PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    selected BOOLEAN NOT NULL DEFAULT FALSE,
    rejected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    parent_version_id UUID REFERENCES design_versions(id) ON DELETE SET NULL,

    -- Ensure unique version numbers per room
    CONSTRAINT unique_version_per_room UNIQUE (room_id, version_number)
);

-- Design images table
CREATE TABLE design_images (
    id UUID PRIMARY KEY,
    design_version_id UUID NOT NULL REFERENCES design_versions(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    prompt TEXT NOT NULL,
    selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User preferences table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_type preference_type NOT NULL,
    preference_value TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. Create Indexes for Query Performance
-- ============================================================

-- Room queries
CREATE INDEX idx_rooms_user_created ON rooms(user_id, created_at DESC);

-- Design version queries
CREATE INDEX idx_design_versions_room_version ON design_versions(room_id, version_number ASC);

-- Design image queries
CREATE INDEX idx_design_images_version_created ON design_images(design_version_id, created_at ASC);

-- Preference queries
CREATE INDEX idx_preferences_user_confidence ON user_preferences(user_id, confidence DESC);
CREATE INDEX idx_preferences_lookup ON user_preferences(user_id, preference_type, preference_value);

-- ============================================================
-- 4. Enable Row Level Security (Optional)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE design_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE design_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create policies for service role (allow all operations)
CREATE POLICY "Enable all operations for service role" ON users
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON rooms
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON design_versions
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON design_images
    FOR ALL USING (true);

CREATE POLICY "Enable all operations for service role" ON user_preferences
    FOR ALL USING (true);
