-- Add columns for CSV backfill data
-- Run this in Supabase SQL Editor before running backfill_from_csv.py
-- 
-- Data types:
--   offering_type: TEXT (e.g., "Private Placement", "Underwritten", "RDO")
--   bank: TEXT (e.g., "Canaccord", "BofA", "Lucid")
--   investors: TEXT (comma-separated list, e.g., "R01 Fund, Framework Ventures")
--   share_equivalent: TEXT (stored as text to preserve formatting, e.g., "837,696,130")

ALTER TABLE sec_filing_alerts 
ADD COLUMN IF NOT EXISTS offering_type TEXT,
ADD COLUMN IF NOT EXISTS bank TEXT,
ADD COLUMN IF NOT EXISTS investors TEXT,
ADD COLUMN IF NOT EXISTS share_equivalent TEXT;

-- Add comments for documentation
COMMENT ON COLUMN sec_filing_alerts.offering_type IS 'Type of offering (e.g., Private Placement, Underwritten, RDO, etc.)';
COMMENT ON COLUMN sec_filing_alerts.bank IS 'Underwriting bank or financial institution';
COMMENT ON COLUMN sec_filing_alerts.investors IS 'List of investors participating in the offering (comma-separated)';
COMMENT ON COLUMN sec_filing_alerts.share_equivalent IS 'Total share equivalent for the offering (stored as text to preserve formatting)';
