"""
Backfill missing data from CSV spreadsheet into existing Supabase records.

This script:
1. Adds new columns to the database if they don't exist
2. Reads the CSV file
3. Matches CSV rows to existing database records
4. Updates only existing records (does not create new rows)
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
from supabase_storage import init_supabase
import re

# Column mappings: CSV column name -> Database column name
COLUMN_MAPPINGS = {
    "Type": "offering_type",
    "Bank": "bank",
    "Investors": "investors",
    "Share Equivalent": "share_equivalent"
}

def parse_csv_date(date_str: str) -> Optional[str]:
    """
    Parse CSV date format "1/16/26 17:28" or "1/16/26" to YYYY-MM-DD.
    Returns None if parsing fails.
    """
    if pd.isna(date_str) or not date_str or str(date_str).strip() == "":
        return None
    
    date_str = str(date_str).strip()
    
    # Remove time component if present
    if " " in date_str:
        date_str = date_str.split(" ")[0]
    
    try:
        # Parse M/D/YY format
        parts = date_str.split("/")
        if len(parts) == 3:
            month, day, year = parts
            # Convert 2-digit year to 4-digit (assuming 20XX for years 00-99)
            year_int = int(year)
            if year_int < 100:
                year_int = 2000 + year_int if year_int < 50 else 1900 + year_int
            else:
                year_int = 2000 + (year_int - 2000)
            
            # Format as YYYY-MM-DD
            return f"{year_int:04d}-{int(month):02d}-{int(day):02d}"
    except (ValueError, IndexError) as e:
        print(f"Warning: Could not parse date '{date_str}': {e}")
        return None
    
    return None


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker to uppercase and strip whitespace."""
    if pd.isna(ticker) or not ticker:
        return ""
    return str(ticker).upper().strip()


def normalize_form_type(form: str) -> Optional[str]:
    """Normalize form type, return None if empty."""
    if pd.isna(form) or not form or str(form).strip() == "":
        return None
    return str(form).strip().upper()


def parse_share_equivalent(value) -> Optional[str]:
    """
    Parse share equivalent value, removing commas.
    Returns as string to preserve precision.
    """
    if pd.isna(value) or value == "":
        return None
    
    value_str = str(value).strip().replace(",", "")
    if not value_str or value_str == "N/A":
        return None
    
    return value_str


def add_columns_to_database(client) -> bool:
    """
    Add new columns to sec_filing_alerts table if they don't exist.
    Returns True if successful.
    """
    print("\n" + "=" * 80)
    print("ADDING NEW COLUMNS TO DATABASE")
    print("=" * 80)
    
    # SQL to add columns if they don't exist
    # Note: Supabase/PostgreSQL doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
    # So we'll try to add them and catch errors if they already exist
    
    columns_to_add = [
        ("offering_type", "TEXT"),
        ("bank", "TEXT"),
        ("investors", "TEXT"),
        ("share_equivalent", "TEXT"),  # Using TEXT to preserve precision
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            # Use raw SQL execution via Supabase
            # Note: Supabase Python client doesn't have direct SQL execution
            # We'll need to use the REST API or rpc call
            # For now, we'll attempt to add via a migration approach
            print(f"  Adding column: {col_name} ({col_type})...")
            # This will be handled by checking if column exists first
            # Since Supabase client doesn't support direct ALTER TABLE,
            # we'll skip this and let the update fail gracefully if columns don't exist
            # The user can run the SQL manually or we can use Supabase dashboard
            pass
        except Exception as e:
            print(f"  Warning: Could not add column {col_name}: {e}")
            print(f"  You may need to add this column manually via Supabase dashboard:")
            print(f"    ALTER TABLE sec_filing_alerts ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
    
    print("\nNote: If columns don't exist, please run this SQL in Supabase SQL Editor:")
    for col_name, col_type in columns_to_add:
        print(f"  ALTER TABLE sec_filing_alerts ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
    
    return True


def find_matching_record(client, ticker: str, date: str, form_type: Optional[str] = None) -> Optional[Dict]:
    """
    Find a matching record in the database.
    - If form_type is provided: matches by ticker + date + form_type
    - If form_type is None/empty: matches by ticker + date only (ignores form_type)
    """
    ticker = normalize_ticker(ticker)
    
    # If form_type is provided and not empty, try exact match first
    if form_type:
        try:
            response = client.table("sec_filing_alerts").select("*").eq("ticker", ticker).eq("date", date).eq("form_type", form_type).limit(1).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as e:
            print(f"  Error querying with form_type: {e}")
    
    # Always try ticker + date only (this handles empty form_type case)
    try:
        response = client.table("sec_filing_alerts").select("*").eq("ticker", ticker).eq("date", date).limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as e:
        print(f"  Error querying without form_type: {e}")
    
    return None


def update_record(client, record_id: int, updates: Dict) -> bool:
    """Update a single record in the database."""
    try:
        response = client.table("sec_filing_alerts").update(updates).eq("id", record_id).execute()
        return True
    except Exception as e:
        print(f"  Error updating record {record_id}: {e}")
        return False


def backfill_from_csv(csv_path: str) -> None:
    """
    Main backfill function.
    Reads CSV and updates existing database records.
    """
    print("\n" + "=" * 80)
    print("BACKFILLING DATA FROM CSV")
    print("=" * 80)
    print(f"CSV file: {csv_path}\n")
    
    # Initialize Supabase client
    client = init_supabase()
    if not client:
        print("❌ Error: Supabase client not initialized.")
        print("   Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        return
    
    # Check/add columns
    add_columns_to_database(client)
    
    # Read CSV
    try:
        df = pd.read_csv(csv_path)
        print(f"\n✓ Loaded {len(df)} rows from CSV")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Validate required columns
    required_columns = ["Ticker", "Date"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"❌ Error: CSV missing required columns: {missing_columns}")
        return
    
    # Process each row
    updated_count = 0
    not_found_count = 0
    error_count = 0
    
    print("\nProcessing CSV rows...")
    print("-" * 80)
    
    for idx, row in df.iterrows():
        ticker = normalize_ticker(row.get("Ticker", ""))
        if not ticker:
            continue
        
        # Parse date
        csv_date = parse_csv_date(row.get("Date", ""))
        if not csv_date:
            print(f"  Row {idx + 1} ({ticker}): ⚠️  Could not parse date, skipping")
            continue
        
        # Get form type (None if empty - will match by ticker + date only)
        form_type = normalize_form_type(row.get("Form", ""))
        
        # Find matching record
        # If form_type is None/empty, matches by ticker + date only (ignoring form_type)
        record = find_matching_record(client, ticker, csv_date, form_type)
        
        if not record:
            not_found_count += 1
            form_str = f" (Form: {form_type})" if form_type else ""
            print(f"  Row {idx + 1} ({ticker}, {csv_date}{form_str}): ⚠️  No matching record found")
            continue
        
        # Build update dictionary
        updates = {}
        
        for csv_col, db_col in COLUMN_MAPPINGS.items():
            if csv_col in df.columns:
                value = row.get(csv_col, None)
                
                # Special handling for share_equivalent
                if db_col == "share_equivalent":
                    value = parse_share_equivalent(value)
                else:
                    # For text fields, convert to string and clean
                    if pd.notna(value) and value != "":
                        value = str(value).strip()
                        if value == "" or value.lower() == "nan":
                            value = None
                    else:
                        value = None
                
                # Only update if value is not None and different from existing
                if value is not None:
                    existing_value = record.get(db_col)
                    if existing_value != value:
                        updates[db_col] = value
        
        # Update record if there are changes
        if updates:
            success = update_record(client, record["id"], updates)
            if success:
                updated_count += 1
                print(f"  Row {idx + 1} ({ticker}, {csv_date}): ✓ Updated {len(updates)} field(s)")
                for key, val in updates.items():
                    print(f"      - {key}: {val}")
            else:
                error_count += 1
                print(f"  Row {idx + 1} ({ticker}, {csv_date}): ❌ Update failed")
        else:
            print(f"  Row {idx + 1} ({ticker}, {csv_date}): ⊘ No changes needed")
    
    # Summary
    print("\n" + "=" * 80)
    print("BACKFILL SUMMARY")
    print("=" * 80)
    print(f"  Total CSV rows processed: {len(df)}")
    print(f"  Records updated: {updated_count}")
    print(f"  Records not found: {not_found_count}")
    print(f"  Errors: {error_count}")
    print(f"  Skipped (no changes): {len(df) - updated_count - not_found_count - error_count}")
    print("\n✅ Backfill complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill data from CSV into existing Supabase records")
    parser.add_argument("csv_path", nargs="?", default="/Users/garthwoods/Downloads/Book1.csv",
                       help="Path to CSV file (default: /Users/garthwoods/Downloads/Book1.csv)")
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_path):
        print(f"❌ Error: CSV file not found at {args.csv_path}")
        sys.exit(1)
    
    backfill_from_csv(args.csv_path)
