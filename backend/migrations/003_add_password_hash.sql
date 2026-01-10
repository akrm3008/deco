-- Add password_hash column to users table for custom authentication
-- Execute this in Supabase SQL Editor

-- Remove email column (not needed for username/password auth)
ALTER TABLE users
DROP COLUMN IF EXISTS email;

DROP INDEX IF EXISTS idx_users_email;

-- Add password_hash for authentication
ALTER TABLE users
ADD COLUMN password_hash TEXT;

-- Make username unique for login
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
