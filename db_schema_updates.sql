-- Database schema updates to improve environment configuration
-- Add missing columns to GEE_ENV_CONFIG table

-- Add DB_USERNAME column if it doesn't exist
ALTER TABLE GEE_ENV_CONFIG ADD COLUMN DB_USERNAME TEXT;

-- Add DB_HOST column if it doesn't exist  
ALTER TABLE GEE_ENV_CONFIG ADD COLUMN DB_HOST TEXT;

-- Add LAST_TESTED column to track when connection was last tested
ALTER TABLE GEE_ENV_CONFIG ADD COLUMN LAST_TESTED DATETIME;

-- Update existing records to move DB_NAME to DB_USERNAME for Oracle connections
-- This fixes the current issue where DB_NAME is used as username for Oracle
UPDATE GEE_ENV_CONFIG 
SET DB_USERNAME = DB_NAME 
WHERE DB_TYPE = 'Oracle' AND DB_USERNAME IS NULL;

-- For SQLite, clear unnecessary fields that should not be used
UPDATE GEE_ENV_CONFIG 
SET DB_HOST = NULL, DB_PORT = NULL, DB_USERNAME = NULL, DB_INSTANCE = NULL 
WHERE DB_TYPE = 'SQLite';