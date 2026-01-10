-- Add authentication fields to users table
-- Execute this in Supabase SQL Editor

-- Add email and username columns
ALTER TABLE users
ADD COLUMN email TEXT,
ADD COLUMN username TEXT;

-- Create index for fast email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Note: We don't add password_hash because Supabase Auth handles passwords
-- in its own auth.users table
