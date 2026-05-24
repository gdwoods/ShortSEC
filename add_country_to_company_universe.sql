-- Add country column to company_universe table
-- Run this in Supabase SQL Editor before running populate_company_universe.py

ALTER TABLE company_universe 
ADD COLUMN IF NOT EXISTS country TEXT;

-- Add index for faster country-based queries
CREATE INDEX IF NOT EXISTS idx_company_universe_country ON company_universe(country);

-- Add comment for documentation
COMMENT ON COLUMN company_universe.country IS 'Company country derived from SEC filings business address';
